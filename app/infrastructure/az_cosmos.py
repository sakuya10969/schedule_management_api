import logging
import uuid
import time
from typing import Any
from fastapi import HTTPException
from dateutil.parser import parse
from azure.cosmos import CosmosClient, exceptions

from app.config.config import get_config
from app.interfaces.az_cosmos_interface import AzCosmosDBClientInterface

logger = logging.getLogger(__name__)

config = get_config()


class AzCosmosDBClient(AzCosmosDBClientInterface):
    def __init__(self):
        """Cosmos DB クライアント初期化"""
        try:
            self.cosmos_db_client = CosmosClient(
                config["AZ_COSMOS_DB_ENDPOINT"], config["AZ_COSMOS_DB_KEY"]
            )
            self.database = self.cosmos_db_client.create_database_if_not_exists(
                id=config["AZ_COSMOS_DB_NAME"]
            )
            self.container = self.database.create_container_if_not_exists(
                id=config["AZ_COSMOS_DB_CONTAINER_NAME"],
                partition_key={
                    "paths": [f"/{config['AZ_COSMOS_DB_PARTITION_KEY']}"],
                    "kind": "Hash",
                },
            )
            logger.info("Cosmos DB クライアントの初期化成功")
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Cosmos DB への接続エラー: {e}")
            raise HTTPException(status_code=503, detail="Cosmos DB サービス利用不可")
        except Exception as e:
            logger.error(f"Cosmos DB クライアントの初期化エラー: {e}")
            raise HTTPException(status_code=500, detail="Cosmos DB 初期化エラー")

    def create_form_data(self, payload: dict[str, Any]) -> str:
        """フォームデータをCosmos DBに保存する"""
        cosmos_db_id = str(uuid.uuid4())
        data = {
            "id": cosmos_db_id,
            "partitionKey": config["AZ_COSMOS_DB_PARTITION_KEY"],
            **payload,
        }
        try:
            self.container.create_item(body=data)
            logger.info("フォームデータを保存しました")
            return cosmos_db_id
        except exceptions.CosmosResourceExistsError:
            logger.error("重複するトークンが存在します")
            raise HTTPException(status_code=409, detail="Duplicate cosmos_db_id")
        except Exception as e:
            logger.error(f"フォームデータの保存エラー: {e}")
            raise HTTPException(status_code=500, detail="データ保存エラー")

    def get_form_data(self, cosmos_db_id: str) -> dict[str, Any]:
        """トークンからフォームデータを取得する"""
        try:
            item = self.container.read_item(
                item=cosmos_db_id, partition_key=config["AZ_COSMOS_DB_PARTITION_KEY"]
            )
            for key in ["_rid", "_self", "_etag", "_ts"]:
                item.pop(key, None)
            return item
        except exceptions.CosmosResourceNotFoundError:
            logger.error(f"トークンが見つかりません: {cosmos_db_id}")
            raise HTTPException(status_code=404, detail="トークンが見つかりません")
        except Exception as e:
            logger.error(f"フォームデータ取得エラー: {e}")
            raise HTTPException(status_code=500, detail="データ取得エラー")

    def update_form_data(
        self,
        cosmos_db_id: str,
        schedule_interview_datetime: str,
        event_ids: dict[str, str],
    ) -> None:
        """イベントIDをフォームデータに追加する"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                form = self.container.read_item(
                    item=cosmos_db_id,
                    partition_key=config["AZ_COSMOS_DB_PARTITION_KEY"],
                )
                form["schedule_interview_datetime"] = schedule_interview_datetime
                form["event_ids"] = event_ids
                self.container.replace_item(item=form["id"], body=form)
                return
            except exceptions.CosmosResourceNotFoundError:
                logger.error(f"更新対象のトークンが見つかりません: {cosmos_db_id}")
                raise HTTPException(status_code=404, detail="トークンが見つかりません")
            except exceptions.CosmosHttpResponseError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Cosmos DB 更新失敗: {e}")
                    raise HTTPException(status_code=500, detail="データ更新エラー")
                logger.warning(f"更新リトライ ({retry_count}/{max_retries})")
                time.sleep(2**retry_count)

    def remove_candidate_from_other_forms(
        self,
        selected_cosmos_db_id: str,
        selected_schedule_interview_datetime: list[str],
    ) -> None:
        """他のフォームから選択された候補日を削除"""
        try:
            query = """
            SELECT * FROM c 
            WHERE c.partitionKey = @partitionKey 
              AND c.id != @currentCosmosDbId
              AND ARRAY_CONTAINS(c.schedule_interview_datetimes, @selectedScheduleInterviewDatetime)
            """
            parameters = [
                {
                    "name": "@partitionKey",
                    "value": config["AZ_COSMOS_DB_PARTITION_KEY"],
                },
                {"name": "@currentCosmosDbId", "value": selected_cosmos_db_id},
                {
                    "name": "@selectedScheduleInterviewDatetime",
                    "value": selected_schedule_interview_datetime,
                },
            ]
            forms = list(self.container.query_items(query=query, parameters=parameters))

            for form in forms:
                updated_candidates = [
                    c
                    for c in form["schedule_interview_datetimes"]
                    if not (
                        parse(c[0]) == parse(selected_schedule_interview_datetime[0])
                        and parse(c[1])
                        == parse(selected_schedule_interview_datetime[1])
                    )
                ]
                form["candidates"] = updated_candidates
                for key in ["_rid", "_self", "_attachments", "_ts"]:
                    form.pop(key, None)
                self.container.replace_item(item=form["id"], body=form)
        except Exception as e:
            logger.error(f"候補日削除エラー: {e}")
            raise HTTPException(status_code=500, detail="候補日削除エラー")

    def confirm_form(self, cosmos_db_id: str) -> None:
        """フォームを確定状態に更新"""
        try:
            form = self.get_form_data(cosmos_db_id)
            form["is_confirmed"] = True
            self.container.replace_item(item=form["id"], body=form)
        except exceptions.CosmosResourceNotFoundError:
            logger.error(f"確定対象のトークンが見つかりません: {cosmos_db_id}")
            raise HTTPException(status_code=404, detail="トークンが見つかりません")
        except Exception as e:
            logger.error(f"フォーム確定エラー: {e}")
            raise HTTPException(status_code=500, detail="フォーム確定エラー")

    def finalize_form(
        self, cosmos_db_id: str, selected_schedule_interview_datetime: list[str]
    ) -> None:
        """フォームを確定し、他の候補日を削除"""
        try:
            self.remove_candidate_from_other_forms(
                cosmos_db_id, selected_schedule_interview_datetime
            )
            self.confirm_form(cosmos_db_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"フォーム最終確定エラー: {e}")
            raise HTTPException(status_code=500, detail="フォーム最終確定エラー")
        
    def delete_form_data(self, cosmos_db_id: str) -> None:
        """特定のCosmos DBレコードを削除する"""
        try:
            self.container.delete_item(
                item=cosmos_db_id,
                partition_key=config["AZ_COSMOS_DB_PARTITION_KEY"],
            )
            logger.info(f"Cosmos DBレコードを削除しました: {cosmos_db_id}")
        except exceptions.CosmosResourceNotFoundError:
            logger.warning(f"削除対象のトークンが見つかりません: {cosmos_db_id}")
            raise HTTPException(status_code=404, detail="削除対象が見つかりません")
        except Exception as e:
            logger.error(f"Cosmos DBレコード削除エラー: {e}")
            raise HTTPException(status_code=500, detail="削除中にエラーが発生しました")


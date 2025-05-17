import logging
import uuid
import time
from typing import Dict, List, Any
from fastapi import HTTPException
from dateutil.parser import parse
from azure.cosmos import CosmosClient, exceptions

from app.config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()
class AzCosmosDBClient:
    def __init__(self):
        """Cosmos DB クライアント初期化"""
        try:
            self.cosmos_db_client = CosmosClient(config['AZ_COSMOS_DB_ENDPOINT'], config['AZ_COSMOS_DB_KEY'])
            self.database = self.cosmos_db_client.create_database_if_not_exists(id=config['AZ_COSMOS_DB_NAME'])
            self.container = self.database.create_container_if_not_exists(
                id=config['AZ_COSMOS_DB_CONTAINER_NAME'],
                partition_key={"paths": [f"/{config['AZ_COSMOS_DB_PARTITION_KEY']}"], "kind": "Hash"}
            )
            logger.info("Cosmos DB クライアントの初期化成功")
        except Exception as e:
            logger.error(f"Cosmos DB クライアントの初期化に失敗: {e}")
            raise HTTPException(status_code=500, detail="Cosmos DB 初期化エラー")

    def create_form_data(self, payload: Dict[str, Any]) -> str:
        """フォームデータをCosmos DBに保存する"""
        token = str(uuid.uuid4())
        data = {"id": token, "partitionKey": config['AZ_COSMOS_DB_PARTITION_KEY'], **payload}
        try:
            self.container.create_item(body=data)
            logger.info("フォームデータを保存しました")
            return token
        except Exception as e:
            logger.error(f"フォームデータの保存に失敗: {e}")
            raise HTTPException(status_code=500, detail="Failed to store form data")

    def get_form_data(self, token: str) -> Dict[str, Any]:
        """トークンからフォームデータを取得する"""
        try:
            item = self.container.read_item(item=token, partition_key=config['AZ_COSMOS_DB_PARTITION_KEY'])
            for key in ["_rid", "_self", "_etag", "_ts"]:
                item.pop(key, None)
            logger.info("フォームデータを取得しました")
            return item
        except Exception as e:
            logger.error(f"トークンが見つかりません: {e}")
            raise HTTPException(status_code=404, detail="Token not found")

    def update_form_with_events(self, token: str, event_ids: Dict[str, str]) -> None:
        """イベントIDをフォームデータに追加する"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                form = self.container.read_item(item=token, partition_key=config['AZ_COSMOS_DB_PARTITION_KEY'])
                form["event_ids"] = event_ids
                self.container.replace_item(item=form["id"], body=form)
                logger.info("フォームデータを更新しました")
                return
            except exceptions.CosmosHttpResponseError as e:
                retry_count += 1
                logger.warning(f"Cosmos DB 更新リトライ中 ({retry_count}回目): {e}")
                if retry_count >= max_retries:
                    logger.error(f"Cosmos DB 更新に失敗: {e}")
                    raise
                time.sleep(2**retry_count)

    def remove_candidate_from_other_forms(self, selected_token: str, selected_candidate: List[str]) -> None:
        """他のフォームから選択された候補日を削除"""
        query = """
        SELECT * FROM c 
        WHERE c.partitionKey = @partitionKey 
          AND c.id != @currentToken
          AND ARRAY_CONTAINS(c.candidates, @selectedCandidate)
        """
        parameters = [
            {"name": "@partitionKey", "value": config['AZ_COSMOS_DB_PARTITION_KEY']},
            {"name": "@currentToken", "value": selected_token},
            {"name": "@selectedCandidate", "value": selected_candidate},
        ]
        forms = list(self.container.query_items(query=query, parameters=parameters))

        for form in forms:
            updated_candidates = [
                c for c in form["candidates"]
                if not (parse(c[0]) == parse(selected_candidate[0]) and parse(c[1]) == parse(selected_candidate[1]))
            ]
            form["candidates"] = updated_candidates
            for key in ["_rid", "_self", "_attachments", "_ts"]:
                form.pop(key, None)
            self.container.replace_item(item=form["id"], body=form)
            logger.info("候補日を削除しました")

    def confirm_form(self, token: str) -> None:
        """フォームを確定状態に更新"""
        try:
            form = self.get_form_data(token)
            form["isConfirmed"] = True
            self.container.replace_item(item=form["id"], body=form)
            logger.info("フォームを確定しました")
        except Exception as e:
            logger.error(f"フォームの確定に失敗しました: {e}")
            raise

    def finalize_form(self, token: str, selected_candidate: List[str]) -> None:
        """フォームを確定し、他の候補日を削除"""
        try:
            self.remove_candidate_from_other_forms(token, selected_candidate)
            self.confirm_form(token)
            logger.info("フォームを最終確定しました")
        except Exception as e:
            logger.error(f"フォームの最終確定に失敗しました: {e}")
            raise

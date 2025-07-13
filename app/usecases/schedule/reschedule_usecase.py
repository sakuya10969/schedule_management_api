import logging

from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.infrastructure.graph_api import GraphAPIClient
from app.config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()


async def reschedule_usecase(cosmos_db_id: str) -> None:
    """リスケジュール処理を行うユースケース"""
    try:
        cosmos_db_client = AzCosmosDBClient()
        form = cosmos_db_client.get_form_data(cosmos_db_id)

        # イベントの削除
        graph_api_client = GraphAPIClient()
        for user_email, event_id in form["event_ids"].items():
            try:
                graph_api_client.delete_event(user_email, event_id)
                logger.info(f"予定削除成功: {user_email} - {event_id}")
            except Exception as e:
                logger.error(f"予定削除失敗: {user_email} - {event_id}: {e}")
                raise

        # フォームのリセット
        form["is_confirmed"] = False
        form.pop("event_ids", None)
        cosmos_db_client.update_form_with_data(cosmos_db_id, form, None)

    except Exception as e:
        logger.error(f"リスケジュールユースケースエラー: {e}")
        raise

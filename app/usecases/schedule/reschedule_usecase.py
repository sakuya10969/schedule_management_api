import logging

from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.infrastructure.graph_api import GraphAPIClient
from app.infrastructure.appointment_repository import AppointmentRepository
from app.utils.formatting import parse_candidate
from app.config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()


async def reschedule_usecase(cosmos_db_id: str, schedule_interview_datetime: str) -> None:
    """リスケジュール処理を行うユースケース"""
    try:
        cosmos_db_client = AzCosmosDBClient()
        form = cosmos_db_client.get_form_data(cosmos_db_id)

        # CosmosDBのschedule_interview_datetimeを更新
        form["schedule_interview_datetime"] = schedule_interview_datetime
        cosmos_db_client.container.replace_item(item=form["id"], body=form)
        logger.info(f"CosmosDBの日時更新成功: {cosmos_db_id}")

        # DBのschedule_interview_datetimeを更新
        appointment_repository = AppointmentRepository()
        appointment_repository.update_schedule_interview_datetime(cosmos_db_id, schedule_interview_datetime)
        logger.info(f"DBの日時更新成功: {cosmos_db_id}")

        # Outlookカレンダーのイベント時刻を更新
        graph_api_client = GraphAPIClient()
        start_str, end_str, _ = parse_candidate(schedule_interview_datetime)
        
        for user_email, event_id in form["event_ids"].items():
            try:
                graph_api_client.update_event_time(user_email, event_id, start_str, end_str)
                logger.info(f"予定時刻更新成功: {user_email} - {event_id}")
            except Exception as e:
                logger.error(f"予定時刻更新失敗: {user_email} - {event_id}: {e}")
                raise

        # フォームのリセット
        form["is_confirmed"] = False
        cosmos_db_client.container.replace_item(item=form["id"], body=form)

    except Exception as e:
        logger.error(f"リスケジュールユースケースエラー: {e}")
        raise

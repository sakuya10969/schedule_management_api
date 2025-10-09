import logging

from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.infrastructure.graph_api import GraphAPIClient
from app.infrastructure.appointment_repository import AppointmentRepository
from app.schemas import FormData
from app.utils.slot import split_candidates
from app.config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()

class GetRescheduleDataUsecase:
    def __init__(self):
        self.cosmos_db_client = AzCosmosDBClient()
        self.graph_api_client = GraphAPIClient()
        self.appointment_repository = AppointmentRepository()

    async def execute(self, cosmos_db_id: str) -> FormData:
        """リスケジュール用のフォームデータを取得するユースケース"""
        try:
            form_data = self.cosmos_db_client.get_form_data(cosmos_db_id)
            form_data["schedule_interview_datetimes"] = split_candidates(
                form_data["schedule_interview_datetimes"], form_data["duration_minutes"]
            )

            return FormData(**form_data)

        except Exception as e:
            logger.error(f"リスケジュール用フォームデータが見つかりません: {e}")
            raise
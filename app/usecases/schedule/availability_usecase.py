import logging
from typing import Any

from app.schemas import ScheduleRequest, AvailabilityResponse
from app.infrastructure.graph_api import GraphAPIClient
from app.utils.time import time_string_to_float
from app.utils.availability import aggregate_user_availability, calculate_common_availability

logger = logging.getLogger(__name__)


class AvailabilityUsecase:
    def __init__(self):
        self.graph_api_client = GraphAPIClient()

    async def execute(
        self,
        schedule_req: ScheduleRequest,
    ) -> AvailabilityResponse:
        """ユーザーの空き時間を計算して返すユースケース"""
        logger.info(f"空き時間取得開始: {schedule_req}")
        try:
            schedule_info_list = self.graph_api_client.get_schedules(schedule_req)
            logger.info(f"スケジュール情報: {schedule_info_list}")
            common_times, slot_employees_map = self._calculate_common_times(schedule_req, schedule_info_list)
            logger.info(f"空き時間: {common_times}")
            logger.info(f"各スロットの参加者リスト: {slot_employees_map}")
            return AvailabilityResponse(common_availability=common_times, slot_employees_map=slot_employees_map)
        except Exception as e:
            logger.exception("空き時間取得ユースケースに失敗しました")
            raise


    def _calculate_common_times(
        self, schedule_req: ScheduleRequest, schedule_info_list: list[dict[str, Any]]
    ) -> tuple[list[list[str, str]], dict[str, list[str]]]:
        start_hour = time_string_to_float(schedule_req.start_time)
        end_hour = time_string_to_float(schedule_req.end_time)
        slot_duration = schedule_req.duration_minutes / 60.0

        date_user_slots, date_list = aggregate_user_availability(
            schedule_info_list,
            schedule_req.employee_emails,
            start_hour,
            end_hour,
            slot_duration,
            schedule_req.start_date,
            schedule_req.end_date,
        )
        logger.info(f"date_user_slots: {date_user_slots}")
        logger.info(f"date_list: {date_list}")

        common_availability, slot_employees_map = calculate_common_availability(
            date_user_slots,
            date_list,
            schedule_req.employee_emails,
            schedule_req.required_participants,
            schedule_req.duration_minutes,
            start_hour,
            end_hour,
        )
        return common_availability, slot_employees_map
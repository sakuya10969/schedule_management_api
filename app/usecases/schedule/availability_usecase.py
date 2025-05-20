import logging
from typing import Dict, List, Any, Tuple

from app.schemas import ScheduleRequest, AvailabilityResponse
from app.infrastructure.graph_api import GraphAPIClient
from app.utils.time import (
    time_string_to_float,
    find_common_availability_in_date_range,
    find_common_availability_participants_in_date_range,
    format_availability_result
)

logger = logging.getLogger(__name__)

async def get_availability_usecase(schedule_req: ScheduleRequest) -> AvailabilityResponse:
    """ユーザーの空き時間を計算して返すユースケース"""
    try:
        graph_api_client = GraphAPIClient()
        schedule_info = graph_api_client.get_schedules(schedule_req)
        common_times = _calculate_common_times(schedule_req, schedule_info)

        return AvailabilityResponse(common_availability=common_times)

    except Exception as e:
        logger.exception("空き時間取得ユースケースに失敗しました")
        raise


def parse_availability(schedule_data_list: List[Dict[str, Any]], start_hour: float, end_hour: float, slot_duration: float) -> List[List[Tuple[float, float]]]:
    """空き時間をパースする"""
    result = []

    for day_idx, schedule_data in enumerate(schedule_data_list):
        schedules_info = schedule_data.get("value", [])

        for sched_idx, schedule in enumerate(schedules_info):
            availability_view = schedule.get("availabilityView", "")

            free_slots = []
            for i, status in enumerate(availability_view):
                slot_start = start_hour + i * slot_duration
                slot_end = slot_start + slot_duration
                if slot_end > end_hour:
                    continue
                if status == "0":
                    free_slots.append((slot_start, slot_end))

            result.append(free_slots)

    return result


def _calculate_common_times(schedule_req: ScheduleRequest, schedule_info_list: List[Dict[str, Any]]) -> List[List[str]]:
    """共通の空き時間を計算"""
    start_hour = time_string_to_float(schedule_req.start_time)
    end_hour = time_string_to_float(schedule_req.end_time)
    slot_duration = schedule_req.duration_minutes / 60.0

    all_free_slots = []

    for i, schedule_info in enumerate(schedule_info_list):
        user_email = getattr(schedule_req.users[i], 'email', f'user_{i}')
        free_slots = parse_availability([schedule_info], start_hour, end_hour, slot_duration)
        all_free_slots.extend(free_slots)

    return _get_available_slots(schedule_req, all_free_slots)


def _get_available_slots(schedule_req: ScheduleRequest, free_slots_list: List[List[Tuple[float, float]]]) -> List[List[str]]:
    """必要人数に応じた空き時間を取得"""

    start_hour = time_string_to_float(schedule_req.start_time)
    end_hour = time_string_to_float(schedule_req.end_time)

    if len(schedule_req.users) == schedule_req.required_participants:
        available_slots = find_common_availability_in_date_range(
            free_slots_list=free_slots_list,
            duration_minutes=schedule_req.duration_minutes,
            start_date=schedule_req.start_date,
            end_date=schedule_req.end_date,
            start_hour=start_hour,
            end_hour=end_hour,
            required_participants=schedule_req.required_participants,
            users=schedule_req.users
        )
    else:
        available_slots = find_common_availability_participants_in_date_range(
            free_slots_list=free_slots_list,
            duration_minutes=schedule_req.duration_minutes,
            required_participants=schedule_req.required_participants,
            users=schedule_req.users,
            start_date=schedule_req.start_date,
            end_date=schedule_req.end_date,
            start_hour=start_hour,
            end_hour=end_hour
        )

    formatted_result = format_availability_result(available_slots)
    return formatted_result

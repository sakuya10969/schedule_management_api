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
        graph_client = GraphAPIClient()
        schedule_info = graph_client.get_schedules(schedule_req)
        common_times = _calculate_common_times(schedule_req, schedule_info)
        return AvailabilityResponse(common_availability=common_times)

    except Exception as e:
        logger.error(f"空き時間取得ユースケースに失敗しました: {e}")
        raise

def parse_availability(schedule_data: Dict[str, Any], start_hour: float, end_hour: float) -> List[List[Tuple[float, float]]]:
    """空き時間をパースする"""
    schedules_info = schedule_data.get("value", [])
    slot_duration = 0.5
    
    result = []
    for schedule in schedules_info:
        availability_view = schedule.get("availabilityView", "")
        free_slots = [
            (start_hour + i * slot_duration, start_hour + (i + 1) * slot_duration)
            for i, status in enumerate(availability_view)
            if status == "0" and start_hour + (i + 1) * slot_duration <= end_hour
        ]
        result.append(free_slots)
    
    return result

def _calculate_common_times(schedule_req: ScheduleRequest, schedule_info: Dict[str, Any]) -> List[List[str]]:
    """共通の空き時間を計算"""
    start_hour = time_string_to_float(schedule_req.start_time)
    end_hour = time_string_to_float(schedule_req.end_time)
    free_slots_list = parse_availability(schedule_info, start_hour, end_hour)

    return _get_available_slots(schedule_req, free_slots_list)

def _get_available_slots(schedule_req: ScheduleRequest, free_slots_list: List[List[str]]) -> List[List[str]]:
    """必要人数に応じた空き時間を取得"""
    start_hour = time_string_to_float(schedule_req.start_time)
    end_hour = time_string_to_float(schedule_req.end_time)

    if len(schedule_req.users) == schedule_req.required_participants:
        # 全員参加の場合
        available_slots = find_common_availability_in_date_range(
            free_slots_list=free_slots_list,
            duration_minutes=schedule_req.duration_minutes,
            start_date=schedule_req.start_date,
            end_date=schedule_req.end_date,
            start_hour=start_hour,
            end_hour=end_hour
        )
    else:
        # 一部参加の場合
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
    
    return format_availability_result(available_slots)

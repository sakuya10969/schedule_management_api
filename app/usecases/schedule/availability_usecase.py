import logging
from app.schemas import ScheduleRequest, AvailabilityResponse
from app.services.schedule_service import ScheduleService
from app.utils.time import (
    time_string_to_float,
    slot_to_time,
    find_common_availability,
    find_common_availability_participants,
)

logger = logging.getLogger(__name__)

async def get_availability_usecase(schedule_req: ScheduleRequest) -> AvailabilityResponse:
    """ユーザーの空き時間を計算して返すユースケース"""
    try:
        schedule_service = ScheduleService()
        schedule_info = schedule_service.get_schedules(schedule_req)
        common_times = _calculate_common_times(schedule_req, schedule_info)
        return AvailabilityResponse(common_availability=common_times)

    except Exception as e:
        logger.error(f"空き時間取得ユースケースに失敗しました: {e}")
        raise

def _calculate_common_times(schedule_req: ScheduleRequest, schedule_info: dict) -> list:
    """共通の空き時間を計算"""
    schedule_service = ScheduleService()
    start_hour = time_string_to_float(schedule_req.start_time)
    end_hour = time_string_to_float(schedule_req.end_time)
    free_slots_list = schedule_service.parse_availability(schedule_info, start_hour, end_hour)

    datetime_tuples = _get_datetime_tuples(schedule_req, free_slots_list)
    return _format_datetime_tuples(datetime_tuples)

def _get_datetime_tuples(schedule_req: ScheduleRequest, free_slots_list: list) -> list:
    """必要人数に応じた空き時間を取得"""
    if len(schedule_req.users) == schedule_req.required_participants:
        common_slots = find_common_availability(free_slots_list, schedule_req.duration_minutes)
        return slot_to_time(schedule_req.start_date, common_slots)
    else:
        common_slots_users = find_common_availability_participants(
            free_slots_list,
            schedule_req.duration_minutes,
            schedule_req.required_participants,
            schedule_req.users,
        )
        return [
            slot_to_time(schedule_req.start_date, common_slots) 
            for common_slots in common_slots_users
        ]

def _format_datetime_tuples(datetime_tuples: list) -> list:
    """datetimeオブジェクトを文字列に変換"""
    return [
        [dt1.strftime("%Y-%m-%dT%H:%M:%S"), dt2.strftime("%Y-%m-%dT%H:%M:%S")]
        for dt1, dt2 in datetime_tuples
    ]

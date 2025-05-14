import logging
from app.schemas import ScheduleRequest, AvailabilityResponse
from app.services.schedule_service import ScheduleService
from app.utils.time import time_string_to_float
from app.utils.availability import (
    find_common_availability_in_date_range,
    find_common_availability_participants_in_date_range,
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

    return _get_available_slots(schedule_req, free_slots_list)

def _get_available_slots(schedule_req: ScheduleRequest, free_slots_list: list) -> list:
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
        
        # 結果を整形
        result = []
        for date_str, slots in available_slots.items():
            for slot in slots:
                start_str, end_str = slot.split(" - ")
                start_hour = float(start_str)
                end_hour = float(end_str)
                
                # 日付と時間を組み合わせてdatetime文字列を作成
                start_dt = f"{date_str}T{int(start_hour):02d}:{int((start_hour % 1) * 60):02d}:00"
                end_dt = f"{date_str}T{int(end_hour):02d}:{int((end_hour % 1) * 60):02d}:00"
                
                result.append([start_dt, end_dt])
        
        return result
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
        
        # 結果を整形
        result = []
        for date_str, slots_with_users in available_slots.items():
            for slot, users in slots_with_users:
                start_str, end_str = slot.split(" - ")
                start_hour = float(start_str)
                end_hour = float(end_str)
                
                # 日付と時間を組み合わせてdatetime文字列を作成
                start_dt = f"{date_str}T{int(start_hour):02d}:{int((start_hour % 1) * 60):02d}:00"
                end_dt = f"{date_str}T{int(end_hour):02d}:{int((end_hour % 1) * 60):02d}:00"
                
                result.append([start_dt, end_dt])
        
        return result

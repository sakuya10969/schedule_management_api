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
        logger.info(f"空き時間計算開始: ユーザー数={len(schedule_req.users)}, 必要参加者数={schedule_req.required_participants}")
        graph_api_client = GraphAPIClient()
        schedule_info = graph_api_client.get_schedules(schedule_req)
        logger.info(f"取得したスケジュール情報数: {len(schedule_info)}")
        common_times = _calculate_common_times(schedule_req, schedule_info)
        logger.info(f"共通の空き時間数: {len(common_times)}")
        return AvailabilityResponse(common_availability=common_times)

    except Exception as e:
        logger.error(f"空き時間取得ユースケースに失敗しました: {e}")
        raise

def parse_availability(schedule_data_list: List[Dict[str, Any]], start_hour: float, end_hour: float, slot_duration: float) -> List[List[Tuple[float, float]]]:
    """空き時間をパースする"""
    result = []
    
    for schedule_data in schedule_data_list:
        schedules_info = schedule_data.get("value", [])
        logger.debug(f"スケジュール情報の数: {len(schedules_info)}")
        for schedule in schedules_info:
            availability_view = schedule.get("availabilityView", "")
            free_slots = [
                (start_hour + i * slot_duration, start_hour + (i + 1) * slot_duration)
                for i, status in enumerate(availability_view)
                if status == "0" and start_hour + (i + 1) * slot_duration <= end_hour
            ]
            logger.debug(f"空き時間スロット数: {len(free_slots)}")
            result.append(free_slots)
    
    return result

def _calculate_common_times(schedule_req: ScheduleRequest, schedule_info_list: List[Dict[str, Any]]) -> List[List[str]]:
    """共通の空き時間を計算"""
    start_hour = time_string_to_float(schedule_req.start_time)
    end_hour = time_string_to_float(schedule_req.end_time)
    slot_duration = schedule_req.duration_minutes / 60.0
    
    logger.info(f"共通時間計算開始: 開始時間={start_hour}, 終了時間={end_hour}, スロット時間={slot_duration}")
    
    # 各スケジュール情報から空き時間を取得
    all_free_slots = []
    for i, schedule_info in enumerate(schedule_info_list):
        logger.info(f"ユーザー {i+1} のスケジュール処理開始")
        free_slots = parse_availability([schedule_info], start_hour, end_hour, slot_duration)
        logger.info(f"ユーザー {i+1} の空き時間スロット数: {len(free_slots)}")
        all_free_slots.extend(free_slots)

    logger.info(f"全ユーザーの空き時間スロット合計: {len(all_free_slots)}")
    return _get_available_slots(schedule_req, all_free_slots)

def _get_available_slots(schedule_req: ScheduleRequest, free_slots_list: List[List[str]]) -> List[List[str]]:
    """必要人数に応じた空き時間を取得"""
    start_hour = time_string_to_float(schedule_req.start_time)
    end_hour = time_string_to_float(schedule_req.end_time)

    logger.info(f"空き時間スロット処理開始: 入力スロット数={len(free_slots_list)}")

    if len(schedule_req.users) == schedule_req.required_participants:
        logger.info("全員参加モードで処理")
        # 全員参加の場合
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
        logger.info(f"一部参加モードで処理: 必要参加者数={schedule_req.required_participants}")
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
    
    logger.info(f"最終的な空き時間スロット数: {len(available_slots)}")
    return format_availability_result(available_slots)

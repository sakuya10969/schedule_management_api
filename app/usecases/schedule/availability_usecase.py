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
    logger.info(f"空き時間取得開始: {schedule_req}")
    try:
        graph_api_client = GraphAPIClient()        
        schedule_info = graph_api_client.get_schedules(schedule_req)
        logger.debug(f"スケジュール情報取得完了: {len(schedule_info)}件")
        
        common_times = _calculate_common_times(schedule_req, schedule_info)
        logger.info(f"共通の空き時間計算完了: {len(common_times)}件の候補時間を特定")

        return AvailabilityResponse(common_availability=common_times)

    except Exception as e:
        logger.exception("空き時間取得ユースケースに失敗しました")
        raise

def parse_availability(schedule_data_list: List[Dict[str, Any]], start_hour: float, end_hour: float, slot_duration: float) -> List[List[Tuple[float, float]]]:
    """空き時間をパースする"""
    logger.debug(f"空き時間パース開始: データ数={len(schedule_data_list)}, 開始時刻={start_hour}, 終了時刻={end_hour}, スロット間隔={slot_duration}")
    result = []

    for day_idx, schedule_data in enumerate(schedule_data_list):
        schedules_info = schedule_data.get("value", [])
        logger.debug(f"日付インデックス{day_idx}のスケジュール情報処理中: {len(schedules_info)}件")

        for sched_idx, schedule in enumerate(schedules_info):
            availability_view = schedule.get("availabilityView", "")
            logger.debug(f"スケジュール{sched_idx}の可用性ビュー長: {len(availability_view)}")

            free_slots = []
            for i, status in enumerate(availability_view):
                slot_start = start_hour + i * slot_duration
                slot_end = slot_start + slot_duration
                if slot_end > end_hour:
                    continue
                if status == "0":
                    free_slots.append((slot_start, slot_end))
            
            logger.debug(f"空きスロット検出: {len(free_slots)}件")
            result.append(free_slots)

    logger.info(f"空き時間パース完了: 合計{len(result)}件の空きスロットリスト")
    return result

def _calculate_common_times(schedule_req: ScheduleRequest, schedule_info_list: List[Dict[str, Any]]) -> List[List[str]]:
    """共通の空き時間を計算"""
    start_hour = time_string_to_float(schedule_req.start_time)
    end_hour = time_string_to_float(schedule_req.end_time)
    slot_duration = schedule_req.duration_minutes / 60.0
    logger.debug(f"計算パラメータ: 開始={start_hour}, 終了={end_hour}, 間隔={slot_duration}")

    all_free_slots = []

    for i, schedule_info in enumerate(schedule_info_list):
        user_email = getattr(schedule_req.users[i], 'email', f'user_{i}')
        logger.debug(f"ユーザー {user_email} の空き時間を処理中")
        free_slots = parse_availability([schedule_info], start_hour, end_hour, slot_duration)
        logger.debug(f"ユーザー {user_email} の空きスロット数: {len(free_slots)}")
        all_free_slots.extend(free_slots)

    logger.info(f"全ユーザーの空きスロット合計: {len(all_free_slots)}件")
    return _get_available_slots(schedule_req, all_free_slots)

def _get_available_slots(schedule_req: ScheduleRequest, free_slots_list: List[List[Tuple[float, float]]]) -> List[List[str]]:
    """必要人数に応じた空き時間を取得"""
    logger.info(f"利用可能なスロットの計算開始: 必要参加者数={schedule_req.required_participants}")

    start_hour = time_string_to_float(schedule_req.start_time)
    end_hour = time_string_to_float(schedule_req.end_time)

    logger.debug("全員参加必須モードで計算実行")
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

    logger.debug(f"利用可能なスロット数: {len(available_slots)}")
    formatted_result = format_availability_result(available_slots)
    logger.info(f"最終的な候補時間数: {len(formatted_result)}")
    return formatted_result

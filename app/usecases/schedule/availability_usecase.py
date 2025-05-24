import logging
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from datetime import datetime

from app.schemas import ScheduleRequest, AvailabilityResponse
from app.infrastructure.graph_api import GraphAPIClient
from app.utils.time import (
    time_string_to_float,
    find_common_slots,
    format_slot_to_datetime_str
)

logger = logging.getLogger(__name__)

async def get_availability_usecase(schedule_req: ScheduleRequest) -> AvailabilityResponse:
    """ユーザーの空き時間を計算して返すユースケース"""
    logger.info(f"空き時間取得開始: {schedule_req}")
    try:
        graph_api_client = GraphAPIClient()
        schedule_info_list = graph_api_client.get_schedules(schedule_req)
        logger.debug(f"スケジュール情報取得完了: {len(schedule_info_list)}件")
        logger.info(f"スケジュール情報: {schedule_info_list}")
        common_times = _calculate_common_times(schedule_req, schedule_info_list)
        logger.info(f"共通の空き時間計算完了: {len(common_times)}件の候補時間を特定")
        return AvailabilityResponse(common_availability=common_times)
    except Exception as e:
        logger.exception("空き時間取得ユースケースに失敗しました")
        raise

def parse_availability(schedule_data: Dict[str, Any], start_hour: float, end_hour: float, slot_duration: float) -> List[Tuple[float, float]]:
    """1ユーザー・1日分の空き時間をパースする"""
    schedules_info = schedule_data.get("value", [])
    result: List[Tuple[float, float]] = []
    for schedule in schedules_info:
        availability_view = schedule.get("availabilityView", "")
        for i, status in enumerate(availability_view):
            slot_start = start_hour + i * slot_duration
            slot_end = slot_start + slot_duration
            if slot_end > end_hour:
                continue
            if status == "0":
                result.append((slot_start, slot_end))
    return result

def _calculate_common_times(schedule_req: ScheduleRequest, schedule_info_list: List[Dict[str, Any]]) -> List[List[str]]:
    start_hour = time_string_to_float(schedule_req.start_time)
    end_hour = time_string_to_float(schedule_req.end_time)
    slot_duration = schedule_req.duration_minutes / 60.0

    date_user_slots = defaultdict(list)
    user_count = len(schedule_req.users)
    date_list = []

    # 追加: 日付範囲の比較用
    start_date_dt = datetime.strptime(schedule_req.start_date, "%Y-%m-%d")
    end_date_dt = datetime.strptime(schedule_req.end_date, "%Y-%m-%d")

    for idx, schedule_info in enumerate(schedule_info_list):
        user_idx = idx % user_count
        free_slots = parse_availability(schedule_info, start_hour, end_hour, slot_duration)
        date = None
        for v in schedule_info.get("value", []):
            for item in v.get("scheduleItems", []):
                date = item["start"]["dateTime"][:10]
                break
            if date:
                break
        # ここで日付範囲チェック
        if date:
            date_dt = datetime.strptime(date, "%Y-%m-%d")
            if start_date_dt <= date_dt <= end_date_dt:
                date_user_slots[date].append(free_slots)
                if date not in date_list:
                    date_list.append(date)

    result = []
    for date in date_list:
        user_slots_list = date_user_slots[date]
        if not user_slots_list or len(user_slots_list) < schedule_req.required_participants:
            continue
        common_slots = find_common_slots(
            user_slots_list,
            schedule_req.users,
            schedule_req.required_participants,
            schedule_req.duration_minutes,
            start_hour,
            end_hour
        )
        for slot, _ in common_slots:
            start_dt, end_dt = format_slot_to_datetime_str(date, slot)
            result.append([start_dt, end_dt])
    return result

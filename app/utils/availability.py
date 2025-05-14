from typing import List, Tuple, Union, Dict
from datetime import datetime, timedelta
from app.utils.slot import find_continuous_slots, find_slots_with_participants

def _find_common_slots_for_date(
    free_slots_list: List[List[Tuple[float, float]]],
    duration_minutes: int,
    start_hour: float,
    end_hour: float
) -> List[str]:
    """指定された日付の指定時間帯における共通空き時間を探す"""
    # 各ユーザーの空き時間を指定時間帯でフィルタリング
    filtered_slots = []
    for user_slots in free_slots_list:
        filtered_user_slots = [
            slot for slot in user_slots
            if start_hour <= slot[0] and slot[1] <= end_hour
        ]
        filtered_slots.append(filtered_user_slots)

    if not filtered_slots:
        return []

    required_slots = duration_minutes // 30
    user_availability_sets = [set(slots) for slots in filtered_slots]
    common_slots = set.intersection(*user_availability_sets)
    sorted_slots = sorted(common_slots, key=lambda x: x[0])

    return find_continuous_slots(sorted_slots, required_slots)

def _find_common_slots_with_participants_for_date(
    free_slots_list: List[List[Tuple[float, float]]],
    duration_minutes: int,
    required_participants: int,
    users: List[Union[str, object]],
    start_hour: float,
    end_hour: float
) -> List[Tuple[str, List[str]]]:
    """指定された日付の指定時間帯における指定人数以上のユーザーが空いている共通時間帯を探す"""
    # 各ユーザーの空き時間を指定時間帯でフィルタリング
    filtered_slots = []
    for user_slots in free_slots_list:
        filtered_user_slots = [
            slot for slot in user_slots
            if start_hour <= slot[0] and slot[1] <= end_hour
        ]
        filtered_slots.append(filtered_user_slots)

    if not filtered_slots or required_participants <= 0:
        return []

    required_slots = (duration_minutes + 29) // 30
    return find_slots_with_participants(filtered_slots, users, required_participants, required_slots)

def find_common_availability_in_date_range(
    free_slots_list: List[List[Tuple[float, float]]], 
    duration_minutes: int,
    start_date: str,
    end_date: str,
    start_hour: float,
    end_hour: float
) -> Dict[str, List[str]]:
    """指定された日付範囲内で、各日付の指定時間帯における共通空き時間を探す"""
    if not free_slots_list:
        return {}

    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
    current_date = start_datetime
    result = {}

    while current_date <= end_datetime:
        current_date_str = current_date.strftime("%Y-%m-%d")
        common_slots = _find_common_slots_for_date(
            free_slots_list,
            duration_minutes,
            start_hour,
            end_hour
        )
        if common_slots:
            result[current_date_str] = common_slots
        current_date += timedelta(days=1)

    return result

def find_common_availability_participants_in_date_range(
    free_slots_list: List[List[Tuple[float, float]]], 
    duration_minutes: int, 
    required_participants: int, 
    users: List[Union[str, object]],
    start_date: str,
    end_date: str,
    start_hour: float,
    end_hour: float
) -> Dict[str, List[Tuple[str, List[str]]]]:
    """指定された日付範囲内で、各日付の指定時間帯における指定人数以上のユーザーが空いている共通時間帯を探す"""
    if not free_slots_list or required_participants <= 0:
        return {}

    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
    current_date = start_datetime
    result = {}

    while current_date <= end_datetime:
        current_date_str = current_date.strftime("%Y-%m-%d")
        common_slots = _find_common_slots_with_participants_for_date(
            free_slots_list,
            duration_minutes,
            required_participants,
            users,
            start_hour,
            end_hour
        )
        if common_slots:
            result[current_date_str] = common_slots
        current_date += timedelta(days=1)

    return result

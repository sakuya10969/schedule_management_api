from datetime import datetime, timedelta
from typing import List, Tuple, Union, Dict
import logging

logger = logging.getLogger(__name__)

def time_string_to_float(time_str: str) -> float:
    """'HH:MM' 形式の文字列を小数の時間数へ変換する"""
    hour, minute = map(int, time_str.split(":"))
    return hour + minute / 60.0

def parse_time_str_to_datetime(start_date: str, float_hour: float) -> datetime:
    """
    start_date : "YYYY-MM-DD" の形式
    float_hour: 例) 21.5 → 21時30分, 25.0 → 翌日1時0分 (24h超)
    戻り値: 上記に基づいて日付時刻を調整した datetime オブジェクト
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    day_offset = int(float_hour // 24)
    remainder_hours = float_hour % 24
    hour = int(remainder_hours)
    minute = int(round((remainder_hours - hour) * 60))
    new_date = start_dt + timedelta(days=day_offset)
    return datetime(new_date.year, new_date.month, new_date.day, hour, minute)

def parse_slot_str(slot_str: str) -> Tuple[float, float]:
    """'21.5 - 22.5' のような文字列をパースし、(start_hour, end_hour)を返す"""
    start_str, end_str = map(str.strip, slot_str.split("-"))
    return float(start_str), float(end_str)

def parse_slot(start_date: str, slot_str: str) -> Tuple[datetime, datetime]:
    """スロット文字列を開始・終了datetimeのタプルに変換"""
    start_hour, end_hour = parse_slot_str(slot_str)
    start_dt = parse_time_str_to_datetime(start_date, start_hour)
    end_dt = parse_time_str_to_datetime(start_date, end_hour)
    return start_dt, end_dt

def slot_to_time(start_date: str, slots: List[str]) -> List[Tuple[datetime, datetime]]:
    """スロットのリストをdatetimeタプルのリストに変換"""
    return [parse_slot(start_date, slot) for slot in slots]

def find_continuous_slots(slots: List[Tuple[float, float]], required_slots: int) -> List[str]:
    """連続する時間枠を見つける"""
    if not slots or required_slots <= 0:
        return []

    sorted_slots = sorted(slots, key=lambda x: x[0])
    continuous_groups = []
    current_group = [sorted_slots[0]]

    for i in range(1, len(sorted_slots)):
        if abs(current_group[-1][1] - sorted_slots[i][0]) < 1e-2:
            current_group.append(sorted_slots[i])
        else:
            if len(current_group) >= required_slots:
                continuous_groups.append(current_group)
            current_group = [sorted_slots[i]]

    if len(current_group) >= required_slots:
        continuous_groups.append(current_group)

    result = []
    for group in continuous_groups:
        for i in range(len(group) - required_slots + 1):
            start = group[i][0]
            end = group[i + required_slots - 1][1]
            result.append(f"{start} - {end}")

    return sorted(result, key=lambda x: float(x.split(" - ")[0]))

def find_common_slots(
    free_slots_list: List[List[Tuple[float, float]]],
    users: List[Union[str, object]],
    required_participants: int,
    required_slots: int,
    start_hour: float = 0.0,
    end_hour: float = 24.0
) -> List[Tuple[str, List[str]]]:
    """必要な参加者数を満たす連続スロットを見つける"""
    if not free_slots_list or required_participants <= 0:
        return []

    # スロットのフィルタリングと参加者の収集
    slot_users = {}
    for i, user_slots in enumerate(free_slots_list):
        user = users[i] if i < len(users) else f"User-{i}"
        filtered_slots = [
            slot for slot in user_slots
            if start_hour <= slot[0] and slot[1] <= end_hour
        ]
        for slot in filtered_slots:
            slot_users.setdefault(slot, []).append(user)

    # 必要人数を満たすスロットを抽出
    available_slots = [
        (slot, users) for slot, users in slot_users.items()
        if len(users) >= required_participants
    ]
    available_slots.sort(key=lambda x: x[0][0])

    if not available_slots:
        return []

    # 連続スロットの検出と結果の生成
    result = []
    current_window = []
    current_users = set()

    for slot, users in available_slots:
        if not current_window or abs(current_window[-1][0][1] - slot[0]) < 1e-2:
            current_window.append((slot, users))
            if len(current_window) == 1:
                current_users = set(users)
            else:
                current_users &= set(users)
        else:
            if len(current_window) >= required_slots and len(current_users) >= required_participants:
                start_slot = current_window[0][0]
                end_slot = current_window[-1][0]
                result.append((f"{start_slot[0]} - {end_slot[1]}", list(current_users)))
            current_window = [(slot, users)]
            current_users = set(users)

    if len(current_window) >= required_slots and len(current_users) >= required_participants:
        start_slot = current_window[0][0]
        end_slot = current_window[-1][0]
        result.append((f"{start_slot[0]} - {end_slot[1]}", list(current_users)))

    return result

def find_common_availability_in_date_range(
    free_slots_list: List[List[Tuple[float, float]]], 
    duration_minutes: int,
    start_date: str,
    end_date: str,
    start_hour: float,
    end_hour: float,
    required_participants: int = None,
    users: List[Union[str, object]] = None
) -> Dict[str, Union[List[str], List[Tuple[str, List[str]]]]]:
    """日付範囲内の共通空き時間を探す"""
    if not free_slots_list:
        return {}

    required_slots = (duration_minutes + 29) // 30
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    result = {}

    while start_dt <= end_dt:
        current_date = start_dt.strftime("%Y-%m-%d")
        
        if required_participants and users:
            slots = find_common_slots(
                free_slots_list,
                users,
                required_participants,
                required_slots,
                start_hour,
                end_hour
            )
        else:
            filtered_slots = []
            for user_slots in free_slots_list:
                filtered_user_slots = [
                    slot for slot in user_slots
                    if start_hour <= slot[0] and slot[1] <= end_hour
                ]
                filtered_slots.append(set(filtered_user_slots))
            
            if filtered_slots:
                common_slots = set.intersection(*filtered_slots)
                slots = find_continuous_slots(list(common_slots), required_slots)
            else:
                slots = []

        if slots:
            result[current_date] = slots
        start_dt += timedelta(days=1)

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
    """日付範囲内の必要参加者数を満たす共通空き時間を探す"""
    if not free_slots_list:
        return {}

    required_slots = (duration_minutes + 29) // 30
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    result = {}

    while start_dt <= end_dt:
        current_date = start_dt.strftime("%Y-%m-%d")
        slots = find_common_slots(
            free_slots_list,
            users,
            required_participants,
            required_slots,
            start_hour,
            end_hour
        )
        if slots:
            result[current_date] = slots
        start_dt += timedelta(days=1)

    return result

def format_slot_to_datetime_str(date_str: str, slot_str: str) -> Tuple[str, str]:
    """
    日付文字列とスロット文字列からISO形式のdatetime文字列を生成
    """
    start_hour, end_hour = parse_slot_str(slot_str)
    
    # 時間と分を計算
    start_hour_int = int(start_hour)
    start_minute = int((start_hour % 1) * 60)
    end_hour_int = int(end_hour)
    end_minute = int((end_hour % 1) * 60)
    
    # ISO形式のdatetime文字列を生成
    start_dt = f"{date_str}T{start_hour_int:02d}:{start_minute:02d}:00"
    end_dt = f"{date_str}T{end_hour_int:02d}:{end_minute:02d}:00"
    
    return start_dt, end_dt

def format_availability_result(
    available_slots: Dict[str, Union[List[str], List[Tuple[str, List[str]]]]]
) -> List[List[str]]:
    """
    空き時間の結果をdatetime文字列のリストに変換
    """
    result = []
    for date_str, slots in available_slots.items():
        if isinstance(slots[0], tuple):  # (slot, users)形式の場合
            for slot, _ in slots:
                start_dt, end_dt = format_slot_to_datetime_str(date_str, slot)
                result.append([start_dt, end_dt])
        else:  # スロット文字列のリストの場合
            for slot in slots:
                start_dt, end_dt = format_slot_to_datetime_str(date_str, slot)
                result.append([start_dt, end_dt])
    return result


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

def find_continuous_slots(slots: List[Tuple[float, float]], duration: float) -> List[str]:
    """指定された duration (時間単位) に満たす連続スロットを見つける（展開版）"""
    if not slots or duration <= 0:
        return []

    sorted_slots = sorted(slots, key=lambda x: x[0])
    result = []

    start = None
    end = None

    for slot in sorted_slots:
        if start is None:
            start, end = slot
        elif abs(end - slot[0]) < 1e-2:
            end = slot[1]
        else:
            result.extend(generate_subslots(start, end, duration))
            start, end = slot

    if start is not None:
        result.extend(generate_subslots(start, end, duration))

    return sorted(result, key=lambda x: float(x.split(" - ")[0]))

def generate_subslots(start: float, end: float, duration: float) -> List[str]:
    result = []
    current = start
    while current + duration <= end + 1e-6:
        result.append(f"{round(current, 2)} - {round(current + duration, 2)}")
        current += duration
    return result

def find_common_slots(
    free_slots_list: List[List[Tuple[float, float]]],
    users: List[Union[str, object]],
    required_participants: int,
    duration_minutes: int,
    start_hour: float = 0.0,
    end_hour: float = 24.0
) -> List[Tuple[str, List[str]]]:
    if not free_slots_list or required_participants <= 0:
        return []

    slot_users: Dict[Tuple[float, float], List[str]] = {}
    duration_hours = duration_minutes / 60.0

    for i, user_slots in enumerate(free_slots_list):
        user = users[i] if i < len(users) else f"User-{i}"
        filtered_slots = [
            slot for slot in user_slots
            if start_hour <= slot[0] and slot[1] <= end_hour
        ]
        for slot in filtered_slots:
            slot_users.setdefault(slot, []).append(user)

    available_slots = [slot for slot, user_list in slot_users.items() if len(user_list) >= required_participants]
    available_slots.sort(key=lambda x: x[0])

    continuous_ranges = find_continuous_slots(available_slots, duration_hours)

    result = [(r, []) for r in continuous_ranges]
    for idx, (range_str, _) in enumerate(result):
        start, end = map(float, range_str.split(" - "))
        participants = set(users)
        for i, user_slots in enumerate(free_slots_list):
            user = users[i] if i < len(users) else f"User-{i}"
            covered = any(s <= start and e >= end for s, e in user_slots)
            if not covered:
                participants.discard(user)
        result[idx] = (range_str, list(participants))

    return [r for r in result if len(r[1]) >= required_participants]

def find_common_availability_in_date_range(
    free_slots_list: List[List[Tuple[float, float]]], 
    duration_minutes: int,
    start_date: str,
    end_date: str,
    start_hour: float,
    end_hour: float,
    required_participants: int,
    users: List[Union[str, object]]
) -> Dict[str, Union[List[str], List[Tuple[str, List[str]]]]]:
    if not free_slots_list:
        return {}

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    result = {}

    while start_dt <= end_dt:
        current_date = start_dt.strftime("%Y-%m-%d")

        slots = find_common_slots(
            free_slots_list,
            users,
            required_participants,
            duration_minutes,
            start_hour,
            end_hour
        )

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

def split_candidates(candidates: List[List[str]], duration_minutes: int) -> List[List[str]]:
    """
    候補時間を指定した分単位でざっくり分割して返す
    """
    result = []

    for start, end in candidates:
        # ISO形式からdatetimeへ変換
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)

        # 開始・終了の差分を計算
        time_diff = (end_dt - start_dt).total_seconds() / 60

        # 特殊処理: 60分の場合かつ1時間半のケース
        if duration_minutes == 60 and time_diff == 90:
            # 最初の60分スロット
            first_end = start_dt + timedelta(minutes=60)
            result.append([
                start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                first_end.strftime("%Y-%m-%dT%H:%M:%S")
            ])
            # 次のスロット：30分ずらして60分
            second_start = start_dt + timedelta(minutes=30)
            result.append([
                second_start.strftime("%Y-%m-%dT%H:%M:%S"),
                end_dt.strftime("%Y-%m-%dT%H:%M:%S")
            ])
            continue

        # 通常の分割処理
        delta = timedelta(minutes=duration_minutes)
        current = start_dt
        while current < end_dt:
            next_time = min(current + delta, end_dt)
            result.append([
                current.strftime("%Y-%m-%dT%H:%M:%S"),
                next_time.strftime("%Y-%m-%dT%H:%M:%S")
            ])
            current = next_time

    return result

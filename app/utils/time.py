from datetime import datetime, timedelta
from typing import List, Tuple, Union, Dict, Any, Set
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

def time_string_to_float(time_str: str) -> float:
    """'HH:MM'形式の時刻文字列を小数時間に変換する (例: '13:30' -> 13.5)"""
    hour, minute = map(int, time_str.split(":"))
    return hour + minute / 60.0

def parse_time_str_to_datetime(start_date: str, float_hour: float) -> datetime:
    """日付文字列と小数時間から datetime オブジェクトを生成する"""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    day_offset = int(float_hour // 24)
    remainder_hours = float_hour % 24
    hour = int(remainder_hours)
    minute = int(round((remainder_hours - hour) * 60))
    new_date = start_dt + timedelta(days=day_offset)
    return datetime(new_date.year, new_date.month, new_date.day, hour, minute)

def parse_slot_str(slot_str: str) -> Tuple[float, float]:
    """時間範囲文字列を開始・終了時刻の小数タプルに変換する (例: '21.5 - 22.5' -> (21.5, 22.5))"""
    start_str, end_str = map(str.strip, slot_str.split("-"))
    return float(start_str), float(end_str)

def parse_slot(start_date: str, slot_str: str) -> Tuple[datetime, datetime]:
    """日付と時間範囲から開始・終了日時のタプルを生成する"""
    start_hour, end_hour = parse_slot_str(slot_str)
    start_dt = parse_time_str_to_datetime(start_date, start_hour)
    end_dt = parse_time_str_to_datetime(start_date, end_hour)
    return start_dt, end_dt

def slot_to_time(start_date: str, slots: List[str]) -> List[Tuple[datetime, datetime]]:
    """時間範囲のリストを datetime タプルのリストに変換する"""
    return [parse_slot(start_date, slot) for slot in slots]

def find_continuous_slots(slots: List[Tuple[float, float]], duration: float) -> List[str]:
    """指定された時間長に合致する連続した時間枠を抽出する"""
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
    """指定された時間範囲内で、指定時間長の部分時間枠を生成する"""
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
    """必要参加者数を満たす共通の空き時間を探索する"""
    if not free_slots_list or required_participants <= 0:
        return []

    EPS = 1e-6
    duration_hours = duration_minutes / 60.0
    slot_users: Dict[Tuple[float, float], Set[str]] = {}

    # スロットごとのユーザー割り当て
    for i, user_slots in enumerate(free_slots_list):
        user = users[i] if i < len(users) else f"User-{i}"
        for slot in user_slots:
            if start_hour <= slot[0] and slot[1] <= end_hour:
                slot_users.setdefault(slot, set()).add(user)

    # 必要人数を満たすスロットだけ抽出
    available_slots = [
        slot for slot, user_set in slot_users.items()
        if len(user_set) >= required_participants
    ]
    available_slots.sort(key=lambda x: x[0])

    # スロットの連結（連続時間を満たす範囲を抽出）
    continuous_ranges = find_continuous_slots(available_slots, duration_hours)

    # 最終チェック：その連続時間帯を本当にカバーできているユーザーだけ抽出
    result = []
    for range_str in continuous_ranges:
        start, end = map(float, range_str.split(" - "))
        participants = []
        for i, user_slots in enumerate(free_slots_list):
            user = users[i] if i < len(users) else f"User-{i}"
            if any(s - EPS <= start and e + EPS >= end for s, e in user_slots):
                participants.append(user)
        if len(participants) >= required_participants:
            result.append((range_str, participants))

    return result

def format_slot_to_datetime_str(date_str: str, slot_str: str) -> Tuple[str, str]:
    """時間枠を ISO 8601形式の日時文字列に変換する
    例: ('2023-10-01', '13.5 - 14.5') -> ('2023-10-01T13:30:00', '2023-10-01T14:30:00')
    """
    start_hour, end_hour = parse_slot_str(slot_str)
    # 日付をdatetimeオブジェクトに変換
    base_date = datetime.strptime(date_str, "%Y-%m-%d")
    # 開始時刻と終了時刻を計算
    start_dt = base_date + timedelta(hours=start_hour)
    end_dt = base_date + timedelta(hours=end_hour)

    return start_dt.isoformat(), end_dt.isoformat()

def format_availability_result(
    available_slots: Dict[str, Union[List[str], List[Tuple[str, List[str]]]]]
) -> List[List[str]]:
    """空き時間の結果を ISO 8601形式の日時文字列のリストに変換する
    ユーザー情報付きの時間枠と通常の時間枠の両方に対応
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
    """候補時間を指定された分単位で分割する
    60分の場合は1時間半の特殊ケースにも対応し、30分ずらしで2つの60分枠を生成
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

def aggregate_user_availability(
    schedule_info_list: List[Dict[str, Any]],
    start_hour: float,
    end_hour: float,
    slot_duration: float,
    start_date: str,
    end_date: str,
) -> Tuple[Dict[str, List[List[Tuple[float, float]]]], List[str]]:
    date_user_slots = defaultdict(list)
    date_list = []

    start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
    date_sequence = [
        (start_date_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range((end_date_dt - start_date_dt).days + 1)
    ]

    for schedule_info in schedule_info_list:
        for idx, v in enumerate(schedule_info.get("value", [])):
            if idx >= len(date_sequence):
                continue  # 念のため保険

            date = date_sequence[idx]  # ← リクエストした日付とインデックスで対応
            availability_view = v.get("availabilityView", "")
            if not availability_view:
                continue

            free_slots = []
            for i, status in enumerate(availability_view):
                slot_start = start_hour + i * slot_duration
                slot_end = slot_start + slot_duration
                if slot_end > end_hour:
                    continue
                if status == "0":
                    free_slots.append((slot_start, slot_end))

            if free_slots:
                date_user_slots[date].append(free_slots)
                if date not in date_list:
                    date_list.append(date)

    return date_user_slots, date_list

def calculate_common_availability(
    date_user_slots: Dict[str, List[List[Tuple[float, float]]]],
    date_list: List[str],
    users: List[Union[str, object]],
    required_participants: int,
    duration_minutes: int,
    start_hour: float,
    end_hour: float
) -> List[List[str]]:
    """日付ごとの共通の空き時間を計算する"""
    result = []
    for date in date_list:
        user_slots_list = date_user_slots[date]
        if not user_slots_list or len(user_slots_list) < required_participants:
            continue
        common_slots = find_common_slots(
            user_slots_list,
            users,
            required_participants,
            duration_minutes,
            start_hour,
            end_hour
        )
        for slot, _ in common_slots:
            start_dt, end_dt = format_slot_to_datetime_str(date, slot)
            result.append([start_dt, end_dt])
    return result

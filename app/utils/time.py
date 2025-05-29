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

def generate_subslots(start: float, end: float, duration: float) -> List[str]:
    """指定された時間範囲内で、指定時間長の部分時間枠を生成する"""
    result = []
    current = start
    while current + duration <= end + 1e-6:
        result.append(f"{round(current, 2)} - {round(current + duration, 2)}")
        current += duration
    return result

def find_continuous_slots(slots: List[Tuple[float, float]], duration: float) -> List[str]:
    """指定された時間長に合致する連続した時間枠を抽出する"""
    if not slots or duration <= 0:
        return []

    sorted_slots = sorted(slots, key=lambda x: x[0])
    result = []
    current_slot = None

    for slot in sorted_slots:
        if current_slot is None:
            current_slot = slot
        elif abs(current_slot[1] - slot[0]) < 1e-2:
            current_slot = (current_slot[0], slot[1])
        else:
            result.extend(generate_subslots(current_slot[0], current_slot[1], duration))
            current_slot = slot

    if current_slot is not None:
        result.extend(generate_subslots(current_slot[0], current_slot[1], duration))

    return sorted(result, key=lambda x: float(x.split(" - ")[0]))

def format_slot_to_datetime_str(date_str: str, slot_str: str) -> Tuple[str, str]:
    """時間枠を ISO 8601形式の日時文字列に変換する
    例: ('2023-10-01', '13.5 - 14.5') -> ('2023-10-01T13:30:00', '2023-10-01T14:30:00')
    """
    start_hour, end_hour = parse_slot_str(slot_str)
    base_date = datetime.strptime(date_str, "%Y-%m-%d")
    start_dt = base_date + timedelta(hours=start_hour)
    end_dt = base_date + timedelta(hours=end_hour)
    return start_dt.isoformat(), end_dt.isoformat()

def format_availability_result(
    available_slots: Dict[str, Union[List[str], List[Tuple[str, List[str]]]]]
) -> List[List[str]]:
    """空き時間の結果を ISO 8601形式の日時文字列のリストに変換する"""
    result = []
    for date_str, slots in available_slots.items():
        if isinstance(slots[0], tuple):
            result.extend([format_slot_to_datetime_str(date_str, slot) for slot, _ in slots])
        else:
            result.extend([format_slot_to_datetime_str(date_str, slot) for slot in slots])
    return [[start, end] for start, end in result]

def split_candidates(schedule_interview_datetimes: List[List[str]], duration_minutes: int) -> List[List[str]]:
    """候補時間を指定された分単位で分割する"""
    result = []

    for start, end in schedule_interview_datetimes:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        time_diff = (end_dt - start_dt).total_seconds() / 60

        if duration_minutes == 60 and time_diff == 90:
            first_end = start_dt + timedelta(minutes=60)
            second_start = start_dt + timedelta(minutes=30)
            result.extend([
                [start_dt.isoformat(), first_end.isoformat()],
                [second_start.isoformat(), end_dt.isoformat()]
            ])
            continue

        delta = timedelta(minutes=duration_minutes)
        current = start_dt
        while current < end_dt:
            next_time = min(current + delta, end_dt)
            result.append([current.isoformat(), next_time.isoformat()])
            current = next_time

    return result

def parse_availability(schedule_data: Dict[str, Any], start_hour: float, end_hour: float, slot_duration: float) -> List[Tuple[float, float]]:
    """1ユーザー・1日分の空き時間をパースする"""
    result = []
    for schedule in schedule_data.get("value", []):
        availability_view = schedule.get("availabilityView", "")
        for i, status in enumerate(availability_view):
            if status != "0":
                continue
            slot_start = start_hour + i * slot_duration
            slot_end = slot_start + slot_duration
            if slot_end <= end_hour:
                result.append((slot_start, slot_end))
    return result

def extract_email(val: Union[str, object]) -> str:
    """EmployeeEmail 型 or str から生アドレス文字列を取り出す"""
    return getattr(val, "email", val)

def find_common_slots(
    free_slots_list: List[List[Tuple[float, float]]],
    employee_emails: List[Union[str, object]],
    required_participants: int,
    duration_minutes: int,
    start_hour: float = 0.0,
    end_hour: float = 24.0,
) -> List[Tuple[str, List[str]]]:
    """必要参加者数を満たす共通の空き時間を探索する"""
    if not free_slots_list or required_participants <= 0:
        return []

    EPS = 1e-6
    duration_hours = duration_minutes / 60.0
    slot_users = defaultdict(set)

    for i, user_slots in enumerate(free_slots_list):
        user_email = extract_email(employee_emails[i]) if i < len(employee_emails) else f"Employee-{i}"
        for slot in user_slots:
            if start_hour <= slot[0] and slot[1] <= end_hour:
                slot_users[slot].add(user_email)

    available_slots = [
        slot for slot, users in slot_users.items() 
        if len(users) >= required_participants
    ]
    available_slots.sort(key=lambda x: x[0])

    continuous_ranges = find_continuous_slots(available_slots, duration_hours)
    result = []

    for range_str in continuous_ranges:
        start, end = map(float, range_str.split(" - "))
        participants = [
            extract_email(employee_emails[i]) if i < len(employee_emails) else f"Employee-{i}"
            for i, user_slots in enumerate(free_slots_list)
            if any(s - EPS <= start and e + EPS >= end for s, e in user_slots)
        ]
        if len(participants) >= required_participants:
            result.append((range_str, participants))

    return result

def aggregate_user_availability(
    schedule_info_list: List[Dict[str, Any]],
    employee_emails: List[Union[str, object]],
    start_hour: float,
    end_hour: float,
    slot_duration: float,
    start_date: str,
    end_date: str,
) -> Tuple[Dict[str, List[List[Tuple[float, float]]]], List[str]]:
    """Graph API 取得結果を date_user_slots に整理する"""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    date_seq = [
        (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range((end_dt - start_dt).days + 1)
    ]
    
    num_days = len(date_seq)
    num_users = len(employee_emails)
    date_user_slots = {
        d: [[] for _ in range(num_users)] for d in date_seq
    }
    email_to_idx = {extract_email(e): i for i, e in enumerate(employee_emails)}

    for idx, schedule_info in enumerate(schedule_info_list):
        day_idx = idx // num_users
        if day_idx >= num_days:
            break

        date = date_seq[day_idx]
        v_items = schedule_info.get("value", [])
        if not v_items:
            continue

        info = v_items[0]
        schedule_id = info.get("scheduleId", "")
        user_idx = email_to_idx.get(schedule_id)
        if user_idx is None:
            continue

        av_view = info.get("availabilityView", "")
        if not av_view:
            continue

        for i, flag in enumerate(av_view):
            if flag == "0":
                slot_start = start_hour + i * slot_duration
                slot_end = slot_start + slot_duration
                if slot_end <= end_hour:
                    date_user_slots[date][user_idx].append((slot_start, slot_end))

    return date_user_slots, date_seq

def calculate_common_availability(
    date_user_slots: Dict[str, List[List[Tuple[float, float]]]],
    date_list: List[str],
    employee_emails: List[Union[str, object]],
    required_participants: int,
    duration_minutes: int,
    start_hour: float,
    end_hour: float,
) -> List[List[str]]:
    """date_user_slots から [開始ISO, 終了ISO] のリストを返す"""
    result = []

    for date in date_list:
        user_slots_list = date_user_slots[date]
        active_users = [slots for slots in user_slots_list if slots]
        
        if len(active_users) < required_participants:
            continue

        common_slots = find_common_slots(
            user_slots_list,
            employee_emails,
            required_participants,
            duration_minutes,
            start_hour,
            end_hour,
        )

        for slot_str, _ in common_slots:
            start_dt, end_dt = format_slot_to_datetime_str(date, slot_str)
            result.append([start_dt, end_dt])

    return result

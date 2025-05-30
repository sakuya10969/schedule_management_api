from datetime import datetime, timedelta
from typing import Any, Dict, List, Set, Tuple, Union
from collections import defaultdict
import logging
import math

logger = logging.getLogger(__name__)

# 1. 時間文字列のパース関連
EPS: float = 1e-6  # 浮動小数点誤差許容
DateStr = str
HourFloat = float
Slot = Tuple[HourFloat, HourFloat]

def time_string_to_float(time_str: str) -> HourFloat:
    """'HH:MM' 形式の文字列を小数時間(float)に変換する。例: '13:30' → 13.5"""
    h, m = map(int, time_str.split(":"))
    return h + m / 60.0

def float_to_hm(hour_val: HourFloat) -> Tuple[int, int]:
    """小数時間(float)を (時, 分) のタプルに変換する。例: 13.5 → (13, 30)"""
    h = int(hour_val)
    m = int(round((hour_val - h) * 60))
    return h, m

def parse_time_str_to_datetime(date_str: DateStr, hour_val: HourFloat) -> datetime:
    """日付文字列と小数時間から tz-naive の datetime オブジェクトを生成する。例: ('2023-01-01', 13.5) → datetime(2023, 1, 1, 13, 30)"""
    base_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    day_offset, hour_remainder = divmod(hour_val, 24)
    h, m = float_to_hm(hour_remainder)
    return datetime(base_date.year, base_date.month, base_date.day, h, m) + timedelta(days=int(day_offset))

def parse_slot_str(slot: str) -> Slot:
    """'9.0 - 10.5' のようなスロット文字列を (float, float) のタプルに変換する。"""
    start, end = map(str.strip, slot.split("-"))
    return float(start), float(end)

def slot_to_datetime(date_str: DateStr, slot: Slot) -> Tuple[datetime, datetime]:
    """日付文字列とスロットタプルから、開始・終了の datetime タプルを返す。"""
    s, e = slot
    return parse_time_str_to_datetime(date_str, s), parse_time_str_to_datetime(date_str, e)

def slot_str_to_iso(date_str: DateStr, slot_str: str) -> Tuple[str, str]:
    """日付文字列とスロット文字列から、ISO8601形式の開始・終了時刻文字列を返す。"""
    s, e = parse_slot_str(slot_str)
    start_dt, end_dt = slot_to_datetime(date_str, (s, e))
    return start_dt.isoformat(), end_dt.isoformat()

# 2. スロット操作関連
def generate_subslots(start: HourFloat, end: HourFloat, length: HourFloat) -> List[str]:
    """[start, end] の範囲内で、長さ length の連続スロットをすべて列挙し、スロット文字列リストで返す。"""
    cur = start
    slots: List[str] = []
    while cur + length <= end + EPS:
        slots.append(f"{cur:.2f} - {(cur + length):.2f}")
        cur += length
    return slots

def merge_adjacent(slots: List[Slot]) -> List[Slot]:
    """隣接（端点一致）するスロットをマージする。前提: ソート済み。例: [(9.0, 10.0), (10.0, 11.0)] → [(9.0, 11.0)]"""
    if not slots:
        return []
    merged = [slots[0]]
    for s, e in slots[1:]:
        prev_s, prev_e = merged[-1]
        if math.isclose(prev_e, s, abs_tol=EPS):
            merged[-1] = (prev_s, e)
        else:
            merged.append((s, e))
    return merged

def find_continuous_slots(slots: List[Slot], length: HourFloat) -> List[str]:
    """必要な長さ length を満たす連続領域をスロット文字列で返す。例: [(9.0, 12.0)], 1.0 → ['9.00 - 10.00', '10.00 - 11.00', '11.00 - 12.00']"""
    cont: List[str] = []
    for merged_start, merged_end in merge_adjacent(sorted(slots, key=lambda x: x[0])):
        cont.extend(generate_subslots(merged_start, merged_end, length))
    return sorted(cont, key=lambda x: float(x.split(" - ")[0]))

def split_candidates(candidates: List[List[str]], length_min: int) -> List[List[str]]:
    """[[ISO, ISO]] のペアを length_min 分割する。60分枠で90分の区間が来た場合は 60+60-30 の特殊ロジックも踏襲。"""
    out: List[List[str]] = []
    delta = timedelta(minutes=length_min)

    for start_iso, end_iso in candidates:
        start_dt, end_dt = map(datetime.fromisoformat, (start_iso, end_iso))
        total_min = (end_dt - start_dt).total_seconds() / 60

        # 特殊ケース: 90分幅を 60+60-30 に分割 (採用ロジックそのまま)
        if length_min == 60 and math.isclose(total_min, 90, abs_tol=EPS):
            out.append([start_dt.isoformat(), (start_dt + delta).isoformat()])
            out.append([(start_dt + timedelta(minutes=30)).isoformat(), end_dt.isoformat()])
            continue

        cur = start_dt
        while cur < end_dt - EPS * timedelta(days=1):
            nxt = min(cur + delta, end_dt)
            out.append([cur.isoformat(), nxt.isoformat()])
            cur = nxt
    return out

# 3. 空き時間計算のコア機能
def extract_email(val: Union[str, object]) -> str:
    """オブジェクトまたは文字列からメールアドレスを抽出する。オブジェクトの場合は .email 属性を参照し、なければそのまま返す。"""
    return getattr(val, "email", val)

def _slot_users_map(
    free_slots_list: List[List[Slot]],
    employee_emails: List[Union[str, object]],
    start_hour: HourFloat,
    end_hour: HourFloat,
) -> Dict[Slot, Set[str]]:
    """各スロットごとに利用可能なユーザーのメールアドレスを集計する。"""
    mapping: Dict[Slot, Set[str]] = defaultdict(set)
    for idx, user_slots in enumerate(free_slots_list):
        mail = extract_email(employee_emails[idx]) if idx < len(employee_emails) else f"Employee-{idx}"
        for s, e in user_slots:
            if start_hour <= s and e <= end_hour:
                mapping[(s, e)].add(mail)
    return mapping

def _available_participants(
    slot_range: str,
    free_slots_list: List[List[Slot]],
    employee_emails: List[Union[str, object]],
) -> List[str]:
    """指定したスロット範囲に参加可能なユーザーのメールアドレスリストを返す。"""
    start, end = map(float, slot_range.split(" - "))
    participants: List[str] = []
    for idx, each_slots in enumerate(free_slots_list):
        if any(s - EPS <= start and end <= e + EPS for s, e in each_slots):
            participants.append(extract_email(employee_emails[idx]) if idx < len(employee_emails) else f"Employee-{idx}")
    return participants

def find_common_slots(
    free_slots_list: List[List[Slot]],
    employee_emails: List[Union[str, object]],
    required: int,
    duration_min: int,
    start_hour: HourFloat = 0.0,
    end_hour: HourFloat = 24.0,
) -> List[Tuple[str, List[str]]]:
    """指定した人数(required)が同時に参加可能なスロットを抽出し、スロット文字列と参加者リストのタプルリストで返す。"""
    if not free_slots_list or required <= 0:
        return []

    slot_users = _slot_users_map(free_slots_list, employee_emails, start_hour, end_hour)
    qualified_slots = [slot for slot, users in slot_users.items() if len(users) >= required]

    continuous = find_continuous_slots(qualified_slots, duration_min / 60.0)
    results: List[Tuple[str, List[str]]] = []

    for rng in continuous:
        members = _available_participants(rng, free_slots_list, employee_emails)
        if len(members) >= required:
            results.append((rng, members))
    return results

# 4. Graph API からの予定データ処理
def _date_sequence(start_date: DateStr, end_date: DateStr) -> List[DateStr]:
    """開始日と終了日から、日付文字列(YYYY-MM-DD)のリストを生成する。"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end - start).days + 1)]

def _process_schedule(
    schedule_info: Dict[str, Any],
    email_to_idx: Dict[str, int],
    date: DateStr,
    start_hour: HourFloat,
    end_hour: HourFloat,
    slot_dur: HourFloat,
    date_user_slots: Dict[DateStr, List[List[Slot]]],
) -> None:
    """Graph API のスケジュール情報から、各ユーザーの空きスロットを date_user_slots に格納する。"""
    values = schedule_info.get("value") or []
    if not values:
        return
    info = values[0]
    idx = email_to_idx.get(info.get("scheduleId", ""))
    if idx is None:
        return
    for i, flag in enumerate(info.get("availabilityView", "")):
        if flag != "0":
            continue
        s = start_hour + i * slot_dur
        e = s + slot_dur
        if e <= end_hour:
            date_user_slots[date][idx].append((s, e))

def aggregate_user_availability(
    schedule_info_list: List[Dict[str, Any]],
    employee_emails: List[Union[str, object]],
    start_hour: HourFloat,
    end_hour: HourFloat,
    slot_duration: HourFloat,
    start_date: DateStr,
    end_date: DateStr,
) -> Tuple[Dict[DateStr, List[List[Slot]]], List[DateStr]]:
    """各ユーザー・各日付ごとの空きスロット情報を集計し、日付リストとともに返す。"""
    dates = _date_sequence(start_date, end_date)
    date_user_slots: Dict[DateStr, List[List[Slot]]] = {d: [[] for _ in employee_emails] for d in dates}
    email_to_idx = {extract_email(e): i for i, e in enumerate(employee_emails)}

    for idx, schedule_info in enumerate(schedule_info_list):
        day_idx, _ = divmod(idx, len(employee_emails))
        if day_idx >= len(dates):
            break
        _process_schedule(schedule_info, email_to_idx, dates[day_idx], start_hour, end_hour, slot_duration, date_user_slots)
    return date_user_slots, dates

def calculate_common_availability(
    date_user_slots: Dict[DateStr, List[List[Slot]]],
    date_list: List[DateStr],
    employee_emails: List[Union[str, object]],
    required: int,
    duration_min: int,
    start_hour: HourFloat,
    end_hour: HourFloat,
) -> List[List[str]]:
    """各日付ごとに、指定人数(required)が同時に参加可能な空き時間候補(ISO8601形式の開始・終了ペア)をリストで返す。"""
    final: List[List[str]] = []
    for date in date_list:
        user_slots = date_user_slots[date]
        if sum(1 for s in user_slots if s) < required:
            continue
        for rng, _ in find_common_slots(user_slots, employee_emails, required, duration_min, start_hour, end_hour):
            final.append(list(slot_str_to_iso(date, rng)))
    return final

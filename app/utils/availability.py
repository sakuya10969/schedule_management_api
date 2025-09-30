from collections import defaultdict
from typing import Any

from app.utils.time import date_sequence
from app.utils.time import slot_str_to_iso
from app.utils.slot import find_continuous_slots

# 空き時間の分析・計算・集計

def extract_email(val: str | object) -> str:
    """オブジェクトまたは文字列からメールアドレスを抽出する。オブジェクトの場合は .email 属性を参照し、なければそのまま返す。"""
    return getattr(val, "email", val)

def _slot_users_map(
    free_slots_list: list[list[tuple[float, float]]],
    employee_emails: list[str | object],
    start_hour: float,
    end_hour: float,
) -> dict[tuple[float, float], set[str]]:
    """各スロットごとに利用可能なユーザーのメールアドレスを集計する。"""
    mapping: dict[tuple[float, float], set[str]] = defaultdict(set)
    for idx, user_slots in enumerate(free_slots_list):
        mail = extract_email(employee_emails[idx]) if idx < len(employee_emails) else f"Employee-{idx}"
        for start, end in user_slots:
            if start_hour <= start and end <= end_hour:
                mapping[(start, end)].add(mail)
    return mapping

def _available_participants(
    slot_range: str,
    free_slots_list: list[list[tuple[float, float]]],
    employee_emails: list[str | object],
) -> list[str]:
    """指定したスロット範囲に参加可能なユーザーのメールアドレスリストを返す。"""
    start, end = map(float, slot_range.split(" - "))
    participants: list[str] = []
    for idx, each_slots in enumerate(free_slots_list):
        if any(s <= start and end <= e for s, e in each_slots):
            participants.append(extract_email(employee_emails[idx]) if idx < len(employee_emails) else f"Employee-{idx}")
    return participants

def find_common_slots(
    free_slots_list: list[list[tuple[float, float]]],
    employee_emails: list[str | object],
    required: int,
    duration_min: int,
    start_hour: float = 0.0,
    end_hour: float = 24.0,
) -> list[tuple[str, list[str]]]:
    """指定した人数(required)が同時に参加可能なスロットを抽出し、スロット文字列と参加者リストのタプルリストで返す。"""
    if not free_slots_list or required <= 0:
        return []

    slot_users = _slot_users_map(free_slots_list, employee_emails, start_hour, end_hour)
    qualified_slots = [slot for slot, users in slot_users.items() if len(users) >= required]

    continuous = find_continuous_slots(qualified_slots, duration_min / 60.0)
    results: list[tuple[str, list[str]]] = []

    for rng in continuous:
        members = _available_participants(rng, free_slots_list, employee_emails)
        if len(members) >= required:
            results.append((rng, members))
    return results

def parse_user_daily_slots(
    schedule_info: dict[str, Any],
    start_hour: float,
    end_hour: float,
    slot_dur: float,
) -> list[tuple[float, float]]:
    """1ユーザー・1日のスケジュール情報から空きスロットリストを返す（副作用なし）。"""
    slots: list[tuple[float, float]] = []
    values = schedule_info.get("value") or []
    if not values:
        return slots
    
    availability = values[0].get("availabilityView", "")
    for i, flag in enumerate(availability):
        if flag != "0":
            continue
        s = start_hour + i * slot_dur
        e = s + slot_dur
        if e <= end_hour:
            slots.append((s, e))
    return slots

def _group_schedule_by_email_date(
    schedule_info_list: list[dict[str, Any]],
    employee_emails: list[str | object],
    date_list: list[str],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Graph APIの結果をemail/date別に構造化する。"""
    email_date_map: dict[str, dict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
    
    # schedule_info_listは日付×ユーザー順に並んでいる前提で処理
    for idx, schedule_info in enumerate(schedule_info_list):
        day_idx, user_idx = divmod(idx, len(employee_emails))
        if day_idx >= len(date_list) or user_idx >= len(employee_emails):
            continue
        
        date = date_list[day_idx]
        email = extract_email(employee_emails[user_idx])
        email_date_map[email][date] = schedule_info
    
    return email_date_map

def aggregate_user_availability(
    schedule_info_list: list[dict[str, Any]],
    employee_emails: list[str | object],
    start_hour: float,
    end_hour: float,
    slot_duration: float,
    start_date: str,
    end_date: str,
) -> tuple[dict[str, list[list[tuple[float, float]]]], list[str]]:
    """各ユーザー・各日付ごとの空きスロット情報を集計し、日付リストとともに返す。"""
    date_list = date_sequence(start_date, end_date)
    date_user_slots: dict[str, list[list[tuple[float, float]]]] = {d: [[] for _ in employee_emails] for d in date_list}
    email_to_idx = {extract_email(e): i for i, e in enumerate(employee_emails)}
    
    # Graph APIの結果をemail/date別に構造化
    email_date_map = _group_schedule_by_email_date(schedule_info_list, employee_emails, date_list)
    
    # 各日付・各ユーザーに対してスロットを集計
    for date in date_list:
        for email_obj in employee_emails:
            email = extract_email(email_obj)
            schedule_info = email_date_map.get(email, {}).get(date)
            if not schedule_info:
                continue
            
            slots = parse_user_daily_slots(schedule_info, start_hour, end_hour, slot_duration)
            idx = email_to_idx[email]
            date_user_slots[date][idx].extend(slots)
    
    return date_user_slots, date_list

def calculate_common_availability(
    date_user_slots: dict[str, list[list[tuple[float, float]]]],
    date_list: list[str],
    employee_emails: list[str | object],
    required: int,
    duration_min: int,
    start_hour: float,
    end_hour: float,
) -> list[list[str]]:
    """各日付ごとに、指定人数(required)が同時に参加可能な空き時間候補(ISO8601形式の開始・終了ペア)をリストで返す。"""
    final: list[list[str]] = []
    for date in date_list:
        user_slots = date_user_slots[date]
        if sum(1 for s in user_slots if s) < required:
            continue
        for rng, _ in find_common_slots(user_slots, employee_emails, required, duration_min, start_hour, end_hour):
            final.append(list(slot_str_to_iso(date, rng)))
    return final

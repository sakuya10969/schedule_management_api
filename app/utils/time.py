from datetime import datetime, timedelta
from typing import List, Set, Tuple, Dict, Union, Optional

def time_string_to_float(time_str: str) -> float:
    """'HH:MM' 形式の文字列を小数の時間数へ変換する"""
    hour, minute = map(int, time_str.split(":"))
    return hour + minute / 60.0

def parse_time_str_to_datetime(start_date: str, float_hour: float) -> datetime:
    """日付文字列と時間数から datetime オブジェクトを生成する"""
    base_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    
    days = int(float_hour // 24)
    hours = int(float_hour % 24)
    minutes = int(round((float_hour % 1) * 60))
    
    target_date = base_date + timedelta(days=days)
    return datetime(
        target_date.year, 
        target_date.month, 
        target_date.day, 
        hours, 
        minutes
    )

def parse_slot(start_date: str, common_slot: str) -> Tuple[datetime, datetime]:
    """時間範囲文字列から開始・終了時刻を datetime で返す"""
    start_str, end_str = map(str.strip, common_slot.split("-"))
    start_hour, end_hour = float(start_str), float(end_str)
    
    return (
        parse_time_str_to_datetime(start_date, start_hour),
        parse_time_str_to_datetime(start_date, end_hour)
    )

def slot_to_time(start_date: str, common_slots: List[str]) -> List[Tuple[datetime, datetime]]:
    """スロット文字列リストを datetime タプルのリストに変換する"""
    return [parse_slot(start_date, slot) for slot in common_slots]

def find_continuous_slots(sorted_slots: List[Tuple[float, float]], required_slots: int) -> List[str]:
    """連続する時間枠を見つける"""
    if not sorted_slots:
        return []

    # 隣接スロットのグラフを構築
    adjacency = {slot: [] for slot in sorted_slots}
    
    for i in range(len(sorted_slots) - 1):
        curr_slot = sorted_slots[i]
        next_slot = sorted_slots[i + 1]
        
        if abs(curr_slot[1] - next_slot[0]) < 1e-2:
            adjacency[curr_slot].append(next_slot)
            adjacency[next_slot].append(curr_slot)

    # 連続コンポーネントを探索
    visited = set()
    components = []
    
    for slot in sorted_slots:
        if slot not in visited:
            component = []
            queue = [slot]
            visited.add(slot)
            
            while queue:
                current = queue.pop(0)
                component.append(current)
                
                for neighbor in adjacency[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
                        
            components.append(sorted(component, key=lambda x: x[0]))

    # 必要なスロット数を満たす時間帯を抽出
    result = []
    
    for component in components:
        for i in range(len(component) - required_slots + 1):
            start = component[i][0]
            end = component[i + required_slots - 1][1]
            result.append(f"{start} - {end}")

    return sorted(set(result), key=lambda x: float(x.split(" - ")[0]))

def find_slots_with_participants(
    free_slots_list: List[List[Tuple[float, float]]],
    users: List[Union[str, object]],
    required_participants: int,
    required_slots: int
) -> List[Tuple[str, List[str]]]:
    """必要な参加者数を満たす連続スロットを見つける"""
    if not free_slots_list or required_participants <= 0:
        return []

    # スロットごとの空きユーザーを収集
    slot_users = {}
    for i, user_slots in enumerate(free_slots_list):
        user = users[i] if i < len(users) else f"User-{i}"
        for slot in user_slots:
            if slot not in slot_users:
                slot_users[slot] = []
            slot_users[slot].append(user)

    # 必要人数を満たすスロットを抽出
    available_slots = sorted(
        [(slot, users) for slot, users in slot_users.items() if len(users) >= required_participants],
        key=lambda x: x[0][0]
    )

    if not available_slots:
        return []

    # 連続スロットをグループ化
    continuous_groups = []
    current_group = [available_slots[0]]
    
    for i in range(1, len(available_slots)):
        prev_slot = current_group[-1][0]
        curr_slot = available_slots[i][0]
        
        if abs(prev_slot[1] - curr_slot[0]) < 1e-2:
            current_group.append(available_slots[i])
        else:
            continuous_groups.append(current_group)
            current_group = [available_slots[i]]
            
    continuous_groups.append(current_group)

    # 有効な時間枠を抽出
    result = []
    for group in continuous_groups:
        if len(group) < required_slots:
            continue
            
        for i in range(len(group) - required_slots + 1):
            window = group[i:i + required_slots]
            common_users = set(user.email if hasattr(user, 'email') else user for user in window[0][1])
            
            for _, users_list in window[1:]:
                common_users &= set(user.email if hasattr(user, 'email') else user for user in users_list)
                
            if len(common_users) >= required_participants:
                start_slot = window[0][0]
                end_slot = window[-1][0]
                slot_str = f"{start_slot[0]} - {end_slot[1]}"
                result.append((slot_str, list(common_users)))

    return result

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

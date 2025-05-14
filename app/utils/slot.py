from typing import List, Tuple, Union

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
import math
from datetime import datetime, timedelta

# スロット操作（生成・マージ・分割・連続性検出）

def generate_subslots(start: float, end: float, length: float) -> list[str]:
    """[start, end] の範囲内で、長さ length の連続スロットをすべて列挙し、スロット文字列リストで返す。"""
    cur = start
    slots: list[str] = []
    while cur + length <= end:
        slots.append(f"{cur:.2f} - {(cur + length):.2f}")
        cur += length
    return slots

def merge_adjacent(slots: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """隣接（端点一致）するスロットをマージする。前提: ソート済み。例: [(9.0, 10.0), (10.0, 11.0)] → [(9.0, 11.0)]"""
    if not slots:
        return []
    merged = [slots[0]]
    for start, end in slots[1:]:
        prev_start, prev_end = merged[-1]
        if math.isclose(prev_end, start):
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))
    return merged

def find_continuous_slots(slots: list[tuple[float, float]], length: float) -> list[str]:
    """必要な長さ length を満たす連続領域をスロット文字列で返す。例: [(9.0, 12.0)], 1.0 → ['9.00 - 10.00', '10.00 - 11.00', '11.00 - 12.00']"""
    cont: list[str] = []
    for merged_start, merged_end in merge_adjacent(sorted(slots, key=lambda x: x[0])):
        cont.extend(generate_subslots(merged_start, merged_end, length))
    return sorted(cont, key=lambda x: float(x.split(" - ")[0]))

def split_candidates(candidates: list[list[str]], length_min: int) -> list[list[str]]:
    """[[ISO, ISO]] のペアを length_min 分割する。60分枠で90分の区間が来た場合は 60+60-30 の特殊ロジックも踏襲。"""
    out: list[list[str]] = []
    delta = timedelta(minutes=length_min)

    for start_iso, end_iso in candidates:
        start_datetime, end_datetime = map(datetime.fromisoformat, (start_iso, end_iso))
        total_min = (end_datetime - start_datetime).total_seconds() / 60

        # 特殊ケース: 90分幅を 60+60-30 に分割 (採用ロジックそのまま)
        if length_min == 60 and math.isclose(total_min, 90):
            out.append([start_datetime.isoformat(), (start_datetime + delta).isoformat()])
            out.append([(start_datetime + timedelta(minutes=30)).isoformat(), end_datetime.isoformat()])
            continue

        cur = start_datetime
        while cur < end_datetime:
            nxt = min(cur + delta, end_datetime)
            out.append([cur.isoformat(), nxt.isoformat()])
            cur = nxt
    return out

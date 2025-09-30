from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# 時間関連のユーティリティ（解析・変換・フォーマット）

def time_string_to_float(time: str) -> float:
    """'HH:MM' 形式の文字列を小数時間(float)に変換する。例: '13:30' → 13.5"""
    hour, minute = map(int, time.split(":"))
    return hour + minute / 60.0

def float_to_hm(hour_float: float) -> tuple[int, int]:
    """小数時間(float)を (時, 分) のタプルに変換する。例: 13.5 → (13, 30)"""
    hour = int(hour_float)
    minute = int((hour_float - hour) * 60 + 0.5)  # 明示的に四捨五入
    return hour, minute

def parse_time_str_to_datetime(date_str: str, hour_float: float) -> datetime:
    """日付文字列と小数時間から tz-naive の datetime オブジェクトを生成する。例: ('2023-01-01', 13.5) → datetime(2023, 1, 1, 13, 30)"""
    base_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    day_offset, hour_remainder = divmod(hour_float, 24)
    hour, minute = float_to_hm(hour_remainder)
    return datetime(base_date.year, base_date.month, base_date.day, hour, minute) + timedelta(days=int(day_offset))

def parse_slot_str(slot: str) -> tuple[float, float]:
    """'9.0 - 10.5' のようなスロット文字列を (float, float) のタプルに変換する。"""
    start, end = map(str.strip, slot.split("-"))
    return float(start), float(end)

def slot_to_datetime(date_str: str, slot: tuple[float, float]) -> tuple[datetime, datetime]:
    """日付文字列とスロットタプルから、開始・終了の datetime タプルを返す。"""
    start, end = slot
    return parse_time_str_to_datetime(date_str, start), parse_time_str_to_datetime(date_str, end)

def slot_str_to_iso(date_str: str, slot_str: str) -> tuple[str, str]:
    """日付文字列とスロット文字列から、ISO8601形式の開始・終了時刻文字列を返す。"""
    start, end = parse_slot_str(slot_str)
    start_datetime, end_datetime = slot_to_datetime(date_str, (start, end))
    return start_datetime.isoformat(), end_datetime.isoformat()

def date_sequence(start_date: str, end_date: str) -> list[str]:
    """開始日と終了日から、日付文字列(YYYY-MM-DD)のリストを生成する。"""
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
    return [(start_date_obj + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end_date_obj - start_date_obj).days + 1)]

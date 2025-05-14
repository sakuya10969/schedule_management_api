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

from datetime import datetime, timedelta

def time_string_to_float(time_str: str) -> float:
    """'HH:MM' 形式の文字列を小数の時間数へ変換する"""
    hour, minute = map(int, time_str.split(":"))
    return hour + minute / 60.0

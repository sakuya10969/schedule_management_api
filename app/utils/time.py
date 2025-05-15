from datetime import datetime, timedelta

def time_string_to_float(time_str: str) -> float:
    """'HH:MM' 形式の文字列を小数の時間数へ変換する"""
    hour, minute = map(int, time_str.split(":"))
    return hour + minute / 60.0

def parse_time_str_to_datetime(start_date: str, float_hour: float) -> datetime:
    """
    start_date : "YYYY-MM-DD" の形式
    float_hour: 例) 21.5 → 21時30分, 25.0 → 翌日1時0分 (24h超)
    戻り値: 上記に基づいて日付時刻を調整した datetime オブジェクト
    """
    # 1. 日付部分をパースして date オブジェクトに変換
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()  # date型

    # 2. float_hour の値から「何日先か」「何時何分か」を計算
    day_offset = int(float_hour // 24)  # 24H 以上の場合、翌日以降へ
    remainder_hours = float_hour % 24   # 24 で割った余り(0~23.999..)

    hour = int(remainder_hours)              # 時
    minute = int(round((remainder_hours - hour) * 60))  # 分 (小数点以下を分に変換)

    # 3. base_dt に day_offset 日足して (year, month, day, hour, minute) を datetime化
    new_date = start_dt + timedelta(days=day_offset)
    dt = datetime(new_date.year, new_date.month, new_date.day, hour, minute)
    return dt


def parse_slot(start_date: str, common_slot: str):
    """
    common_slot: "21.5 - 22.5" のような文字列をパースし、
                開始datetime, 終了datetime をタプルで返す
    """
    start_str, end_str = common_slot.split("-")
    start_str = start_str.strip()  # "21.5"
    end_str = end_str.strip()    # "22.5"

    # float に変換
    start_hour = float(start_str)
    end_hour = float(end_str)

    start_dt = parse_time_str_to_datetime(start_date, start_hour)
    end_dt = parse_time_str_to_datetime(start_date, end_hour)

    return start_dt, end_dt


def slot_to_time(start_date: str, common_slots: list) -> list:
    """
    文字列形式のスロット情報をdatetimeオブジェクトに変換する
    
    例：
     ['21.5 - 22.5', '22.0 - 23.0', '22.5 - 23.5', '23.0 - 24.0', 
     '23.5 - 24.5', '24.0 - 25.0', '24.5 - 25.5', '25.0 - 26.0', 
     '25.5 - 26.5', '26.0 - 27.0', '26.5 - 27.5', '27.0 - 28.0', 
     '27.5 - 28.5', '28.0 - 29.0', '28.5 - 29.5', '29.0 - 30.0', 
     '29.5 - 30.5', '30.0 - 31.0', '30.5 - 31.5', '31.0 - 32.0', 
     '31.5 - 32.5', '32.0 - 33.0', '32.5 - 33.5', '44.0 - 45.0', 
     '44.5 - 45.5', '45.0 - 46.0']
    """
    common_time_list = []
    for common_slot in common_slots:
        common_time_list.append(parse_slot(start_date, common_slot))
    
    return common_time_list


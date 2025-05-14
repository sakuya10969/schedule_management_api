import logging
from fastapi import HTTPException
from typing import List

from app.schemas import ScheduleRequest, FormData
from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.infrastructure.graph_api import GraphAPIClient
from app.utils.time import time_string_to_float
from app.utils.availability import find_common_availability_in_date_range

logger = logging.getLogger(__name__)

async def retrieve_form_data_usecase(token: str) -> FormData:
    """
    フォームデータを取得し、最新の空き時間を含めて返すユースケース
    """
    try:
        cosmos_db_client = AzCosmosDBClient()
        form_data = cosmos_db_client.get_form_data(token)
        
        if not form_data.get("isConfirmed", False):
            # ScheduleRequestを作成
            schedule_request = ScheduleRequest(
                start_date=form_data["start_date"],
                end_date=form_data["end_date"],
                start_time=form_data["start_time"],
                end_time=form_data["end_time"],
                selected_days=form_data["selected_days"],
                duration_minutes=form_data["duration_minutes"],
                users=form_data["users"],
                time_zone="Tokyo Standard Time",
            )
            form_data["candidates"] = _get_available_slots(schedule_request)

        return FormData(**form_data)

    except Exception as e:
        logger.error(f"フォームデータが見つかりません: {e}")
        raise HTTPException(status_code=404, detail="Token not found")

def _get_available_slots(schedule_request: ScheduleRequest) -> List[List[str]]:
    """空き時間スロットを取得して整形"""
    try:
        graph_api_client = GraphAPIClient()
        schedule_info = graph_api_client.get_schedules(
            target_user_email=schedule_request.users[0].email,
            body=schedule_request.model_dump()
        )

        start_hour = time_string_to_float(schedule_request.start_time)
        end_hour = time_string_to_float(schedule_request.end_time)
        
        # 新しい日付範囲対応の関数を使用
        available_slots = find_common_availability_in_date_range(
            free_slots_list=schedule_info,
            duration_minutes=schedule_request.duration_minutes,
            start_date=schedule_request.start_date,
            end_date=schedule_request.end_date,
            start_hour=start_hour,
            end_hour=end_hour
        )

        # 結果を整形
        result = []
        for date_str, slots in available_slots.items():
            for slot in slots:
                start_str, end_str = slot.split(" - ")
                start_hour = float(start_str)
                end_hour = float(end_str)
                
                # 日付と時間を組み合わせてdatetime文字列を作成
                start_dt = f"{date_str}T{int(start_hour):02d}:{int((start_hour % 1) * 60):02d}:00"
                end_dt = f"{date_str}T{int(end_hour):02d}:{int((end_hour % 1) * 60):02d}:00"
                
                result.append([start_dt, end_dt])

        return result

    except Exception as e:
        logger.error(f"空き時間の取得に失敗しました: {e}")
        return []

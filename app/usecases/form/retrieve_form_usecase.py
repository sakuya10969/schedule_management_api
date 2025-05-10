import logging
from fastapi import HTTPException

from app.schemas import ScheduleRequest, FormData
from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.infrastructure.graph_api import GraphAPIClient
from app.utils.time import (
    time_string_to_float,
    slot_to_time,
    find_common_availability,
)

logger = logging.getLogger(__name__)

async def retrieve_form_data_usecase(token: str) -> FormData:
    """
    フォームデータを取得し、最新の空き時間を含めて返すユースケース
    """
    try:
        form_data = _get_form_data(token)
        
        if not form_data.get("isConfirmed", False):
            schedule_request = _create_schedule_request(form_data)
            form_data["candidates"] = _get_available_slots(schedule_request)

        return FormData(**form_data)

    except Exception as e:
        logger.error(f"フォームデータが見つかりません: {e}")
        raise HTTPException(status_code=404, detail="Token not found")

def _get_form_data(token: str) -> dict:
    """Cosmos DBからフォームデータを取得"""
    cosmos_db_client = AzCosmosDBClient()
    return cosmos_db_client.get_form_data(token)

def _create_schedule_request(form_data: dict) -> ScheduleRequest:
    """フォームデータからScheduleRequestを作成"""
    return ScheduleRequest(
        start_date=form_data["start_date"],
        end_date=form_data["end_date"],
        start_time=form_data["start_time"],
        end_time=form_data["end_time"],
        selected_days=form_data["selected_days"],
        duration_minutes=form_data["duration_minutes"],
        users=form_data["users"],
        time_zone="Tokyo Standard Time",
    )

def _get_available_slots(schedule_request: ScheduleRequest) -> list:
    """空き時間スロットを取得して整形"""
    try:
        graph_api_client = GraphAPIClient()
        schedule_info = graph_api_client.get_schedules(
            target_user_email=schedule_request.users[0].email,
            body=schedule_request.model_dump()
        )

        start_hour = time_string_to_float(schedule_request.start_time)
        end_hour = time_string_to_float(schedule_request.end_time)
        
        free_slots_list = find_common_availability(schedule_info, start_hour, end_hour)
        common_times = slot_to_time(schedule_request.start_date, free_slots_list)

        return [
            [
                start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            ]
            for start_dt, end_dt in common_times
        ]

    except Exception as e:
        logger.error(f"空き時間の取得に失敗しました: {e}")
        return []

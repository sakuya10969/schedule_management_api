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
from app.utils.access_token import get_access_token

logger = logging.getLogger(__name__)

async def retrieve_form_data_usecase(access_token: str) -> FormData:
    """
    フォームデータを取得し、最新の空き時間を含めて返すユースケース
    """
    try:
        cosmos_db_client = AzCosmosDBClient()
        item = cosmos_db_client.get_form_data(access_token)

        if not item.get("isConfirmed", False):
            schedule_request = ScheduleRequest(
                start_date=item["start_date"],
                end_date=item["end_date"],
                start_time=item["start_time"],
                end_time=item["end_time"],
                selected_days=item["selected_days"],
                duration_minutes=item["duration_minutes"],
                users=item["users"],
                time_zone="Tokyo Standard Time",
            )

            try:
                graph_api_client = GraphAPIClient(access_token)
                schedule_info = graph_api_client.get_schedules(
                    target_user_email=schedule_request.users[0].email,
                    body=schedule_request.model_dump()
                )

                start_hour = time_string_to_float(schedule_request.start_time)
                end_hour = time_string_to_float(schedule_request.end_time)
                free_slots_list = find_common_availability(
                    schedule_info, start_hour, end_hour
                )
                common_times = slot_to_time(schedule_request.start_date, free_slots_list)

                formatted_candidates = [
                    [
                        start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                        end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    ]
                    for start_dt, end_dt in common_times
                ]

                item["candidates"] = formatted_candidates
            except Exception as e:
                logger.error(f"空き時間の取得に失敗しました: {e}")

        return FormData(**item)

    except Exception as e:
        logger.error(f"フォームデータが見つかりません: {e}")
        raise HTTPException(status_code=404, detail="Token not found")

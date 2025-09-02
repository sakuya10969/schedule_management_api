import logging
from fastapi import HTTPException
from typing import Any

from app.schemas import FormData, ScheduleRequest
from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.infrastructure.graph_api import GraphAPIClient
from app.utils.time import (
    split_candidates,
    time_string_to_float,
    aggregate_user_availability,
    calculate_common_availability,
)

logger = logging.getLogger(__name__)


async def retrieve_form_data_usecase(cosmos_db_id: str) -> FormData:
    """
    フォームデータを取得し、返すユースケース
    """
    try:
        cosmos_db_client = AzCosmosDBClient()
        form_data = cosmos_db_client.get_form_data(cosmos_db_id)
        
        # is_confirmedがfalseの場合、最新の空き時間を取得
        if not form_data.get("is_confirmed", True):
            logger.info("is_confirmedがfalseのため、最新の空き時間を取得します")
            
            # ScheduleRequestを構築
            schedule_req = ScheduleRequest(
                employee_emails=form_data["employee_emails"],
                start_date=form_data["start_date"],
                end_date=form_data["end_date"],
                start_time=form_data["start_time"],
                end_time=form_data["end_time"],
                duration_minutes=form_data["duration_minutes"],
                required_participants=form_data["required_participants"]
            )
            
            # 最新の空き時間を取得
            common_times = await _get_latest_availability(schedule_req)
            
            # フラット化して文字列リストに変換
            flattened_times = []
            for time_group in common_times:
                flattened_times.extend(time_group)
            
            form_data["schedule_interview_datetimes"] = flattened_times
        else:
            form_data["schedule_interview_datetimes"] = split_candidates(
                form_data["schedule_interview_datetimes"], form_data["duration_minutes"]
            )

        return FormData(**form_data)

    except Exception as e:
        logger.error(f"フォームデータが見つかりません: {e}")
        raise HTTPException(status_code=404, detail="AzCosmosId not found")


async def _get_latest_availability(schedule_req: ScheduleRequest) -> list[list[str]]:
    """最新の空き時間を取得する"""
    try:
        graph_api_client = GraphAPIClient()
        schedule_info_list = graph_api_client.get_schedules(schedule_req)
        logger.info(f"スケジュール情報: {schedule_info_list}")
        common_times = _calculate_common_times(schedule_req, schedule_info_list)
        logger.info(f"空き時間: {common_times}")
        return common_times
    except Exception as e:
        logger.exception("最新の空き時間取得に失敗しました")
        raise


def _calculate_common_times(
    schedule_req: ScheduleRequest, schedule_info_list: list[dict[str, Any]]
) -> list[list[str]]:
    start_hour = time_string_to_float(schedule_req.start_time)
    end_hour = time_string_to_float(schedule_req.end_time)
    slot_duration = schedule_req.duration_minutes / 60.0

    date_user_slots, date_list = aggregate_user_availability(
        schedule_info_list,
        schedule_req.employee_emails,
        start_hour,
        end_hour,
        slot_duration,
        schedule_req.start_date,
        schedule_req.end_date,
    )
    logger.info(f"date_user_slots: {date_user_slots}")
    logger.info(f"date_list: {date_list}")

    return calculate_common_availability(
        date_user_slots,
        date_list,
        schedule_req.employee_emails,
        schedule_req.required_participants,
        schedule_req.duration_minutes,
        start_hour,
        end_hour,
    )

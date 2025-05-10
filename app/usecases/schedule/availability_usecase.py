import logging
from app.schemas import ScheduleRequest, AvailabilityResponse
from app.infrastructure.graph_api import GraphAPIClient
from app.utils.time import (
    time_string_to_float,
    slot_to_time,
    find_common_availability,
    find_common_availability_participants,
)
from app.services.schedule_service import parse_availability
logger = logging.getLogger(__name__)

async def get_availability_usecase(schedule_req: ScheduleRequest) -> AvailabilityResponse:
    """
    ユーザーの空き時間を計算して返すユースケース
    """
    try:
        # Graph API クライアントの初期化
        graph_api_client = GraphAPIClient()
        
        # Graph APIを使ってスケジュール情報を取得
        schedule_info = graph_api_client.get_schedules(schedule_req.users[0].email, schedule_req.dict())
        logger.info(f"取得したスケジュール情報: {schedule_info}")
        
        # 時間範囲を浮動小数点に変換
        start_hour = time_string_to_float(schedule_req.start_time)
        end_hour = time_string_to_float(schedule_req.end_time)

        # 空き時間リストを解析
        free_slots_list = parse_availability(schedule_info, start_hour, end_hour)
        
        # 必要人数に応じて空き時間を抽出
        if len(schedule_req.users) == schedule_req.required_participants:
            # 全員が参加できる共通の空き時間を取得
            common_slots = find_common_availability(free_slots_list, schedule_req.duration_minutes)
            datetime_tuples = slot_to_time(schedule_req.start_date, common_slots)
        else:
            # 必要人数を満たす空き時間を取得
            common_slots_users = find_common_availability_participants(
                free_slots_list,
                schedule_req.duration_minutes,
                schedule_req.required_participants,
                schedule_req.users,
            )
            datetime_tuples = [
                slot_to_time(schedule_req.start_date, common_slots) for common_slots in common_slots_users
            ]

        # datetimeオブジェクトを文字列に変換
        common_times = [
            [dt1.strftime("%Y-%m-%dT%H:%M:%S"), dt2.strftime("%Y-%m-%dT%H:%M:%S")]
            for dt1, dt2 in datetime_tuples
        ]

        # 空き時間レスポンスとして返却
        return AvailabilityResponse(common_availability=common_times)

    except Exception as e:
        logger.error(f"空き時間取得ユースケースに失敗しました: {e}")
        raise

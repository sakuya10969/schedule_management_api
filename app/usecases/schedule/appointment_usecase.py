import logging
from fastapi import BackgroundTasks

from app.schemas import AppointmentRequest, AppointmentResponse
from app.infrastructure.graph_api import GraphAPIClient
from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.services.email_service import send_confirmation_emails, send_no_available_schedule_emails
from app.utils.formatter import parse_candidate

logger = logging.getLogger(__name__)

async def create_appointment_usecase(
    background_tasks: BackgroundTasks, appointment_req: AppointmentRequest
) -> AppointmentResponse:
    """
    面接担当者の予定を登録し、確認メールを送信するユースケース
    """
    try:
        # 候補日が指定されていない場合（none）
        if not appointment_req.candidate or appointment_req.candidate.lower() == "none":
            logger.info("候補として '可能な日程がない' が選択されました。予定は登録されません。")
            # 非同期でメール送信
            background_tasks.add_task(
                send_no_available_schedule_emails, appointment_req
            )
            return AppointmentResponse(
                message="候補として '可能な日程がない' が選択されました。予定は登録されません。",
                subjects=[],
                meeting_urls=[],
                users=appointment_req.users,
            )

        # 候補文字列をパースして開始・終了時刻を取得
        try:
            start_str, end_str, selected_candidate = parse_candidate(appointment_req.candidate)
            logger.info(f"候補日パース成功: {start_str} - {end_str}")
        except Exception as e:
            logger.error(f"候補日パース失敗: {e}")
            raise

        # イベント情報を作成
        event = {
            "subject": f"面接: {appointment_req.lastname} {appointment_req.firstname}",
            "body": {
                "contentType": "HTML",
                "content": f"候補日: {start_str} - {end_str}"
            },
            "start": {"dateTime": start_str, "timeZone": "Tokyo Standard Time"},
            "end": {"dateTime": end_str, "timeZone": "Tokyo Standard Time"},
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness",
        }

        # Graph APIクライアントとDBクライアントを初期化
        graph_api_client = GraphAPIClient()
        cosmos_db_client = AzCosmosDBClient()

        created_events = []
        event_ids = {}

        # 各ユーザーのカレンダーに予定を登録
        for user_email in appointment_req.users:
            try:
                event_resp = graph_api_client.register_event(user_email, event)
                created_events.append(event_resp)
                event_id = event_resp.get("id")
                if event_id:
                    event_ids[user_email] = event_id
                logger.info(f"イベント登録成功: {user_email} - {event_id}")
            except Exception as e:
                logger.error(f"イベント登録失敗: {user_email} - {e}")

        # イベントIDをCosmos DBに保存
        cosmos_db_client.update_form_with_events(appointment_req.token, event_ids)

        # メール送信を非同期で実施
        background_tasks.add_task(
            send_confirmation_emails, appointment_req, [e.get("onlineMeeting", {}).get("joinUrl") for e in created_events]
        )

        return AppointmentResponse(
            message="予定を登録しました。確認メールは別途送信されます。",
            subjects=[e.get("subject") for e in created_events],
            meeting_urls=[e.get("onlineMeeting", {}).get("joinUrl") for e in created_events],
            users=appointment_req.users,
        )

    except Exception as e:
        logger.error(f"予定作成ユースケースエラー: {e}")
        raise

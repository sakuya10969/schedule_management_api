import logging
from typing import Optional

from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.infrastructure.graph_api import GraphAPIClient
from app.infrastructure.appointment_repository import AppointmentRepository
from app.utils.formatting import parse_candidate
from app.utils.time import split_candidates
from app.config.config import get_config
from app.schemas import FormData
from app.utils.formatting import format_candidate_date
from app.constants import EMPLOYEE_EMAILS

logger = logging.getLogger(__name__)

config = get_config()


async def get_reschedule_data_usecase(cosmos_db_id: str) -> FormData:
    """リスケジュール用のフォームデータを取得するユースケース"""
    try:
        cosmos_db_client = AzCosmosDBClient()
        form_data = cosmos_db_client.get_form_data(cosmos_db_id)
        form_data["schedule_interview_datetimes"] = split_candidates(
            form_data["schedule_interview_datetimes"], form_data["duration_minutes"]
        )

        return FormData(**form_data)

    except Exception as e:
        logger.error(f"リスケジュール用フォームデータが見つかりません: {e}")
        raise


async def reschedule_usecase(cosmos_db_id: str, schedule_interview_datetime: Optional[str]) -> None:
    """リスケジュール処理を行うユースケース"""
    try:
        cosmos_db_client = AzCosmosDBClient()
        form_data = cosmos_db_client.get_form_data(cosmos_db_id)

        # 可能な日程がない場合の処理
        if schedule_interview_datetime is None:
            logger.info("候補として '可能な日程がない' が選択されました。")
            
            # Outlookカレンダーのイベントを削除
            graph_api_client = GraphAPIClient()
            if "event_ids" in form_data:
                for user_email, event_id in form_data["event_ids"].items():
                    try:
                        graph_api_client.delete_event(user_email, event_id)
                        logger.info(f"Outlookイベント削除成功: {user_email} - {event_id}")
                    except Exception as e:
                        logger.error(f"Outlookイベント削除失敗: {user_email} - {event_id}: {e}")

            # DBのアポイントメントレコードを削除
            appointment_repository = AppointmentRepository()
            appointment_repository.delete_appointment(cosmos_db_id)
            logger.info(f"DBレコード削除成功: {cosmos_db_id}")
            
            # CosmosDBのフォームデータを削除
            cosmos_db_client.delete_form_data(cosmos_db_id)
            logger.info(f"CosmosDBレコード削除成功: {cosmos_db_id}")
            
            _send_no_available_reschedule_emails(form_data)
            return

        # CosmosDBのschedule_interview_datetimeを更新
        form_data["schedule_interview_datetime"] = schedule_interview_datetime
        cosmos_db_client.container.replace_item(item=form_data["id"], body=form_data)
        logger.info(f"CosmosDBの日時更新成功: {cosmos_db_id}")

        # DBのschedule_interview_datetimeを更新
        appointment_repository = AppointmentRepository()
        appointment_repository.update_schedule_interview_datetime(cosmos_db_id, schedule_interview_datetime)
        logger.info(f"DBの日時更新成功: {cosmos_db_id}")

        # Outlookカレンダーのイベント時刻を更新
        graph_api_client = GraphAPIClient()
        start_str, end_str, _ = parse_candidate(schedule_interview_datetime)
        
        for user_email, event_id in form_data["event_ids"].items():
            try:
                graph_api_client.update_event_time(user_email, event_id, start_str, end_str)
                logger.info(f"予定時刻更新成功: {user_email} - {event_id}")
            except Exception as e:
                logger.error(f"予定時刻更新失敗: {user_email} - {event_id}: {e}")
                raise

        # リスケジュール完了メールを送信
        _send_reschedule_emails(form_data, schedule_interview_datetime)

        # フォームのリセット
        form_data["is_confirmed"] = False
        cosmos_db_client.container.replace_item(item=form_data["id"], body=form_data)

    except Exception as e:
        logger.error(f"リスケジュールユースケースエラー: {e}")
        raise


def _send_reschedule_emails(form_data: dict, schedule_interview_datetime: Optional[str]) -> None:
    """リスケジュール完了メールを送信"""
    graph_api_client = GraphAPIClient()
    
    # 社内向けメール
    internal_subject = f"【{form_data['company']}/{form_data['candidate_lastname']}{form_data['candidate_firstname']}様】日程変更完了"
    internal_body = (
        "面接日程が再調整されました。詳細は下記の通りです。<br><br>"
        f"・氏名<br>{form_data['candidate_lastname']} {form_data['candidate_firstname']}<br>"
        f"・所属<br>{form_data['company']}<br>"
        f"・メールアドレス<br>{form_data['candidate_email']}<br>"
        f"・変更後日程<br>{format_candidate_date(schedule_interview_datetime)}<br><br>"
        "※カレンダーの予定も自動的に更新されています。<br><br>"
        "以上、よろしくお願いいたします。"
    )
    
    # 社内関係者へメール送信
    recipients = []
    if form_data.get('employee_email'):
        recipients.append(form_data['employee_email'])
    recipients.extend(EMPLOYEE_EMAILS)
    recipients = list(set(recipients))  # 重複を除去
    
    for recipient_email in recipients:
        try:
            graph_api_client.send_email(
                config["SYSTEM_SENDER_EMAIL"],
                recipient_email,
                internal_subject,
                internal_body,
            )
            logger.info(f"社内向けリスケジュールメール送信成功: {recipient_email}")
        except Exception as e:
            logger.error(f"社内向けリスケジュールメール送信失敗: {recipient_email}: {e}")

    # クライアント向けメール
    client_subject = "日程変更完了（インテリジェントフォース）"
    reschedule_link = f"{config['CLIENT_URL']}/reschedule?cosmosDbId={form_data['id']}"
    client_body = (
        f"{form_data['candidate_lastname']}様<br><br>"
        "この度は日程変更のご対応をいただき、ありがとうございます。<br>"
        "変更後の面接日程が確定いたしました。<br><br>"
        f"・氏名<br>{form_data['candidate_lastname']} {form_data['candidate_firstname']}<br><br>"
        f"・所属<br>{form_data['company']}<br><br>"
        f"・メールアドレス<br>{form_data['candidate_email']}<br><br>"
        f"・確定日程<br>{format_candidate_date(schedule_interview_datetime)}<br><br>"
        "会議URLについては、別途お送りいたします。<br><br>"
        "※さらに日程の再調整が必要な場合は、以下のリンクからご対応ください：<br>"
        f'<a href="{reschedule_link}">{reschedule_link}</a><br><br>'
        "以上になります。<br>"
        "変更後の日程にてお待ちしております。"
    )
    
    try:
        graph_api_client.send_email(
            config["SYSTEM_SENDER_EMAIL"],
            form_data['candidate_email'],
            client_subject,
            client_body,
        )
        logger.info(f"クライアント向けリスケジュールメール送信成功: {form_data['candidate_email']}")
    except Exception as e:
        logger.error(f"クライアント向けリスケジュールメール送信失敗: {form_data['candidate_email']}: {e}")


def _send_no_available_reschedule_emails(form_data: dict) -> None:
    """可能な日程がない場合の社内向けメール送信"""
    if not form_data.get('employee_email'):
        logger.warning("employee_email が無いため通知メールをスキップします")
        return

    graph_api_client = GraphAPIClient()
    subject = f"【{form_data['company']}/{form_data['candidate_lastname']}{form_data['candidate_firstname']}様】再調整日程なし"
    body = (
        f"{form_data['candidate_lastname']}様<br><br>"
        "以下の候補者から日程再調整の回答がありましたが、提示された日程では面接の調整ができませんでした。<br><br>"
        f"・氏名<br>{form_data['candidate_lastname']} {form_data['candidate_firstname']}<br><br>"
        f"・所属<br>{form_data['company']}<br><br>"
        f"・メールアドレス<br>{form_data['candidate_email']}<br><br>"
        "候補者からは「可能な日程がない」との回答がありました。<br>"
        "別の日程を提示するか、直接候補者と調整をお願いします。<br><br>"
        "※このメールは自動送信されています。"
    )
    
    # 社内関係者へメール送信
    recipients = []
    if form_data.get('employee_email'):
        recipients.append(form_data['employee_email'])
    recipients.extend(EMPLOYEE_EMAILS)
    recipients = list(set(recipients))  # 重複を除去
    
    for recipient_email in recipients:
        try:
            graph_api_client.send_email(
                config["SYSTEM_SENDER_EMAIL"],
                recipient_email,
                subject,
                body,
            )
            logger.info(f"再調整不可メール送信成功: {recipient_email}")
        except Exception as e:
            logger.error(f"再調整不可メール送信失敗: {recipient_email}: {e}")

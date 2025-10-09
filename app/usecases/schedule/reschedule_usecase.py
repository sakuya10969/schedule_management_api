import logging

from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.infrastructure.graph_api import GraphAPIClient
from app.infrastructure.appointment_repository import AppointmentRepository
from app.utils.formatting import parse_candidate
from app.config.config import get_config
from app.schemas import RescheduleRequest
from app.utils.formatting import format_candidate_date
from app.constants import EMPLOYEE_EMAILS

logger = logging.getLogger(__name__)

config = get_config()


class RescheduleUsecase:
    def __init__(self):
        self.cosmos_db_client = AzCosmosDBClient()
        self.graph_api_client = GraphAPIClient()
        self.appointment_repository = AppointmentRepository()

    async def execute(self, reschedule_req: RescheduleRequest) -> None:
        """リスケジュール処理を行うユースケース"""
        try:
            form_data = self.cosmos_db_client.get_form_data(reschedule_req.cosmos_db_id)
            # 可能な日程がない場合の処理
            if reschedule_req.schedule_interview_datetime is None:
                logger.info("候補として '可能な日程がない' が選択されました。")
                # Outlookカレンダーのイベントを削除
                if "event_ids" in form_data:
                    for user_email, event_id in form_data["event_ids"].items():
                        try:
                            self.graph_api_client.delete_event(user_email, event_id)
                            logger.info(f"Outlookイベント削除成功: {user_email} - {event_id}")
                        except Exception as e:
                            logger.error(f"Outlookイベント削除失敗: {user_email} - {event_id}: {e}")
                # DBのアポイントメントレコードを削除
                self.appointment_repository.delete_appointment(reschedule_req.cosmos_db_id)
                logger.info(f"DBレコード削除成功: {reschedule_req.cosmos_db_id}")
                # CosmosDBのフォームデータを削除
                self.cosmos_db_client.delete_form_data(reschedule_req.cosmos_db_id)
                logger.info(f"CosmosDBレコード削除成功: {reschedule_req.cosmos_db_id}")
                
                self._send_no_available_reschedule_emails(reschedule_req.cosmos_db_id)
                return

            # CosmosDBのschedule_interview_datetimeを更新
            form_data["schedule_interview_datetime"] = reschedule_req.schedule_interview_datetime
            self.cosmos_db_client.container.replace_item(item=form_data["id"], body=form_data)
            logger.info(f"CosmosDBの日時更新成功: {reschedule_req.cosmos_db_id}")
            # DBのschedule_interview_datetimeを更新
            self.appointment_repository.update_schedule_interview_datetime(reschedule_req.cosmos_db_id, reschedule_req.schedule_interview_datetime)
            logger.info(f"DBの日時更新成功: {reschedule_req.cosmos_db_id}")
            # Outlookカレンダーのイベント時刻を更新
            start_str, end_str, _ = parse_candidate(reschedule_req.schedule_interview_datetime)
            
            for user_email, event_id in form_data["event_ids"].items():
                try:
                    self.graph_api_client.update_event_time(user_email, event_id, start_str, end_str)
                    logger.info(f"予定時刻更新成功: {user_email} - {event_id}")
                except Exception as e:
                    logger.error(f"予定時刻更新失敗: {user_email} - {event_id}: {e}")
                    raise

            # リスケジュール完了メールを送信
            self._send_reschedule_emails(reschedule_req.cosmos_db_id, reschedule_req.schedule_interview_datetime)
            # フォームのリセット
            form_data["is_confirmed"] = False
            self.cosmos_db_client.container.replace_item(item=form_data["id"], body=form_data)

        except Exception as e:
            logger.error(f"リスケジュールユースケースエラー: {e}")
            raise


    def _send_reschedule_emails(self, cosmos_db_id: str, schedule_interview_datetime: str | None) -> None:
        """リスケジュール完了メールを送信"""
        # DBからアポイントメントデータを取得
        appointment_data = self.appointment_repository.get_appointment_by_cosmos_db_id(cosmos_db_id)
        
        if not appointment_data:
            logger.error(f"アポイントメントデータが見つかりません: {cosmos_db_id}")
            return

        # 社内向けメール
        internal_subject = f"【{appointment_data.company}/{appointment_data.candidate_lastname}{appointment_data.candidate_firstname}様】日程変更完了"
        internal_body = (
            "面接日程が再調整されました。詳細は下記の通りです。<br><br>"
            f"・氏名<br>{appointment_data.candidate_lastname} {appointment_data.candidate_firstname}<br>"
            f"・所属<br>{appointment_data.company}<br>"
            f"・メールアドレス<br>{appointment_data.candidate_email}<br>"
            f"・変更後日程<br>{format_candidate_date(schedule_interview_datetime)}<br><br>"
            "※カレンダーの予定も自動的に更新されています。<br><br>"
            "以上、よろしくお願いいたします。"
        )
        # 社内関係者へメール送信
        recipients = []
        if appointment_data.employee_email:
            recipients.append(appointment_data.employee_email)
        # recipients.extend(EMPLOYEE_EMAILS)
        recipients = list(set(recipients))  # 重複を除去
        
        for recipient_email in recipients:
            try:
                self.graph_api_client.send_email(
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
        reschedule_link = f"{config['CLIENT_URL']}/reschedule?cosmosDbId={cosmos_db_id}"
        client_body = (
            f"{appointment_data.candidate_lastname}様<br><br>"
            "この度は日程変更のご対応をいただき、ありがとうございます。<br>"
            "変更後の面接日程が確定いたしました。<br><br>"
            f"・氏名<br>{appointment_data.candidate_lastname} {appointment_data.candidate_firstname}<br><br>"
            f"・所属<br>{appointment_data.company}<br><br>"
            f"・メールアドレス<br>{appointment_data.candidate_email}<br><br>"
            f"・確定日程<br>{format_candidate_date(schedule_interview_datetime)}<br><br>"
            "会議URLについては、別途お送りいたします。<br><br>"
            "※さらに日程の再調整が必要な場合は、以下のリンクからご対応ください：<br>"
            f'<a href="{reschedule_link}">{reschedule_link}</a><br><br>'
            "以上になります。<br>"
            "変更後の日程にてお待ちしております。"
        )
        
        try:
            self.graph_api_client.send_email(
                config["SYSTEM_SENDER_EMAIL"],
                appointment_data.candidate_email,
                client_subject,
                client_body,
            )
            logger.info(f"クライアント向けリスケジュールメール送信成功: {appointment_data.candidate_email}")
        except Exception as e:
            logger.error(f"クライアント向けリスケジュールメール送信失敗: {appointment_data.candidate_email}: {e}")


    def _send_no_available_reschedule_emails(self, cosmos_db_id: str) -> None:
        """可能な日程がない場合の社内向けメール送信"""
        # DBからアポイントメントデータを取得
        appointment_data = self.appointment_repository.get_appointment_by_cosmos_db_id(cosmos_db_id)
        
        if not appointment_data:
            logger.error(f"予約データが見つかりません: {cosmos_db_id}")
            return

        if not appointment_data.employee_email:
            logger.warning("面接担当者のメールアドレスがないため通知メールをスキップします")
            return

        subject = f"【{appointment_data.company}/{appointment_data.candidate_lastname}{appointment_data.candidate_firstname}様】再調整日程なし"
        body = (
            f"{appointment_data.candidate_lastname}様<br><br>"
            "以下の候補者から日程再調整の回答がありましたが、提示された日程では面接の調整ができませんでした。<br><br>"
            f"・氏名<br>{appointment_data.candidate_lastname} {appointment_data.candidate_firstname}<br><br>"
            f"・所属<br>{appointment_data.company}<br><br>"
            f"・メールアドレス<br>{appointment_data.candidate_email}<br><br>"
            "候補者からは「可能な日程がない」との回答がありました。<br>"
            "別の日程を提示するか、直接候補者と調整をお願いします。<br><br>"
            "※このメールは自動送信されています。"
        )
        
        # 社内関係者へメール送信
        recipients = []
        if appointment_data.employee_email:
            recipients.append(appointment_data.employee_email)
        recipients.extend([*EMPLOYEE_EMAILS, config["SYSTEM_SENDER_EMAIL"]])
        
        for recipient_email in recipients:
            try:
                self.graph_api_client.send_email(
                    config["SYSTEM_SENDER_EMAIL"],
                    recipient_email,
                    subject,
                    body,
                )
                logger.info(f"再調整不可メール送信成功: {recipient_email}")
            except Exception as e:
                logger.error(f"再調整不可メール送信失敗: {recipient_email}: {e}")

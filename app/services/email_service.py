import logging
from typing import List

from app.config.config import get_config
from app.infrastructure.graph_api import GraphAPIClient
from app.utils.formatter import format_candidate_date
from app.schemas import AppointmentRequest

logger = logging.getLogger(__name__)

config = get_config()

class EmailService:
    def __init__(self):
        self.graph_client = GraphAPIClient()

    def send_confirmation_emails(
        self, appointment_req: AppointmentRequest, meeting_urls: List[str]
    ) -> None:
        """内部向けおよび先方向けの確認メール送信処理をまとめる。"""
        meeting_url = meeting_urls[0] if isinstance(meeting_urls, list) else meeting_urls
        
        # 内部関係者向けメール送信
        subject = f"【{appointment_req.company}/{appointment_req.lastname}{appointment_req.firstname}様】日程確定"
        body = (
            "日程調整が完了しました。詳細は下記の通りです。<br><br>"
            f"・氏名<br>{appointment_req.lastname} {appointment_req.firstname}<br>"
            f"・所属<br>{appointment_req.company}<br>"
            f"・メールアドレス<br>{appointment_req.email}<br>"
            f"・日程<br>{format_candidate_date(appointment_req.candidate)}<br>"
            f'・会議URL<br><a href="{meeting_url}">{meeting_url}</a><br><br>'
        )
        for to_email in appointment_req.users:
            self.graph_client.send_email(
                config['SYSTEM_SENDER_EMAIL'], 
                to_email, 
                subject, 
                body
            )

        # クライアント向けメール送信
        subject = "日程確定（インテリジェントフォース）"
        reschedule_link = f"{config['API_URL']}/reschedule?token={appointment_req.token}"
        body = (
            f"{appointment_req.lastname}様<br><br>"
            "この度は日程を調整いただきありがとうございます。<br>"
            "ご登録いただいた内容、および当日の会議URLは下記の通りです。<br><br>"
            f"・氏名<br>{appointment_req.lastname} {appointment_req.firstname}<br><br>"
            f"・所属<br>{appointment_req.company}<br><br>"
            f"・メールアドレス<br>{appointment_req.email}<br><br>"
            f"・日程<br>{format_candidate_date(appointment_req.candidate)}<br><br>"
            f"・会議URL<br>{meeting_url}<br><br>"
            "※日程の再調整が必要な場合はこちらからご対応ください：<br>"
            f"{reschedule_link}<br>"
            "再調整のご対応後は、元の予定は自動的に削除されます。<br><br>"
            "以上になります。<br>"
            "当日はどうぞよろしくお願いいたします。"
        )
        self.graph_client.send_email(
            config['SYSTEM_SENDER_EMAIL'],
            appointment_req.email,
            subject,
            body
        )

    def send_no_available_schedule_emails(
        self, appointment_req: AppointmentRequest
    ) -> None:
        """可能な日程がない場合のメールを担当者に送信する"""
        subject = f"【{appointment_req.company}/{appointment_req.lastname}{appointment_req.firstname}様】日程確定"
        body = (
            f"{appointment_req.lastname}様<br><br>"
            "以下の候補者から日程調整の回答がありましたが、提示された日程では面接の調整ができませんでした。<br><br>"
            f"・氏名<br>{appointment_req.lastname} {appointment_req.firstname}<br><br>"
            f"・所属<br>{appointment_req.company}<br><br>"
            f"・メールアドレス<br>{appointment_req.email}<br><br>"
            "候補者からは「可能な日程がない」との回答がありました。<br>"
            "別の日程を提示するか、直接候補者と調整をお願いします。<br><br>"
            "※このメールは自動送信されています。"
        )

        for to_email in appointment_req.users:
            self.graph_client.send_email(
                config['SYSTEM_SENDER_EMAIL'],
                to_email,
                subject,
                body
            )

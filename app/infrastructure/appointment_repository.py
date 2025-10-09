from sqlalchemy import insert, update, delete, select

from app.config.config import get_config
from app.schemas.schedule import AppointmentRequest
from app.infrastructure.db import engine, metadata

config = get_config()


class AppointmentRepository:
    def __init__(self):
        self.engine = engine
        self.metadata = metadata

        if "schedule_management" not in self.metadata.tables:
            self.metadata.reflect(bind=self.engine, only=["schedule_management"])

        self.appointments = self.metadata.tables["schedule_management"]

    def get_appointment_by_cosmos_db_id(self, cosmos_db_id: str):
        """cosmos_db_idに基づいてアポイントメントデータを取得する"""
        with self.engine.begin() as conn:
            stmt = select(self.appointments).where(
                self.appointments.c.cosmos_db_id == cosmos_db_id
            )
            result = conn.execute(stmt)
            return result.fetchone()

    def create_appointment(self, appointment_req: AppointmentRequest):
        values = {
            "scheduled_interview_datetime": appointment_req.schedule_interview_datetime,
            "employee_email": appointment_req.employee_email,
            "candidate_lastname": appointment_req.candidate_lastname,
            "candidate_firstname": appointment_req.candidate_firstname,
            "company": appointment_req.company,
            "candidate_email": appointment_req.candidate_email,
            "cosmos_db_id": appointment_req.cosmos_db_id,
            "candidate_id": appointment_req.candidate_id or None,
            "interview_stage": appointment_req.interview_stage or None,
            # "university": appointment_req.university or None
        }

        with self.engine.begin() as conn:
            stmt = insert(self.appointments).values(values)
            conn.execute(stmt)

    def update_schedule_interview_datetime(self, cosmos_db_id: str, new_schedule_interview_datetime: str):
        """cosmos_db_idに基づいてscheduled_interview_datetimeを更新する"""
        with self.engine.begin() as conn:
            stmt = update(self.appointments).where(
                self.appointments.c.cosmos_db_id == cosmos_db_id
            ).values(scheduled_interview_datetime=new_schedule_interview_datetime)
            conn.execute(stmt)

    def delete_appointment(self, cosmos_db_id: str):
        """cosmos_db_idに基づいてレコードを削除する"""
        with self.engine.begin() as conn:
            stmt = delete(self.appointments).where(
                self.appointments.c.cosmos_db_id == cosmos_db_id
            )
            conn.execute(stmt)

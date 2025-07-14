from sqlalchemy import create_engine, MetaData, insert, update
from sqlalchemy.engine import URL
from app.config.config import get_config
from app.schemas.schedule import AppointmentRequest

config = get_config()


class AppointmentRepository:
    def __init__(self):
        self.engine = create_engine(
            URL.create(
                "mssql+pyodbc",
                username="azureuser",
                password="SRM-password",
                host="srm-server-k.database.windows.net",
                port=1433,
                database="db-SRM-K",
                query={"driver": "ODBC Driver 18 for SQL Server"},
            ),
            echo=True,
            fast_executemany=True,
        )

        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)
        self.appointments = self.meta.tables["schedule_management"]

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

from sqlalchemy import create_engine, MetaData, insert
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
                query={"driver": "ODBC Driver 18 for SQL Server"}
            ),
            echo=True,
            fast_executemany=True,
        )

        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)
        self.appointments = self.meta.tables["appointments"]

    def create_appointment(self, appointment_req: AppointmentRequest):
        values = {
            "candidate": appointment_req.candidate,
            "user": appointment_req.user,
            "lastname": appointment_req.lastname,
            "firstname": appointment_req.firstname,
            "company": appointment_req.company,
            "email": appointment_req.email,
            "token": appointment_req.token,
            "candidate_id": appointment_req.candidate_id,
            "stage": appointment_req.stage,
        }

        with self.engine.begin() as conn:
            stmt = insert(self.appointments).values(values)
            conn.execute(stmt)

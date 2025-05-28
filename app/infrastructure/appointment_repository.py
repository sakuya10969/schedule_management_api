from sqlalchemy import create_engine, MetaData, insert
from app.config.config import get_config
from app.schemas.schedule import AppointmentRequest

config = get_config()

class AppointmentRepository:
    def __init__(self):
        self.engine = create_engine(config["DATABASE_URL"], echo=True)
        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)
        self.appointments = self.meta.tables["appointments"]

    def create_appointment(self, appointment_req: AppointmentRequest):
        with self.engine.connect() as conn:
            stmt = insert(self.appointments).values(
                title=appointment_req.title,
                start_time=appointment_req.start_time,
                end_time=appointment_req.end_time,
            )
            conn.execute(stmt)
            conn.commit()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.appointment import Appointment
from app.config.config import get_config

config = get_config()

class AppointmentRepository:
    def __init__(self):
        self.engine = create_engine(config["DATABASE_URL"], echo=True)
        self.Session = sessionmaker(bind=self.engine)

    def create_appointment(self, appointment: Appointment):
        session = self.Session()
        try:
            session.add(appointment)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

from sqlalchemy import select
from app.config.config import get_config
from app.infrastructure.db import engine, metadata

config = get_config()


class EmployeeDirectoryRepository:
    def __init__(self):
        self.engine = engine
        self.metadata = metadata

        if "employee_directory" not in self.metadata.tables:
            self.metadata.reflect(bind=self.engine, only=["employee_directory"])

        self.employee_directory = self.metadata.tables["employee_directory"]

    def get_all_employee_directory(self):
        with self.engine.begin() as conn:
            stmt = select(self.employee_directory)
            result = conn.execute(stmt)
            return result.fetchall()

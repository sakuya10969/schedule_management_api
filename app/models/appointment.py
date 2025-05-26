from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    candidate = Column(String)
    lastname = Column(String)
    firstname = Column(String)
    company = Column(String)
    email = Column(String)
    token = Column(String)
    candidate_id = Column(Integer)
    stage = Column(Integer)
    
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import form_router, schedule_router
from app.config.config import get_config

config = get_config()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(form_router.router)
app.include_router(schedule_router.router)
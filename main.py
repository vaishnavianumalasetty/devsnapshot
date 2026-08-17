from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from routes.auth import router as auth_router
from models import database

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="dev-secret-change-later")

app.include_router(auth_router)


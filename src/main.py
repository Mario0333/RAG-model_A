from fastapi import FastAPI
from routes import base,data
from motor.motor_asyncio import AsyncIOMotorClient
from helpers.config import get_settings
from contextlib import asynccontextmanager


app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database connection
    settings = get_settings()
    app.mongo_conn = AsyncIOMotorClient(settings.MONGODG_URL)
    app.db_client = app.mongo_conn[settings.MONGODG_DATABASE]
    print("Database connection established.")

    yield  # This yield separates startup and shutdown

    # Shutdown: Close database connection
    app.mongo_conn.close()
    print("Database connection closed.")

app.include_router(base.base_router)
app.include_router(data.data_router)



from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.bookings import router as bookings_router
from app.api.experiments import router as experiments_router
from app.api.rooms import router as rooms_router
from app.config import settings
from app.db import Base, engine
from app.worker import worker_manager


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    await worker_manager.start()
    yield
    await worker_manager.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(rooms_router)
app.include_router(bookings_router)
app.include_router(experiments_router)


@app.get("/")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

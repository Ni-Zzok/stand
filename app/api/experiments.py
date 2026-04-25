from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories import ExperimentsRepository, MetricsRepository
from app.schemas import MetricsEventRead, WorkerDelayUpdate
from app.worker import worker_manager

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("/reset")
def reset_data(db: Session = Depends(get_db)) -> dict[str, str]:
    ExperimentsRepository.reset_all(db)
    db.commit()
    return {"status": "ok", "message": "All experiment tables cleared"}


@router.post("/seed")
def seed_data(db: Session = Depends(get_db)) -> dict[str, str]:
    ExperimentsRepository.seed_defaults(db)
    db.commit()
    return {"status": "ok", "message": "Seed data created"}


@router.get("/metrics", response_model=list[MetricsEventRead])
def list_metrics(db: Session = Depends(get_db)) -> list[MetricsEventRead]:
    return MetricsRepository.list_all(db)


@router.post("/worker/on")
def worker_on() -> dict[str, str | bool]:
    worker_manager.enabled = True
    return {"status": "ok", "worker_enabled": worker_manager.enabled}


@router.post("/worker/off")
def worker_off() -> dict[str, str | bool]:
    worker_manager.enabled = False
    return {"status": "ok", "worker_enabled": worker_manager.enabled}


@router.post("/worker/delay")
def worker_delay(payload: WorkerDelayUpdate) -> dict[str, str | int]:
    worker_manager.delay_ms = payload.delay_ms
    return {"status": "ok", "delay_ms": worker_manager.delay_ms}

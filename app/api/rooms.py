from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories import RoomRepository
from app.schemas import RoomRead

router = APIRouter(tags=["rooms"])


@router.get("/rooms", response_model=list[RoomRead])
def list_rooms(db: Session = Depends(get_db)) -> list[RoomRead]:
    return RoomRepository.list_all(db)

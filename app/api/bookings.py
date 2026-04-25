from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories import BookingRepository
from app.schemas import BookingCreate, BookingRead
from app.services import BookingService

router = APIRouter(tags=["bookings"])


@router.get("/bookings", response_model=list[BookingRead])
def list_bookings(db: Session = Depends(get_db)) -> list[BookingRead]:
    return BookingRepository.list_all(db)


@router.post("/bookings", response_model=BookingRead)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)) -> BookingRead:
    return BookingService.create_booking(db=db, payload=payload)

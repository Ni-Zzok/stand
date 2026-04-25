from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.queue_manager import QueueTask, task_queue
from app.repositories import (
    AuditRepository,
    BookingRepository,
    MetricsRepository,
    NotificationRepository,
    RoomRepository,
    UserRepository,
)
from app.schemas import BookingCreate


class BookingService:
    @staticmethod
    def create_booking(db: Session, payload: BookingCreate):
        request_id = str(uuid4())
        started_at = datetime.utcnow()

        try:
            room = RoomRepository.get_by_id(db, payload.room_id)
            if room is None:
                raise HTTPException(status_code=404, detail="Room not found")

            user = UserRepository.get_by_id(db, payload.user_id)
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")

            if BookingRepository.has_conflict(db, payload.room_id, payload.start_time, payload.end_time):
                finished_at = datetime.utcnow()
                duration_ms = (finished_at - started_at).total_seconds() * 1000
                MetricsRepository.create(
                    db=db,
                    request_id=request_id,
                    scenario=payload.scenario,
                    mode=payload.mode,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                    result="conflict",
                    notes=(
                        f"conflict for room_id={payload.room_id} "
                        f"interval={payload.start_time.isoformat()}..{payload.end_time.isoformat()}"
                    ),
                )
                db.commit()
                raise HTTPException(status_code=409, detail="Booking conflict detected")

            booking = BookingRepository.create(
                db=db,
                room_id=payload.room_id,
                user_id=payload.user_id,
                start_time=payload.start_time,
                end_time=payload.end_time,
                mode=payload.mode,
            )

            if payload.mode == "centralized_sync":
                AuditRepository.create(db, booking_id=booking.id, event_type="booking_created_sync")
                NotificationRepository.create(db, booking_id=booking.id, recipient=user.name, status="created_sync")
            elif payload.mode == "hybrid_async":
                now = datetime.utcnow()
                task_queue.put_nowait(
                    QueueTask(
                        task_type="audit_log",
                        booking_id=booking.id,
                        recipient=user.name,
                        enqueued_at=now,
                        request_id=request_id,
                    )
                )
                task_queue.put_nowait(
                    QueueTask(
                        task_type="notification",
                        booking_id=booking.id,
                        recipient=user.name,
                        enqueued_at=now,
                        request_id=request_id,
                    )
                )
            else:
                raise HTTPException(status_code=400, detail="Unsupported mode")

            finished_at = datetime.utcnow()
            duration_ms = (finished_at - started_at).total_seconds() * 1000
            MetricsRepository.create(
                db=db,
                request_id=request_id,
                scenario=payload.scenario,
                mode=payload.mode,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
                result="success",
                notes=f"booking_id={booking.id}",
            )
            db.commit()
            db.refresh(booking)
            return booking

        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            finished_at = datetime.utcnow()
            duration_ms = (finished_at - started_at).total_seconds() * 1000
            MetricsRepository.create(
                db=db,
                request_id=request_id,
                scenario=payload.scenario,
                mode=payload.mode,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
                result="error",
                notes=str(exc),
            )
            db.commit()
            raise HTTPException(status_code=500, detail="Internal server error") from exc

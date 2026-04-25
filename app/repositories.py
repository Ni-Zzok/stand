from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models


class RoomRepository:
    @staticmethod
    def get_by_id(db: Session, room_id: int) -> models.Room | None:
        return db.get(models.Room, room_id)

    @staticmethod
    def list_all(db: Session) -> list[models.Room]:
        return list(db.scalars(select(models.Room).order_by(models.Room.id)))


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> models.User | None:
        return db.get(models.User, user_id)


class BookingRepository:
    @staticmethod
    def create(
        db: Session,
        room_id: int,
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        mode: str,
    ) -> models.Booking:
        booking = models.Booking(
            room_id=room_id,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            mode=mode,
            status="confirmed",
        )
        db.add(booking)
        db.flush()
        db.refresh(booking)
        return booking

    @staticmethod
    def has_conflict(db: Session, room_id: int, start_time: datetime, end_time: datetime) -> bool:
        stmt = (
            select(models.Booking)
            .where(models.Booking.room_id == room_id)
            .where(models.Booking.start_time < end_time)
            .where(models.Booking.end_time > start_time)
            .limit(1)
        )
        return db.scalar(stmt) is not None

    @staticmethod
    def list_all(db: Session) -> list[models.Booking]:
        return list(db.scalars(select(models.Booking).order_by(models.Booking.id)))


class AuditRepository:
    @staticmethod
    def create(db: Session, booking_id: int, event_type: str = "booking_created") -> models.AuditLog:
        record = models.AuditLog(booking_id=booking_id, event_type=event_type)
        db.add(record)
        db.flush()
        db.refresh(record)
        return record


class NotificationRepository:
    @staticmethod
    def create(db: Session, booking_id: int, recipient: str, status: str = "created") -> models.Notification:
        record = models.Notification(booking_id=booking_id, recipient=recipient, status=status)
        db.add(record)
        db.flush()
        db.refresh(record)
        return record


class MetricsRepository:
    @staticmethod
    def create(
        db: Session,
        request_id: str,
        scenario: str,
        mode: str,
        started_at: datetime,
        finished_at: datetime,
        duration_ms: float,
        result: str,
        notes: str,
    ) -> models.MetricsEvent:
        metric = models.MetricsEvent(
            request_id=request_id,
            scenario=scenario,
            mode=mode,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            result=result,
            notes=notes,
        )
        db.add(metric)
        db.flush()
        db.refresh(metric)
        return metric

    @staticmethod
    def list_all(db: Session) -> list[models.MetricsEvent]:
        return list(db.scalars(select(models.MetricsEvent).order_by(models.MetricsEvent.id)))


class ExperimentsRepository:
    @staticmethod
    def reset_all(db: Session) -> None:
        tables = [
            models.MetricsEvent,
            models.Notification,
            models.AuditLog,
            models.Booking,
            models.Room,
            models.User,
        ]
        for table in tables:
            db.execute(delete(table))

    @staticmethod
    def seed_defaults(db: Session) -> None:
        rooms = [
            models.Room(name="Blue Room", status="active"),
            models.Room(name="Green Room", status="active"),
            models.Room(name="Orange Room", status="active"),
        ]
        users = [
            models.User(name="Alice"),
            models.User(name="Bob"),
            models.User(name="Charlie"),
        ]
        db.add_all(rooms + users)

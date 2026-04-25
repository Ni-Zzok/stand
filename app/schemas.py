from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


ModeType = Literal["centralized_sync", "hybrid_async"]


class UserRead(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class RoomRead(BaseModel):
    id: int
    name: str
    status: str

    model_config = {"from_attributes": True}


class BookingCreate(BaseModel):
    room_id: int
    user_id: int
    start_time: datetime
    end_time: datetime
    mode: ModeType
    scenario: str = Field(default="manual")

    @field_validator("end_time")
    @classmethod
    def end_must_be_greater_than_start(cls, value: datetime, info):
        start = info.data.get("start_time")
        if start and value <= start:
            raise ValueError("end_time must be greater than start_time")
        return value


class BookingRead(BaseModel):
    id: int
    room_id: int
    user_id: int
    start_time: datetime
    end_time: datetime
    status: str
    mode: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MetricsEventRead(BaseModel):
    id: int
    request_id: str
    scenario: str
    mode: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    result: str
    notes: str

    model_config = {"from_attributes": True}


class WorkerDelayUpdate(BaseModel):
    delay_ms: int = Field(ge=0)

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


TaskType = Literal["audit_log", "notification"]


@dataclass(slots=True)
class QueueTask:
    task_type: TaskType
    booking_id: int
    recipient: str
    enqueued_at: datetime
    request_id: str


task_queue: asyncio.Queue[QueueTask] = asyncio.Queue()

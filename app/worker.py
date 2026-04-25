import asyncio
from datetime import datetime

from app.db import SessionLocal
from app.queue_manager import QueueTask, task_queue
from app.repositories import AuditRepository, MetricsRepository, NotificationRepository


class WorkerManager:
    def __init__(self) -> None:
        self.enabled: bool = True
        self.delay_ms: int = 0
        self._runner_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._runner_task is None or self._runner_task.done():
            self._runner_task = asyncio.create_task(self._run(), name="booking-worker")

    async def stop(self) -> None:
        if self._runner_task and not self._runner_task.done():
            self._runner_task.cancel()
            try:
                await self._runner_task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        while True:
            task: QueueTask = await task_queue.get()
            if not self.enabled:
                await asyncio.sleep(0.05)
                await task_queue.put(task)
                task_queue.task_done()
                continue

            started_at = datetime.utcnow()
            try:
                if self.delay_ms > 0:
                    await asyncio.sleep(self.delay_ms / 1000)

                with SessionLocal() as db:
                    if task.task_type == "audit_log":
                        AuditRepository.create(db, booking_id=task.booking_id, event_type="booking_created_async")
                    elif task.task_type == "notification":
                        NotificationRepository.create(
                            db,
                            booking_id=task.booking_id,
                            recipient=task.recipient,
                            status="created_async",
                        )
                    finished_at = datetime.utcnow()
                    duration_ms = (finished_at - started_at).total_seconds() * 1000
                    MetricsRepository.create(
                        db=db,
                        request_id=task.request_id,
                        scenario="worker",
                        mode="hybrid_async",
                        started_at=started_at,
                        finished_at=finished_at,
                        duration_ms=duration_ms,
                        result="success",
                        notes=f"worker task={task.task_type} booking_id={task.booking_id}",
                    )
                    db.commit()
            except Exception as exc:  # noqa: BLE001
                with SessionLocal() as db:
                    finished_at = datetime.utcnow()
                    duration_ms = (finished_at - started_at).total_seconds() * 1000
                    MetricsRepository.create(
                        db=db,
                        request_id=task.request_id,
                        scenario="worker",
                        mode="hybrid_async",
                        started_at=started_at,
                        finished_at=finished_at,
                        duration_ms=duration_ms,
                        result="error",
                        notes=f"worker error for task={task.task_type}: {exc}",
                    )
                    db.commit()
            finally:
                task_queue.task_done()


worker_manager = WorkerManager()

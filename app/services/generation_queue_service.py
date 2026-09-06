from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha1
from socket import gethostname
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resume_parse_task import ResumeParseTask
from app.models.career_intelligence import ResumeTailoringTask

logger = logging.getLogger(__name__)

WORKER_ID_MAX_LENGTH = 100


@dataclass
class QueueHeartbeat:
    worker_id: str
    status: str = "ready"


class GenerationQueueService:
    def __init__(self, db: Session, current_user: object | None = None) -> None:
        self.db = db
        self.current_user = current_user

    def heartbeat_worker(self, worker_id: str) -> QueueHeartbeat:
        logger.debug("queue heartbeat worker_id=%s", worker_id)
        return QueueHeartbeat(worker_id=worker_id)

    def run_once(self, worker_id: str) -> str | None:
        task = self._claim_resume_parse_task(worker_id)
        if task is None:
            task = self._claim_resume_tailoring_task(worker_id)
            if task is None:
                logger.debug("queue worker poll worker_id=%s", worker_id)
                return None
            logger.info("queue worker claimed tailoring task_id=%s worker_id=%s", task.id, worker_id)
            from app.services.job_portal_service import JobPortalService
            JobPortalService(self.db).process_resume_tailoring_task(task.id, worker_id)
            return str(task.id)

        logger.info("queue worker claimed task_id=%s worker_id=%s", task.id, worker_id)
        from app.services.job_portal_service import JobPortalService

        JobPortalService(self.db).process_resume_parse_task(task.id, worker_id)
        return str(task.id)

    def _claim_resume_parse_task(self, worker_id: str) -> ResumeParseTask | None:
        task = self.db.scalar(
            select(ResumeParseTask)
            .where(ResumeParseTask.status == "queued")
            .order_by(ResumeParseTask.created_at.asc())
            .with_for_update(skip_locked=True)
        )
        if task is None:
            return None

        task.status = "running"
        task.stage = "claiming"
        task.worker_id = worker_id
        task.attempts += 1
        task.started_at = task.started_at or datetime.now(UTC)
        task.heartbeat_at = datetime.now(UTC)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def _claim_resume_tailoring_task(self, worker_id: str) -> ResumeTailoringTask | None:
        task = self.db.scalar(
            select(ResumeTailoringTask)
            .where(ResumeTailoringTask.status == "queued")
            .order_by(ResumeTailoringTask.created_at.asc())
            .with_for_update(skip_locked=True)
        )
        if task is None:
            return None
        task.status = "running"
        task.stage = "claiming"
        task.worker_id = worker_id
        task.attempts += 1
        task.started_at = task.started_at or datetime.now(UTC)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task


def run_worker_loop(
    worker_id: str | None = None,
    *,
    stop_after_idle: bool = False,
    concurrency: int | None = None,
) -> None:
    resolved_concurrency = concurrency or settings.queue_worker_concurrency
    if resolved_concurrency < 1:
        raise ValueError("Worker concurrency must be at least 1.")

    base_worker_id = worker_id or settings.queue_worker_id or _default_worker_id()
    worker_ids = _worker_ids(base_worker_id, resolved_concurrency)
    if resolved_concurrency == 1:
        logger.info("generation.worker.start concurrency=1 worker_id=%s", worker_ids[0])
        _run_worker_slot(worker_ids[0], stop_after_idle=stop_after_idle)
        return

    logger.info(
        "generation.worker_pool.start concurrency=%s base_worker_id=%s",
        resolved_concurrency,
        _fit_worker_id(base_worker_id),
    )
    with ThreadPoolExecutor(
        max_workers=resolved_concurrency,
        thread_name_prefix="generation-worker",
    ) as executor:
        futures = [
            executor.submit(_run_worker_slot, slot_worker_id, stop_after_idle=stop_after_idle)
            for slot_worker_id in worker_ids
        ]
        for future in futures:
            future.result()


def _run_worker_slot(worker_id: str, *, stop_after_idle: bool) -> None:
    from app.db.session import SessionLocal

    logger.info("generation.worker.slot.start worker_id=%s", worker_id)
    idle_logged = False
    poll_interval = max(settings.queue_poll_interval_seconds, 0.1)
    while True:
        try:
            with SessionLocal() as db:
                service = GenerationQueueService(db)
                service.heartbeat_worker(worker_id)
                run = service.run_once(worker_id)
        except KeyboardInterrupt:
            logger.info("generation.worker.slot.stopped worker_id=%s", worker_id)
            return
        except Exception:
            logger.exception("generation.worker.slot.error worker_id=%s", worker_id)
            time.sleep(poll_interval)
            continue

        if run is None:
            if stop_after_idle:
                logger.info("generation.worker.slot.stop_after_idle worker_id=%s", worker_id)
                return
            if not idle_logged:
                logger.info(
                    "generation.worker.slot.idle worker_id=%s poll_interval_seconds=%s",
                    worker_id,
                    poll_interval,
                )
                idle_logged = True
            time.sleep(poll_interval)
            continue
        idle_logged = False


def _default_worker_id() -> str:
    return f"{gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"


def _worker_ids(base_worker_id: str, concurrency: int) -> list[str]:
    if concurrency == 1:
        return [_fit_worker_id(base_worker_id)]
    return [_fit_worker_id(f"{base_worker_id}:{slot}") for slot in range(1, concurrency + 1)]


def _fit_worker_id(worker_id: str) -> str:
    if len(worker_id) <= WORKER_ID_MAX_LENGTH:
        return worker_id
    digest = sha1(worker_id.encode("utf-8")).hexdigest()[:10]
    prefix_limit = WORKER_ID_MAX_LENGTH - len(digest) - 1
    return f"{worker_id[:prefix_limit]}:{digest}"

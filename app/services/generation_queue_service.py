from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class QueueHeartbeat:
    worker_id: str
    status: str = "ready"


class GenerationQueueService:
    def __init__(self, db: Session, current_user: object | None = None) -> None:
        self.db = db
        self.current_user = current_user

    def heartbeat_worker(self, worker_id: str) -> QueueHeartbeat:
        logger.info("queue heartbeat worker_id=%s", worker_id)
        return QueueHeartbeat(worker_id=worker_id)


def run_worker_loop() -> None:
    logger.info("queue worker started")
    time.sleep(0.1)

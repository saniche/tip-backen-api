import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import HTTPException
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from shared.models import ProcessingJob, ProcessingOutbox

logger = logging.getLogger("tip-api")


def serialize_job(value: dict[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def deserialize_job(value: bytes) -> dict[str, Any]:
    result = json.loads(value)
    if not isinstance(result, dict):
        raise ValueError("Invalid queued job payload")
    return result


def redis_settings() -> RedisSettings:
    settings = RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    settings.conn_retries = 0
    return settings


def queue_name() -> str:
    value = os.environ.get("ARQ_QUEUE_NAME", "arq:queue")
    if not value:
        raise ValueError("ARQ_QUEUE_NAME must not be empty")
    return value


def max_attempts() -> int:
    try:
        value = int(os.environ.get("ARQ_MAX_ATTEMPTS", "3"))
    except ValueError as exc:
        raise ValueError("ARQ_MAX_ATTEMPTS must be between 1 and 3") from exc
    if not 1 <= value <= 3:
        raise ValueError("ARQ_MAX_ATTEMPTS must be between 1 and 3")
    return value


def job_timeout() -> int:
    try:
        value = int(os.environ.get("ARQ_JOB_TIMEOUT_SECONDS", "1800"))
    except ValueError as exc:
        raise ValueError("ARQ_JOB_TIMEOUT_SECONDS must be a positive integer") from exc
    if value < 1:
        raise ValueError("ARQ_JOB_TIMEOUT_SECONDS must be a positive integer")
    return value


async def connect_queue() -> ArqRedis:
    try:
        queue = await create_pool(
            redis_settings(), default_queue_name=queue_name(),
            job_serializer=serialize_job, job_deserializer=deserialize_job,
        )
        try:
            await queue.ping()
        except (RedisError, OSError, TimeoutError):
            await queue.aclose()
            raise
        return queue
    except (RedisError, OSError, TimeoutError) as exc:
        logger.warning("Background queue is unavailable", exc_info=True)
        raise HTTPException(status_code=503, detail="Background processing is unavailable") from exc


def persist_work(db: Session, job: ProcessingJob, task_name: str, arguments: dict) -> ProcessingOutbox:
    db.add(job)
    db.flush()
    outbox = ProcessingOutbox(processing_job_id=job.id, task_name=task_name, arguments=arguments)
    db.add(outbox)
    db.commit()
    return outbox


async def publish_work(queue: ArqRedis, db: Session, outbox: ProcessingOutbox) -> None:
    try:
        await queue.enqueue_job(
            "execute_processing_job", outbox.processing_job_id,
            _job_id=outbox.processing_job_id, _queue_name=queue_name(),
        )
    except (RedisError, OSError, TimeoutError) as exc:
        logger.warning(
            "Background job enqueue failed or was ambiguous",
            extra={"processing_job_id": outbox.processing_job_id},
            exc_info=True,
        )
        raise HTTPException(status_code=503, detail="Background processing is unavailable") from exc
    outbox.last_dispatched_at = datetime.now(timezone.utc)
    db.commit()

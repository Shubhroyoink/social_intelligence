import json
import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("task_queue.job_manager")

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

JOB_PREFIX = "job:"
JOB_QUEUE_KEY = "queue:social_pipeline"
JOB_INDEX_KEY = "index:jobs"


class JobManager:
    """Async Job Queue and State Manager supporting Redis with automatic in-memory fallback.

    Architecture:
    - If Redis is available, job states are persisted in Redis Hashes / Strings
      and broadcast via Redis channels.
    - If Redis is unavailable or uninstalled, operations fall back transparently
      to thread-safe in-memory stores, guaranteeing zero downtime.
    """

    def __init__(self, host: str = REDIS_HOST, port: int = REDIS_PORT, db: int = REDIS_DB, password: Optional[str] = REDIS_PASSWORD):
        self._redis_client = None
        self._redis_available = False
        self._lock = threading.Lock()
        self._in_memory_jobs: Dict[str, Dict[str, Any]] = {}
        self._in_memory_order: List[str] = []
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pipeline_worker_")

        self._init_redis(host, port, db, password)

    def _init_redis(self, host: str, port: int, db: int, password: Optional[str]):
        try:
            import redis
            # Try 127.0.0.1 first, then localhost
            for target_host in [host, "127.0.0.1", "localhost"]:
                try:
                    client = redis.Redis(
                        host=target_host,
                        port=port,
                        db=db,
                        password=password,
                        decode_responses=True,
                        socket_connect_timeout=2.0,
                        socket_timeout=2.0,
                    )
                    if client.ping():
                        self._redis_client = client
                        self._redis_available = True
                        print(f"[JobManager] Successfully connected to Redis at {target_host}:{port}/{db}")
                        return
                except Exception:
                    continue
            self._redis_client = None
            self._redis_available = False
            print("[JobManager] Redis server not reachable on 127.0.0.1:6379. Using in-memory fallback queue.")
        except ImportError:
            self._redis_client = None
            self._redis_available = False
            print("[JobManager] Python 'redis' library not installed (run 'pip install redis'). Using in-memory fallback queue.")

    @property
    def is_redis_active(self) -> bool:
        if self._redis_available and self._redis_client:
            try:
                if self._redis_client.ping():
                    return True
            except Exception:
                self._redis_available = False
        # Try reconnecting
        self._init_redis(REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD)
        return self._redis_available

    def create_job(self, topic: str, config: Optional[Dict[str, Any]] = None) -> str:
        """Create a new job and return unique job_id."""
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        job_data = {
            "job_id": job_id,
            "topic": topic,
            "status": "queued",
            "percent": 0,
            "current_step": "Initialized",
            "message": f"Job queued for '{topic}'",
            "config": config or {},
            "created_at": now,
            "updated_at": now,
            "error": None,
            "result_summary": None,
        }

        if self._redis_available and self._redis_client:
            try:
                self._redis_client.set(f"{JOB_PREFIX}{job_id}", json.dumps(job_data))
                self._redis_client.lpush(JOB_INDEX_KEY, job_id)
                self._redis_client.ltrim(JOB_INDEX_KEY, 0, 99)  # keep last 100
                return job_id
            except Exception as e:
                logger.warning(f"Redis set failed ({e}), falling back to in-memory store")

        with self._lock:
            self._in_memory_jobs[job_id] = job_data
            self._in_memory_order.insert(0, job_id)
            if len(self._in_memory_order) > 100:
                old = self._in_memory_order.pop()
                self._in_memory_jobs.pop(old, None)

        return job_id

    def update_progress(self, job_id: str, step: str, percent: int, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Update job progress percentage (0-100), current step name, and log message."""
        now = datetime.now(timezone.utc).isoformat()
        clamped_pct = max(0, min(100, int(percent)))

        if self._redis_available and self._redis_client:
            try:
                raw = self._redis_client.get(f"{JOB_PREFIX}{job_id}")
                if raw:
                    data = json.loads(raw)
                    data["status"] = "running"
                    data["current_step"] = step
                    data["percent"] = clamped_pct
                    data["message"] = message
                    data["updated_at"] = now
                    if extra:
                        data.setdefault("extra", {}).update(extra)
                    self._redis_client.set(f"{JOB_PREFIX}{job_id}", json.dumps(data))
                    # Publish progress update
                    try:
                        self._redis_client.publish(f"job_updates:{job_id}", json.dumps({
                            "job_id": job_id, "step": step, "percent": clamped_pct, "message": message
                        }))
                    except Exception:
                        pass
                    return
            except Exception as e:
                logger.warning(f"Redis update failed ({e}), updating in-memory")

        with self._lock:
            if job_id in self._in_memory_jobs:
                data = self._in_memory_jobs[job_id]
                data["status"] = "running"
                data["current_step"] = step
                data["percent"] = clamped_pct
                data["message"] = message
                data["updated_at"] = now
                if extra:
                    data.setdefault("extra", {}).update(extra)

    def set_completed(self, job_id: str, result_summary: Optional[Dict[str, Any]] = None) -> None:
        """Mark job as successfully completed."""
        now = datetime.now(timezone.utc).isoformat()
        if self._redis_available and self._redis_client:
            try:
                raw = self._redis_client.get(f"{JOB_PREFIX}{job_id}")
                if raw:
                    data = json.loads(raw)
                    data["status"] = "completed"
                    data["percent"] = 100
                    data["current_step"] = "Completed"
                    data["message"] = "Pipeline execution completed successfully."
                    data["updated_at"] = now
                    data["result_summary"] = result_summary or {}
                    self._redis_client.set(f"{JOB_PREFIX}{job_id}", json.dumps(data))
                    return
            except Exception as e:
                logger.warning(f"Redis set_completed failed ({e})")

        with self._lock:
            if job_id in self._in_memory_jobs:
                data = self._in_memory_jobs[job_id]
                data["status"] = "completed"
                data["percent"] = 100
                data["current_step"] = "Completed"
                data["message"] = "Pipeline execution completed successfully."
                data["updated_at"] = now
                data["result_summary"] = result_summary or {}

    def set_failed(self, job_id: str, error_message: str) -> None:
        """Mark job as failed with error details."""
        now = datetime.now(timezone.utc).isoformat()
        if self._redis_available and self._redis_client:
            try:
                raw = self._redis_client.get(f"{JOB_PREFIX}{job_id}")
                if raw:
                    data = json.loads(raw)
                    data["status"] = "failed"
                    data["current_step"] = "Failed"
                    data["message"] = f"Failed: {error_message}"
                    data["error"] = str(error_message)
                    data["updated_at"] = now
                    self._redis_client.set(f"{JOB_PREFIX}{job_id}", json.dumps(data))
                    return
            except Exception as e:
                logger.warning(f"Redis set_failed failed ({e})")

        with self._lock:
            if job_id in self._in_memory_jobs:
                data = self._in_memory_jobs[job_id]
                data["status"] = "failed"
                data["current_step"] = "Failed"
                data["message"] = f"Failed: {error_message}"
                data["error"] = str(error_message)
                data["updated_at"] = now

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data by ID."""
        if self._redis_available and self._redis_client:
            try:
                raw = self._redis_client.get(f"{JOB_PREFIX}{job_id}")
                if raw:
                    return json.loads(raw)
            except Exception as e:
                logger.warning(f"Redis get_job failed ({e})")

        with self._lock:
            return self._in_memory_jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List most recent jobs."""
        jobs = []
        if self._redis_available and self._redis_client:
            try:
                job_ids = self._redis_client.lrange(JOB_INDEX_KEY, 0, limit - 1)
                for jid in job_ids:
                    raw = self._redis_client.get(f"{JOB_PREFIX}{jid}")
                    if raw:
                        jobs.append(json.loads(raw))
                return jobs
            except Exception as e:
                logger.warning(f"Redis list_jobs failed ({e})")

        with self._lock:
            for jid in self._in_memory_order[:limit]:
                if jid in self._in_memory_jobs:
                    jobs.append(self._in_memory_jobs[jid])
        return jobs

    def submit_pipeline_job(self, topic: str, run_pipeline_fn: Callable[..., Any], kwargs: Dict[str, Any]) -> str:
        """Create a job and submit it for background async execution with real-time progress tracking."""
        job_id = self.create_job(topic, config={"topic": topic, **{k: v for k, v in kwargs.items() if not callable(v)}})

        def _progress_callback(step: str, percent: int, message: str, extra: Optional[Dict[str, Any]] = None):
            self.update_progress(job_id, step, percent, message, extra)

        def _worker_task():
            try:
                self.update_progress(job_id, "Starting", 5, f"Initializing pipeline execution for '{topic}'...")
                # Pass progress_callback into run_pipeline
                kwargs_with_cb = dict(kwargs)
                kwargs_with_cb["progress_callback"] = _progress_callback
                result = run_pipeline_fn(**kwargs_with_cb)
                
                post_count = len(result) if isinstance(result, list) else 0
                self.set_completed(job_id, result_summary={"posts_processed": post_count, "topic": topic})
            except Exception as ex:
                logger.exception(f"Pipeline job {job_id} failed with error: {ex}")
                self.set_failed(job_id, str(ex))

        self._executor.submit(_worker_task)
        return job_id


# Global singleton instance
_GLOBAL_JOB_MANAGER: Optional[JobManager] = None
_GLOBAL_LOCK = threading.Lock()


def get_job_manager() -> JobManager:
    """Retrieve global JobManager singleton."""
    global _GLOBAL_JOB_MANAGER
    if _GLOBAL_JOB_MANAGER is None:
        with _GLOBAL_LOCK:
            if _GLOBAL_JOB_MANAGER is None:
                _GLOBAL_JOB_MANAGER = JobManager()
    return _GLOBAL_JOB_MANAGER

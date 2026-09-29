import time
import pytest
from task_queue.job_manager import JobManager, get_job_manager


def test_job_manager_creation():
    mgr = JobManager(host="127.0.0.1", port=9999)  # Non-existent Redis port tests in-memory fallback
    assert mgr is not None
    job_id = mgr.create_job("AI Agents", config={"max_videos": 3})
    assert job_id is not None
    assert isinstance(job_id, str)

    job = mgr.get_job(job_id)
    assert job["topic"] == "AI Agents"
    assert job["status"] == "queued"
    assert job["percent"] == 0
    assert job["config"]["max_videos"] == 3


def test_job_manager_progress_update():
    mgr = JobManager(host="127.0.0.1", port=9999)
    job_id = mgr.create_job("Electric Vehicles")

    mgr.update_progress(job_id, "Sentiment Analysis", 55, "Analyzing sentiments with RoBERTa...")
    job = mgr.get_job(job_id)
    assert job["status"] == "running"
    assert job["current_step"] == "Sentiment Analysis"
    assert job["percent"] == 55
    assert "Analyzing sentiments" in job["message"]


def test_job_manager_completion():
    mgr = JobManager(host="127.0.0.1", port=9999)
    job_id = mgr.create_job("Quantum Computing")

    mgr.set_completed(job_id, result_summary={"posts_processed": 120, "topic": "Quantum Computing"})
    job = mgr.get_job(job_id)
    assert job["status"] == "completed"
    assert job["percent"] == 100
    assert job["current_step"] == "Completed"
    assert job["result_summary"]["posts_processed"] == 120


def test_job_manager_failure():
    mgr = JobManager(host="127.0.0.1", port=9999)
    job_id = mgr.create_job("Faulty Job")

    mgr.set_failed(job_id, "Rate limit exceeded on provider")
    job = mgr.get_job(job_id)
    assert job["status"] == "failed"
    assert job["current_step"] == "Failed"
    assert "Rate limit exceeded" in job["error"]


def test_job_manager_list_jobs():
    mgr = JobManager(host="127.0.0.1", port=9999)
    j1 = mgr.create_job("Topic A")
    j2 = mgr.create_job("Topic B")

    jobs = mgr.list_jobs(limit=10)
    job_ids = [j["job_id"] for j in jobs]
    assert j1 in job_ids
    assert j2 in job_ids


def test_job_manager_async_pipeline_execution():
    mgr = JobManager(host="127.0.0.1", port=9999)

    def dummy_pipeline(topic_query, progress_callback=None, **kwargs):
        if progress_callback:
            progress_callback("Step 1", 30, "Doing step 1")
            progress_callback("Step 2", 70, "Doing step 2")
        return [{"id": "1", "text": "sample post"}]

    job_id = mgr.submit_pipeline_job(
        topic="Async Test Topic",
        run_pipeline_fn=dummy_pipeline,
        kwargs={"topic_query": "Async Test Topic"}
    )

    assert job_id is not None

    # Wait for completion (dummy task finishes almost instantly)
    for _ in range(50):
        job = mgr.get_job(job_id)
        if job["status"] in ("completed", "failed"):
            break
        time.sleep(0.05)

    final_job = mgr.get_job(job_id)
    assert final_job["status"] == "completed"
    assert final_job["percent"] == 100
    assert final_job["result_summary"]["posts_processed"] == 1

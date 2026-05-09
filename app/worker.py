from celery import Celery
import os

# Initialize Celery using the Redis URL from environment variables
celery_app = Celery(
    "tasks",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0")
)

@celery_app.task
def run_eval_task(test_case_id: int):
    """Placeholder for the background evaluation task."""
    return f"Processed test case {test_case_id}"
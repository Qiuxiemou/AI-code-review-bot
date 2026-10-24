from redis import Redis
from rq import Queue

redis_connection = Redis.from_url(
    "redis://redis:6379/0"
)

task_queue = Queue(
    "default",
    connection=redis_connection,
)


def enqueue_review(run_id: int):
    job = task_queue.enqueue(
        "worker.tasks.process_pull_request",
        run_id,
        job_timeout=120,
    )

    return job.id

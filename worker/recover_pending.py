from sqlalchemy import select

from app.database import ReviewRun, SessionLocal
from app.queue import enqueue_review


def main():
    with SessionLocal() as session:
        run_ids = session.execute(
            select(ReviewRun.id).where(
                ReviewRun.status == "pending"
            )
        ).scalars().all()

    for run_id in run_ids:
        job_id = enqueue_review(run_id)
        print(f"Enqueued run {run_id}: {job_id}")

    print(f"Recovery scan finished: {len(run_ids)} runs")


if __name__ == "__main__":
    main()

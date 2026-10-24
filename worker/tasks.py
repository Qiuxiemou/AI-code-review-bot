
import os

from sqlalchemy import select

from app.database import (
    Comment,
    ReviewRun,
    SessionLocal,
)
from app.github_client import (
    find_existing_comment,
    post_pr_comment,
    get_repository_id,
)

def process_pull_request(run_id: int):
    print(f"Processing run {run_id}", flush=True)

    owner = "Qiuxiemou"
    repo = "ai-review-test"

    with SessionLocal.begin() as session:
        run = session.execute(
            select(ReviewRun)
            .where(ReviewRun.id == run_id)
            .with_for_update()
        ).scalar_one_or_none()

        if run is None:
            raise ValueError(f"Run {run_id} not found")

        if run.status == "completed":
            print("Already completed, skipping", flush=True)
            return

        if run.status not in ("pending", "failed"):
            print(
                f"Unexpected status: {run.status}",
                flush=True,
            )
            return

        existing_record = session.execute(
            select(Comment).where(
                Comment.review_run_id == run_id
            )
        ).scalar_one_or_none()

        if existing_record is not None:
            run.status = "completed"
            return


        pr_number = run.pr_number

        # 验证数据库任务所属仓库是否正确
        if run.repository_id != get_repository_id(owner, repo):
            raise ValueError(
                "Task repository does not match target repository"
            )

        marker = f"<!-- ai-review-bot:run:{run_id} -->"

        existing_comment_id = find_existing_comment(
            owner,
            repo,
            pr_number,
            marker,
        )


        if existing_comment_id is not None:
            comment_id = existing_comment_id
        else:
            message = (
                f"已收到 PR #{pr_number}，"
                f"已记录本次提交。\n\n{marker}"
            )

            comment_id = post_pr_comment(
                owner,
                repo,
                pr_number,
                message,
            )

        session.add(
            Comment(
                review_run_id=run_id,
                github_comment_id=comment_id,
            )
        )

        run.status = "completed"

    print(
        f"Run {run_id} completed, "
        f"comment ID: {comment_id}",
        flush=True,
    )

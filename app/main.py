from app.queue import enqueue_review
from redis.exceptions import RedisError
import logging

import hashlib
import hmac
import os

from fastapi import FastAPI, HTTPException, Request

from contextlib import asynccontextmanager

from sqlalchemy.dialects.postgresql import insert

from app.database import (
    ReviewRun,
    SessionLocal,
    WebhookDelivery,
    create_tables,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="AI Code Review Bot",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "api"}


def verify_signature(body: bytes, signature: str | None) -> bool:
    """verify GitHub Webhook HMAC-SHA256"""

    secret = os.environ["WEBHOOK_SECRET"]

    if not signature:
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)




@app.post("/webhook", status_code=202)
async def github_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_signature(body, signature):
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook signature",
        )

    event_type = request.headers.get("X-GitHub-Event")
    delivery_id = request.headers.get("X-GitHub-Delivery")

    if not event_type or not delivery_id:
        raise HTTPException(
            status_code=400,
            detail="Missing GitHub event headers",
        )

    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    action = payload.get("action")

    should_create_run = (
        event_type == "pull_request"
        and action in ("opened", "reopened", "synchronize")
    )

    run_values = None

    if should_create_run:
        try:
            run_values = {
                "installation_id": int(payload["installation"]["id"]),
                "repository_id": int(payload["repository"]["id"]),
                "pr_number": int(payload["number"]),
                "head_sha": payload["pull_request"]["head"]["sha"],
                "delivery_id": delivery_id,
                "status": "pending",
            }

            if len(run_values["head_sha"]) != 40:
                raise ValueError("Invalid SHA")

        except (KeyError, TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="Missing or invalid PR fields",
            )

    with SessionLocal.begin() as session:
        delivery_stmt = (
            insert(WebhookDelivery)
            .values(
                delivery_id=delivery_id,
                event_type=event_type,
            )
            .on_conflict_do_nothing(
                index_elements=["delivery_id"]
            )
            .returning(WebhookDelivery.delivery_id)
        )

        inserted_delivery = session.execute(
            delivery_stmt
        ).scalar_one_or_none()

        if inserted_delivery is None:
            return {
                "status": "duplicate_delivery",
                "delivery_id": delivery_id,
            }

        if run_values is not None:
            run_stmt = (
                insert(ReviewRun)
                .values(**run_values)
                .on_conflict_do_nothing(
                    constraint="uq_review_target"
                )
                .returning(ReviewRun.id)
            )

            run_id = session.execute(
                run_stmt
            ).scalar_one_or_none()

            if run_id is None:
                return {
                    "status": "duplicate_pr_version",
                    "delivery_id": delivery_id,
                }


    if run_values is not None:
        try:
            job_id = enqueue_review(run_id)
        except RedisError:
            logging.exception(
                "Failed to enqueue run %s", run_id
            )
            return {
                "status": "recorded_pending_dispatch",
                "delivery_id": delivery_id,
                "run_id": run_id,
            }

        return {
            "status": "queued",
            "delivery_id": delivery_id,
            "run_id": run_id,
            "job_id": job_id,
        }

    return {
        "status": "recorded",
        "delivery_id": delivery_id,
        "event": event_type,
    }


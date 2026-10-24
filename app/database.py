import os
from datetime import datetime
from sqlalchemy import BigInteger
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)


DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    delivery_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )
    event_type: Mapped[str] = mapped_column(String(100))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ReviewRun(Base):
    __tablename__ = "review_runs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    delivery_id: Mapped[str] = mapped_column(
        ForeignKey("webhook_deliveries.delivery_id")
    )

    installation_id: Mapped[int] = mapped_column(Integer)
    repository_id: Mapped[int] = mapped_column(Integer)
    pr_number: Mapped[int] = mapped_column(Integer)
    head_sha: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
    )

    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "repository_id",
            "pr_number",
            "head_sha",
            name="uq_review_target",
        ),
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    review_run_id: Mapped[int] = mapped_column(
        ForeignKey("review_runs.id"),
        unique=True,
        nullable=False,
    )

    github_comment_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

def create_tables():
    Base.metadata.create_all(bind=engine)

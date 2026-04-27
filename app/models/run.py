from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base
from core.enums import RunStatus


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_id: Mapped[str | None] = mapped_column(String, nullable=True)

    status: Mapped[str] = mapped_column(String, default=RunStatus.CREATED)

    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)

    judge_model: Mapped[str] = mapped_column(String)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

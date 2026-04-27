# models/metric_result.py

from sqlalchemy import String, Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base


class MetricResult(Base):
    __tablename__ = "metric_results"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    query_id: Mapped[str] = mapped_column(String, index=True)

    metric_name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    error_type: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

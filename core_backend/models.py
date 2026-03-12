from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from core_backend.database import Base

class Report(Base):
    __tablename__ = "reports"

    id           = Column(Integer, primary_key=True, index=True)
    query        = Column(String, nullable=False)
    signal_label = Column(String, nullable=False)
    confidence   = Column(Float, nullable=False)
    report_text  = Column(Text, nullable=False)
    sources      = Column(String, nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

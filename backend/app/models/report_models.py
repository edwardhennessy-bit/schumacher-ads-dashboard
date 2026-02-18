"""
Database models for report generation history and configuration.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ReportHistory(Base):
    """Track generated reports."""
    __tablename__ = "report_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(50), nullable=False)  # monthly_review, weekly_agenda, weekly_email
    title = Column(String(500), nullable=False)
    url = Column(String(1000), default="")
    date_range_start = Column(String(20), default="")
    date_range_end = Column(String(20), default="")
    status = Column(String(20), default="completed")  # completed, failed, generating
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, default=dict)


class ReportConfig(Base):
    """Store report template configuration."""
    __tablename__ = "report_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(50), unique=True, nullable=False)
    config_json = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

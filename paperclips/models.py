# models.py
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List

db = SQLAlchemy()

class RequestLog(db.Model):
    __tablename__ = "request_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(db.String(50), nullable=True)
    prompt: Mapped[str] = mapped_column(db.Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    responses: Mapped[List["ResponseLog"]] = relationship("ResponseLog", backref="request", lazy=True)
    
    def __init__(self, prompt: str, user_id: Optional[str] = None):
        self.prompt = prompt
        self.user_id = user_id

class ResponseLog(db.Model):
    __tablename__ = "response_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("request_logs.id"), nullable=False)
    completion: Mapped[str] = mapped_column(db.Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __init__(self, request_id: int, completion: str):
        self.request_id = request_id
        self.completion = completion

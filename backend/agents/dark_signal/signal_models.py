from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DarkSignal(BaseModel):
    source: str
    title: str
    summary: str
    url: Optional[str] = None
    entity: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    credibility: float = Field(default=0.0, ge=0.0, le=1.0)
    recency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    published_date: Optional[datetime] = None

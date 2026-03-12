from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class AnalyzeResponse(BaseModel):
    sentiment_label: Literal["positive", "neutral", "negative"]
    sentiment_score: float
    value_level: Literal["high", "medium", "low"]
    industries: list[str]
    themes: list[str]
    risk_summary: str
    evidence: list[str]


class BatchAnalyzeRequest(BaseModel):
    items: list[AnalyzeRequest] = Field(min_length=1, max_length=200)

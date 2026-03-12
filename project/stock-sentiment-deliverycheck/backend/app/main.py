from fastapi import FastAPI

from .analyzer import analyze_text
from .models import AnalyzeRequest, AnalyzeResponse, BatchAnalyzeRequest

app = FastAPI(title="Stock Sentiment Subproject", version="0.2.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "stock-sentiment-subproject", "mode": "local_rule_engine"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    result = analyze_text(payload.text)
    return AnalyzeResponse(**result)


@app.post("/analyze/batch")
def analyze_batch(payload: BatchAnalyzeRequest) -> dict[str, object]:
    rows = [analyze_text(item.text) for item in payload.items]
    return {"count": len(rows), "items": rows, "mode": "local_rule_engine"}

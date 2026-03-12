# stock-sentiment-modecheck3

requirement-driven standalone subproject (no external model dependency).

## Commands

```bash
bash scripts/check.sh
bash scripts/run.sh
bash scripts/seed.sh
bash scripts/autoevolve.sh
bash scripts/today_sentiment.sh
bash scripts/today_sentiment.sh <stamp> "<query>" <limit> A_SHARE
bash backend/run.sh
```

## Structure

- `evolve.json`: requirement and strategy config
- `backend/`: FastAPI sentiment service skeleton
- `frontend/`: static demo page
- `scripts/today_sentiment.sh`: daily sentiment run (A_SHARE default, supports US)
- `reports/`: local run reports

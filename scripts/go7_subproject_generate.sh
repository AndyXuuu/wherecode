#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBPROJECT_KEY="${1:-stock-sentiment}"

REQUIREMENTS=""
MODULE_HINTS="crawl,sentiment,theme,industry,risk"
MAX_MODULES="6"
STRATEGY="balanced"
REQUESTED_BY="go7-generate"
EXECUTE="false"
FORCE_CLEAN="false"

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/go7_subproject_generate.sh [subproject_key] [options]

Options:
  --requirements <text>      required if no existing evolve.json requirements
  --module-hints <csv>       default: crawl,sentiment,theme,industry,risk
  --max-modules <n>          default: 6
  --strategy <speed|balanced|safe>
  --requested-by <name>      default: go7-generate
  --execute <true|false>     default: false
  --force-clean              remove existing subproject dir before regenerate
  -h, --help
USAGE
}

if [[ "${SUBPROJECT_KEY}" == "-h" || "${SUBPROJECT_KEY}" == "--help" || "${SUBPROJECT_KEY}" == "help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --requirements)
      REQUIREMENTS="${2:-}"
      shift
      ;;
    --module-hints)
      MODULE_HINTS="${2:-}"
      shift
      ;;
    --max-modules)
      MAX_MODULES="${2:-}"
      shift
      ;;
    --strategy)
      STRATEGY="${2:-}"
      shift
      ;;
    --requested-by)
      REQUESTED_BY="${2:-}"
      shift
      ;;
    --execute)
      EXECUTE="${2:-}"
      shift
      ;;
    --force-clean)
      FORCE_CLEAN="true"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1"
      usage
      exit 1
      ;;
  esac
  shift
done

SUBPROJECT_DIR="${ROOT_DIR}/project/${SUBPROJECT_KEY}"
SCRIPTS_DIR="${SUBPROJECT_DIR}/scripts"
REPORT_DIR="${SUBPROJECT_DIR}/reports"
CONFIG_PATH="${SUBPROJECT_DIR}/evolve.json"
BACKEND_DIR="${SUBPROJECT_DIR}/backend"
BACKEND_APP_DIR="${BACKEND_DIR}/app"
BACKEND_TEST_DIR="${BACKEND_DIR}/tests"
FRONTEND_DIR="${SUBPROJECT_DIR}/frontend"

if [[ "${FORCE_CLEAN}" == "true" && -d "${SUBPROJECT_DIR}" ]]; then
  rm -rf "${SUBPROJECT_DIR}"
fi

mkdir -p "${SCRIPTS_DIR}" "${REPORT_DIR}" "${BACKEND_APP_DIR}" "${BACKEND_TEST_DIR}" "${FRONTEND_DIR}"

if [[ -z "${REQUIREMENTS}" && -f "${CONFIG_PATH}" ]]; then
  REQUIREMENTS="$(python3 - "${CONFIG_PATH}" <<'PY'
import json
import sys
from pathlib import Path

try:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    payload = {}
print(str(payload.get("requirements") or "").strip())
PY
)"
fi

if [[ -z "${REQUIREMENTS}" ]]; then
  echo "requirements is required (pass --requirements or keep it in existing evolve.json)"
  exit 1
fi

cat > "${SUBPROJECT_DIR}/AGENTS.md" <<'AGENT'
# subproject agent dna

1) update local plan
2) implement
3) run checks
4) update docs
AGENT

cat > "${SUBPROJECT_DIR}/agent.md" <<'AGENT_LEGACY'
# compatibility note
See `AGENTS.md` in the same directory.
AGENT_LEGACY

cat > "${SUBPROJECT_DIR}/README.md" <<EOF2
# ${SUBPROJECT_KEY}

requirement-driven standalone subproject (no external model dependency).

## Commands

\`\`\`bash
bash scripts/check.sh
bash scripts/run.sh
bash scripts/seed.sh
bash scripts/autoevolve.sh
bash scripts/today_sentiment.sh
bash scripts/today_sentiment.sh <stamp> "<query>" <limit> A_SHARE
bash backend/run.sh
\`\`\`

## Structure

- \`evolve.json\`: requirement and strategy config
- \`backend/\`: FastAPI sentiment service skeleton
- \`frontend/\`: static demo page
- \`scripts/today_sentiment.sh\`: daily sentiment run (A_SHARE default, supports US)
- \`reports/\`: local run reports
EOF2

python3 - "${CONFIG_PATH}" "${SUBPROJECT_KEY}" "${REQUIREMENTS}" "${MODULE_HINTS}" "${MAX_MODULES}" "${STRATEGY}" "${REQUESTED_BY}" "${EXECUTE}" <<'PY'
import json
import sys
from pathlib import Path

(
    config_path,
    subproject_key,
    requirements,
    module_hints_csv,
    max_modules_raw,
    strategy_raw,
    requested_by,
    execute_raw,
) = sys.argv[1:]

module_hints = [item.strip() for item in module_hints_csv.split(",") if item.strip()]
if not module_hints:
    module_hints = ["crawl", "sentiment", "theme", "industry", "risk"]

try:
    max_modules = int(max_modules_raw)
except Exception:
    max_modules = 6
if max_modules < 1 or max_modules > 20:
    max_modules = 6

strategy = (strategy_raw or "balanced").strip().lower()
if strategy not in {"speed", "balanced", "safe"}:
    strategy = "balanced"

execute = str(execute_raw).strip().lower() == "true"
payload = {
    "project_name_prefix": subproject_key,
    "task_title": f"{subproject_key} autonomous task",
    "requirements": requirements,
    "module_hints": module_hints,
    "max_modules": max_modules,
    "strategy": strategy,
    "requested_by": requested_by or "go7-generate",
    "execute": execute,
}

Path(config_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

cat > "${SCRIPTS_DIR}/check.sh" <<'CHECK'
#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

required_files=(
  "${DIR}/evolve.json"
  "${DIR}/scripts/run.sh"
  "${DIR}/scripts/seed.sh"
  "${DIR}/scripts/autoevolve.sh"
  "${DIR}/scripts/today_sentiment.sh"
  "${DIR}/backend/app/main.py"
  "${DIR}/backend/app/analyzer.py"
  "${DIR}/backend/app/models.py"
  "${DIR}/backend/tests/test_analyzer.py"
  "${DIR}/frontend/index.html"
)

for path in "${required_files[@]}"; do
  test -f "${path}"
done

python3 -m json.tool "${DIR}/evolve.json" >/dev/null
python3 -m py_compile "${DIR}/backend/app/models.py" "${DIR}/backend/app/analyzer.py" "${DIR}/backend/app/main.py"
PYTHONPATH="${DIR}/backend" python3 -m unittest discover -s "${DIR}/backend/tests" -p 'test_*.py' >/dev/null

echo "subproject checks passed: ${DIR}"
CHECK

cat > "${SCRIPTS_DIR}/seed.sh" <<'SEED'
#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${DIR}/evolve.json"
REPORT_DIR="${DIR}/reports"
LATEST_SUMMARY_PATH="${REPORT_DIR}/latest_seed.json"
STAMP="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "missing config: ${CONFIG_PATH}"
  exit 1
fi

mkdir -p "${REPORT_DIR}"
report_path="${REPORT_DIR}/${STAMP}-seed.json"

python3 - "${CONFIG_PATH}" "${report_path}" "${LATEST_SUMMARY_PATH}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

config_path, report_path, latest_path = sys.argv[1:]
payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
report = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "mode": "local_rule_engine",
    "status": "seeded",
    "project_name_prefix": payload.get("project_name_prefix"),
    "requirements": payload.get("requirements"),
    "module_hints": payload.get("module_hints"),
    "max_modules": payload.get("max_modules"),
    "strategy": payload.get("strategy"),
}
Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
latest = {"updated_at": datetime.now(timezone.utc).isoformat(), "report_path": str(Path(report_path).resolve()), **report}
Path(latest_path).write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

echo "report_written=${report_path}"
echo "latest_summary=${LATEST_SUMMARY_PATH}"
SEED

cat > "${SCRIPTS_DIR}/autoevolve.sh" <<'AUTO'
#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${DIR}/evolve.json"
REPORT_DIR="${DIR}/reports"
LATEST_SEED_PATH="${REPORT_DIR}/latest_seed.json"
LATEST_AUTO_PATH="${REPORT_DIR}/latest_autoevolve.json"
STAMP="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
AUTO_REPORT="${REPORT_DIR}/${STAMP}-autoevolve.json"

if [[ ! -f "${LATEST_SEED_PATH}" ]]; then
  echo "missing ${LATEST_SEED_PATH}; run seed.sh first"
  exit 1
fi

python3 -m py_compile "${DIR}/backend/app/models.py" "${DIR}/backend/app/analyzer.py" "${DIR}/backend/app/main.py"
PYTHONPATH="${DIR}/backend" python3 -m unittest discover -s "${DIR}/backend/tests" -p 'test_*.py' >/dev/null

python3 - "${CONFIG_PATH}" "${AUTO_REPORT}" "${LATEST_AUTO_PATH}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

config_path, auto_report_path, latest_path = sys.argv[1:]
config = json.loads(Path(config_path).read_text(encoding="utf-8"))

sys.path.insert(0, str(Path(config_path).parent / "backend"))
from app.analyzer import analyze_text  # type: ignore

sample_text = (
    f"{config.get('requirements', '')} "
    "Nvidia reports strong chip demand with record growth and profit."
)
sample_result = analyze_text(sample_text)

summary = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "mode": "local_rule_engine",
    "run_id": datetime.now(timezone.utc).strftime("local_%Y%m%dT%H%M%SZ"),
    "final_status": "succeeded",
    "sample_result": sample_result,
}
Path(auto_report_path).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
latest = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "run_id": summary["run_id"],
    "final_status": summary["final_status"],
    "mode": summary["mode"],
    "report_path": str(Path(auto_report_path).resolve()),
}
Path(latest_path).write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(str(Path(auto_report_path)))
print(json.dumps({"run_id": latest["run_id"], "final_status": latest["final_status"], "mode": latest["mode"]}, ensure_ascii=False))
PY
AUTO

cat > "${SCRIPTS_DIR}/run.sh" <<'RUN'
#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"

bash "${DIR}/scripts/check.sh"
bash "${DIR}/scripts/seed.sh" "${STAMP}"
bash "${DIR}/scripts/autoevolve.sh" "${STAMP}"

echo "subproject run done: ${DIR}"
echo "reports: ${DIR}/reports"
RUN

cat > "${SCRIPTS_DIR}/today_sentiment.sh" <<'TODAY'
#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${DIR}/reports"
LATEST_REPORT="${REPORT_DIR}/latest_today_sentiment.json"
STAMP="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
QUERY="${2:-}"
LIMIT="${3:-20}"
MARKET_PROFILE="${4:-A_SHARE}"

mkdir -p "${REPORT_DIR}"
REPORT_PATH="${REPORT_DIR}/${STAMP}-today-sentiment.json"

python3 - "${DIR}" "${QUERY}" "${LIMIT}" "${REPORT_PATH}" "${LATEST_REPORT}" "${MARKET_PROFILE}" <<'PY'
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

root_dir, query_raw, limit_raw, report_path, latest_path, market_profile_raw = sys.argv[1:]
query = str(query_raw).strip()
limit = max(1, min(100, int(limit_raw)))

market_profile = str(market_profile_raw).strip().upper()
if market_profile not in {"A_SHARE", "US"}:
    market_profile = "A_SHARE"

if market_profile == "A_SHARE":
    default_query = "A股 OR 上证指数 OR 深证成指 OR 创业板 OR 沪深300 OR 科创50"
    hl = "zh-CN"
    gl = "CN"
    ceid = "CN:zh-Hans"
else:
    default_query = "stock market OR S&P 500 OR Nasdaq OR Dow Jones"
    hl = "en-US"
    gl = "US"
    ceid = "US:en"

if not query:
    query = default_query

rss_url = (
    "https://news.google.com/rss/search?"
    + urllib.parse.urlencode(
        {
            "q": f"{query} when:1d",
            "hl": hl,
            "gl": gl,
            "ceid": ceid,
        }
    )
)

with urllib.request.urlopen(rss_url, timeout=20) as resp:
    raw = resp.read()
doc = ET.fromstring(raw)
channel = doc.find("channel")
items = []
if channel is not None:
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date_raw = (item.findtext("pubDate") or "").strip()
        if not title:
            continue
        published_at = ""
        published_date = ""
        if pub_date_raw:
            try:
                dt = parsedate_to_datetime(pub_date_raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt_utc = dt.astimezone(timezone.utc)
                published_at = dt_utc.isoformat()
                published_date = dt_utc.date().isoformat()
            except Exception:
                pass
        items.append(
            {
                "title": title,
                "link": link,
                "published_at": published_at,
                "published_date": published_date,
            }
        )

today_utc = datetime.now(timezone.utc).date().isoformat()
today_items = [it for it in items if it.get("published_date") == today_utc]
selected = today_items[:limit]
fallback_used = False
if not selected:
    selected = items[:limit]
    fallback_used = True

sys.path.insert(0, str(Path(root_dir) / "backend"))
from app.analyzer import analyze_text  # type: ignore

if market_profile == "A_SHARE":
    COMPANY_MAP = {
        "贵州茅台": "600519",
        "宁德时代": "300750",
        "比亚迪": "002594",
        "中芯国际": "688981",
        "中国平安": "601318",
        "工商银行": "601398",
        "招商银行": "600036",
        "隆基绿能": "601012",
    }
    INDEX_MAP = {
        "上证指数": "SSE",
        "上证": "SSE",
        "深证成指": "SZSE",
        "深证": "SZSE",
        "创业板": "CHINEXT",
        "沪深300": "CSI300",
        "科创50": "STAR50",
        "a股": "ASHARE",
    }
    SKIP_TICKERS = {"ETF", "CEO", "GDP"}
else:
    COMPANY_MAP = {
        "nvidia": "NVDA",
        "broadcom": "AVGO",
        "tesla": "TSLA",
        "apple": "AAPL",
        "microsoft": "MSFT",
        "amazon": "AMZN",
        "alphabet": "GOOGL",
        "google": "GOOGL",
        "meta": "META",
        "amd": "AMD",
        "intel": "INTC",
        "micron": "MU",
        "palantir": "PLTR",
        "berkshire": "BRK.B",
        "jpmorgan": "JPM",
        "goldman": "GS",
    }
    INDEX_MAP = {
        "s&p 500": "SPX",
        "nasdaq": "IXIC",
        "dow jones": "DJI",
    }
    SKIP_TICKERS = {"US", "ETF", "CEO", "GDP", "NYSE", "NASDAQ"}


def extract_mentions(title: str) -> list[str]:
    lowered = title.lower()
    out: list[str] = []
    for phrase, symbol in INDEX_MAP.items():
        if phrase in lowered:
            out.append(symbol)
    for phrase, symbol in COMPANY_MAP.items():
        if phrase.lower().isascii():
            matched = bool(re.search(r"\b" + re.escape(phrase.lower()) + r"\b", lowered))
        else:
            matched = phrase in title
        if matched:
            out.append(symbol)
    for tk in re.findall(r"\(([A-Z]{1,5})\)", title):
        if tk not in SKIP_TICKERS:
            out.append(tk)
    for tk in re.findall(r"\b(?:NASDAQ|NYSE)\s*:\s*([A-Z]{1,5})\b", title):
        if tk not in SKIP_TICKERS:
            out.append(tk)
    for tk in re.findall(r"\b(?:60\d{4}|68\d{4}|00\d{4}|30\d{4})\b", title):
        out.append(tk)
    return sorted(set(out))


rows = []
scores = []
labels = []
industry_counts: Counter[str] = Counter()
theme_counts: Counter[str] = Counter()
stock_stats: dict[str, dict[str, object]] = {}
matrix_counter: Counter[tuple[str, str]] = Counter()
for item in selected:
    analysis = analyze_text(item["title"])
    score = float(analysis.get("sentiment_score", 0.0))
    label = str(analysis.get("sentiment_label", "neutral"))
    industries = [str(x) for x in (analysis.get("industries") or [])]
    themes = [str(x) for x in (analysis.get("themes") or [])]
    risk_summary = str(analysis.get("risk_summary") or "")
    mentions = extract_mentions(item["title"])
    scores.append(score)
    labels.append(label)
    industry_counts.update(industries)
    theme_counts.update(themes)
    matrix_industries = industries or ["none"]
    matrix_themes = themes or ["none"]
    for ind in matrix_industries:
        for th in matrix_themes:
            matrix_counter[(ind, th)] += 1

    for symbol in mentions:
        row = stock_stats.setdefault(
            symbol,
            {
                "symbol": symbol,
                "mentions": 0,
                "scores": [],
                "label_counts": Counter(),
                "industry_counts": Counter(),
                "theme_counts": Counter(),
                "risk_counts": Counter(),
                "headlines": [],
            },
        )
        row["mentions"] = int(row["mentions"]) + 1
        row["scores"].append(score)
        row["label_counts"][label] += 1
        row["industry_counts"].update(industries)
        row["theme_counts"].update(themes)
        if "risk signals:" in risk_summary:
            tags = [x.strip() for x in risk_summary.replace("risk signals:", "").split(",") if x.strip()]
            row["risk_counts"].update(tags)
        if len(row["headlines"]) < 3:
            row["headlines"].append(item["title"])

    rows.append(
        {
            **item,
            "stock_mentions": mentions,
            "analysis": analysis,
        }
    )

avg_score = (sum(scores) / len(scores)) if scores else 0.0
label_counts = dict(Counter(labels))
if avg_score > 0.5:
    overall = "positive"
elif avg_score < -0.5:
    overall = "negative"
else:
    overall = "neutral"

stock_entities: list[dict[str, object]] = []
for symbol, row in stock_stats.items():
    stock_scores = row["scores"]
    avg = (sum(stock_scores) / len(stock_scores)) if stock_scores else 0.0
    if avg > 0.5:
        sentiment = "positive"
    elif avg < -0.5:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    stock_entities.append(
        {
            "symbol": symbol,
            "mentions": row["mentions"],
            "average_sentiment_score": avg,
            "overall_sentiment": sentiment,
            "label_counts": dict(row["label_counts"]),
            "industries": [k for k, _ in row["industry_counts"].most_common(5)],
            "themes": [k for k, _ in row["theme_counts"].most_common(5)],
            "risk_tags": [k for k, _ in row["risk_counts"].most_common(5)],
            "sample_headlines": row["headlines"],
        }
    )
stock_entities.sort(key=lambda x: (-int(x["mentions"]), -float(x["average_sentiment_score"]), str(x["symbol"])))

industry_theme_matrix: dict[str, dict[str, int]] = {}
for (industry, theme), count in matrix_counter.items():
    row = industry_theme_matrix.setdefault(industry, {})
    row[theme] = count

payload = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "mode": "local_rule_engine",
    "model_dependency": False,
    "market_profile": market_profile,
    "query": query,
    "source": "Google News RSS",
    "source_url": rss_url,
    "today_utc": today_utc,
    "fallback_used": fallback_used,
    "selected_count": len(rows),
    "overall_sentiment": overall,
    "average_sentiment_score": avg_score,
    "label_counts": label_counts,
    "industry_counts": dict(industry_counts),
    "theme_counts": dict(theme_counts),
    "industry_theme_matrix": industry_theme_matrix,
    "stock_entities": stock_entities,
    "items": rows,
}

Path(report_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
latest = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "report_path": str(Path(report_path).resolve()),
    "mode": payload["mode"],
    "model_dependency": payload["model_dependency"],
    "market_profile": payload["market_profile"],
    "overall_sentiment": payload["overall_sentiment"],
    "average_sentiment_score": payload["average_sentiment_score"],
    "selected_count": payload["selected_count"],
    "fallback_used": payload["fallback_used"],
}
Path(latest_path).write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(str(Path(report_path)))
print(
    json.dumps(
        {
            **{k: latest[k] for k in ["overall_sentiment", "average_sentiment_score", "selected_count", "fallback_used"]},
            "market_profile": latest["market_profile"],
            "stock_entities_count": len(stock_entities),
        },
        ensure_ascii=False,
    )
)
PY
TODAY

cat > "${BACKEND_DIR}/requirements.txt" <<'REQ'
fastapi==0.115.0
uvicorn==0.30.6
pydantic==2.9.2
REQ

cat > "${BACKEND_DIR}/run.sh" <<'BRUN'
#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${DIR}"

python3 -m uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-18080}" --reload
BRUN

cat > "${BACKEND_APP_DIR}/__init__.py" <<'PY'
"""Stock sentiment backend package."""
PY

cat > "${BACKEND_APP_DIR}/models.py" <<'PY'
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
PY

cat > "${BACKEND_APP_DIR}/analyzer.py" <<'PY'
from __future__ import annotations

import re

POSITIVE_WORDS = {
    "beat", "growth", "upgrade", "bullish", "breakthrough", "record", "strong", "profit", "surge", "win",
    "上涨", "反弹", "增长", "盈利", "回暖", "新高", "利好", "增持", "突破"
}
NEGATIVE_WORDS = {
    "miss", "drop", "downgrade", "bearish", "investigation", "fraud", "risk", "loss", "weak", "decline",
    "下跌", "下挫", "暴跌", "亏损", "风险", "调查", "减持", "预警", "违约", "下调"
}

THEME_KEYWORDS = {
    "compute": ["gpu", "accelerator", "chipset", "infrastructure", "算力", "服务器"],
    "semiconductor": ["chip", "semiconductor", "wafer", "fab", "芯片", "半导体", "晶圆"],
    "new_energy": ["ev", "electric vehicle", "battery", "charging", "新能源", "光伏", "风电", "储能", "锂电"],
    "biotech": ["drug", "clinical", "trial", "biotech", "医药", "创新药", "生物医药", "临床"],
    "consumer": ["消费", "白酒", "家电", "零售", "旅游", "餐饮"],
    "military": ["军工", "国防", "航天", "船舶"],
}

INDUSTRY_KEYWORDS = {
    "technology": ["software", "cloud", "saas", "platform", "app", "科技", "软件", "互联网", "半导体", "芯片"],
    "finance": ["bank", "broker", "fund", "credit", "insurance", "银行", "证券", "券商", "保险", "基金"],
    "healthcare": ["health", "hospital", "pharma", "medical", "医疗", "医药", "医院", "制药"],
    "energy": ["oil", "gas", "solar", "wind", "energy", "新能源", "光伏", "风电", "煤炭", "石油", "天然气"],
    "consumer": ["消费", "白酒", "家电", "零售", "文旅", "餐饮"],
}

RISK_KEYWORDS = {
    "regulation": ["regulation", "regulator", "ban", "probe", "监管", "问询", "调查", "处罚"],
    "liquidity": ["debt", "liquidity", "cash burn", "default", "债务", "流动性", "违约", "现金流"],
    "execution": ["delay", "recall", "supply chain", "shortage", "延期", "召回", "供应链", "短缺"],
}


def _count_hits(text: str, keywords: set[str]) -> int:
    lowered = text.lower()
    return sum(1 for kw in keywords if kw and kw.lower() in lowered)


def _match_by_keyword(text: str, mapping: dict[str, list[str]]) -> list[str]:
    lowered = text.lower()
    hits: list[str] = []
    for name, words in mapping.items():
        if any(word in lowered for word in words):
            hits.append(name)
    return sorted(set(hits))


def analyze_text(text: str) -> dict[str, object]:
    pos = _count_hits(text, POSITIVE_WORDS)
    neg = _count_hits(text, NEGATIVE_WORDS)

    score = float(pos - neg)
    if score > 1:
        label = "positive"
    elif score < -1:
        label = "negative"
    else:
        label = "neutral"

    themes = _match_by_keyword(text, THEME_KEYWORDS)
    industries = _match_by_keyword(text, INDUSTRY_KEYWORDS)
    risks = _match_by_keyword(text, RISK_KEYWORDS)

    if label == "positive" and len(risks) == 0 and len(themes) > 0:
        value_level = "high"
    elif label == "negative" or len(risks) >= 2:
        value_level = "low"
    else:
        value_level = "medium"

    if not risks:
        risk_summary = "no obvious short-term risk keywords"
    else:
        risk_summary = "risk signals: " + ", ".join(risks)

    evidence = [
        f"positive_hits={pos}",
        f"negative_hits={neg}",
        f"themes={','.join(themes) if themes else 'none'}",
        f"industries={','.join(industries) if industries else 'none'}",
        f"risks={','.join(risks) if risks else 'none'}",
    ]

    return {
        "sentiment_label": label,
        "sentiment_score": score,
        "value_level": value_level,
        "industries": industries,
        "themes": themes,
        "risk_summary": risk_summary,
        "evidence": evidence,
    }
PY

cat > "${BACKEND_APP_DIR}/main.py" <<'PY'
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
PY

cat > "${BACKEND_TEST_DIR}/test_analyzer.py" <<'PY'
import unittest

from app.analyzer import analyze_text


class AnalyzerTestCase(unittest.TestCase):
    def test_positive_signal(self) -> None:
        row = analyze_text("chip breakthrough with strong growth and record profit")
        self.assertEqual(row["sentiment_label"], "positive")
        self.assertIn(row["value_level"], {"high", "medium"})

    def test_negative_signal(self) -> None:
        row = analyze_text("company faces investigation and loss with debt risk")
        self.assertEqual(row["sentiment_label"], "negative")
        self.assertEqual(row["value_level"], "low")


if __name__ == "__main__":
    unittest.main()
PY

cat > "${FRONTEND_DIR}/index.html" <<'HTML'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Stock Sentiment Console</title>
    <style>
      :root {
        --bg: #f6f8fb;
        --panel: #ffffff;
        --ink: #1f2937;
        --accent: #0f766e;
      }
      body {
        margin: 0;
        font-family: "IBM Plex Sans", "Noto Sans", sans-serif;
        color: var(--ink);
        background: radial-gradient(circle at top right, #dff6f0, var(--bg));
      }
      main {
        max-width: 860px;
        margin: 24px auto;
        background: var(--panel);
        border-radius: 14px;
        box-shadow: 0 12px 36px rgba(15, 118, 110, 0.14);
        padding: 24px;
      }
      textarea {
        width: 100%;
        min-height: 120px;
        border-radius: 8px;
        border: 1px solid #cbd5e1;
        padding: 10px;
        font-size: 14px;
      }
      button {
        margin-top: 10px;
        background: var(--accent);
        color: #fff;
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        cursor: pointer;
      }
      pre {
        background: #111827;
        color: #d1fae5;
        border-radius: 8px;
        padding: 12px;
        overflow-x: auto;
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Stock Sentiment Console (No External Model Dependency)</h1>
      <p>This subproject runs fully local with deterministic keyword rules.</p>
      <textarea id="input">Nvidia reports strong chip demand with record growth.</textarea>
      <br />
      <button id="analyze">Analyze</button>
      <pre id="output">{}</pre>
    </main>

    <script>
      const analyzeButton = document.getElementById("analyze");
      const output = document.getElementById("output");
      const input = document.getElementById("input");

      analyzeButton.addEventListener("click", async () => {
        output.textContent = "loading...";
        try {
          const resp = await fetch("http://127.0.0.1:18080/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: input.value }),
          });
          const data = await resp.json();
          output.textContent = JSON.stringify(data, null, 2);
        } catch (err) {
          output.textContent = String(err);
        }
      });
    </script>
  </body>
</html>
HTML

chmod +x "${SCRIPTS_DIR}/check.sh" "${SCRIPTS_DIR}/seed.sh" "${SCRIPTS_DIR}/autoevolve.sh" "${SCRIPTS_DIR}/today_sentiment.sh" "${SCRIPTS_DIR}/run.sh" "${BACKEND_DIR}/run.sh"

echo "subproject generated: ${SUBPROJECT_DIR}"
echo "code scaffold ready: ${BACKEND_DIR} + ${FRONTEND_DIR}"
echo "mode: local_rule_engine"

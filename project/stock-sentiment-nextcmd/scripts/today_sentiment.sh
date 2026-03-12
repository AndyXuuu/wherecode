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

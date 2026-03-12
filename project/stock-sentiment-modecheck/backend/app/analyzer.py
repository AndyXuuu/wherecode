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

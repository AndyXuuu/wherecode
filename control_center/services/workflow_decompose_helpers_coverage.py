from __future__ import annotations

import json
import re


def coverage_tag_keyword_map() -> dict[str, tuple[str, ...]]:
    return {
        "crawl": ("crawl", "crawler", "collect", "ingest", "抓取", "采集"),
        "sentiment": ("sentiment", "opinion", "舆情", "情绪"),
        "ai_interpret": ("ai", "llm", "interpret", "解读"),
        "value_eval": ("value", "valuation", "eval", "估值", "评估"),
        "industry": ("industry", "sector", "行业"),
        "theme": ("theme", "topic", "题材"),
        "report": ("report", "daily", "dashboard", "报告", "日报"),
    }


def coverage_tag_default_module_map() -> dict[str, str]:
    return {
        "crawl": "crawl-ingestion",
        "sentiment": "sentiment-analysis",
        "ai_interpret": "ai-interpretation",
        "value_eval": "value-evaluation",
        "industry": "industry-analysis",
        "theme": "theme-analysis",
        "report": "reporting-dashboard",
    }


def keyword_matches_haystack(haystack: str, keyword: str) -> bool:
    needle = keyword.strip().lower()
    if not needle:
        return False
    if re.fullmatch(r"[a-z0-9_]+", needle):
        return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None
    return needle in haystack


def normalize_module_key(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not normalized:
        return ""
    if normalized[0].isdigit():
        normalized = f"module-{normalized}"
    return normalized


def normalize_module_candidates(values: list[object]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str):
            candidate = value.strip()
        elif isinstance(value, dict):
            candidate = ""
            for key in ("module_key", "module", "key", "name"):
                raw = value.get(key)
                if isinstance(raw, str) and raw.strip():
                    candidate = raw.strip()
                    break
        else:
            candidate = ""

        if not candidate:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        output.append(candidate)
    return output


def extract_modules_from_metadata(metadata: dict[str, object]) -> list[str]:
    if not isinstance(metadata, dict):
        return []

    candidates: list[object] = []
    direct_modules = metadata.get("modules")
    if isinstance(direct_modules, list):
        candidates.extend(direct_modules)

    module_keys = metadata.get("module_keys")
    if isinstance(module_keys, list):
        candidates.extend(module_keys)

    decomposition = metadata.get("decomposition")
    if isinstance(decomposition, dict):
        nested = decomposition.get("modules")
        if isinstance(nested, list):
            candidates.extend(nested)

    modules_json = metadata.get("modules_json")
    if isinstance(modules_json, str) and modules_json.strip():
        try:
            parsed = json.loads(modules_json)
            if isinstance(parsed, list):
                candidates.extend(parsed)
        except json.JSONDecodeError:
            pass

    return normalize_module_candidates(candidates)


def extract_modules_from_summary(summary: str) -> list[str]:
    raw = summary.strip()
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        modules = parsed.get("modules")
        if isinstance(modules, list):
            return normalize_module_candidates(modules)
    if isinstance(parsed, list):
        return normalize_module_candidates(parsed)

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    by_prefix: list[object] = []
    for line in lines:
        if ":" not in line:
            continue
        prefix, value = line.split(":", 1)
        if prefix.strip().lower() in {"module", "module_key"} and value.strip():
            by_prefix.append(value.strip())
    if by_prefix:
        return normalize_module_candidates(by_prefix)
    return []


def derive_required_coverage_tags(
    *,
    requirements: str,
    module_hints: list[str],
) -> list[str]:
    tags_by_keyword = coverage_tag_keyword_map()
    haystack = f"{requirements} {' '.join(module_hints)}".lower()
    output: list[str] = []
    for tag, keywords in tags_by_keyword.items():
        if any(keyword_matches_haystack(haystack, keyword) for keyword in keywords):
            output.append(tag)
    return output


def extract_declared_coverage_tags(metadata: dict[str, object]) -> set[str]:
    if not isinstance(metadata, dict):
        return set()

    collected: set[str] = set()

    def _add(values: object) -> None:
        if isinstance(values, list):
            for item in values:
                if isinstance(item, str) and item.strip():
                    collected.add(item.strip().lower())

    _add(metadata.get("coverage_tags"))

    decomposition = metadata.get("decomposition")
    if isinstance(decomposition, dict):
        _add(decomposition.get("coverage_tags"))
        module_items = decomposition.get("modules")
        if isinstance(module_items, list):
            for item in module_items:
                if isinstance(item, dict):
                    _add(item.get("coverage_tags"))
    return collected


def infer_coverage_tags_from_module_key(module_key: str) -> set[str]:
    normalized = module_key.strip().lower()
    detected: set[str] = set()
    for tag, keywords in coverage_tag_keyword_map().items():
        if any(keyword_matches_haystack(normalized, keyword) for keyword in keywords):
            detected.add(tag)
    return detected


def infer_coverage_tags_from_module_keys(module_keys: list[str]) -> set[str]:
    detected: set[str] = set()
    for key in module_keys:
        detected.update(infer_coverage_tags_from_module_key(key))
    return detected


def validate_decomposition_coverage(
    requirements: str,
    module_hints: list[str],
    modules: list[str],
    chief_metadata: dict[str, object],
) -> tuple[list[str], list[str]]:
    required_tags = derive_required_coverage_tags(
        requirements=requirements,
        module_hints=module_hints,
    )
    if not required_tags:
        return [], []

    detected_tags = infer_coverage_tags_from_module_keys(modules)
    detected_tags.update(extract_declared_coverage_tags(chief_metadata))
    missing_tags = [tag for tag in required_tags if tag not in detected_tags]
    return required_tags, missing_tags


def extract_requirement_module_map(
    chief_metadata: dict[str, object],
) -> tuple[dict[str, list[str]], bool]:
    if not isinstance(chief_metadata, dict):
        return {}, False

    mapping: dict[str, list[str]] = {}
    explicit = False

    def _upsert(tag_key: object, module_values: object) -> None:
        tag = str(tag_key).strip().lower()
        if not tag:
            return
        values: list[str] = []
        if isinstance(module_values, list):
            for item in module_values:
                if isinstance(item, str) and item.strip():
                    values.append(item.strip())
        elif isinstance(module_values, str) and module_values.strip():
            values.append(module_values.strip())
        if not values:
            return
        existing = mapping.get(tag, [])
        for module in values:
            if module not in existing:
                existing.append(module)
        mapping[tag] = existing

    direct_map = chief_metadata.get("requirement_module_map")
    if isinstance(direct_map, dict):
        explicit = True
        for key, value in direct_map.items():
            _upsert(key, value)

    decomposition = chief_metadata.get("decomposition")
    if isinstance(decomposition, dict):
        nested_map = decomposition.get("requirement_module_map")
        if isinstance(nested_map, dict):
            explicit = True
            for key, value in nested_map.items():
                _upsert(key, value)

        module_items = decomposition.get("modules")
        if isinstance(module_items, list):
            for item in module_items:
                if not isinstance(item, dict):
                    continue
                module_key = item.get("module_key")
                coverage_tags = item.get("coverage_tags")
                if isinstance(module_key, str) and module_key.strip() and isinstance(
                    coverage_tags, list
                ):
                    explicit = True
                    for tag in coverage_tags:
                        _upsert(tag, [module_key])

    return mapping, explicit


def infer_requirement_module_map_from_modules(
    modules: list[str],
) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for module_key in modules:
        for tag in infer_coverage_tags_from_module_key(module_key):
            existing = mapping.get(tag, [])
            if module_key not in existing:
                existing.append(module_key)
            mapping[tag] = existing
    return mapping


def validate_requirement_module_mapping(
    required_tags: list[str],
    modules: list[str],
    chief_metadata: dict[str, object],
) -> tuple[dict[str, list[str]], list[str], dict[str, list[str]], bool]:
    mapping, explicit = extract_requirement_module_map(chief_metadata)

    if not mapping:
        mapping = infer_requirement_module_map_from_modules(modules)

    modules_set = {item.strip() for item in modules if item.strip()}
    normalized_mapping: dict[str, list[str]] = {}
    invalid_modules: dict[str, list[str]] = {}
    for tag, raw_modules in mapping.items():
        valid_items: list[str] = []
        invalid_items: list[str] = []
        for module_key in raw_modules:
            normalized = module_key.strip()
            if not normalized:
                continue
            if normalized in modules_set:
                if normalized not in valid_items:
                    valid_items.append(normalized)
            else:
                if normalized not in invalid_items:
                    invalid_items.append(normalized)
        if valid_items:
            normalized_mapping[tag] = valid_items
        if invalid_items:
            invalid_modules[tag] = invalid_items

    missing_tags = [tag for tag in required_tags if not normalized_mapping.get(tag)]
    return normalized_mapping, missing_tags, invalid_modules, explicit


def build_synthetic_decomposition_fallback(
    requirements: str,
    module_hints: list[str],
    max_modules: int,
    *,
    infer_default_task_packages_handler,
) -> dict[str, object] | None:
    required_tags = derive_required_coverage_tags(
        requirements=requirements,
        module_hints=module_hints,
    )
    modules: list[str] = []
    seen: set[str] = set()

    def _add_module(candidate: str) -> None:
        key = normalize_module_key(candidate)
        if not key or key in seen:
            return
        seen.add(key)
        modules.append(key)

    for hint in module_hints:
        _add_module(hint)

    default_tag_modules = coverage_tag_default_module_map()
    for tag in required_tags:
        if any(
            tag in infer_coverage_tags_from_module_key(module_key)
            for module_key in modules
        ):
            continue
        fallback_module = default_tag_modules.get(tag, f"{tag}-module")
        _add_module(fallback_module)

    if not modules:
        _add_module("core-implementation")

    if len(modules) > max_modules:
        prioritized: list[str] = []
        remaining_tags = set(required_tags)
        for module in modules:
            module_tags = infer_coverage_tags_from_module_key(module)
            if not prioritized or (remaining_tags and (module_tags & remaining_tags)):
                prioritized.append(module)
                remaining_tags -= module_tags
            if len(prioritized) >= max_modules:
                break
        if len(prioritized) < max_modules:
            for module in modules:
                if module in prioritized:
                    continue
                prioritized.append(module)
                if len(prioritized) >= max_modules:
                    break
        modules = prioritized[:max_modules]

    requirement_module_map = infer_requirement_module_map_from_modules(modules)
    if required_tags:
        default_module = modules[0] if modules else "core-implementation"
        for tag in required_tags:
            if requirement_module_map.get(tag):
                continue
            preferred_module = normalize_module_key(default_tag_modules.get(tag, f"{tag}-module"))
            target_module = default_module
            if (
                preferred_module
                and preferred_module not in modules
                and len(modules) < max_modules
            ):
                modules.append(preferred_module)
            if preferred_module and preferred_module in modules:
                target_module = preferred_module
            requirement_module_map[tag] = [target_module]

    return {
        "modules": modules,
        "required_tags": required_tags,
        "requirement_module_map": requirement_module_map,
        "module_task_packages": infer_default_task_packages_handler(modules),
    }

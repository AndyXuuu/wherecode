from __future__ import annotations


def serialize_verify_policy_registry(payload: dict[str, object]) -> dict[str, object]:
    profiles_payload = payload.get("profiles")
    serialized_profiles: dict[str, dict[str, object]] = {}
    if isinstance(profiles_payload, dict):
        for key, value in profiles_payload.items():
            profile_name = str(key).strip().lower()
            if not profile_name or not isinstance(value, dict):
                continue
            profile_entry: dict[str, object] = {}
            allowed_resolvers = value.get("allowed_resolvers")
            if isinstance(allowed_resolvers, set):
                profile_entry["allowed_resolvers"] = sorted(
                    str(item).strip()
                    for item in allowed_resolvers
                    if str(item).strip()
                )
            elif isinstance(allowed_resolvers, list):
                profile_entry["allowed_resolvers"] = sorted(
                    {
                        str(item).strip()
                        for item in allowed_resolvers
                        if str(item).strip()
                    }
                )
            for field in (
                "preflight_slo_min_pass_rate",
                "preflight_slo_max_consecutive_failures",
                "verify_slo_min_pass_rate",
                "verify_slo_max_fetch_failures",
            ):
                if field in value and value[field] is not None:
                    profile_entry[field] = value[field]
            serialized_profiles[profile_name] = profile_entry
    return {
        "default_profile": str(payload.get("default_profile", "")).strip().lower(),
        "profiles": serialized_profiles,
    }


def normalize_verify_policy_registry(
    payload: dict[str, object],
    *,
    allowed_resolvers: set[str],
) -> dict[str, object]:
    default_profile = str(payload.get("default_profile", "")).strip().lower()
    profiles_payload = payload.get("profiles", {})
    if profiles_payload is None:
        profiles_payload = {}
    if not isinstance(profiles_payload, dict):
        raise ValueError("verify policy registry profiles must be object")
    normalized_profiles: dict[str, dict[str, object]] = {}
    for key, value in profiles_payload.items():
        profile_name = str(key).strip().lower()
        if not profile_name:
            continue
        if not isinstance(value, dict):
            raise ValueError(f"invalid verify policy profile: {profile_name}")
        profile_entry: dict[str, object] = {}
        if "allowed_resolvers" in value:
            raw_allowed_resolvers = value.get("allowed_resolvers")
            if not isinstance(raw_allowed_resolvers, list):
                raise ValueError(
                    f"invalid allowed_resolvers in verify policy profile: {profile_name}"
                )
            normalized_allowed_resolvers = {
                str(item).strip()
                for item in raw_allowed_resolvers
                if str(item).strip()
            }
            invalid_resolvers = sorted(
                normalized_allowed_resolvers - allowed_resolvers
            )
            if invalid_resolvers:
                raise ValueError(
                    "invalid allowed_resolvers in verify policy profile: "
                    + ",".join(invalid_resolvers)
                )
            profile_entry["allowed_resolvers"] = normalized_allowed_resolvers
        for field in (
            "preflight_slo_min_pass_rate",
            "verify_slo_min_pass_rate",
        ):
            if field not in value or value[field] is None:
                continue
            raw_value = value[field]
            if not isinstance(raw_value, (int, float)):
                raise ValueError(
                    f"invalid {field} in verify policy profile: {profile_name}"
                )
            float_value = float(raw_value)
            if not (0.0 <= float_value <= 1.0):
                raise ValueError(
                    f"invalid {field} in verify policy profile: {profile_name}"
                )
            profile_entry[field] = float_value
        for field in (
            "preflight_slo_max_consecutive_failures",
            "verify_slo_max_fetch_failures",
        ):
            if field not in value or value[field] is None:
                continue
            raw_value = value[field]
            if not isinstance(raw_value, (int, float)):
                raise ValueError(
                    f"invalid {field} in verify policy profile: {profile_name}"
                )
            int_value = int(raw_value)
            if int_value < 0:
                raise ValueError(
                    f"invalid {field} in verify policy profile: {profile_name}"
                )
            profile_entry[field] = int_value
        normalized_profiles[profile_name] = profile_entry
    return {
        "default_profile": default_profile,
        "profiles": normalized_profiles,
    }

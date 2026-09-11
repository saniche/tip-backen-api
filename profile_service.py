from collections import OrderedDict

PRECEDENCE = ["user_edited", "extracted", "inferred"]


def consolidate_profile_fragments(fragments):
    merged = OrderedDict()
    for fragment in fragments:
        data = fragment.get("data", {}) or {}
        source = fragment.get("evidence_type") or "extracted"
        for key, value in data.items():
            if key not in merged:
                merged[key] = {"value": value, "source": source}
                continue
            current = merged[key]
            if PRECEDENCE.index(source) < PRECEDENCE.index(current["source"]):
                merged[key] = {"value": value, "source": source}
    return {key: payload["value"] for key, payload in merged.items()}


def merge_profile_values(existing_data, existing_evidence, fragments):
    merged = consolidate_profile_fragments(fragments)
    evidence = dict(existing_evidence or {})
    for key, value in (existing_data or {}).items():
        if key == "__evidence__":
            continue
        if evidence.get(key) == "user_edited":
            merged[key] = value
    for fragment in fragments:
        source = fragment.get("evidence_type") or "extracted"
        for key in fragment.get("data") or {}:
            if evidence.get(key) != "user_edited":
                evidence[key] = source
    return merged, evidence

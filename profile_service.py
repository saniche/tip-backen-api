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

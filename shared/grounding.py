"""Shared grounding checks for LLM-written documents (tailored CVs and cover letters).

Two checks with different strictness, because the two documents carry different risks:

* ``unsupported_terms`` (strict, used for CV bullets): every meaningful word of a claim must come
  from the cited evidence. Function words, inflections of evidence words and a few neutral
  verbs are tolerated so natural phrasing no longer fails; numbers and role/seniority words
  still have to be backed by the evidence.
* ``unsupported_facts`` (fact-focused, used for cover letters): prose is free, but anything that
  looks like a fact (number, proper noun, technology, seniority claim) must exist somewhere in
  the supplied profile/job context.
"""

import re
from collections.abc import Iterable

_WORD = re.compile(r"\w+", re.UNICODE)
_FACT_TOKEN = re.compile(r"\w[\w#+.\-]*", re.UNICODE)

STOPWORDS_EN = frozenset(
    """
    about above after again also among and any are around because been before being between both but
    can could during each either else every for from had has have her his how into its just like made
    make many may more most much must not now off once only other our out over own per same she should
    since some such than that the their them then there these they this those through throughout till
    too under until upon very was were what when where whether which while who whom why will with within
    without would you your across along while whose via
    """.split()
)
STOPWORDS_FR = frozenset(
    """
    afin ainsi alors apres aupres aussi autre autres avec avoir avons chaque chez comme dans depuis dont
    elle elles entre est etre fait fois ici ils leur leurs lors mais meme mes mon nous notre nos par
    parmi pas pendant plus pour puis quand que quel quelle quels qui sans ses son sont sous sur tous
    tout toute toutes tres une vers vos votre vous cette ces cet comme ainsi donc ont ete etait
    """.split()
)
# Neutral technical verbs that add no factual claim. Leadership verbs (led, managed, directed,
# spearheaded, architected...) are deliberately absent: they inflate the role.
NEUTRAL_WORDS = frozenset(
    """
    tailored profile candidate target role resume curriculum vitae experience built developed
    implemented delivered created maintained improved supported worked working used using applied
    contributed collaborated tested deployed integrated
    """.split()
)
# Seniority / leadership claims must appear in the sources if the model uses them.
INFLATION_TERMS = frozenset(
    """
    led senior lead leader leading principal director head manager managing architect chief staff
    expert executive vp founder owner
    """.split()
)


def _strip_accents_lite(word: str) -> str:
    return (
        word.replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ç", "c")
        .replace("ù", "u")
        .replace("ô", "o")
        .replace("î", "i")
        .replace("â", "a")
        .replace("û", "u")
    )


def word_stems(word: str) -> set[str]:
    """Candidate base forms so 'APIs' ~ 'API', 'building' ~ 'build', 'makes' ~ 'make', 'running' ~ 'run'."""
    lowered = word.lower()
    stems = {lowered}
    for suffix in ("ing", "ed", "es", "s"):
        if not lowered.endswith(suffix) or len(lowered) - len(suffix) < 3:
            continue
        if suffix == "s" and lowered.endswith("ss"):
            continue
        base = lowered[: -len(suffix)]
        stems.add(base)
        if suffix in ("ing", "ed", "es"):
            stems.add(base + "e")
        if len(base) >= 3 and base[-1] == base[-2]:
            stems.add(base[:-1])
    return stems


_FUNCTION_EXACT = frozenset(_strip_accents_lite(w) for w in STOPWORDS_EN | STOPWORDS_FR)
_NEUTRAL_STEMS = frozenset(stem for w in NEUTRAL_WORDS for stem in word_stems(w))


def _is_function_word(word: str) -> bool:
    lowered = word.lower()
    return _strip_accents_lite(lowered) in _FUNCTION_EXACT or bool(word_stems(lowered) & _NEUTRAL_STEMS)


def _stems_of_text(text: str) -> set[str]:
    return {stem for word in _WORD.findall(text) for stem in word_stems(word)}


def unsupported_terms(claim: str, evidence: Iterable[str]) -> set[str]:
    """Words of ``claim`` (longer than 3 characters, or containing digits) not backed by ``evidence``."""
    evidence_text = " ".join(evidence)
    evidence_stems = _stems_of_text(evidence_text)
    evidence_numbers = {w for w in _WORD.findall(evidence_text) if any(c.isdigit() for c in w)}
    unsupported: set[str] = set()
    for word in _WORD.findall(claim):
        if word.lower() in INFLATION_TERMS:  # applies to short words too ("Led")
            if not word_stems(word) & evidence_stems:
                unsupported.add(word)
            continue
        if any(c.isdigit() for c in word):
            if word not in evidence_numbers:
                unsupported.add(word)
            continue
        if len(word) <= 3:
            continue
        if word_stems(word) & evidence_stems or _is_function_word(word):
            continue
        unsupported.add(word)
    return unsupported


def collect_strings(value) -> list[str]:
    """Every string reachable inside nested dicts/lists/dataclass-like objects."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in collect_strings(item)]
    if isinstance(value, (list, tuple, set)):
        return [s for item in value for s in collect_strings(item)]
    if hasattr(value, "__dict__"):
        return collect_strings(vars(value))
    return []


def _fact_tokens(text: str) -> list[str]:
    return [t.rstrip(".-") for t in _FACT_TOKEN.findall(text) if t.rstrip(".-")]


def source_vocabulary(source_strings: Iterable[str]) -> set[str]:
    vocab: set[str] = set()
    for text in source_strings:
        for token in _fact_tokens(text):
            vocab |= word_stems(token)
    return vocab


def unsupported_facts(text: str, vocabulary: set[str]) -> set[str]:
    """Fact-like tokens in ``text`` (numbers, proper nouns, acronyms, tech names, seniority words)
    that never appear in the source vocabulary."""
    flagged: set[str] = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        tokens = _fact_tokens(sentence)
        for index, token in enumerate(tokens):
            if word_stems(token) & vocabulary:
                continue
            lowered = token.lower()
            looks_factual = (
                any(c.isdigit() for c in token)
                or any(c in token for c in "#+")
                or (len(token) >= 2 and token.isupper())
                or (index > 0 and token[0].isupper())
                or lowered in INFLATION_TERMS
            )
            if looks_factual and not _is_function_word(token):
                flagged.add(token)
    return flagged

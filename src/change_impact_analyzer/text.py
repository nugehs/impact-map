from __future__ import annotations

import re
from collections import Counter


STOP_WORDS = {
    "a",
    "add",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "change",
    "do",
    "fix",
    "for",
    "from",
    "get",
    "has",
    "have",
    "i",
    "in",
    "into",
    "is",
    "it",
    "make",
    "need",
    "new",
    "of",
    "on",
    "or",
    "our",
    "please",
    "should",
    "that",
    "the",
    "this",
    "to",
    "update",
    "use",
    "want",
    "we",
    "when",
    "with",
}


def split_identifier(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    parts = re.split(r"[^A-Za-z0-9]+", spaced)
    return [part.lower() for part in parts if part]


def tokenize(value: str) -> list[str]:
    tokens: list[str] = []
    for raw in re.findall(r"[A-Za-z0-9_./:-]+", value):
        tokens.extend(split_identifier(raw))
    return [token for token in tokens if token and token not in STOP_WORDS]


def weighted_query_terms(request: str) -> Counter[str]:
    terms = Counter(tokenize(request))
    boosted = Counter()
    for term, count in terms.items():
        weight = count
        if len(term) >= 6:
            weight += 1
        if term in DOMAIN_KEYWORDS:
            weight += 2
        boosted[term] = weight
        singular = singularize(term)
        if singular != term:
            boosted[singular] = max(boosted[singular], max(1, weight - 1))
    return boosted


def singularize(term: str) -> str:
    if len(term) <= 4 or term.endswith("ss"):
        return term
    if term.endswith("ies"):
        return term[:-3] + "y"
    if term.endswith("es") and not term.endswith(("ses", "xes")):
        return term[:-2]
    if term.endswith("s"):
        return term[:-1]
    return term


DOMAIN_KEYWORDS = {
    "api",
    "auth",
    "booking",
    "billing",
    "cache",
    "checkout",
    "csv",
    "database",
    "email",
    "export",
    "import",
    "invoice",
    "login",
    "migration",
    "notification",
    "order",
    "payment",
    "refund",
    "report",
    "route",
    "schema",
    "stripe",
    "subscription",
    "upload",
    "user",
    "webhook",
}

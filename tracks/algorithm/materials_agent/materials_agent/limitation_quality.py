"""Shared heuristics for open-issue / limitation sentence quality.

Used by extractor (seed limitations), gap_finder (concrete open gaps), and
evidence_selector (grounding filters). Weak "However + positive result" prose
must not be promoted as a research limitation.
"""

from __future__ import annotations

import re

_STRONG_OPEN_ISSUE = (
    "limitation",
    "limitations",
    "challenge",
    "challenges",
    "remain",
    "remains",
    "remaining",
    "unclear",
    "unresolved",
    "not fully",
    "not well",
    "not wellsuited",
    "not well suited",
    "drawback",
    "uncertain",
    "uncertainty",
    "obstacle",
    "bottleneck",
    "poorly understood",
    "open question",
    "still low",
    "still limited",
    "still poor",
    "yet to be",
    "needs further",
    "further investigation",
    "to be clarified",
    "discrepan",
    "inconsisten",
    "controversy",
    "controversial",
    "debate",
    "debated",
    "cannot be",
    "could not be",
    "industrial scale-up",
    "scale-up",
)

# Word-boundary cues (avoid "low" matching "below", "fail" in "Fermi", etc.)
_NEGATIVE_OUTCOME = (
    "low",
    "poor",
    "lack",
    "fails",
    "failed",
    "failure",
    "difficult",
    "harder",
    "unknown",
    "limited",
    "insufficient",
    "cannot",
    "unable",
    "problem",
    "issue",
    "issues",
    "hinder",
    "hamper",
    "degrade",
    "bottleneck",
    "obstacle",
    "challenge",
    "weak",
    "missing",
    "unreliable",
    "ambiguous",
)

_POSITIVE_RESULT = (
    "beneficial",
    "enhance",
    "enhanced",
    "improve",
    "improved",
    "can reduce",
    "substantially lower",
    "substantially lowered",
    "successfully",
    "excellent",
    "superior",
    "significant improvement",
    "increase the z",
    "higher z",
    "intense effect",
    "promising",
)

_CONTRAST_CUES = (
    "however",
    "nevertheless",
    "nonetheless",
    "yet,",
    " but ",
)

# Descriptive science that often co-occurs with weak "but" contrast.
_DESCRIPTIVE_BAND_NOISE = (
    "band structure",
    "valence band",
    "conduction band",
    "fermi level",
    "pudding mold",
    "dirac cone",
    "shown in figure",
    "are shown in",
)


def _has_phrase(low: str, phrase: str) -> bool:
    if " " in phrase or "-" in phrase:
        return phrase in low
    return re.search(rf"\b{re.escape(phrase)}\b", low) is not None


def _positive_hits(low: str) -> int:
    return sum(1 for p in _POSITIVE_RESULT if _has_phrase(low, p) or (len(p) > 8 and p in low))


def _negative_hits(low: str) -> int:
    return sum(1 for n in _NEGATIVE_OUTCOME if _has_phrase(low, n))


def is_strong_limitation(text: str) -> bool:
    """True when text signals an unresolved scientific open issue.

    Rejects contrastive sentences that mainly report positive experimental
    outcomes (common false positives from bare ``however`` cues), and rejects
    descriptive band-structure prose that only contains a weak ``but``.
    """
    low = (text or "").lower().strip()
    if len(low) < 25:
        return False

    # Strip leading citation markers for cue detection only.
    low_nc = re.sub(r"^\s*(?:\[[^\]]+\]\s*)+", "", low)

    pos = _positive_hits(low_nc)
    neg = _negative_hits(low_nc)
    descriptive = any(d in low_nc for d in _DESCRIPTIVE_BAND_NOISE)

    if any(c in low_nc for c in _STRONG_OPEN_ISSUE):
        if pos >= 2 and neg == 0:
            return False
        if (
            pos >= 1
            and neg == 0
            and "however" in low_nc
            and "remain" not in low_nc
            and "still" not in low_nc
        ):
            if not any(
                k in low_nc
                for k in (
                    "limitation",
                    "challenge",
                    "unclear",
                    "unresolved",
                    "not fully",
                    "not well",
                    "uncertain",
                    "bottleneck",
                    "obstacle",
                    "drawback",
                    "cannot be",
                )
            ):
                return False
        return True

    if any(c in low_nc for c in _CONTRAST_CUES):
        if pos >= 1 and neg == 0:
            return False
        # Pure electronic-structure description with a mild contrast is not an open issue.
        if descriptive and neg <= 1 and not any(
            k in low_nc for k in ("limitation", "challenge", "unclear", "unresolved", "cannot")
        ):
            return False
        return neg >= 1

    return False


def looks_like_limitation(text: str) -> bool:
    """Public alias used by grounding / metrics (same bar as extractor)."""
    return is_strong_limitation(text)


def strip_leading_citations(text: str) -> str:
    """Remove leading [12] / [14, 15] markers for human-readable gap titles."""
    return re.sub(r"^\s*(?:\[[^\]]+\]\s*)+", "", (text or "").strip())

"""Analyzer — rule-based difficulty scoring + optional LLM enhancement."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# --- Heuristic signals ---

# Keywords that suggest higher difficulty / more study time
DIFFICULTY_SIGNALS = {
    "advanced": 0.3,
    "clinical": 0.25,
    "pathology": 0.2,
    "surgery": 0.25,
    "diagnosis": 0.2,
    "mechanism": 0.15,
    "pharmacology": 0.2,
    "toxicology": 0.2,
    "analysis": 0.1,
    "synthesis": 0.15,
    "evaluation": 0.15,
    "application": 0.1,
    "interaction": 0.15,
    "metabolism": 0.15,
    "formulation": 0.2,
    "manufacturing": 0.15,
    "standardization": 0.2,
    "clinical trial": 0.25,
    "research": 0.1,
    "case study": 0.1,
    "problem based": 0.15,
}

# Easy indicator keywords (reduce difficulty)
EASY_SIGNALS = {
    "definition": -0.15,
    "introduction": -0.1,
    "overview": -0.1,
    "classification": -0.05,
    "list": -0.1,
    "diagram": -0.05,
    "label": -0.05,
}

# Average reading speed: ~200 words per minute for technical content
WORDS_PER_HOUR = 1200  # accounting for note-taking, re-reading


@dataclass
class TopicAnalysis:
    """Analysis result for a single topic."""

    difficulty: float = 0.5       # 0.0 (easy) – 1.0 (hard)
    estimated_hours: float = 1.0  # study hours needed


def heuristic_analysis(topic_title: str, weightage: float = 0.0) -> TopicAnalysis:
    """Score a topic using regex-based heuristics.

    Works offline, no API needed. Good enough for a solid baseline.

    Args:
        topic_title: The topic text.
        weightage: Marks/weight if available (higher = more time).

    Returns:
        TopicAnalysis with difficulty and estimated_hours.
    """
    title_lower = topic_title.lower()
    words = len(topic_title.split())

    # --- Difficulty scoring ---
    difficulty = 0.5  # baseline

    for signal, boost in DIFFICULTY_SIGNALS.items():
        if signal in title_lower:
            difficulty += boost

    for signal, reduction in EASY_SIGNALS.items():
        if signal in title_lower:
            difficulty += reduction  # reduction is negative

    # Clamp
    difficulty = max(0.1, min(1.0, difficulty))

    # --- Time estimation ---
    # Base: word count / reading speed, but cap at 5h max per topic
    base_hours = max(0.5, min(5.0, words / WORDS_PER_HOUR))

    # Weightage multiplier (more marks = more study time)
    weight_mult = max(1.0, weightage / 10.0) if weightage > 0 else 1.0

    # Difficulty multiplier (harder topics need more revision passes)
    diff_mult = 1.0 + difficulty * 0.5

    estimated_hours = round(base_hours * weight_mult * diff_mult, 1)

    return TopicAnalysis(difficulty=round(difficulty, 2), estimated_hours=estimated_hours)


def analyze_topics(
    topics: list[dict],
    total_available_hours: float = 200.0,
) -> list[TopicAnalysis]:
    """Run heuristic analysis on a list of topic dicts, then scale hours to fit.

    Each dict must have at least 'title' and optionally 'weightage'.

    Args:
        topics: List of topic dicts from the extractor.
        total_available_hours: Total hours in the study schedule.
            If the sum of raw estimates exceeds this, all hours are
            scaled down proportionally so the schedule fits.

    Returns:
        List of TopicAnalysis, same order as input.
    """
    results = []
    for t in topics:
        analysis = heuristic_analysis(
            topic_title=t.get("title", ""),
            weightage=t.get("weightage", 0.0),
        )
        results.append(analysis)

    # Scale hours if total exceeds available time
    raw_total = sum(r.estimated_hours for r in results)
    if raw_total > total_available_hours and raw_total > 0:
        scale = total_available_hours / raw_total
        for r in results:
            r.estimated_hours = round(r.estimated_hours * scale, 1)
        logger.info(
            "Scaled %d topics: %.1fh → %.1fh (factor %.2f)",
            len(results), raw_total, total_available_hours, scale,
        )

    return results

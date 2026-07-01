"""Content Extractor — regex-based extraction of chapters, topics, weightage from PDFs."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────

@dataclass
class Topic:
    """A single topic / sub-topic."""

    title: str
    weightage: float = 0.0
    chapter: str = "General"
    difficulty: float = 0.5
    estimated_hours: float = 0.0
    metadata: dict = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return self.title.strip()

    def __repr__(self) -> str:
        return f"Topic({self.chapter!r}:{self.display_name!r}, w={self.weightage:.1f})"


@dataclass
class Chapter:
    """A chapter (unit) in the syllabus."""

    title: str
    topics: list[Topic] = field(default_factory=list)

    @property
    def topic_count(self) -> int:
        return len(self.topics)

    def __repr__(self) -> str:
        return f"Chapter({self.title!r}, {len(self.topics)} topics)"


ParsedResult = list[Chapter]


# ── Detection patterns ─────────────────────────────────────────────────

CHAPTER_PATTERNS = [
    r"(?i)^(?:Unit|Chapter|पाठ|अध्याय|अंश)\s*[-–—]?\s*(\d+[\.\):]?\s*.{5,})",
    r"(?i)^(Paper\s*[IVX]+)\s*[:\-–—]\s*(.+)",
    r"^(\d+\.\d+\.\d+\s+.{10,})",
    r"^(\d+\.\d+\s+.{10,})",
    r"^(\d+\.\s+[A-Z][A-Za-z\s\-/]{5,})",
    r"^([A-Z][A-Z\s\-/]{8,})$",
]

TARGET_PATTERNS = [
    r"^[-–—•·]\s+(.+)",
    r"^\d+[\.\)]\s+(.+)",
    r"^[a-z]\)\s+(.+)",
]

WEIGHTAGE_PATTERNS = [
    r"(\d+)\s*(?:marks?|m\.?|Marks?)",
    r"(?:marks?|m\.?|Marks?)\s*[:\-]?\s*(\d+)",
    r"\((\d+)\s*(?:marks?|m\.?)\)",
    r"(\d+)\s*(?:hrs?|hours?)",
]

SKIP_PATTERNS = [
    r"(?i)^\s*(ncism|board of|curriculum for|ayush|new delhi|government|ministry"
    r"|amendment|copyright|all rights reserved|published by"
    r"|course code|course learning|table \d|matched po|contents of course"
    r"|preface|index|syllabus|s\. no\.)\b",
    r"^\s*[-–—•·=._·…]{3,}\s*$",
    r"(?i)^\s*page\s+\d+",
    r"^\s*[-–—•·]\s*$",
    r"^\s*\d+\s*$",
    r"^\s*$",
]

NOISE_RE = re.compile(r"^[A-Z]{2,}(\s+[A-Z]{2,}){1,}$")
SHORT_ALL_CAPS = re.compile(r"^[A-Z]{2,5}$")


def _match_first(text: str, patterns: list[str]) -> str | None:
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return None


def _should_skip(line: str) -> bool:
    for p in SKIP_PATTERNS:
        if re.match(p, line):
            return True
    return False


def _detect_weight(line: str) -> float:
    for p in WEIGHTAGE_PATTERNS:
        m = re.search(p, line)
        if m:
            val = float(m.group(1))
            if val < 200:  # sanity cap — marks/hrs won't exceed 200
                return val
    return 0.0


def _looks_heading(text: str) -> bool:
    if text.isupper() and len(text) >= 6:
        return True
    if re.match(r"^\d+(?:\.\d+)*\.\s+[A-Z]", text):
        return True
    if re.match(r"(?i)^(Unit|Paper)\s*\d", text):
        return True
    return False


# ── Main extraction ────────────────────────────────────────────────────

def extract_structure(
    parsed,
    *,
    default_chapter: str = "Syllabus",
    min_topic_length: int = 10,
    max_topic_length: int = 200,
    min_chapter_topics: int = 2,
) -> ParsedResult:
    """Extract chapters and topics from parsed PDF text.

    Two-pass approach:
    1. Detect chapter headings, collect topic lines into chapters
    2. Post-process: merge tiny chapters, drop noise

    Args:
        parsed: ParsedPDF from parser.parse_pdf().
        default_chapter: Fallback chapter name.
        min_topic_length: Minimum chars for a valid topic.
        max_topic_length: Lines longer than this are truncated.
        min_chapter_topics: Chapters with fewer topics get merged.

    Returns:
        List of Chapter with Topic items.
    """
    chapters = _pass1_extract(parsed, default_chapter, min_topic_length, max_topic_length)
    chapters = _pass2_post_process(chapters, min_chapter_topics)

    total = sum(len(c.topics) for c in chapters)
    logger.info("Extracted %d chapters, %d topics", len(chapters), total)
    return chapters


def _pass1_extract(
    parsed, default_chapter: str, min_len: int, max_len: int,
) -> ParsedResult:
    """Pass 1: Detect chapters and collect topic lines."""
    all_text = parsed.full_text()
    chapters: list[Chapter] = []
    current: Chapter | None = None

    def ensure_chapter():
        nonlocal current
        if current is None:
            current = Chapter(title=default_chapter)
            chapters.append(current)

    for raw in all_text.splitlines():
        line = raw.strip()

        if not line or _should_skip(line):
            continue

        if line.startswith("--- Page"):
            continue

        # Skip noise
        if NOISE_RE.match(line) or SHORT_ALL_CAPS.match(line):
            continue

        # Chapter heading?
        title = _match_first(line, CHAPTER_PATTERNS)
        if title and len(title) >= 5:
            current = Chapter(title=title)
            chapters.append(current)
            continue

        # Topic line (bullet, numbered, etc.)
        topic = _match_first(line, TARGET_PATTERNS)
        if topic and len(topic) >= min_len:
            clean = _truncate(topic, max_len)
            w = _detect_weight(line)
            ensure_chapter()
            current.topics.append(Topic(title=clean, weightage=w, chapter=current.title))
        elif current is not None and not _looks_heading(line):
            # Orphan prose inside a chapter — include as topic if reasonable
            stripped = line.strip(" -•·)")
            if min_len <= len(stripped) <= max_len:
                ensure_chapter()
                current.topics.append(Topic(
                    title=stripped,
                    weightage=_detect_weight(line),
                    chapter=current.title,
                ))
        elif not chapters and not _looks_heading(line):
            # Text before any chapter
            stripped = line.strip(" -•·)")
            if min_len <= len(stripped) <= max_len:
                ensure_chapter()
                current.topics.append(Topic(
                    title=stripped,
                    weightage=_detect_weight(line),
                    chapter=current.title,
                ))

    if not chapters:
        chapters.append(Chapter(title=default_chapter))

    return chapters


def _pass2_post_process(chapters: ParsedResult, min_topics: int) -> ParsedResult:
    """Pass 2: merge tiny chapters, drop empty ones, cap chapter count."""
    if len(chapters) <= 1:
        return chapters

    merged: list[Chapter] = []
    for ch in chapters:
        if ch.topic_count < min_topics and merged:
            # Merge into previous chapter
            prev = merged[-1]
            for t in ch.topics:
                t.chapter = prev.title
                t.metadata["section"] = ch.title
                prev.topics.append(t)
        elif ch.topic_count >= min_topics:
            merged.append(ch)

    result = [ch for ch in merged if ch.topic_count > 0]

    if not result:
        return [Chapter(title="Syllabus")]

    # If still too many chapters, group into batches of ~5
    if len(result) > 15:
        batches = []
        for i in range(0, len(result), 5):
            batch = result[i:i + 5]
            batch_topics = []
            for ch in batch:
                batch_topics.extend(ch.topics)
            batches.append(Chapter(title=batch[0].title, topics=batch_topics))
        return batches

    return result


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len, word-bounded."""
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0].rstrip(".,;:- ") + "..."

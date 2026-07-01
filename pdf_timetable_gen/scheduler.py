"""Schedule Generator — constraint-aware topic-to-day mapping with balanced load."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Sequence

from .constraint import PhaseGrouping, StudyConstraints
from .extractor import Chapter, Topic

logger = logging.getLogger(__name__)


# --- Data model ---

@dataclass
class DaySlot:
    """A single time slot within a day."""

    phase: str           # "learn", "practice", "revise"
    topic_title: str
    chapter: str
    hours: float
    difficulty: float


@dataclass
class DayPlan:
    """Full plan for one day."""

    day_number: int
    date: date | None
    total_hours: float = 0.0
    slots: list[DaySlot] = field(default_factory=list)

    def add_slot(self, phase: str, topic: Topic, hours: float) -> None:
        self.slots.append(DaySlot(
            phase=phase,
            topic_title=topic.display_name,
            chapter=topic.chapter,
            hours=hours,
            difficulty=topic.difficulty,
        ))
        self.total_hours = round(self.total_hours + hours, 1)


@dataclass
class GeneratedSchedule:
    """Complete generated timetable."""

    constraints: StudyConstraints
    days: list[DayPlan]
    total_topics: int = 0
    total_hours: float = 0.0

    def __post_init__(self) -> None:
        self.total_topics = sum(len(d.slots) for d in self.days)
        self.total_hours = round(sum(d.total_hours for d in self.days), 1)


# --- Generator ---

class ScheduleGenerator:
    """Build a study schedule respecting all constraints."""

    def __init__(self, constraints: StudyConstraints, start_date: date | None = None):
        self.constraints = constraints
        self.start_date = start_date or date.today() + timedelta(days=1)

    def generate(self, chapters: list[Chapter]) -> GeneratedSchedule:
        """Generate a complete study schedule.

        Args:
            chapters: Extracted syllabus chapters and topics.

        Returns:
            GeneratedSchedule covering all study days + revision buffer.
        """
        constraints = self.constraints
        errors = constraints.validate()
        if errors:
            raise ValueError(f"Invalid constraints: {'; '.join(errors)}")

        # Flatten and prioritize
        all_topics = _flatten_topics(chapters)
        total_hours_needed = sum(t.estimated_hours for t in all_topics)

        logger.info(
            "Scheduling %d topics (%.1fh needed) into %d study days (%.1fh available)",
            len(all_topics), total_hours_needed,
            constraints.study_days, constraints.available_hours,
        )

        if total_hours_needed > constraints.available_hours:
            logger.warning(
                "Over-subscribed by %.1fh — compressing topic hours",
                total_hours_needed - constraints.available_hours,
            )

        # Build the schedule
        days: list[DayPlan] = []
        topic_queue = _prioritize_topics(all_topics)
        total_slots = sum(len(c.topics) for c in chapters)

        for day_idx in range(constraints.total_days):
            weekday = (self.start_date.weekday() + day_idx) % 7

            # Skip revision buffer days (last N days)
            is_revision = day_idx >= constraints.total_days - constraints.revision_buffer_days

            # Skip explicit rest days (unless in revision buffer)
            is_rest = weekday in constraints.rest_days and not is_revision

            if is_rest and not is_revision:
                continue

            if is_revision:
                plan = self._revision_day(len(days) + 1, topic_queue)
            else:
                plan = self._study_day(len(days) + 1, topic_queue)

            plan.date = self.start_date + timedelta(days=day_idx)
            days.append(plan)

        return GeneratedSchedule(constraints=constraints, days=days)

    # --- Day builders ---

    def _study_day(self, day_number: int, topic_queue: list[Topic]) -> DayPlan:
        """Build a normal study day."""
        plan = DayPlan(day_number=day_number, date=None)
        hours_left = self.constraints.hours_per_day
        difficult_streak = 0
        topic_index = 0

        while hours_left > 0.25 and topic_index < len(topic_queue):
            topic = topic_queue[topic_index]
            topic_index += 1

            # Difficulty balancing
            if difficult_streak >= self.constraints.max_consecutive_difficult:
                # Look ahead for an easier topic
                easy_swap = self._find_easy_ahead(topic_queue, topic_index)
                if easy_swap:
                    topic = easy_swap
                    topic_queue.remove(topic)
                    topic_index -= 1

            # Determine phase based on grouping mode
            phase = self._phase(topic, plan)

            # Hours allocation
            slot_hours = min(topic.estimated_hours, hours_left)
            if slot_hours < 0.25:
                slot_hours = hours_left

            plan.add_slot(phase, topic, round(slot_hours, 1))
            hours_left = round(hours_left - slot_hours, 1)

            if topic.difficulty > 0.6:
                difficult_streak += 1
            else:
                difficult_streak = 0

            # Re-queue if not fully consumed
            remaining = round(topic.estimated_hours - slot_hours, 1)
            if remaining > 0.25:
                topic.estimated_hours = remaining
                topic_queue.insert(topic_index, topic)

        return plan

    def _revision_day(self, day_number: int, topic_queue: list[Topic]) -> DayPlan:
        """Build a revision day — focus on top-weighted topics."""
        plan = DayPlan(day_number=day_number, date=None)
        hours_left = self.constraints.hours_per_day

        # Top 20% by weightage for revision
        priority = sorted(topic_queue, key=lambda t: t.weightage, reverse=True)
        rev_count = max(3, int(len(topic_queue) * 0.2))
        rev_topics = priority[:rev_count]

        for topic in rev_topics:
            if hours_left < 0.3:
                break
            rev_hours = min(topic.estimated_hours * 0.4, hours_left)
            plan.add_slot("revise", topic, round(rev_hours, 1))
            hours_left = round(hours_left - rev_hours, 1)

        return plan

    def _phase(self, topic: Topic, plan: DayPlan) -> str:
        """Determine study phase based on grouping mode."""
        mode = self.constraints.phase_grouping

        if mode == PhaseGrouping.INTERLEAVED:
            return random.choice(["learn", "practice", "revise"])

        # LINEAR or CONCENTRATED: all learn for now
        # (full linear phase separation is a v0.2 feature)
        return "learn"

    def _find_easy_ahead(self, queue: list[Topic], from_idx: int) -> Topic | None:
        """Find the easiest topic at or after from_idx."""
        candidates = queue[from_idx:]
        if not candidates:
            return None
        easiest = min(candidates, key=lambda t: t.difficulty)
        if easiest.difficulty < 0.5:
            return easiest
        return None


# --- Helpers ---

def _flatten_topics(chapters: list[Chapter]) -> list[Topic]:
    """Deep-copy topics from chapters into a flat list."""
    result = []
    for ch in chapters:
        for t in ch.topics:
            result.append(Topic(
                title=t.title,
                weightage=t.weightage,
                chapter=t.chapter,
                difficulty=t.difficulty,
                estimated_hours=t.estimated_hours,
                metadata=dict(t.metadata),
            ))
    return result


def _prioritize_topics(topics: list[Topic]) -> list[Topic]:
    """Pareto sort: 60% weightage + 40% difficulty, descending."""
    return sorted(
        topics,
        key=lambda t: (t.weightage * 0.6 + t.difficulty * 0.4),
        reverse=True,
    )

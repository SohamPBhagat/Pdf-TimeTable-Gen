"""Constraint Engine — user-configurable study parameters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PhaseGrouping(str, Enum):
    """Study phases for the Learn → Practice → Revise cycle."""

    LINEAR = "linear"          # Learn everything, then practice, then revise
    INTERLEAVED = "interleaved"  # Mix phases within each topic
    CONCENTRATED = "concentrated"  # One phase at a time per topic


@dataclass
class StudyConstraints:
    """All user-configurable constraints for schedule generation."""

    total_days: int = 39
    hours_per_day: float = 6.0
    rest_days_per_week: int = 1  # e.g., Sunday off
    rest_days: list[int] = field(default_factory=list)  # e.g., [6] for Sunday
    phase_grouping: PhaseGrouping = PhaseGrouping.LINEAR
    max_consecutive_difficult: int = 2  # don't stack hard topics
    revision_buffer_days: int = 3      # days reserved at end for full revision

    @property
    def study_days(self) -> int:
        """Total usable days after rest days are removed."""
        weeks = self.total_days // 7
        remaining = self.total_days % 7
        rest = weeks * self.rest_days_per_week
        # Count explicit rest days that fall within the remaining days
        for d in self.rest_days:
            if d < remaining:
                rest += 1
        return self.total_days - rest - self.revision_buffer_days

    @property
    def available_hours(self) -> float:
        """Total study hours available."""
        return self.study_days * self.hours_per_day

    def validate(self) -> list[str]:
        """Return list of validation errors (empty = valid)."""
        errors = []
        if self.total_days < 1:
            errors.append("total_days must be >= 1")
        if self.hours_per_day < 1:
            errors.append("hours_per_day must be >= 1")
        if self.revision_buffer_days >= self.total_days:
            errors.append("revision_buffer_days must be less than total_days")
        if self.max_consecutive_difficult < 1:
            errors.append("max_consecutive_difficult must be >= 1")
        if self.study_days < 1:
            errors.append(
                f"Not enough study days after rest days and revision buffer. "
                f"Got {self.study_days}, need at least 1."
            )
        return errors

    def __repr__(self) -> str:
        return (
            f"StudyConstraints(days={self.total_days}, "
            f"hours/day={self.hours_per_day}, "
            f"rest={self.rest_days}, "
            f"phases={self.phase_grouping.value})"
        )

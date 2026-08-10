#!/usr/bin/env python3
"""
Competition schedule logic for the Roboracer Event Manager.

Pure data logic (no GUI) so it can be unit-tested. The organizer authors a
fine-grained, group-based timetable in a simple Google Sheet (exported to CSV)
and this module parses it and renders it to markdown for the Schedule page.

Sheet schema (flat, one row per entry):

    Date,Start,End,Session,Group,Team,Notes

- A row with ``Team`` filled is a *bookable slot* (regulated practice, and
  time-trial heats) and renders inside a per-session booking table.
- A row without ``Team`` is a *shared block* (group/open practice, lunch,
  head-to-head, awards, ...) and renders in the day's timetable.
- ``Group`` labels shared group practice; regulated practice is ungrouped.
- Blank ``Date`` inherits the day above; blank ``Start``/``End`` = "All day";
  ``End`` may be the literal ``Close``. Times are 24h (``9:40`` -> ``09:40``).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

COLUMNS = ["Date", "Start", "End", "Session", "Group", "Team", "Notes"]


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def parse_minutes(value: str) -> int | None:
    """Parse ``HH:MM`` / ``H:MM`` into minutes since midnight, else None."""
    if not value:
        return None
    v = value.strip()
    if ":" not in v:
        return None
    try:
        h, m = v.split(":", 1)
        return int(h) * 60 + int(m)
    except ValueError:
        return None


def format_minutes(total: int) -> str:
    """Format minutes since midnight as zero-padded ``HH:MM`` (24h)."""
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def normalize_time(value: str) -> str:
    """Normalize a time cell: zero-pad 24h times, pass ``Close`` and blanks."""
    if value is None:
        return ""
    v = str(value).strip()
    if not v:
        return ""
    if v.lower() in {"close", "tbd", "tba"}:
        return v.capitalize() if v.lower() != "tba" else "TBA"
    mins = parse_minutes(v)
    return format_minutes(mins) if mins is not None else v


def _day_heading(date_str: str) -> str:
    """Turn an ISO (or known) date into 'Weekday, Month D'; else return as-is."""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return f"{dt.strftime('%A, %B')} {dt.day}"
        except ValueError:
            continue
    return date_str


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ScheduleRow:
    date: str = ""
    start: str = ""
    end: str = ""
    session: str = ""
    group: str = ""
    team: str = ""
    notes: str = ""

    @property
    def is_all_day(self) -> bool:
        return not self.start and not self.end

    @property
    def is_slot(self) -> bool:
        return bool(self.team.strip())

    @property
    def time_range(self) -> str:
        if self.is_all_day:
            return "All day"
        if self.start and self.end:
            return f"{self.start} - {self.end}"
        return self.start or self.end


# ---------------------------------------------------------------------------
# CSV loading / writing
# ---------------------------------------------------------------------------

def _row_get(row: dict, key: str) -> str:
    """Case-insensitive column lookup that tolerates surrounding whitespace."""
    for k, v in row.items():
        if k and k.strip().lower() == key.lower():
            return (v or "").strip()
    return ""


def load_schedule_csv(path: str | Path) -> list[ScheduleRow]:
    """Parse a schedule CSV into rows, forward-filling the date column."""
    rows: list[ScheduleRow] = []
    last_date = ""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            date = _row_get(raw, "Date") or last_date
            start = normalize_time(_row_get(raw, "Start"))
            end = normalize_time(_row_get(raw, "End"))
            session = _row_get(raw, "Session")
            group = _row_get(raw, "Group")
            team = _row_get(raw, "Team")
            notes = _row_get(raw, "Notes")
            # Skip fully-empty spacer rows.
            if not any((session, team, start, end, notes)):
                continue
            if date:
                last_date = date
            rows.append(ScheduleRow(date, start, end, session, group, team, notes))
    return rows


def rows_to_csv(rows: list[ScheduleRow]) -> str:
    """Serialize rows back to CSV text with the canonical header."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(COLUMNS)
    for r in rows:
        writer.writerow([r.date, r.start, r.end, r.session, r.group, r.team, r.notes])
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Group assignment
# ---------------------------------------------------------------------------

def auto_assign_groups(team_keys: list[str], size: int) -> dict[str, str]:
    """Partition team keys into groups of ``size`` (Group '1', '2', ...)."""
    size = max(1, int(size))
    return {key: str(i // size + 1) for i, key in enumerate(team_keys)}


def _group_sort_key(label: str):
    label = (label or "").strip()
    return (0, int(label)) if label.isdigit() else (1, label.lower())


# ---------------------------------------------------------------------------
# Slot grid generation (regulated practice / time-trial heats)
# ---------------------------------------------------------------------------

def generate_slot_grid(
    date: str,
    start: str,
    end: str,
    slot_minutes: int,
    session: str,
    count: int | None = None,
    switch_minutes: int = 0,
    group: str = "",
) -> list[ScheduleRow]:
    """Produce empty-``Team`` slot rows for a bookable session.

    Steps ``slot_minutes + switch_minutes`` from ``start``; stops at ``end``
    (if given) and/or after ``count`` slots (if given). At least one bound is
    required.
    """
    begin = parse_minutes(normalize_time(start))
    if begin is None:
        raise ValueError("A valid start time is required")
    end_min = parse_minutes(normalize_time(end))
    if end_min is None and count is None:
        raise ValueError("Provide an end time and/or a slot count")

    slot_minutes = max(1, int(slot_minutes))
    step = slot_minutes + max(0, int(switch_minutes))
    rows: list[ScheduleRow] = []
    t = begin
    made = 0
    while True:
        if count is not None and made >= count:
            break
        slot_end = t + slot_minutes
        if end_min is not None and slot_end > end_min:
            break
        rows.append(ScheduleRow(
            date=date, start=format_minutes(t), end=format_minutes(slot_end),
            session=session, group=group, team="", notes="",
        ))
        made += 1
        t += step
    return rows


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_groups_markdown(groups: dict[str, str], team_display: dict[str, str]) -> str:
    """Render practice-group rosters.

    ``groups`` maps team_key -> group label; ``team_display`` maps team_key ->
    display name. Returns an empty string if no groups are assigned.
    """
    by_group: dict[str, list[str]] = {}
    for key, label in groups.items():
        if not label:
            continue
        name = team_display.get(key, key)
        by_group.setdefault(label, []).append(name)
    if not by_group:
        return ""

    lines = ["## Practice Groups", ""]
    lines.append(
        "*Groups apply to shared open-practice blocks. Regulated practice is open "
        "booking (any team, first-come, first-served).*"
    )
    lines.append("")
    for label in sorted(by_group, key=_group_sort_key):
        members = ", ".join(sorted(by_group[label], key=str.lower))
        lines.append(f"- **Group {label}** — {members}")
    return "\n".join(lines)


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join([":---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(c or "" for c in r) + " |")
    return "\n".join(out)


def _ordered_dates(rows: list[ScheduleRow]) -> list[str]:
    seen: list[str] = []
    for r in rows:
        if r.date not in seen:
            seen.append(r.date)
    return seen


def render_schedule_markdown(
    rows: list[ScheduleRow], tz_label: str = "ET", days: list | None = None
) -> str:
    """Render the full day-by-day schedule (timetable + booking tables).

    ``days`` is an optional ordered day skeleton (list of ``{"date","label"}``
    dicts or ``(date, label)`` tuples) imported from the event timeline. Those
    days set the order and headings (e.g. "Race Day - Tuesday, June 23") and are
    shown even with no session rows yet; any extra dates found in ``rows`` are
    appended after them.
    """
    # Build the ordered day list: timeline days first (merging labels that share a
    # date, e.g. Time Trials + Race on the same day), then any extra CSV dates.
    date_order: list[str] = []
    labels_by_date: dict[str, list[str]] = {}
    for d in days or []:
        date = d.get("date") if isinstance(d, dict) else d[0]
        label = (d.get("label") if isinstance(d, dict) else (d[1] if len(d) > 1 else "")) or ""
        if not date:
            continue
        if date not in labels_by_date:
            labels_by_date[date] = []
            date_order.append(date)
        if label and label not in labels_by_date[date]:
            labels_by_date[date].append(label)
    for date in _ordered_dates(rows):
        if date and date not in labels_by_date:
            labels_by_date[date] = []
            date_order.append(date)

    order = [(date, " & ".join(labels_by_date[date])) for date in date_order]
    if not order:
        return ""
    time_col = f"Time ({tz_label})"
    parts: list[str] = []

    for date, label in order:
        day_rows = [r for r in rows if r.date == date]
        blocks = [r for r in day_rows if not r.is_slot and not r.is_all_day]
        slots = [r for r in day_rows if r.is_slot]
        all_day = [r for r in day_rows if r.is_all_day and not r.is_slot]

        heading = _day_heading(date)
        if label:
            heading = f"{label} - {heading}"
        parts.append(f"### {heading}")

        if blocks:
            show_group = any(r.group for r in blocks)
            headers = [time_col] + (["Group"] if show_group else []) + ["Activity", "Notes"]
            table_rows = []
            for r in blocks:
                cells = [r.time_range]
                if show_group:
                    cells.append(r.group)
                cells += [r.session, r.notes]
                table_rows.append(cells)
            parts.append(_md_table(headers, table_rows))

        # Booking sub-tables, grouped by (session, group) in first-seen order.
        seen_keys: list[tuple[str, str]] = []
        for r in slots:
            k = (r.session, r.group)
            if k not in seen_keys:
                seen_keys.append(k)
        for session, group in seen_keys:
            group_slots = [r for r in slots if r.session == session and r.group == group]
            heading = f"**{session}"
            if group:
                heading += f" — Group {group}"
            heading += " booking**"
            parts.append(heading)
            table_rows = [
                [str(i), r.time_range, r.team] for i, r in enumerate(group_slots, 1)
            ]
            parts.append(_md_table(["Slot", time_col, "Team"], table_rows))

        for r in all_day:
            text = r.notes or r.session
            parts.append(f"*All day:* {text}")

    return "\n\n".join(parts)

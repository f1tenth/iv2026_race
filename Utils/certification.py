#!/usr/bin/env python3
"""
Registration certification logic for the Roboracer Event Manager.

Pure data logic (no GUI) so it can be unit-tested independently. It loads the
three Google-Form CSV exports (registration, video submission, hardware list),
matches submissions to registrations despite messy/inconsistent team names and
different submitters, deduplicates to the latest submission per team, evaluates
link safety with offline heuristics, and produces the data needed for the
Certification tab and the website participants table.

A team is *certified* when it has a matched registration AND its video demo and
hardware list have both been hand-ticked as satisfied.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FORM_REGISTRATION = "registration"
FORM_VIDEO = "video"
FORM_HARDWARE = "hardware"

# Fuzzy team-name match threshold (difflib ratio).
TEAM_NAME_RATIO = 0.80

# Link safety classifications.
LINK_OK = "ok"
LINK_SUSPICIOUS = "suspicious"
LINK_BLOCKED = "blocked"
LINK_NONE = "no_link"

# Hosts we trust outright (suffix match against the registered domain).
ALLOWED_HOST_SUFFIXES = (
    "youtube.com",
    "youtu.be",
    "drive.google.com",
    "docs.google.com",
    "sharepoint.com",
    "box.com",
    "github.com",
    "githubusercontent.com",
    "slack.com",
    "dropbox.com",
    "onedrive.live.com",
    "1drv.ms",
)

# Known URL shorteners -> always suspicious (destination is hidden).
URL_SHORTENERS = {
    "bit.ly",
    "t.co",
    "tinyurl.com",
    "goo.gl",
    "is.gd",
    "ow.ly",
    "buff.ly",
    "rebrand.ly",
    "cutt.ly",
    "shorturl.at",
}

# Executable / script extensions -> blocked outright.
DANGEROUS_EXTENSIONS = (
    ".exe",
    ".scr",
    ".bat",
    ".cmd",
    ".com",
    ".js",
    ".vbs",
    ".jar",
    ".apk",
    ".msi",
    ".ps1",
    ".sh",
    ".dll",
)

_URL_RE = re.compile(r"https?://[^\s,;]+", re.IGNORECASE)
_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def normalize_team_name(name: str) -> str:
    """Return a stable canonical key for a team name.

    Lowercases, drops parentheticals like ``(tentative)``, strips punctuation
    and separators, and collapses whitespace so that ``AIR UOP (tentative)``,
    ``AIR UOP`` and ``air-uop`` all collapse to the same key.
    """
    if name is None:
        return ""
    s = str(name).strip().lower()
    s = re.sub(r"\([^)]*\)", " ", s)  # drop parentheticals
    s = re.sub(r"[^a-z0-9]+", " ", s)  # punctuation/separators -> space
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_email(email: str) -> str:
    """Lowercase and trim a single email address."""
    if email is None:
        return ""
    return str(email).strip().lower()


def split_emails(cell: str) -> list[str]:
    """Extract all email addresses from a cell (handles ``;`` / ``,`` lists)."""
    if cell is None:
        return []
    return [normalize_email(m) for m in re.findall(r"[^\s,;]+@[^\s,;]+", str(cell))]


def parse_members(text: str) -> list[tuple[str, str]]:
    """Parse the free-text "other members" field into ``(name, email)`` tuples.

    Handles the form's expected ``FirstName LastName (email), ...`` format plus
    newlines, stray labels, and ``N/A`` placeholders. Entries without a clean
    name still contribute their email for matching purposes.
    """
    if text is None:
        return []
    raw = str(text).strip()
    if not raw or raw.lower() in {"n/a", "na", "none"}:
        return []

    members: list[tuple[str, str]] = []
    # Match "Name (email)" pairs first.
    for m in re.finditer(r"([A-Za-z.\-' ]+?)\s*\(([^)]*@[^)]*)\)", raw):
        name = re.sub(r"\s+", " ", m.group(1)).strip(" ,.")
        email = normalize_email(m.group(2))
        if name or email:
            members.append((name, email))

    if members:
        return members

    # Fallback: no parenthesised emails, grab any bare emails.
    return [("", e) for e in split_emails(raw)]


def parse_links(cell: str) -> list[str]:
    """Return all http(s) URLs found in a cell (a cell may hold several)."""
    if cell is None:
        return []
    if isinstance(cell, float) and pd.isna(cell):
        return []
    return _URL_RE.findall(str(cell))


# ---------------------------------------------------------------------------
# Link safety
# ---------------------------------------------------------------------------

def _host_allowed(host: str) -> bool:
    return any(host == s or host.endswith("." + s) for s in ALLOWED_HOST_SUFFIXES)


def classify_link(
    url: str,
    blocked_links: set[str] | None = None,
    allowed_links: set[str] | None = None,
) -> tuple[str, list[str]]:
    """Classify a single URL with offline heuristics.

    Returns ``(status, reasons)`` where status is one of ``ok``, ``suspicious``,
    ``blocked`` or ``no_link``. User overrides take precedence.
    """
    blocked_links = blocked_links or set()
    allowed_links = allowed_links or set()

    if not url or not str(url).strip():
        return LINK_NONE, ["No URL found in submission"]

    url = str(url).strip()
    if url in blocked_links:
        return LINK_BLOCKED, ["Manually marked malicious"]
    if url in allowed_links:
        return LINK_OK, ["Manually marked safe"]

    # Free text with no actual URL in it (e.g. a hardware list typed inline).
    if "://" not in url:
        return LINK_NONE, ["No URL found in submission"]

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    reasons: list[str] = []

    if scheme not in {"http", "https"}:
        return LINK_BLOCKED, [f"Non-web scheme: {scheme or 'none'}"]
    if not host:
        return LINK_BLOCKED, ["No host in URL"]

    # Hard blocks.
    if "@" in (parsed.netloc or ""):
        reasons.append("Embedded credentials in URL (user@host)")
    path_lower = parsed.path.lower()
    if path_lower.endswith(DANGEROUS_EXTENSIONS):
        reasons.append("Points to an executable/script file")
    if reasons:
        return LINK_BLOCKED, reasons

    # Suspicious signals.
    if _IPV4_RE.match(host):
        reasons.append("Host is a raw IP address")
    if host.startswith("xn--") or ".xn--" in host:
        reasons.append("Punycode host (possible homograph)")
    if host in URL_SHORTENERS:
        reasons.append("URL shortener hides the destination")
    if host.count(".") >= 4:
        reasons.append("Unusually deep subdomain nesting")

    if reasons:
        return LINK_SUSPICIOUS, reasons

    if _host_allowed(host):
        return LINK_OK, [f"Trusted host: {host}"]

    # Unknown but otherwise unremarkable host.
    return LINK_SUSPICIOUS, [f"Host not on allowlist: {host}"]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Submission:
    """A single video or hardware form response."""

    form: str
    submitter_name: str
    submitter_email: str
    team_name: str  # raw, as submitted
    raw_cell: str
    timestamp: datetime | None
    links: list[str] = field(default_factory=list)
    submission_id: str = ""
    team_key: str = ""  # resolved team this belongs to
    match_reason: str = ""

    @property
    def primary_link(self) -> str:
        return self.links[0] if self.links else ""

    def link_status(
        self, blocked: set[str] | None = None, allowed: set[str] | None = None
    ) -> tuple[str, list[str]]:
        if not self.links:
            return LINK_NONE, ["No URL found in submission"]
        # Worst status across all links in the cell.
        order = {LINK_OK: 0, LINK_NONE: 1, LINK_SUSPICIOUS: 2, LINK_BLOCKED: 3}
        worst = (LINK_OK, ["All links OK"])
        for link in self.links:
            status, reasons = classify_link(link, blocked, allowed)
            if order[status] >= order[worst[0]]:
                worst = (status, reasons)
        return worst


@dataclass
class Registration:
    """A registration-form response."""

    team_key: str
    display_name: str
    affiliation: str
    submitter_name: str
    submitter_email: str
    members: list[tuple[str, str]]  # (name, email), includes submitter
    timestamp: datetime | None

    @property
    def member_emails(self) -> set[str]:
        return {e for _, e in self.members if e}

    @property
    def member_names(self) -> set[str]:
        return {n.lower() for n, _ in self.members if n}


@dataclass
class Team:
    """A team aggregated across all three forms."""

    team_key: str
    display_name: str
    affiliation: str
    registration: Registration | None
    members: list[tuple[str, str]]
    all_video: list[Submission] = field(default_factory=list)
    all_hardware: list[Submission] = field(default_factory=list)
    latest_video: Submission | None = None
    latest_hardware: Submission | None = None
    video_satisfied: bool = False
    hardware_satisfied: bool = False

    @property
    def registration_matched(self) -> bool:
        return self.registration is not None

    @property
    def has_video(self) -> bool:
        return self.latest_video is not None

    @property
    def has_hardware(self) -> bool:
        return self.latest_hardware is not None

    @property
    def is_candidate(self) -> bool:
        """Considered only if both a video AND a hardware submission exist."""
        return self.has_video and self.has_hardware

    @property
    def certified(self) -> bool:
        return (
            self.registration_matched
            and self.video_satisfied
            and self.hardware_satisfied
        )


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def _to_dt(value) -> datetime | None:
    ts = pd.to_datetime(value, errors="coerce")
    if ts is pd.NaT or pd.isna(ts):
        return None
    return ts.to_pydatetime()


def _cell(row, idx: int) -> str:
    """Safely read column ``idx`` from a positional row as a clean string."""
    if idx >= len(row):
        return ""
    val = row.iloc[idx]
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def _make_submission_id(form: str, ts_raw: str, email: str, link: str) -> str:
    digest = hashlib.sha1(
        f"{form}|{ts_raw}|{email}|{link}".encode("utf-8")
    ).hexdigest()
    return f"{form}-{digest[:10]}"


def load_registrations(path: str | Path) -> list[Registration]:
    """Load the registration CSV (columns by position: 0..6)."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    regs: list[Registration] = []
    for _, row in df.iterrows():
        ts_raw = _cell(row, 0)
        name = _cell(row, 1)
        email = normalize_email(_cell(row, 2))
        affiliation = _cell(row, 3)
        members_text = _cell(row, 5)
        team_name = _cell(row, 6)
        if not team_name and not name:
            continue

        members = [(name, email)] if (name or email) else []
        members += parse_members(members_text)

        regs.append(
            Registration(
                team_key=normalize_team_name(team_name),
                display_name=team_name,
                affiliation=affiliation,
                submitter_name=name,
                submitter_email=email,
                members=members,
                timestamp=_to_dt(ts_raw),
            )
        )
    return regs


def _load_submissions(path: str | Path, form: str) -> list[Submission]:
    """Load a video/hardware CSV (columns: 0 ts, 1 name, 2 email, 3 team, 4 link)."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    subs: list[Submission] = []
    for _, row in df.iterrows():
        ts_raw = _cell(row, 0)
        name = _cell(row, 1)
        email = normalize_email(_cell(row, 2))
        team_name = _cell(row, 3)
        raw_cell = _cell(row, 4)
        if not team_name and not name and not raw_cell:
            continue
        links = parse_links(raw_cell)
        subs.append(
            Submission(
                form=form,
                submitter_name=name,
                submitter_email=email,
                team_name=team_name,
                raw_cell=raw_cell,
                timestamp=_to_dt(ts_raw),
                links=links,
                submission_id=_make_submission_id(
                    form, ts_raw, email, links[0] if links else raw_cell
                ),
            )
        )
    return subs


def load_video_submissions(path: str | Path) -> list[Submission]:
    return _load_submissions(path, FORM_VIDEO)


def load_hardware_submissions(path: str | Path) -> list[Submission]:
    return _load_submissions(path, FORM_HARDWARE)


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def _match_submission(
    sub: Submission,
    regs: list[Registration],
    reg_by_key: dict[str, Registration],
) -> tuple[str, str]:
    """Resolve a submission to a registration team_key.

    Returns ``(team_key, reason)``. Falls back to the submission's own
    normalized team name when nothing matches.
    """
    own_key = normalize_team_name(sub.team_name)
    email = sub.submitter_email
    name = sub.submitter_name.lower().strip()

    # 1. Exact normalized team-name match.
    if own_key and own_key in reg_by_key:
        return own_key, "Exact team name"

    # 2. Submitter email/name belongs to a registration's member set.
    for reg in regs:
        if email and email in reg.member_emails:
            return reg.team_key, f"Member email {email}"
    for reg in regs:
        if name and name in reg.member_names:
            return reg.team_key, f"Member name {sub.submitter_name}"

    # 3. Fuzzy team-name match.
    best_key, best_ratio = "", 0.0
    for reg in regs:
        if not reg.team_key or not own_key:
            continue
        ratio = SequenceMatcher(None, own_key, reg.team_key).ratio()
        if ratio > best_ratio:
            best_key, best_ratio = reg.team_key, ratio
    if best_ratio >= TEAM_NAME_RATIO:
        return best_key, f"Fuzzy team name ({best_ratio:.0%})"

    # 4. No match -> stand-alone key from the submission itself.
    return own_key or f"_unmatched_{sub.submission_id}", "No registration match"


def _latest(subs: list[Submission]) -> Submission | None:
    if not subs:
        return None
    return max(subs, key=lambda s: (s.timestamp or datetime.min))


def build_teams(
    regs: list[Registration],
    videos: list[Submission],
    hardware: list[Submission],
    overrides: dict | None = None,
    ticks: dict | None = None,
) -> list[Team]:
    """Aggregate registrations + submissions into Team objects.

    ``overrides`` may contain:
      - ``submission_links``: {submission_id: team_key}  (manual re-link)
      - ``ignored_submissions``: [submission_id, ...]    (drop as redundant)
    ``ticks`` maps team_key -> {"video_satisfied": bool, "hardware_satisfied": bool}.
    """
    overrides = overrides or {}
    ticks = ticks or {}
    submission_links = overrides.get("submission_links", {})
    ignored = set(overrides.get("ignored_submissions", []))

    reg_by_key: dict[str, Registration] = {}
    for reg in regs:
        # If duplicate registrations share a key, keep the latest.
        existing = reg_by_key.get(reg.team_key)
        if existing is None or (reg.timestamp or datetime.min) >= (
            existing.timestamp or datetime.min
        ):
            reg_by_key[reg.team_key] = reg

    teams: dict[str, Team] = {}

    def ensure_team(team_key: str) -> Team:
        if team_key not in teams:
            reg = reg_by_key.get(team_key)
            t = ticks.get(team_key, {})
            teams[team_key] = Team(
                team_key=team_key,
                display_name=reg.display_name if reg else team_key,
                affiliation=reg.affiliation if reg else "",
                registration=reg,
                members=reg.members if reg else [],
                video_satisfied=bool(t.get("video_satisfied", False)),
                hardware_satisfied=bool(t.get("hardware_satisfied", False)),
            )
        return teams[team_key]

    # Make sure every registration produces a team even with no submissions.
    for key in reg_by_key:
        ensure_team(key)

    for sub in videos + hardware:
        if sub.submission_id in ignored:
            continue
        if sub.submission_id in submission_links:
            team_key = submission_links[sub.submission_id]
            sub.match_reason = "Manual override"
        else:
            team_key, sub.match_reason = _match_submission(sub, regs, reg_by_key)
        sub.team_key = team_key

        team = ensure_team(team_key)
        # If team had no registration but the submission carries a nicer name.
        if not team.registration and not team.display_name:
            team.display_name = sub.team_name
        if sub.form == FORM_VIDEO:
            team.all_video.append(sub)
        else:
            team.all_hardware.append(sub)

    for team in teams.values():
        team.latest_video = _latest(team.all_video)
        team.latest_hardware = _latest(team.all_hardware)
        # Fall back to a readable name from a submission if no registration.
        if not team.display_name:
            src = team.latest_video or team.latest_hardware
            if src:
                team.display_name = src.team_name

    return sorted(teams.values(), key=lambda t: t.display_name.lower())


# ---------------------------------------------------------------------------
# Participant table rendering
# ---------------------------------------------------------------------------

def _clean_members_html(members: list[tuple[str, str]], fallback: str) -> str:
    """Render team members as ``Name<br>Name`` with emails stripped."""
    names: list[str] = []
    seen: set[str] = set()
    for n, _ in members:
        n = n.strip()
        if n and n.lower() not in seen:
            seen.add(n.lower())
            names.append(n)
    if not names:
        return fallback or "N/A"
    return "<br>".join(names)


def render_participant_rows(teams: list[Team]) -> str:
    """Build ``<tr>`` rows for certified teams for the participants tbody."""
    rows = []
    for team in teams:
        if not team.certified:
            continue
        members_html = _clean_members_html(team.members, "N/A")
        rows.append(
            "<tr>\n"
            f'<td style="text-align: left">{team.display_name}</td>\n'
            f'<td style="text-align: left">{team.affiliation}</td>\n'
            f'<td style="text-align: left">{members_html}</td>\n'
            "</tr>"
        )
    return "\n".join(rows)

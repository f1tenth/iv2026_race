#!/usr/bin/env python3
"""
Generate a Challonge bulk "Add Participants" list from the certified teams.

Challonge's bulk add takes one participant per line:

    Team Display Name, Team Captain Email or Username

The team captain is the registrant (the person who submitted the registration).
Uses the same certification data as the Event Manager, so the roster matches who
is actually certified.

Run:  uv run python Utils/challonge_participants.py
Writes Utils/challonge_participants.txt and prints the list.
"""

import json
import sys
from pathlib import Path

import certification as cert

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "event_config.json"
OUTPUT_FILE = SCRIPT_DIR / "challonge_participants.txt"


def main() -> None:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    teams = cert.teams_from_config(config.get("certification", {}))

    certified = [t for t in teams if t.certified]
    if certified:
        pool, label = certified, "certified"
    else:
        # Fall back to candidates (submitted both video + hardware) if nothing
        # has been ticked as certified yet.
        pool, label = [t for t in teams if t.is_candidate], "candidate"

    pool.sort(key=lambda t: t.display_name.lower())
    lines = [f"{t.display_name}, {t.leader_email}".rstrip(", ") for t in pool]
    output = "\n".join(lines)

    print(output)
    OUTPUT_FILE.write_text(output + "\n", encoding="utf-8")
    print(
        f"\n[{len(lines)} {label} team(s) written to {OUTPUT_FILE}]",
        file=sys.stderr,
    )
    missing = [t.display_name for t in pool if not t.leader_email]
    if missing:
        print(
            "[warning: no captain email for: " + ", ".join(missing) + "]",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()

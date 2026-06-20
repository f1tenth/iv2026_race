# Roboracer Event Management Utilities

This folder contains utilities for managing the Roboracer race event website.

## Event Manager GUI

The **Event Manager** is a GUI-based tool that allows organizers to easily configure and update the race website for new events.

### Running the Event Manager

```bash
# From the project root directory
uv run python Utils/event_manager.py
```

### Features

1. **Event Details Tab** - Configure:
   - Conference acronym (e.g., "ICRA") - year is added automatically
   - Full conference name (without year, e.g., "IEEE Conference on Robotics and Automation")
   - Race number (e.g., "25TH")
   - Year - combined with conference name automatically
   - Venue name and location
   - Conference URL and logo
   - Conference dates (without year, e.g., "May 19th - 23rd")
   - Contact email
   - CNAME (domain)

2. **Dates & Timeline Tab** - Automatically calculate event dates:
   - Set the Race Day (before-last day of conference)
   - All other dates are calculated using configurable offsets
   - Preview calculated dates before applying

3. **Orientations Tab** - Configure orientation meeting links:
   - Zoom meeting links
   - Slides links (Google Presentations)
   - Video recording links (Google Drive)

4. **Registration Tab** - Manage registration status:
   - Toggle registration open/closed
   - Set registration form link
   - Configure Sim Racing League settings

5. **Results & Stream Tab** - Configure results and streaming:
   - Time trial sheet link
   - Head-to-head bracket link
   - YouTube/Twitch streaming settings

6. **Certification Tab** - Certify teams from the three Google-Form CSV exports:
   - Load the Registration, Video Submission, and Hardware List CSVs (auto-detected
     in `Utils/`; paths are remembered between sessions)
   - **Process / Reprocess** matches submissions to registrations even when a
     different team member submitted each form and team names are inconsistent
     (exact → member email/name → fuzzy name → manual override)
   - Only **candidate teams** (submitted *both* a video and a hardware list) are
     shown for checking; teams missing either appear under "Not considered"
   - Per submission: see the submitter, the **raw link** (always shown so you can
     inspect it), an offline **safety badge** (ok / suspicious / blocked / no-link),
     an **Open Link** button (with a confirmation showing the full URL; disabled for
     blocked/no-link), **Mark malicious**, **Ignore submission**, and a dropdown of
     older submissions (only the latest counts)
   - Tick **Video satisfied** and **Hardware satisfied** individually; once both are
     ticked *and* the team is matched to a registration it becomes **certified**
   - Use **Manually link this submission to registration** to fix mismatches
   - **Team members**: add or remove members on the selected team (Add/Remove
     member). Edits are stored as deltas and survive reprocessing
   - **Add Manual Team**: register a team by hand (name, affiliation, leader,
     members). Manual teams count as registered and are certified by default, so
     they appear in the participants list even without form submissions; select
     one to **Remove Manual Team**
   - **Emails to team leaders** (no external API):
     - **Compose Email** opens your mail client (via `mailto:`) pre-filled to the
       team leader — a *confirmation* if all three requirements are met, otherwise
       a *reminder* that names exactly which requirement(s) are still outstanding.
       Subjects are templated (e.g. `Roboracer IV 2026 Registration - Confirmation`)
     - Every email includes the standing reminder that team members must also
       register for the conference itself to access the venue
     - **Export Emails...** writes one `.eml` file per registered team into a folder
       you choose (confirmations + reminders) for you to review and send in bulk
     - **Email Settings...** configures the signature, the conference-registration
       URL and note (e.g. the dedicated competition category), and optional extra
       paragraphs appended to confirmation/reminder emails (prize pool, travel
       stipend, and other competition-specific details)
   - Re-run any time after new responses arrive — your ticks, overrides, member
     edits, and manual teams all persist
   - On **Apply to Repository**, certified teams (including manual ones) populate
     the Participants table on the registration page

### Configuration File

All settings are stored in `Utils/event_config.json`. This file can be:
- Edited manually if needed
- Backed up for different events
- Version controlled

### Applying Changes

Click **"Apply to Repository"** to update all HTML and Markdown files with the new configuration. The tool will:
- Update page titles
- Update conference names and dates
- Update venue information
- Update registration status and links
- Update orientation links
- Update result/stream links
- Update CNAME file

### Date Calculation

The date calculator replaces the old Excel-based AutoDateCalculator. It uses these default offsets from race day:

| Event | Offset (days) |
|-------|---------------|
| Qualification | -1 |
| Team Training | -2 |
| Track Setup | -3 |
| Orientation 2 | -38 |
| Registration Closes | -40 |
| Orientation 1 | -66 |
| Registration Opens | -113 |

Adjust these offsets in the Dates & Timeline tab as needed.

## Files

- `event_config.json` - Current event configuration (JSON), including the
  `certification` block (CSV paths, per-team ticks, and link/match overrides)
- `event_manager.py` - Main GUI application
- `certification.py` - Certification logic (CSV loading, matching, link safety,
  participant-row rendering) used by the Certification tab
- `test_certification.py` - Assertion tests for `certification.py`
  (run: `uv run python Utils/test_certification.py`)
- `*Form Responses.csv` - The three Google-Form exports (Registration, Video
  Submission, Hardware List) consumed by the Certification tab


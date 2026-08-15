#!/usr/bin/env python3
"""Generate Adelaide's project portfolio and GitHub statistics.

The script is designed for GitHub Actions. It discovers public repositories,
keeps renamed repositories linked by their stable numeric IDs, categorises new
projects, renders the pink SVG cards, and updates only the generated section of
the profile README.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
GENERATED_DIR = ROOT / "assets" / "generated"
STATE_PATH = GENERATED_DIR / "profile-state.json"

OWNER = os.environ.get("PROFILE_OWNER", "Adelaidemhuntana")
PROFILE_REPOSITORY_ID = 1334098560

START_MARKER = "<!-- AUTO-PROFILE:START -->"
END_MARKER = "<!-- AUTO-PROFILE:END -->"

CATEGORY_ORDER = [
    "Data Engineering",
    "Cloud & AI",
    "Software Development",
    "Learning & More Projects",
    "Other Projects",
]

CATEGORY_INFO = {
    "Data Engineering": (
        "DB",
        "Pipelines, analytics, reporting and cloud data services",
        "data-engineering",
    ),
    "Cloud & AI": (
        "AI",
        "Cloud-ready APIs, intelligent systems and learning tools",
        "cloud-ai",
    ),
    "Software Development": (
        "</>",
        "Web applications, responsive interfaces and portfolio work",
        "software-development",
    ),
    "Learning & More Projects": (
        "+",
        "Additional builds, coursework and practical exercises",
        "learning-more",
    ),
    "Other Projects": (
        "...",
        "New public work that is still being classified",
        "other-projects",
    ),
}

# Stable repository IDs keep these choices correct after a repository rename.
CATEGORY_OVERRIDES = {
    870650668: "Data Engineering",
    1228086103: "Cloud & AI",
    1255115903: "Cloud & AI",
    880809395: "Software Development",
    898606885: "Software Development",
    1199917963: "Software Development",
    900740594: "Software Development",
    1022297313: "Learning & More Projects",
    1018009619: "Learning & More Projects",
    1090790131: "Learning & More Projects",
}

DISPLAY_ORDER = {
    870650668: 10,
    1228086103: 20,
    1255115903: 30,
    880809395: 40,
    898606885: 50,
    1199917963: 60,
    900740594: 70,
    1022297313: 80,
    1018009619: 90,
    1090790131: 100,
}

LEGACY_DISPLAY_TITLES = {
    # Show the new platform identity while the repository still has its old
    # website name. Once it is renamed, the new repository name is used.
    870650668: (
        "Mahube-valley-primary-school-website",
        "Smart School Placement Hub",
    ),
    1228086103: (
        "multi-agent-ai-course-generator",
        "Multi-Agent AI Course Generator",
    ),
    1255115903: (
        "aws-partyrock-educare-ai-sa",
        "AWS PartyRock Educare AI",
    ),
    880809395: (
        "my-shecodes-plus-weather-final-project",
        "SheCodes Weather App",
    ),
    1090790131: (
        "jhb58-mars_rover_prep",
        "Mars Rover Preparation",
    ),
}

CURATED_DESCRIPTIONS = {
    870650668: (
        "A data and cloud platform improving Grade 1 and Grade 8 school "
        "placement. Includes FastAPI services, ETL analytics and AWS deployment."
    ),
    1228086103: (
        "A distributed multi-agent system that researches, evaluates and "
        "creates structured courses using cloud-ready services."
    ),
    1255115903: (
        "Educational AI projects using AWS PartyRock to support South African "
        "learners and analyse learning needs."
    ),
    880809395: (
        "A responsive weather application using live forecast data and a clean "
        "user interface."
    ),
    898606885: (
        "Coding notes, challenges and mini projects documenting my software "
        "learning journey."
    ),
    1199917963: (
        "A personal portfolio presenting my software, data and cloud projects."
    ),
    900740594: (
        "A preschool website project created with Python and web technologies."
    ),
    1022297313: "A practical website project developed while building frontend skills.",
    1018009619: "Python coursework and exercises documenting progress through CS50P.",
    1090790131: (
        "A Python preparation project practising file parsing, state management "
        "and error handling."
    ),
}

CURATED_TAGS = {
    870650668: ["Python", "PySpark", "FastAPI", "Power BI", "Amazon S3", "Amazon RDS"],
    1228086103: ["Python", "FastAPI", "Docker", "Google Cloud"],
    1255115903: ["AWS", "PartyRock", "AI", "Education"],
    880809395: ["JavaScript", "HTML", "CSS", "API"],
    898606885: ["JavaScript", "Python", "Notes"],
    1199917963: ["HTML", "CSS", "JavaScript", "Portfolio"],
    900740594: ["Python", "Web", "Education"],
    1022297313: ["HTML", "CSS", "Learning"],
    1018009619: ["Python", "CS50P", "Learning"],
    1090790131: ["Python", "Testing", "Learning"],
}

CURATED_BADGES = {
    870650668: "DATA",
    1228086103: "AI",
    1255115903: "AWS",
    880809395: "SUN",
    898606885: "CODE",
    1199917963: "AM",
    900740594: "WEB",
    1022297313: "WEB",
    1018009619: "PY",
    1090790131: "PY",
}

ACRONYMS = {
    "ai": "AI",
    "api": "API",
    "aws": "AWS",
    "css": "CSS",
    "css3": "CSS3",
    "cs50p": "CS50P",
    "etl": "ETL",
    "gcp": "GCP",
    "html": "HTML",
    "html5": "HTML5",
    "ml": "ML",
    "partyrock": "PartyRock",
    "rds": "RDS",
    "s3": "S3",
    "sa": "SA",
    "sql": "SQL",
    "shecodes": "SheCodes",
    "ui": "UI",
    "ux": "UX",
}

PALETTE = {
    "rose": "#E83E76",
    "deep": "#7F1837",
    "wine": "#8B1E42",
    "pink": "#D92E68",
    "paper": "#FFFDFB",
    "paper2": "#FFF5F3",
    "chip": "#FFF0F3",
    "border": "#E8C7D0",
    "muted": "#72535E",
    "body": "#493139",
}


def api_json(url: str, token: str, body: dict[str, Any] | None = None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "a-montana-profile-automation",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed ({exc.code}): {details}") from exc


def fetch_readme(repo: dict[str, Any], token: str) -> str:
    full_name = urllib.parse.quote(repo["full_name"], safe="/")
    try:
        payload = api_json(f"https://api.github.com/repos/{full_name}/readme", token)
    except RuntimeError as exc:
        if "(404)" in str(exc):
            return ""
        raise
    encoded = payload.get("content", "").replace("\n", "")
    if not encoded:
        return ""
    return base64.b64decode(encoded).decode("utf-8", errors="replace")


def fetch_languages(repo: dict[str, Any], token: str) -> dict[str, int]:
    full_name = urllib.parse.quote(repo["full_name"], safe="/")
    return api_json(f"https://api.github.com/repos/{full_name}/languages", token)


def fetch_live_data() -> dict[str, Any]:
    token = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required when a fixture is not supplied")

    repos: list[dict[str, Any]] = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/users/{OWNER}/repos"
            f"?per_page=100&page={page}&type=owner&sort=updated"
        )
        batch = api_json(url, token)
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    for repo in repos:
        repo["languages"] = fetch_languages(repo, token)
        repo["readme_text"] = fetch_readme(repo, token)

    user = api_json(f"https://api.github.com/users/{OWNER}", token)
    query = """
      query($login: String!) {
        user(login: $login) {
          contributionsCollection {
            contributionCalendar {
              totalContributions
              weeks {
                contributionDays {
                  date
                  contributionCount
                  contributionLevel
                }
              }
            }
          }
        }
      }
    """
    contribution_result = api_json(
        "https://api.github.com/graphql",
        token,
        {"query": query, "variables": {"login": OWNER}},
    )
    if contribution_result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {contribution_result['errors']}")
    calendar = contribution_result["data"]["user"]["contributionsCollection"][
        "contributionCalendar"
    ]

    return {
        "repos": repos,
        "user": {
            "public_repos": user.get("public_repos", len(repos)),
            "followers": user.get("followers", 0),
        },
        "contributions": {
            "total": calendar.get("totalContributions", 0),
            "weeks": calendar.get("weeks", []),
        },
    }


def load_data(fixture_path: str | None) -> dict[str, Any]:
    if fixture_path:
        return json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    return fetch_live_data()


def repository_id(repo: dict[str, Any]) -> int:
    return int(repo["id"])


def humanise_name(name: str) -> str:
    words = [word for word in re.split(r"[-_\s]+", name.strip("-_ ")) if word]
    result = []
    for word in words:
        lower = word.lower()
        result.append(ACRONYMS.get(lower, word.capitalize()))
    return " ".join(result)


def display_title(repo: dict[str, Any]) -> str:
    rid = repository_id(repo)
    legacy = LEGACY_DISPLAY_TITLES.get(rid)
    if legacy and repo["name"] == legacy[0]:
        return legacy[1]
    return humanise_name(repo["name"])


def searchable_text(repo: dict[str, Any]) -> str:
    topics = " ".join(repo.get("topics") or [])
    languages = " ".join((repo.get("languages") or {}).keys())
    return " ".join(
        [
            repo.get("name") or "",
            repo.get("description") or "",
            topics,
            languages,
            repo.get("readme_text") or "",
        ]
    ).lower()


def category_for(repo: dict[str, Any]) -> str:
    rid = repository_id(repo)
    if rid in CATEGORY_OVERRIDES:
        return CATEGORY_OVERRIDES[rid]

    text = searchable_text(repo)
    if repo.get("fork") or re.search(
        r"\b(course|coursework|progress|prep|practice|assessment|tutorial|learning|exercise)\b",
        text,
    ):
        return "Learning & More Projects"
    if re.search(
        r"\b(data engineering|etl|pipeline|pyspark|spark|power bi|analytics|warehouse|data lake)\b",
        text,
    ):
        return "Data Engineering"
    if re.search(
        r"\b(aws|amazon s3|amazon rds|google cloud|gcp|cloud run|cloud|docker|artificial intelligence|generative ai|machine learning|multi-agent|llm)\b",
        text,
    ):
        return "Cloud & AI"
    if re.search(
        r"\b(portfolio|website|web app|application|frontend|backend|java|javascript|html|css|python|typescript|react|flask|fastapi)\b",
        text,
    ):
        return "Software Development"
    return "Other Projects"


def description_for(repo: dict[str, Any]) -> str:
    rid = repository_id(repo)
    if rid in CURATED_DESCRIPTIONS:
        return CURATED_DESCRIPTIONS[rid]
    description = (repo.get("description") or "").strip()
    if description:
        return description
    return "A public project in progress. Open the repository to follow its development."


def detected_tags(repo: dict[str, Any]) -> list[str]:
    rid = repository_id(repo)
    if rid in CURATED_TAGS:
        return CURATED_TAGS[rid]

    languages = list((repo.get("languages") or {}).keys())
    topics = [humanise_name(topic) for topic in (repo.get("topics") or [])]
    text = searchable_text(repo)
    services = []
    for label, pattern in [
        ("Amazon S3", r"\b(amazon s3|aws s3)\b"),
        ("Amazon RDS", r"\b(amazon rds|aws rds)\b"),
        ("FastAPI", r"\bfastapi\b"),
        ("PySpark", r"\bpyspark\b"),
        ("Power BI", r"\bpower bi\b"),
        ("Docker", r"\bdocker\b"),
        ("AWS", r"\baws\b"),
        ("Google Cloud", r"\b(google cloud|gcp)\b"),
    ]:
        if re.search(pattern, text):
            services.append(label)

    tags = []
    for tag in languages + services + topics:
        if tag and tag not in tags:
            tags.append(tag)
    return tags[:6] or ["Project"]


def badge_for(repo: dict[str, Any], category: str, tags: list[str]) -> str:
    rid = repository_id(repo)
    if rid in CURATED_BADGES:
        return CURATED_BADGES[rid]
    first = tags[0].lower() if tags else ""
    language_badges = {
        "python": "PY",
        "java": "JAVA",
        "javascript": "JS",
        "typescript": "TS",
        "html": "WEB",
        "css": "WEB",
    }
    if first in language_badges:
        return language_badges[first]
    return {
        "Data Engineering": "DATA",
        "Cloud & AI": "AI",
        "Software Development": "CODE",
        "Learning & More Projects": "+",
        "Other Projects": "NEW",
    }[category]


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def wrap_lines(text: str, width: int, limit: int) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    lines = textwrap.wrap(cleaned, width=width, break_long_words=False, break_on_hyphens=False)
    if not lines:
        return [""]
    if len(lines) > limit:
        lines = lines[:limit]
        lines[-1] = lines[-1].rstrip(" .") + "..."
    return lines


def chip_markup(tags: list[str], start_x: int, y: int, max_x: int) -> str:
    pieces = []
    x = start_x
    for tag in tags:
        width = max(54, 24 + len(tag) * 7)
        if x + width > max_x:
            break
        pieces.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="26" rx="7" '
            f'fill="{PALETTE["chip"]}" stroke="{PALETTE["border"]}"/>'
            f'<text x="{x + width / 2:g}" y="{y + 17}" text-anchor="middle" '
            f'font-family="Arial, sans-serif" font-size="10.5" '
            f'fill="{PALETTE["deep"]}">{escape(tag)}</text>'
        )
        x += width + 8
    return "".join(pieces)


def card_svg(repo: dict[str, Any], category: str, layout: str) -> str:
    title = display_title(repo)
    description = description_for(repo)
    tags = detected_tags(repo)
    badge = badge_for(repo, category, tags)

    if layout == "wide":
        width, height = 1160, 220
        badge_x, badge_y, badge_size = 22, 24, 72
        text_x = 114
        title_lines = wrap_lines(title, 74, 2)
        desc_lines = wrap_lines(description, 112, 3)
        chip_y, max_x = 176, 1128
        title_size = 19
    else:
        width, height = 570, 220
        badge_x, badge_y, badge_size = 22, 24, 72
        text_x = 112
        title_lines = wrap_lines(title, 38, 2)
        desc_lines = wrap_lines(description, 52, 3)
        chip_y, max_x = 176, 540
        title_size = 17

    title_spans = []
    for index, line in enumerate(title_lines):
        title_spans.append(
            f'<tspan x="{text_x}" dy="{0 if index == 0 else 22}">{escape(line)}</tspan>'
        )
    title_y = 48
    desc_y = 94 if len(title_lines) == 1 else 112
    desc_spans = []
    for index, line in enumerate(desc_lines):
        desc_spans.append(
            f'<tspan x="{text_x}" dy="{0 if index == 0 else 21}">{escape(line)}</tspan>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(description)}</desc>
  <defs>
    <linearGradient id="paper" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFDFB"/><stop offset="1" stop-color="#FFF5F3"/></linearGradient>
    <linearGradient id="rose" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#E83E76"/><stop offset="1" stop-color="#9A1E45"/></linearGradient>
  </defs>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="18" fill="url(#paper)" stroke="#E8C7D0"/>
  <rect x="{badge_x}" y="{badge_y}" width="{badge_size}" height="{badge_size}" rx="15" fill="url(#rose)"/>
  <text x="{badge_x + badge_size / 2:g}" y="{badge_y + 45}" text-anchor="middle" font-family="Arial, sans-serif" font-size="{17 if len(badge) > 3 else 23}" font-weight="700" fill="#FFF9F7">{escape(badge)}</text>
  <text x="{text_x}" y="{title_y}" font-family="Arial, sans-serif" font-size="{title_size}" font-weight="700" fill="#7F1837">{''.join(title_spans)}</text>
  <text x="{text_x}" y="{desc_y}" font-family="Arial, sans-serif" font-size="13.5" fill="#493139">{''.join(desc_spans)}</text>
  {chip_markup(tags, text_x, chip_y, max_x)}
  <path d="M{width - 40} 26h14v14M{width - 27} 27l-16 16" fill="none" stroke="#E83E76" stroke-width="2" stroke-linecap="round"/>
</svg>
'''


def compact_card_svg(repo: dict[str, Any], category: str) -> str:
    title = display_title(repo)
    tags = detected_tags(repo)
    badge = badge_for(repo, category, tags)
    tag = tags[0] if tags else "Project"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="370" height="96" viewBox="0 0 370 96" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(description_for(repo))}</desc>
  <defs><linearGradient id="paper" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFDFB"/><stop offset="1" stop-color="#FFF5F3"/></linearGradient></defs>
  <rect x="1" y="1" width="368" height="94" rx="14" fill="url(#paper)" stroke="#E8C7D0"/>
  <circle cx="40" cy="48" r="24" fill="#FBE8EC"/>
  <text x="40" y="53" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#C32D5D">{escape(badge)}</text>
  <text x="76" y="42" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#7F1837">{escape(title[:35] + ('...' if len(title) > 35 else ''))}</text>
  <text x="76" y="64" font-family="Arial, sans-serif" font-size="11" fill="#72535E">{escape(tag)}</text>
  <path d="M340 25h11v11M350 26l-13 13" fill="none" stroke="#E83E76" stroke-width="1.8" stroke-linecap="round"/>
</svg>
'''


def category_header_svg(title: str, badge: str, subtitle: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="76" viewBox="0 0 1200 76" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(subtitle)}</desc>
  <circle cx="24" cy="28" r="19" fill="#FBE8EC"/>
  <text x="24" y="34" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#C32D5D">{escape(badge)}</text>
  <text x="57" y="34" font-family="Arial, sans-serif" font-size="19" font-weight="700" letter-spacing="1.4" fill="#8B1E42">{escape(title.upper())}</text>
  <text x="57" y="58" font-family="Arial, sans-serif" font-size="12.5" fill="#72535E">{escape(subtitle)}</text>
  <line x1="510" y1="28" x2="1190" y2="28" stroke="#E8C7D0"/>
</svg>
'''


def portfolio_header_svg() -> str:
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="108" viewBox="0 0 1200 108" role="img" aria-labelledby="title desc">
  <title id="title">Project Portfolio</title>
  <desc id="desc">Public work organised automatically by specialisation</desc>
  <text x="600" y="48" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="36" fill="#7F1837">Project Portfolio</text>
  <text x="600" y="80" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" letter-spacing="1.4" fill="#9A6677">PUBLIC WORK ORGANISED AUTOMATICALLY BY SPECIALISATION</text>
</svg>
'''


def placeholder_weeks(total: int) -> list[dict[str, Any]]:
    start = date.today() - timedelta(days=370)
    start -= timedelta(days=(start.weekday() + 1) % 7)
    counts = [0] * (53 * 7)
    remaining = max(0, total)
    positions = [
        22, 31, 43, 57, 66, 75, 91, 105, 116, 128, 139, 151, 166, 178,
        190, 202, 214, 226, 238, 250, 262, 274, 286, 298, 310, 322, 334,
        346, 352, 358, 365,
    ]
    index = 0
    while remaining > 0:
        position = positions[index % len(positions)]
        amount = min(1 + (index % 4), remaining)
        counts[position] += amount
        remaining -= amount
        index += 1
    weeks = []
    for week_index in range(53):
        days = []
        for weekday in range(7):
            day_index = week_index * 7 + weekday
            count = counts[day_index]
            level = "NONE"
            if count == 1:
                level = "FIRST_QUARTILE"
            elif count == 2:
                level = "SECOND_QUARTILE"
            elif count == 3:
                level = "THIRD_QUARTILE"
            elif count >= 4:
                level = "FOURTH_QUARTILE"
            days.append(
                {
                    "date": (start + timedelta(days=day_index)).isoformat(),
                    "contributionCount": count,
                    "contributionLevel": level,
                }
            )
        weeks.append({"contributionDays": days})
    return weeks


def stats_svg(data: dict[str, Any]) -> str:
    total_contributions = int(data.get("contributions", {}).get("total", 0))
    weeks = data.get("contributions", {}).get("weeks") or placeholder_weeks(total_contributions)

    level_colours = {
        "NONE": "#F9E8EC",
        "FIRST_QUARTILE": "#F5B9C8",
        "SECOND_QUARTILE": "#EC7898",
        "THIRD_QUARTILE": "#D9366B",
        "FOURTH_QUARTILE": "#8B1B3D",
    }
    squares = []
    month_labels = []
    seen_months: set[str] = set()
    graph_x, graph_y, step, square = 72, 98, 20, 16
    for week_index, week in enumerate(weeks[-53:]):
        for weekday, day in enumerate(week.get("contributionDays", [])):
            if weekday > 6:
                continue
            level = day.get("contributionLevel", "NONE")
            colour = level_colours.get(level, "#F9E8EC")
            x = graph_x + week_index * step
            y = graph_y + weekday * step
            squares.append(
                f'<rect x="{x}" y="{y}" width="{square}" height="{square}" rx="2" fill="{colour}"><title>{escape(day.get("date", ""))}: {int(day.get("contributionCount", 0))} contributions</title></rect>'
            )
            day_date = day.get("date")
            if weekday == 0 and day_date:
                month_key = day_date[:7]
                if month_key not in seen_months:
                    seen_months.add(month_key)
                    try:
                        label = datetime.strptime(day_date, "%Y-%m-%d").strftime("%b")
                    except ValueError:
                        label = ""
                    month_labels.append(
                        f'<text x="{x}" y="82" font-family="Arial, sans-serif" font-size="11" fill="#72535E">{label}</text>'
                    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="290" viewBox="0 0 1200 290" role="img" aria-labelledby="title desc">
  <title id="title">Contribution activity</title>
  <desc id="desc">Automatically updated contribution calendar for A Montana</desc>
  <defs><linearGradient id="paper" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFDFB"/><stop offset="1" stop-color="#FFF3F2"/></linearGradient></defs>
  <rect x="1" y="1" width="1198" height="288" rx="20" fill="url(#paper)" stroke="#EEC3CD"/>
  <circle cx="34" cy="38" r="18" fill="#D92E68"/>
  <path d="M25 47V37m7 10V29m7 18V34m7 13V25" stroke="#FFF9F7" stroke-width="2"/>
  <text x="64" y="44" font-family="Arial, sans-serif" font-size="17" font-weight="700" letter-spacing="1.8" fill="#D92E68">CONTRIBUTION ACTIVITY</text>
  <text x="1168" y="44" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#72535E">{total_contributions} contributions in the last year</text>
  {''.join(month_labels)}
  {''.join(squares)}
  <text x="72" y="263" font-family="Arial, sans-serif" font-size="11" fill="#72535E">Less</text>
  <rect x="104" y="251" width="13" height="13" rx="3" fill="#F9E8EC"/><rect x="122" y="251" width="13" height="13" rx="3" fill="#F5B9C8"/><rect x="140" y="251" width="13" height="13" rx="3" fill="#EC7898"/><rect x="158" y="251" width="13" height="13" rx="3" fill="#D9366B"/><rect x="176" y="251" width="13" height="13" rx="3" fill="#8B1B3D"/>
  <text x="195" y="263" font-family="Arial, sans-serif" font-size="11" fill="#72535E">More</text>
  <text x="1168" y="263" text-anchor="end" font-family="Georgia, serif" font-size="13" font-style="italic" fill="#72535E">Updated automatically every 6 hours</text>
</svg>
'''


def write_generated_assets(data: dict[str, Any], projects: list[dict[str, Any]]) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    expected = {
        "profile-state.json",
        "project-portfolio-header.svg",
        "github-stats.svg",
    }

    (GENERATED_DIR / "project-portfolio-header.svg").write_text(
        portfolio_header_svg(), encoding="utf-8"
    )
    (GENERATED_DIR / "github-stats.svg").write_text(stats_svg(data), encoding="utf-8")

    categories = {category_for(repo) for repo in projects}
    for category in CATEGORY_ORDER:
        if category not in categories:
            continue
        badge, subtitle, slug = CATEGORY_INFO[category]
        filename = f"category-{slug}.svg"
        expected.add(filename)
        (GENERATED_DIR / filename).write_text(
            category_header_svg(category, badge, subtitle), encoding="utf-8"
        )

    for repo in projects:
        rid = repository_id(repo)
        category = category_for(repo)
        filename = f"project-{rid}.svg"
        expected.add(filename)
        if category == "Learning & More Projects":
            content = compact_card_svg(repo, category)
        else:
            content = card_svg(repo, category, "wide" if category == "Data Engineering" else "standard")
        (GENERATED_DIR / filename).write_text(content, encoding="utf-8")

    for path in GENERATED_DIR.glob("*.svg"):
        if path.name not in expected:
            path.unlink()

    state = {
        str(repository_id(repo)): repo["full_name"]
        for repo in data["repos"]
        if not repo.get("private")
    }
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def project_markdown(projects: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in CATEGORY_ORDER}
    for repo in projects:
        grouped[category_for(repo)].append(repo)
    for category in CATEGORY_ORDER:
        grouped[category].sort(
            key=lambda repo: (
                DISPLAY_ORDER.get(repository_id(repo), 1000),
                repo.get("pushed_at") or "",
            )
        )

    lines = [
        START_MARKER,
        '<p align="center"><img src="./assets/generated/project-portfolio-header.svg" width="100%" alt="Project Portfolio"></p>',
        "",
    ]
    for category in CATEGORY_ORDER:
        repos = grouped[category]
        if not repos:
            continue
        slug = CATEGORY_INFO[category][2]
        lines.extend(
            [
                f'<p><img src="./assets/generated/category-{slug}.svg" width="100%" alt="{escape(category)}"></p>',
                "",
            ]
        )
        if category == "Data Engineering":
            for repo in repos:
                lines.extend(
                    [
                        '<p align="center">',
                        f'  <a href="{escape(repo["html_url"])}"><img src="./assets/generated/project-{repository_id(repo)}.svg" width="100%" alt="{escape(display_title(repo))}"></a>',
                        "</p>",
                        "",
                    ]
                )
        else:
            per_row = 3 if category == "Learning & More Projects" else 2
            width = "32%" if per_row == 3 else "49%"
            for offset in range(0, len(repos), per_row):
                lines.append('<p align="center">')
                for repo in repos[offset : offset + per_row]:
                    lines.append(
                        f'  <a href="{escape(repo["html_url"])}"><img src="./assets/generated/project-{repository_id(repo)}.svg" width="{width}" alt="{escape(display_title(repo))}"></a>'
                    )
                lines.extend(["</p>", ""])

    lines.extend(
        [
            '<p><img src="./assets/generated/category-github-activity.svg" width="100%" alt="GitHub Activity"></p>',
            "",
            '<p align="center"><img src="./assets/generated/github-stats.svg" width="100%" alt="Automatically updated GitHub statistics"></p>',
            END_MARKER,
        ]
    )
    return "\n".join(lines)


def activity_header_svg() -> str:
    return category_header_svg(
        "GitHub Activity",
        "GH",
        "Contribution data and profile statistics from GitHub",
    )


def update_readme(data: dict[str, Any], projects: list[dict[str, Any]]) -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    old_state: dict[str, str] = {}
    if STATE_PATH.exists():
        try:
            old_state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            old_state = {}
    for repo in data["repos"]:
        rid = str(repository_id(repo))
        old_full_name = old_state.get(rid)
        new_full_name = repo["full_name"]
        if old_full_name and old_full_name != new_full_name:
            readme = readme.replace(
                f"https://github.com/{old_full_name}",
                f"https://github.com/{new_full_name}",
            )

    generated = project_markdown(projects)
    if START_MARKER in readme and END_MARKER in readme:
        pattern = re.compile(
            re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
            re.DOTALL,
        )
        readme = pattern.sub(generated, readme)
    else:
        readme = readme.rstrip() + "\n\n" + generated + "\n"
    README_PATH.write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", help="Use local JSON data instead of the GitHub API")
    args = parser.parse_args()

    data = load_data(args.fixture)
    projects = [
        repo
        for repo in data["repos"]
        if not repo.get("private")
        and not repo.get("archived")
        and repository_id(repo) != PROFILE_REPOSITORY_ID
    ]

    # Capture the old state before it is replaced so renamed links in the fixed
    # clickable technology section can be updated as well.
    old_state_text = STATE_PATH.read_text(encoding="utf-8") if STATE_PATH.exists() else None
    write_generated_assets(data, projects)
    if old_state_text is not None:
        STATE_PATH.write_text(old_state_text, encoding="utf-8")
    (GENERATED_DIR / "category-github-activity.svg").write_text(
        activity_header_svg(), encoding="utf-8"
    )
    update_readme(data, projects)
    state = {
        str(repository_id(repo)): repo["full_name"]
        for repo in data["repos"]
        if not repo.get("private")
    }
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        f"Updated {len(projects)} project cards, the profile README and GitHub statistics."
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate Adelaide's pink GitHub profile SVG cards.

When GITHUB_TOKEN is available, public repository and contribution data are
loaded from GitHub's GraphQL API. Without a token, preview data is used so the
profile can be reviewed before it is uploaded.
"""

from __future__ import annotations

import json
import math
import os
import textwrap
import urllib.request
from datetime import datetime
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
USERNAME = os.environ.get("GITHUB_USERNAME", "Adelaidemhuntana")

PROJECTS = [
    "multi-agent-ai-course-generator",
    "my-shecodes-plus-weather-final-project",
    "the-coding-lady",
    "aws-partyrock-educare-ai-sa",
]

PROJECT_FALLBACKS = {
    "multi-agent-ai-course-generator": {
        "description": "A cloud-ready multi-agent AI system that generates structured courses from user prompts.",
        "language": "Python",
        "tags": ["Python", "FastAPI", "Microservices", "AI"],
        "stars": 0,
        "icon": "AI",
    },
    "my-shecodes-plus-weather-final-project": {
        "description": "A responsive weather application with real-time forecasts and a clean user interface.",
        "language": "JavaScript",
        "tags": ["JavaScript", "API", "HTML", "CSS"],
        "stars": 0,
        "icon": "SUN",
    },
    "the-coding-lady": {
        "description": "A collection of coding notes, challenges and mini projects created during my learning journey.",
        "language": "JavaScript",
        "tags": ["JavaScript", "Python", "Notes"],
        "stars": 0,
        "icon": "</>",
    },
    "aws-partyrock-educare-ai-sa": {
        "description": "An educational AI project built with AWS PartyRock for South African learners.",
        "language": "JavaScript",
        "tags": ["AWS", "AI", "Education"],
        "stars": 0,
        "icon": "AWS",
    },
}

COLORS = {
    "paper": "#FFF9F7",
    "panel": "#FFFDFB",
    "blush": "#FDEBED",
    "soft": "#F9D6DF",
    "line": "#EEC3CD",
    "rose": "#D92E68",
    "hot": "#E83E76",
    "wine": "#7F1837",
    "text": "#3E222C",
    "muted": "#72535E",
    "gold": "#D99A51",
}


def graphql_data(token: str) -> dict:
    query = """
    query Profile($login: String!) {
      user(login: $login) {
        login
        followers { totalCount }
        repositories(
          first: 100
          ownerAffiliations: OWNER
          privacy: PUBLIC
          orderBy: {field: UPDATED_AT, direction: DESC}
        ) {
          totalCount
          nodes {
            name
            description
            url
            stargazerCount
            primaryLanguage { name color }
            repositoryTopics(first: 8) {
              nodes { topic { name } }
            }
          }
        }
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
                weekday
              }
            }
          }
        }
      }
    }
    """
    body = json.dumps({"query": query, "variables": {"login": USERNAME}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "adelaide-profile-readme",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], indent=2))
    user = payload.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user {USERNAME!r} was not found")
    return user


def preview_data() -> dict:
    nodes = []
    for name in PROJECTS:
        fallback = PROJECT_FALLBACKS[name]
        nodes.append(
            {
                "name": name,
                "description": fallback["description"],
                "url": f"https://github.com/{USERNAME}/{name}",
                "stargazerCount": fallback["stars"],
                "primaryLanguage": {"name": fallback["language"], "color": "#D92E68"},
                "repositoryTopics": {"nodes": []},
            }
        )

    # A soft preview pattern. GitHub replaces this with the live contribution
    # calendar during the first workflow run.
    weeks = []
    for week in range(53):
        days = []
        for weekday in range(7):
            active = (week * 7 + weekday) % 17 in {0, 4, 9}
            days.append(
                {
                    "date": f"2026-01-{(week + weekday) % 28 + 1:02d}",
                    "weekday": weekday,
                    "contributionCount": ((week + weekday) % 4 + 1) if active else 0,
                }
            )
        weeks.append({"contributionDays": days})

    return {
        "login": USERNAME,
        "followers": {"totalCount": 2},
        "repositories": {"totalCount": 12, "nodes": nodes},
        "contributionsCollection": {
            "contributionCalendar": {"totalContributions": 94, "weeks": weeks}
        },
    }


def svg_document(width: int, height: int, body: str, title: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">Pink professional GitHub profile card for Adelaide Mhuntana</desc>
  <defs>
    <linearGradient id="roseGradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#E83E76"/>
      <stop offset="1" stop-color="#9A1E45"/>
    </linearGradient>
    <linearGradient id="paperGradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FFFDFB"/>
      <stop offset="1" stop-color="#FFF3F2"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#7F1837" flood-opacity="0.10"/>
    </filter>
  </defs>
  {body}
</svg>
'''


def header_svg() -> str:
    body = f'''
  <rect x="1" y="1" width="1198" height="258" rx="24" fill="url(#paperGradient)" stroke="{COLORS['line']}"/>
  <text x="28" y="28" font-family="Arial, sans-serif" font-size="13" font-weight="700" letter-spacing="2.6" fill="{COLORS['hot']}">README.md</text>
  <line x1="130" y1="24" x2="1168" y2="24" stroke="{COLORS['line']}"/>
  <circle cx="1174" cy="24" r="13" fill="{COLORS['wine']}"/>
  <path d="M1168 20c-2-5 3-7 6-4 3-3 8-1 6 4v7c-2 3-10 3-12 0z" fill="#FFF9F7"/>

  <text x="58" y="102" font-family="Georgia, serif" font-size="54" fill="{COLORS['wine']}">Hi, I’m Adelaide Mhuntana</text>
  <text x="60" y="145" font-family="Arial, sans-serif" font-size="27" fill="{COLORS['rose']}">Software Engineer | Data &amp; Cloud</text>
  <text x="60" y="179" font-family="Arial, sans-serif" font-size="19" font-weight="600" fill="{COLORS['wine']}">@Adelaidemhuntana</text>
  <line x1="60" y1="194" x2="1158" y2="194" stroke="{COLORS['line']}"/>
  <rect x="60" y="202" width="5" height="38" fill="{COLORS['hot']}"/>
  <text x="82" y="227" font-family="Georgia, serif" font-size="17" font-style="italic" fill="{COLORS['muted']}">Building reliable data &amp; cloud solutions that turn ideas into impact.</text>

  <path d="M930 191V91a115 115 0 0 1 115-115" fill="none" stroke="{COLORS['soft']}" stroke-width="34" opacity="0.78"/>
  <path d="M1006 191v-63a73 73 0 0 1 73-73" fill="none" stroke="{COLORS['wine']}" stroke-width="30" opacity="0.96"/>
  <rect x="1090" y="44" width="70" height="145" fill="{COLORS['hot']}" opacity="0.88"/>
  <g opacity="0.55" stroke="{COLORS['line']}">
    <line x1="1090" y1="49" x2="1160" y2="49"/><line x1="1090" y1="58" x2="1160" y2="58"/>
    <line x1="1090" y1="67" x2="1160" y2="67"/><line x1="1090" y1="76" x2="1160" y2="76"/>
  </g>
'''
    return svg_document(1200, 260, body, "Adelaide Mhuntana profile header")


def pill(x: int, y: int, label: str) -> str:
    width = max(62, len(label) * 7 + 25)
    return f'''<rect x="{x}" y="{y - 19}" width="{width}" height="28" rx="7" fill="#FFF4F5" stroke="{COLORS['line']}"/>
  <text x="{x + width / 2:.1f}" y="{y}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="{COLORS['wine']}">{escape(label)}</text>'''


def pill_row(start_x: int, y: int, labels: list[str], max_x: int) -> str:
    parts = []
    x = start_x
    row_y = y
    for label in labels:
        width = max(62, len(label) * 7 + 25)
        if x + width > max_x:
            x = start_x
            row_y += 34
        parts.append(pill(x, row_y, label))
        x += width + 10
    return "\n  ".join(parts)


def about_tech_svg() -> str:
    body = f'''
  <rect x="1" y="1" width="1198" height="358" rx="20" fill="url(#paperGradient)" stroke="{COLORS['line']}"/>
  <line x1="414" y1="24" x2="414" y2="335" stroke="{COLORS['line']}"/>
  <circle cx="34" cy="39" r="17" fill="{COLORS['blush']}"/>
  <circle cx="34" cy="34" r="5" fill="none" stroke="{COLORS['rose']}" stroke-width="2"/>
  <path d="M25 48c2-8 16-8 18 0" fill="none" stroke="{COLORS['rose']}" stroke-width="2"/>
  <text x="62" y="44" font-family="Arial, sans-serif" font-size="16" font-weight="700" letter-spacing="1.8" fill="{COLORS['rose']}">ABOUT ME</text>

  <circle cx="34" cy="91" r="4" fill="{COLORS['hot']}"/>
  <text x="50" y="91" font-family="Arial, sans-serif" font-size="14" fill="{COLORS['text']}">Junior software engineer with a passion for</text>
  <text x="50" y="112" font-family="Arial, sans-serif" font-size="14" fill="{COLORS['text']}">data engineering and cloud technologies.</text>
  <circle cx="34" cy="151" r="4" fill="{COLORS['hot']}"/>
  <text x="50" y="151" font-family="Arial, sans-serif" font-size="14" fill="{COLORS['text']}">I enjoy building scalable pipelines, working with</text>
  <text x="50" y="172" font-family="Arial, sans-serif" font-size="14" fill="{COLORS['text']}">clean data and automating the boring stuff.</text>
  <circle cx="34" cy="211" r="4" fill="{COLORS['hot']}"/>
  <text x="50" y="211" font-family="Arial, sans-serif" font-size="14" fill="{COLORS['text']}">Always learning. Always building.</text>
  <text x="50" y="232" font-family="Arial, sans-serif" font-size="14" fill="{COLORS['text']}">Always improving.</text>

  <line x1="30" y1="258" x2="382" y2="258" stroke="{COLORS['line']}"/>
  <text x="32" y="286" font-family="Arial, sans-serif" font-size="15" font-weight="700" letter-spacing="1.4" fill="{COLORS['rose']}">LET’S CONNECT</text>
  <text x="32" y="312" font-family="Arial, sans-serif" font-size="13" fill="{COLORS['wine']}">GitHub  •  LinkedIn  •  Portfolio  •  South Africa</text>
  <rect x="18" y="328" width="378" height="30" fill="url(#roseGradient)"/>
  <text x="207" y="348" text-anchor="middle" font-family="Georgia, serif" font-size="14" font-style="italic" fill="#FFF9F7">Code with purpose. Build with impact.</text>

  <circle cx="449" cy="39" r="17" fill="{COLORS['blush']}"/>
  <text x="449" y="44" text-anchor="middle" font-family="monospace" font-size="14" font-weight="700" fill="{COLORS['wine']}">&lt;/&gt;</text>
  <text x="478" y="44" font-family="Arial, sans-serif" font-size="16" font-weight="700" letter-spacing="1.8" fill="{COLORS['rose']}">TECH STACK</text>

  <text x="444" y="79" font-family="Arial, sans-serif" font-size="12" font-weight="700" letter-spacing="1.4" fill="{COLORS['wine']}">LANGUAGES</text>
  {pill_row(548, 80, ['Python', 'JavaScript', 'SQL', 'Bash'], 1170)}

  <line x1="444" y1="108" x2="1168" y2="108" stroke="{COLORS['line']}"/>
  <text x="444" y="136" font-family="Arial, sans-serif" font-size="12" font-weight="700" letter-spacing="1.4" fill="{COLORS['wine']}">DATA &amp; ENGINEERING</text>
  {pill_row(608, 137, ['Pandas', 'PySpark', 'Airflow', 'dbt', 'Kafka', 'PostgreSQL', 'ETL'], 1170)}

  <line x1="444" y1="180" x2="1168" y2="180" stroke="{COLORS['line']}"/>
  <text x="444" y="208" font-family="Arial, sans-serif" font-size="12" font-weight="700" letter-spacing="1.4" fill="{COLORS['wine']}">CLOUD &amp; DEVOPS</text>
  {pill_row(574, 209, ['AWS', 'S3', 'Lambda', 'EC2', 'Docker', 'GitHub Actions', 'Terraform'], 1170)}

  <line x1="444" y1="252" x2="1168" y2="252" stroke="{COLORS['line']}"/>
  <text x="444" y="280" font-family="Arial, sans-serif" font-size="12" font-weight="700" letter-spacing="1.4" fill="{COLORS['wine']}">TOOLS</text>
  {pill_row(510, 281, ['Git', 'VS Code', 'Postman', 'Jupyter'], 1170)}
'''
    return svg_document(1200, 360, body, "About Adelaide and technology stack")


def wrap_lines(value: str, width: int = 55, max_lines: int = 3) -> list[str]:
    lines = textwrap.wrap(value or "Project details available on GitHub.", width=width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip("., ") + "…"
    return lines


def project_svg(repo: dict) -> str:
    name = repo["name"]
    fallback = PROJECT_FALLBACKS[name]
    description = repo.get("description") or fallback["description"]
    stars = repo.get("stargazerCount", 0)
    language = (repo.get("primaryLanguage") or {}).get("name") or fallback["language"]
    topic_nodes = (repo.get("repositoryTopics") or {}).get("nodes") or []
    topics = [node.get("topic", {}).get("name", "") for node in topic_nodes]
    tags = [language] + [topic for topic in topics if topic.lower() != language.lower()]
    if len(tags) < 3:
        for tag in fallback["tags"]:
            if tag.lower() not in {item.lower() for item in tags}:
                tags.append(tag)
    tags = tags[:4]
    icon = fallback["icon"]

    description_svg = []
    for index, line in enumerate(wrap_lines(description)):
        description_svg.append(
            f'<text x="132" y="{91 + index * 22}" font-family="Arial, sans-serif" font-size="14" fill="{COLORS["text"]}">{escape(line)}</text>'
        )

    tags_svg = []
    x = 132
    for tag in tags:
        width = max(58, len(tag) * 7 + 22)
        if x + width > 470:
            break
        tags_svg.append(
            f'<rect x="{x}" y="174" width="{width}" height="28" rx="7" fill="#FFF1F3" stroke="{COLORS["line"]}"/>'
        )
        tags_svg.append(
            f'<text x="{x + width / 2:.1f}" y="192" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="{COLORS["wine"]}">{escape(tag)}</text>'
        )
        x += width + 8

    icon_size = 28 if len(icon) <= 3 else 20
    body = f'''
  <rect x="1" y="1" width="568" height="228" rx="18" fill="url(#paperGradient)" stroke="{COLORS['line']}"/>
  <rect x="24" y="28" width="86" height="86" rx="14" fill="url(#roseGradient)" filter="url(#shadow)"/>
  <text x="67" y="80" text-anchor="middle" font-family="Arial, sans-serif" font-size="{icon_size}" font-weight="700" fill="#FFF9F7">{escape(icon)}</text>
  <text x="132" y="50" font-family="Arial, sans-serif" font-size="17" font-weight="700" fill="{COLORS['wine']}">{escape(name)}</text>
  {''.join(description_svg)}
  {''.join(tags_svg)}
  <text x="520" y="193" text-anchor="end" font-family="Arial, sans-serif" font-size="13" fill="{COLORS['muted']}">★ {stars}</text>
  <path d="M531 32h14v14M544 33l-16 16" fill="none" stroke="{COLORS['hot']}" stroke-width="2" stroke-linecap="round"/>
'''
    return svg_document(570, 230, body, f"{name} project card")


def contribution_color(count: int, max_count: int) -> str:
    if count <= 0:
        return "#F9E8EC"
    level = max(1, min(4, math.ceil(count / max(1, max_count) * 4)))
    return ["#F9E8EC", "#F5B9C8", "#EC7898", "#D9366B", "#8B1B3D"][level]


def stats_svg(user: dict) -> str:
    repos = user["repositories"]
    nodes = repos.get("nodes") or []
    total_repos = repos.get("totalCount", len(nodes))
    stars = sum(repo.get("stargazerCount", 0) for repo in nodes)
    followers = user.get("followers", {}).get("totalCount", 0)
    calendar = user["contributionsCollection"]["contributionCalendar"]
    contributions = calendar.get("totalContributions", 0)
    weeks = (calendar.get("weeks") or [])[-53:]
    all_counts = [
        day.get("contributionCount", 0)
        for week in weeks
        for day in week.get("contributionDays", [])
    ]
    max_count = max(all_counts or [1])

    metric_values = [contributions, total_repos, stars, followers]
    metric_labels = ["Contributions", "Public repositories", "Total stars", "Followers"]
    metrics = []
    for index, (value, label) in enumerate(zip(metric_values, metric_labels)):
        x = 32 + index * 148
        metrics.append(f'<rect x="{x}" y="76" width="132" height="132" rx="15" fill="#FFF4F5" stroke="{COLORS["line"]}"/>')
        metrics.append(f'<text x="{x + 66}" y="133" text-anchor="middle" font-family="Georgia, serif" font-size="31" fill="{COLORS["wine"]}">{value}</text>')
        metrics.append(f'<text x="{x + 66}" y="164" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="{COLORS["muted"]}">{escape(label)}</text>')

    grid = []
    grid_x = 646
    grid_y = 91
    cell = 8
    gap = 2
    month_marks = []
    seen_month = None
    for week_index, week in enumerate(weeks):
        days = week.get("contributionDays", [])
        for row, day in enumerate(days[:7]):
            count = day.get("contributionCount", 0)
            grid.append(
                f'<rect x="{grid_x + week_index * (cell + gap)}" y="{grid_y + row * (cell + gap)}" width="{cell}" height="{cell}" rx="2" fill="{contribution_color(count, max_count)}"/>'
            )
            if row == 0:
                try:
                    current_month = datetime.fromisoformat(day["date"]).strftime("%b")
                except (KeyError, ValueError):
                    current_month = ""
                if current_month and current_month != seen_month:
                    month_marks.append(
                        f'<text x="{grid_x + week_index * (cell + gap)}" y="77" font-family="Arial, sans-serif" font-size="9" fill="{COLORS["muted"]}">{current_month}</text>'
                    )
                    seen_month = current_month

    body = f'''
  <rect x="1" y="1" width="1198" height="248" rx="20" fill="url(#paperGradient)" stroke="{COLORS['line']}"/>
  <circle cx="34" cy="38" r="18" fill="{COLORS['rose']}"/>
  <path d="M25 47V37m7 10V29m7 18V34m7 13V25" stroke="#FFF9F7" stroke-width="2"/>
  <text x="64" y="44" font-family="Arial, sans-serif" font-size="17" font-weight="700" letter-spacing="1.8" fill="{COLORS['rose']}">GITHUB STATS</text>
  {''.join(metrics)}
  <text x="646" y="44" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="{COLORS['wine']}">Contribution activity</text>
  {''.join(month_marks)}
  {''.join(grid)}
  <text x="646" y="188" font-family="Arial, sans-serif" font-size="10" fill="{COLORS['muted']}">Less</text>
  <rect x="676" y="179" width="9" height="9" rx="2" fill="#F9E8EC"/>
  <rect x="689" y="179" width="9" height="9" rx="2" fill="#F5B9C8"/>
  <rect x="702" y="179" width="9" height="9" rx="2" fill="#EC7898"/>
  <rect x="715" y="179" width="9" height="9" rx="2" fill="#D9366B"/>
  <rect x="728" y="179" width="9" height="9" rx="2" fill="#8B1B3D"/>
  <text x="744" y="188" font-family="Arial, sans-serif" font-size="10" fill="{COLORS['muted']}">More</text>
  <text x="1168" y="226" text-anchor="end" font-family="Georgia, serif" font-size="13" font-style="italic" fill="{COLORS['muted']}">Updated automatically every day</text>
'''
    return svg_document(1200, 250, body, "Live GitHub statistics")


def write_assets(user: dict) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "profile-header.svg").write_text(header_svg(), encoding="utf-8")
    (ASSETS / "about-tech.svg").write_text(about_tech_svg(), encoding="utf-8")

    repo_lookup = {repo["name"]: repo for repo in user["repositories"].get("nodes", [])}
    for name in PROJECTS:
        repo = repo_lookup.get(name)
        if not repo:
            fallback = preview_data()["repositories"]["nodes"]
            repo = next(item for item in fallback if item["name"] == name)
        (ASSETS / f"project-{name}.svg").write_text(project_svg(repo), encoding="utf-8")
    (ASSETS / "github-stats.svg").write_text(stats_svg(user), encoding="utf-8")


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        print(f"Loading live public GitHub data for {USERNAME}")
        user = graphql_data(token)
    else:
        print("GITHUB_TOKEN is not set; generating preview cards")
        user = preview_data()
    write_assets(user)
    print(f"Generated profile SVGs in {ASSETS}")


if __name__ == "__main__":
    main()

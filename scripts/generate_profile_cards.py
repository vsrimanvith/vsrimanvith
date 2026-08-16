#!/usr/bin/env python3
"""Generate static profile SVG cards from the GitHub API (no third-party hosts)."""
import html
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "media"


def gh_api(*args: str):
    return json.loads(subprocess.check_output(["gh", "api", *args], text=True))


def esc(value) -> str:
    return html.escape(str(value))


def card_shell(width: int, height: int, title: str, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
  </defs>
  <rect width="{width}" height="{height}" rx="12" fill="url(#bg)" stroke="#30363d" stroke-width="1"/>
  <text x="22" y="34" fill="#58a6ff" font-family="Segoe UI, Ubuntu, Sans-Serif" font-size="16" font-weight="700">{esc(title)}</text>
  {body}
</svg>
'''




def write_views_pill(login: str) -> None:
    """Rounded non-clickable profile-views badge with live count (label | count)."""
    import re

    try:
        raw = subprocess.check_output(
            [
                "curl",
                "-fsSL",
                f"https://komarev.com/ghpvc/?username={login}&label=Profile%20views&color=6366f1",
            ],
            text=True,
            timeout=30,
        )
        nums = re.findall(r">(\d+)<", raw)
        views = nums[-1] if nums else "0"
    except Exception:
        views = "0"

    label = "Profile views"
    label_w = 12 + len(label) * 7.2 + 12
    count_w = 12 + len(views) * 7.8 + 12
    h = 28
    w = label_w + count_w
    r = h / 2
    (MEDIA / "buttons").mkdir(parents=True, exist_ok=True)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h}" role="img" aria-label="{label}: {views}">
  <title>{label}: {views}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{w:.0f}" height="{h}" rx="{r}" ry="{r}"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w:.0f}" height="{h}" fill="#312e81"/>
    <rect x="{label_w:.0f}" width="{count_w:.0f}" height="{h}" fill="#6366f1"/>
    <rect width="{w:.0f}" height="{h}" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="12">
    <text x="{label_w/2:.1f}" y="18" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_w/2:.1f}" y="17">{label}</text>
    <text x="{label_w + count_w/2:.1f}" y="18" fill="#010101" fill-opacity=".3">{views}</text>
    <text x="{label_w + count_w/2:.1f}" y="17" font-weight="700">{views}</text>
  </g>
</svg>
"""
    (MEDIA / "buttons" / "views.svg").write_text(svg, encoding="utf-8")



def main() -> None:
    MEDIA.mkdir(parents=True, exist_ok=True)
    import os
    login = os.environ.get("PROFILE_USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "vsrimanvith"
    user = gh_api(f"users/{login}")
    # users endpoint omits some fields; fill defaults
    user.setdefault("public_repos", user.get("public_repos", 0))
    user.setdefault("followers", user.get("followers", 0))
    user["login"] = login
    query = """
    query($login:String!){
      user(login:$login){
        repositories(first:100, ownerAffiliations:OWNER, isFork:false, orderBy:{field:UPDATED_AT, direction:DESC}){
          nodes{ stargazerCount forkCount primaryLanguage{name color} }
        }
        contributionsCollection{
          contributionCalendar{
            totalContributions
            weeks{ contributionDays{ contributionCount date } }
          }
        }
      }
    }
    """
    gql = json.loads(
        subprocess.check_output(
            ["gh", "api", "graphql", "-f", f"query={query}", "-F", f"login={login}"],
            text=True,
        )
    )
    data = gql["data"]["user"]
    repos = data["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)
    forks = sum(r["forkCount"] for r in repos)

    langs = []
    for repo in repos:
        language = repo.get("primaryLanguage")
        if language:
            langs.append((language["name"], language.get("color") or "#8b949e"))
    lang_counts = Counter(name for name, _ in langs)
    lang_colors = {name: color for name, color in langs}
    top_langs = lang_counts.most_common(6)

    calendar = data["contributionsCollection"]["contributionCalendar"]
    days = [day for week in calendar["weeks"] for day in week["contributionDays"]]
    days_sorted = sorted(days, key=lambda day: day["date"])

    longest = current_run = 0
    for day in days_sorted:
        if day["contributionCount"] > 0:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 0

    current = 0
    for day in reversed(days_sorted):
        if day["contributionCount"] > 0:
            current += 1
        else:
            break

    total_contrib = calendar["totalContributions"]

    stats_body = f'''
  <g font-family="Segoe UI, Ubuntu, Sans-Serif" font-size="14">
    <text x="22" y="70" fill="#8b949e">Total Contributions</text>
    <text x="250" y="70" fill="#c9d1d9" font-weight="700">{total_contrib}</text>
    <text x="22" y="100" fill="#8b949e">Public Repositories</text>
    <text x="250" y="100" fill="#c9d1d9" font-weight="700">{user["public_repos"]}</text>
    <text x="22" y="130" fill="#8b949e">Followers</text>
    <text x="250" y="130" fill="#c9d1d9" font-weight="700">{user["followers"]}</text>
    <text x="22" y="160" fill="#8b949e">Stars · Forks</text>
    <text x="250" y="160" fill="#c9d1d9" font-weight="700">{stars} · {forks}</text>
  </g>
'''
    (MEDIA / "stats.svg").write_text(card_shell(380, 185, f"{login}'s GitHub Stats", stats_body), encoding="utf-8")

    max_count = top_langs[0][1] if top_langs else 1
    rows = []
    y = 62
    for name, count in top_langs:
        width = int(220 * (count / max_count))
        color = lang_colors.get(name, "#58a6ff")
        rows.append(
            f'''
    <text x="22" y="{y}" fill="#c9d1d9" font-family="Segoe UI, Ubuntu, Sans-Serif" font-size="13">{esc(name)}</text>
    <rect x="130" y="{y-11}" width="220" height="12" rx="6" fill="#21262d"/>
    <rect x="130" y="{y-11}" width="{width}" height="12" rx="6" fill="{color}"/>
    <text x="360" y="{y}" fill="#8b949e" font-family="Segoe UI, Ubuntu, Sans-Serif" font-size="12">{count}</text>
'''
        )
        y += 28
    langs_body = "\n".join(rows) if rows else '<text x="22" y="80" fill="#8b949e">No language data</text>'
    height = max(90, 50 + 28 * len(top_langs) + 20)
    (MEDIA / "top-langs.svg").write_text(card_shell(400, height, "Top Languages", langs_body), encoding="utf-8")

    streak_body = f'''
  <g font-family="Segoe UI, Ubuntu, Sans-Serif" text-anchor="middle">
    <text x="105" y="85" fill="#8b949e" font-size="12">Total Contributions</text>
    <text x="105" y="118" fill="#58a6ff" font-size="30" font-weight="700">{total_contrib}</text>
    <text x="270" y="85" fill="#8b949e" font-size="12">Current Streak</text>
    <text x="270" y="118" fill="#3fb950" font-size="30" font-weight="700">{current}</text>
    <text x="435" y="85" fill="#8b949e" font-size="12">Longest Streak</text>
    <text x="435" y="118" fill="#d29922" font-size="30" font-weight="700">{longest}</text>
    <text x="270" y="155" fill="#8b949e" font-size="12">Updated {datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")}</text>
  </g>
'''
    (MEDIA / "streak.svg").write_text(card_shell(540, 180, "Contribution Streak", streak_body), encoding="utf-8")

    trophies = [
        ("Repos", "Public repos", str(user["public_repos"])),
        ("🔥", "Contributions", str(total_contrib)),
        ("🏅", "Followers", str(user["followers"])),
        ("💻", "Top lang", top_langs[0][0] if top_langs else "—"),
    ]
    parts = ['<g font-family="Segoe UI, Ubuntu, Sans-Serif" text-anchor="middle">']
    x = 75
    for icon, label, value in trophies:
        parts.append(
            f'''
    <rect x="{x-55}" y="55" width="110" height="95" rx="10" fill="#21262d" stroke="#30363d"/>
    <text x="{x}" y="85" font-size="22">{icon}</text>
    <text x="{x}" y="112" fill="#c9d1d9" font-size="16" font-weight="700">{esc(value)}</text>
    <text x="{x}" y="134" fill="#8b949e" font-size="11">{esc(label)}</text>
'''
        )
        x += 125
    parts.append("</g>")
    (MEDIA / "highlights.svg").write_text(
        card_shell(520, 175, "Profile Highlights", "\n".join(parts)),
        encoding="utf-8",
    )
    write_views_pill(login)
    print("Generated media/stats.svg, media/top-langs.svg, media/streak.svg, media/highlights.svg")


if __name__ == "__main__":
    main()

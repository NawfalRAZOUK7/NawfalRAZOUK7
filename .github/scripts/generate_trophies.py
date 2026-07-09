#!/usr/bin/env python3
"""Generate dynamic GitHub profile SVG assets from public profile data."""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import sys
import urllib.error
import urllib.request


USERNAME = os.environ.get("GITHUB_USERNAME", "NawfalRAZOUK7")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
TROPHY_OUTPUT = os.environ.get("TROPHY_OUTPUT", "assets/trophy.svg")
PULSE_OUTPUT = os.environ.get("PULSE_OUTPUT", "assets/profile-pulse.svg")


def github_json(path: str):
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "NawfalRAZOUK7-profile-trophy-generator",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed for {path}: {exc.code} {details}") from exc


def all_public_repos(username: str):
    repos = []
    page = 1
    while True:
        batch = github_json(
            f"/users/{username}/repos?type=owner&sort=updated&direction=desc&per_page=100&page={page}"
        )
        if not batch:
            return repos
        repos.extend(batch)
        page += 1


def repo_languages(repo: dict) -> dict[str, int]:
    owner = repo["owner"]["login"]
    name = repo["name"]
    try:
        return github_json(f"/repos/{owner}/{name}/languages")
    except RuntimeError:
        return {}


def rank(value: float, thresholds: tuple[float, float, float, float, float]) -> str:
    labels = ("SSS", "SS", "S", "A", "B")
    for label, threshold in zip(labels, thresholds):
        if value >= threshold:
            return label
    return "C"


def progress(value: float, max_value: float) -> int:
    if max_value <= 0:
        return 0
    return max(8, min(100, round((value / max_value) * 100)))


def compact_number(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(int(value))


def trophy_card(x: int, y: int, title: str, value: str, label: str, grade: str, pct: int) -> str:
    title = html.escape(title)
    value = html.escape(value)
    label = html.escape(label)
    grade = html.escape(grade)
    return f"""
  <g transform="translate({x} {y})">
    <rect width="145" height="120" rx="14" fill="#0f172a" stroke="#1d4ed8" stroke-opacity=".55"/>
    <circle cx="32" cy="34" r="18" fill="#082f49" stroke="#38bdf8" stroke-opacity=".8"/>
    <path d="M23 25h18v6c0 6-3.8 10-9 10s-9-4-9-10z" fill="#facc15"/>
    <path d="M21 27h-4c0 6 3 10 8 11" fill="none" stroke="#facc15" stroke-width="3" stroke-linecap="round"/>
    <path d="M43 27h4c0 6-3 10-8 11" fill="none" stroke="#facc15" stroke-width="3" stroke-linecap="round"/>
    <rect x="29" y="41" width="6" height="8" rx="2" fill="#facc15"/>
    <rect x="24" y="49" width="16" height="4" rx="2" fill="#facc15"/>
    <text x="128" y="34" text-anchor="end" fill="#facc15" font-size="20" font-weight="800">{grade}</text>
    <text x="18" y="66" fill="#e5e7eb" font-size="15" font-weight="700">{title}</text>
    <text x="18" y="88" fill="#38bdf8" font-size="20" font-weight="800">{value}</text>
    <text x="18" y="105" fill="#94a3b8" font-size="11">{label}</text>
    <rect x="18" y="112" width="109" height="4" rx="2" fill="#1e293b"/>
    <rect x="18" y="112" width="{pct}" height="4" rx="2" fill="#38bdf8"/>
  </g>"""


def pulse_metric(x: int, y: int, title: str, value: str, label: str, color: str) -> str:
    return f"""
  <g transform="translate({x} {y})">
    <rect width="152" height="94" rx="14" fill="#0f172a" stroke="{color}" stroke-opacity=".42"/>
    <text x="18" y="30" fill="{color}" font-size="12" font-weight="800">{html.escape(title)}</text>
    <text x="18" y="62" fill="#f8fafc" font-size="30" font-weight="900">{html.escape(value)}</text>
    <text x="18" y="80" fill="#94a3b8" font-size="11">{html.escape(label)}</text>
  </g>"""


def language_bar(y: int, name: str, pct: float, color: str) -> str:
    width = max(10, round(255 * pct / 100))
    return f"""
  <g transform="translate(398 {y})">
    <text x="0" y="13" fill="#e5e7eb" font-size="13" font-weight="700">{html.escape(name)}</text>
    <text x="300" y="13" text-anchor="end" fill="#94a3b8" font-size="12">{pct:.1f}%</text>
    <rect x="0" y="23" width="300" height="8" rx="4" fill="#1e293b"/>
    <rect x="0" y="23" width="{width}" height="8" rx="4" fill="{color}"/>
  </g>"""


def generate_trophy_svg(username: str, user: dict, repos: list[dict], now: dt.datetime) -> None:
    created = dt.datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))

    stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    forks = sum(repo.get("forks_count", 0) for repo in repos)
    languages = sorted({repo["language"] for repo in repos if repo.get("language")})
    active_since = round((now - created).days / 365.25, 1)
    recent_repos = sum(
        1
        for repo in repos
        if (now - dt.datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))).days <= 120
    )

    trophies = [
        ("Repositories", user.get("public_repos", 0), "public repos", (80, 50, 30, 15, 5), 80),
        ("Stars", stars, "total stargazers", (500, 250, 100, 25, 5), 500),
        ("Followers", user.get("followers", 0), "GitHub followers", (500, 250, 100, 50, 10), 500),
        ("Languages", len(languages), "public repo stack", (12, 10, 8, 5, 3), 12),
        ("Experience", active_since, "years on GitHub", (8, 6, 4, 2, 1), 8),
        ("Active Builds", recent_repos, "updated in 120 days", (30, 20, 12, 6, 2), 30),
        ("Fork Signal", forks, "repo forks", (100, 50, 20, 5, 1), 100),
    ]

    cards = []
    for index, (title, value, label, thresholds, max_value) in enumerate(trophies):
        x = 24 + (index % 4) * 165
        y = 82 + (index // 4) * 140
        display_value = f"{value:.1f}" if isinstance(value, float) and not value.is_integer() else str(int(value))
        cards.append(
            trophy_card(
                x,
                y,
                title,
                display_value,
                label,
                rank(value, thresholds),
                progress(value, max_value),
            )
        )

    height = 380
    generated = now.strftime("%Y-%m-%d %H:%M UTC")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="700" height="{height}" viewBox="0 0 700 {height}" role="img" aria-labelledby="title desc">
  <title id="title">GitHub trophies for {html.escape(username)}</title>
  <desc id="desc">Dynamic trophy card generated from public GitHub profile data.</desc>
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="52%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#082f49"/>
    </linearGradient>
  </defs>
  <rect width="700" height="{height}" rx="18" fill="url(#bg)"/>
  <rect x="1" y="1" width="698" height="{height - 2}" rx="17" fill="none" stroke="#38bdf8" stroke-opacity=".22"/>
  <text x="350" y="38" text-anchor="middle" fill="#e5e7eb" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="24" font-weight="800">GitHub Trophy Board</text>
  <text x="350" y="62" text-anchor="middle" fill="#94a3b8" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="13">Generated from public GitHub stats for @{html.escape(username)} - {generated}</text>
  <g font-family="Inter, Segoe UI, Arial, sans-serif">
{''.join(cards)}
  </g>
</svg>
"""
    os.makedirs(os.path.dirname(TROPHY_OUTPUT), exist_ok=True)
    with open(TROPHY_OUTPUT, "w", encoding="utf-8") as file:
        file.write(svg)


def generate_pulse_svg(username: str, user: dict, repos: list[dict], now: dt.datetime) -> None:
    language_totals: dict[str, int] = {}
    for repo in repos[:80]:
        for language, amount in repo_languages(repo).items():
            language_totals[language] = language_totals.get(language, 0) + amount

    total_language_bytes = sum(language_totals.values()) or 1
    top_languages = sorted(language_totals.items(), key=lambda item: item[1], reverse=True)[:6]
    palette = ("#38bdf8", "#22c55e", "#facc15", "#f97316", "#a78bfa", "#14b8a6")
    language_rows = [
        language_bar(132 + index * 42, language, amount / total_language_bytes * 100, palette[index % len(palette)])
        for index, (language, amount) in enumerate(top_languages)
    ]

    stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    forks = sum(repo.get("forks_count", 0) for repo in repos)
    recent_repos = sum(
        1
        for repo in repos
        if (now - dt.datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))).days <= 120
    )
    latest_repo = max(repos, key=lambda repo: repo.get("updated_at", "")) if repos else {"name": "No repos"}
    generated = now.strftime("%Y-%m-%d %H:%M UTC")

    metrics = [
        pulse_metric(34, 112, "Public Repos", compact_number(user.get("public_repos", 0)), "visible projects", "#38bdf8"),
        pulse_metric(206, 112, "Followers", compact_number(user.get("followers", 0)), "community signal", "#22c55e"),
        pulse_metric(34, 226, "Stars", compact_number(stars), "across public repos", "#facc15"),
        pulse_metric(206, 226, "Active Repos", compact_number(recent_repos), "updated in 120 days", "#f97316"),
    ]

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="760" height="430" viewBox="0 0 760 430" role="img" aria-labelledby="title desc">
  <title id="title">GitHub pulse for {html.escape(username)}</title>
  <desc id="desc">Dynamic profile pulse generated from public repositories, profile metrics, and language usage.</desc>
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="50%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#082f49"/>
    </linearGradient>
  </defs>
  <rect width="760" height="430" rx="20" fill="url(#bg)"/>
  <rect x="1" y="1" width="758" height="428" rx="19" fill="none" stroke="#38bdf8" stroke-opacity=".24"/>
  <g font-family="Inter, Segoe UI, Arial, sans-serif">
    <text x="34" y="46" fill="#e5e7eb" font-size="27" font-weight="900">GitHub Pulse</text>
    <text x="34" y="72" fill="#94a3b8" font-size="13">Generated from public GitHub data for @{html.escape(username)} - {generated}</text>
    <text x="398" y="46" fill="#e5e7eb" font-size="22" font-weight="800">Language Signal</text>
    <text x="398" y="72" fill="#94a3b8" font-size="13">Weighted by code bytes across public repositories</text>
{''.join(metrics)}
    <rect x="34" y="342" width="324" height="52" rx="14" fill="#111827" stroke="#334155"/>
    <text x="54" y="365" fill="#94a3b8" font-size="12" font-weight="700">Latest public activity</text>
    <text x="54" y="386" fill="#e5e7eb" font-size="18" font-weight="800">{html.escape(latest_repo.get("name", "No repos"))}</text>
{''.join(language_rows)}
  </g>
</svg>
"""
    os.makedirs(os.path.dirname(PULSE_OUTPUT), exist_ok=True)
    with open(PULSE_OUTPUT, "w", encoding="utf-8") as file:
        file.write(svg)


def main() -> int:
    user = github_json(f"/users/{USERNAME}")
    repos = all_public_repos(USERNAME)
    now = dt.datetime.now(dt.timezone.utc)
    generate_trophy_svg(USERNAME, user, repos, now)
    generate_pulse_svg(USERNAME, user, repos, now)
    return 0


if __name__ == "__main__":
    sys.exit(main())

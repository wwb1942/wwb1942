#!/usr/bin/env python3
"""Regenerate the featured-projects table in the profile README.

Rules:
- PINNED repos always appear first, in the order listed.
- Rejected repos are always excluded.
- Remaining public non-fork repos with a description are ranked by
  stars desc, then last-push date desc, until MAX_REPOS is reached.
Only the block between FEATURED:START / FEATURED:END markers is rewritten.
"""

import json
import re
import sys
import urllib.request

USER = "wwb1942"
MAX_REPOS = 6
PINNED = [
    "ai-roundtable",
    "codex-portable-memory",
]
EXCLUDED = {
    USER,            # the profile repo itself
    "claude-code-memory-governance",  # placeholder repo, no description
}
API_URL = f"https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed"

README = "README.md"
START = "<!-- FEATURED:START -->"
END = "<!-- FEATURED:END -->"


def fetch_repos():
    req = urllib.request.Request(API_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-readme-updater",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def clean(text, limit=110):
    text = " ".join(str(text or "").split()).replace("|", "\\|")
    if len(text) > limit:
        text = text[: limit - 1].rstrip(" ,.;:-") + "…"
    return text


def build_table(repos):
    by_name = {r["name"]: r for r in repos}
    ordered = []
    for name in PINNED:
        if name in by_name:
            ordered.append(by_name[name])
    rest = [
        r for r in repos
        if r["name"] not in {p for p in PINNED}
        and r["name"] not in EXCLUDED
        and not r.get("fork")
        and (r.get("description") or "").strip()
    ]
    rest.sort(key=lambda r: (-(r.get("stargazers_count") or 0), r.get("pushed_at") or ""))
    for r in rest:
        if len(ordered) >= MAX_REPOS:
            break
        ordered.append(r)

    lines = ["| Project | What it does | Stack |",
             "| --- | --- | --- |"]
    for r in ordered:
        name = r["name"]
        desc = clean(r["description"])
        lang = clean(r.get("language") or "—", 20)
        star = r.get("stargazers_count") or 0
        star_tag = f" · ⭐ {star}" if star > 0 else ""
        lines.append(
            f"| [**{name}**](https://github.com/{USER}/{name}) | {desc} "
            f"| {lang}{star_tag} |"
        )
    return "\n".join(lines)


def main():
    repos = fetch_repos()
    table = build_table(repos)
    with open(README, encoding="utf-8") as f:
        content = f.read()
    pattern = re.compile(
        re.escape(START) + r"\n.*?\n" + re.escape(END), re.DOTALL
    )
    new_block = f"{START}\n{table}\n{END}"
    if not pattern.search(content):
        print("MARKERS NOT FOUND in README — aborting so nothing is broken.")
        return 2
    updated = pattern.sub(new_block, content)
    if updated == content:
        print("No change.")
        return 1
    with open(README, "w", encoding="utf-8", newline="\n") as f:
        f.write(updated)
    print("README featured table updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

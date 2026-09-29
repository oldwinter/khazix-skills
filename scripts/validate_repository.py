#!/usr/bin/env python3
"""Validate repository-wide skill, link, and package contracts."""

from __future__ import annotations

import hashlib
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
    "aihot",
    "hv-analysis",
    "khazix-writer",
    "leader",
    "neat-freak",
    "storage-analyzer",
}


def validate() -> list[str]:
    errors: list[str] = []
    skill_files = sorted(ROOT.glob("*/SKILL.md"))
    found = {path.parent.name for path in skill_files}
    if found != EXPECTED_SKILLS:
        errors.append(f"skill directories differ: {sorted(found)}")

    for skill_file in skill_files:
        text = skill_file.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) != 3 or parts[0] != "":
            errors.append(f"{skill_file.relative_to(ROOT)}: malformed frontmatter")
            continue
        frontmatter = parts[1]
        name = re.search(r"(?m)^name:\s*(.+?)\s*$", frontmatter)
        description = re.search(r"(?m)^description:\s*(?:[>|]\s*)?(.*)$", frontmatter)
        if name is None or name.group(1).strip("\"'") != skill_file.parent.name:
            errors.append(f"{skill_file.relative_to(ROOT)}: name does not match directory")
        if description is None:
            errors.append(f"{skill_file.relative_to(ROOT)}: description is missing")
        if text.count("```") % 2:
            errors.append(f"{skill_file.relative_to(ROOT)}: unbalanced code fences")
        prose = re.sub(r"```.*?```", "", text, flags=re.S)
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", prose):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            relative = target.split("#", 1)[0]
            if relative and not (skill_file.parent / relative).resolve().exists():
                errors.append(f"{skill_file.relative_to(ROOT)}: broken link {target}")

    for readme in (ROOT / "README.md", ROOT / "README.en.md"):
        text = readme.read_text(encoding="utf-8")
        for skill in EXPECTED_SKILLS:
            if f"`{skill}`" not in text:
                errors.append(f"{readme.name}: missing install name {skill}")
        if "python3 -m unittest discover -s . -p 'test*.py' -v" not in text:
            errors.append(f"{readme.name}: missing canonical test command")

    manifest = ROOT / "aihot" / "manifest.sha256"
    entries = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._/-]+)", line)
        if match is None:
            errors.append("aihot/manifest.sha256: invalid line")
            continue
        expected, relative = match.groups()
        path = manifest.parent / relative
        if not path.is_file():
            errors.append(f"aihot/manifest.sha256: missing {relative}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"aihot/manifest.sha256: hash mismatch {relative}")
        entries.append(relative)
    if len(entries) != 6 or len(entries) != len(set(entries)):
        errors.append("aihot/manifest.sha256: expected six unique runtime files")

    workflow = ROOT / ".github" / "workflows" / "repository-integrity.yml"
    if not workflow.is_file():
        errors.append("repository integrity workflow is missing")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Validated 6 skills, local links, README contracts, and AIHOT manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

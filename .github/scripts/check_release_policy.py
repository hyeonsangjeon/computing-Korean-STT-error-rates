#!/usr/bin/env python3
"""Validate that package-facing pull requests carry release metadata."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib


RELEASE_FILES = {
    "LICENSE",
    "MANIFEST.in",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
}
RELEASE_PREFIXES = ("nlptutti/",)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def project_version(revision: str) -> str:
    document = tomllib.loads(git("show", f"{revision}:pyproject.toml"))
    return document["project"]["version"]


def numeric_version(version: str) -> tuple[int, ...] | None:
    parts = version.split(".")
    if not parts or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def is_release_file(path: str) -> bool:
    return path in RELEASE_FILES or path.startswith(RELEASE_PREFIXES)


def check_release_policy(base: str, head: str) -> int:
    changed_files = git("diff", "--name-only", f"{base}...{head}", "--").splitlines()
    release_changes = [path for path in changed_files if is_release_file(path)]

    if not release_changes:
        print("No package-facing files changed; no version bump is required.")
        return 0

    base_version = project_version(base)
    head_version = project_version(head)
    changelog = git("show", f"{head}:CHANGELOG.md")
    errors: list[str] = []

    if head_version == base_version:
        errors.append(
            f"pyproject.toml still uses published version {head_version}; bump it in this PR."
        )

    base_numeric = numeric_version(base_version)
    head_numeric = numeric_version(head_version)
    if base_numeric is not None and head_numeric is not None and head_numeric < base_numeric:
        errors.append(
            f"project version moved backwards from {base_version} to {head_version}."
        )

    changelog_heading = f"## [{head_version}]"
    if changelog_heading not in changelog:
        errors.append(
            f"CHANGELOG.md must include a {changelog_heading} release heading."
        )

    if errors:
        print("Package-facing files changed:", file=sys.stderr)
        for path in release_changes:
            print(f"- {path}", file=sys.stderr)
        print("\nRelease policy check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Release policy passed: {base_version} -> {head_version}; "
        f"{changelog_heading} is present."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Pull request base commit SHA")
    parser.add_argument("--head", required=True, help="Pull request head commit SHA")
    args = parser.parse_args()
    return check_release_policy(args.base, args.head)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Bump the project version in every place that references it.

`backend/app/version.py` is the canonical source of truth. This script edits
it, then keeps the other files (frontend/package.json, birdweatherviz.spec,
README.md, docs/README-desktop.md, TESTING.md) in sync. Run before tagging
a release.

Usage:
    python scripts/bump_version.py 2.2.0
    python scripts/bump_version.py 2.2.0 --history "Short description"
    python scripts/bump_version.py 2.2.0 --dry-run

Behaviour:
- Validates the new version is a strict semver (major.minor.patch[-pre]).
- Prints every file edit it makes; --dry-run shows the diff without writing.
- Skips silently when a file already shows the target version.
- Optionally prepends an entry to VERSION_HISTORY in version.py.

Exit code is non-zero if no files needed updating (useful in CI to detect
"already tagged" runs) or if the version format is invalid.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")
REPO_ROOT = Path(__file__).resolve().parent.parent


def repo(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


def read_canonical_version() -> str:
    txt = repo("backend/app/version.py").read_text()
    m = re.search(r'__version__\s*=\s*"([^"]+)"', txt)
    if not m:
        raise SystemExit("Could not find __version__ in backend/app/version.py")
    return m.group(1)


# Each entry: (path, list of (regex, replacement-template) pairs).
# Replacement template uses %s for the new version.
def edits_for(new: str) -> list[tuple[Path, list[tuple[str, str]]]]:
    return [
        (
            repo("backend/app/version.py"),
            [
                # Version line in the file's leading docstring (multiline)
                (r'(Version:\s*)([0-9.][0-9.\-A-Za-z]*)', f"\\g<1>{new}"),
                # The __version__ assignment
                (r'(__version__\s*=\s*")[^"]+(")', f"\\g<1>{new}\\g<2>"),
            ],
        ),
        (
            repo("frontend/package.json"),
            # JSON; we use a regex but only on the version key
            [(r'("version"\s*:\s*")[^"]+(")', f"\\g<1>{new}\\g<2>")],
        ),
        (
            repo("birdweatherviz.spec"),
            [(r"('CFBundleShortVersionString'\s*:\s*')[^']+(')", f"\\g<1>{new}\\g<2>")],
        ),
        (
            repo("README.md"),
            [
                (r"(\*\*Version:\*\*\s*)[0-9.\-A-Za-z]+", f"\\g<1>{new}"),
                (r"(/releases/download/v)[0-9.\-A-Za-z]+(/)", f"\\g<1>{new}\\g<2>"),
            ],
        ),
        (
            repo("TESTING.md"),
            [(r"(\*\*Version:\*\*\s*)[0-9.\-A-Za-z]+", f"\\g<1>{new}")],
        ),
    ]


def apply_edits(path: Path, patterns: list[tuple[str, str]], dry_run: bool) -> int:
    if not path.exists():
        print(f"  [skip] {path.relative_to(REPO_ROOT)} (not found)")
        return 0
    text = path.read_text()
    new_text = text
    total = 0
    for pat, repl in patterns:
        new_text, n = re.subn(pat, repl, new_text)
        total += n
    if total == 0:
        print(f"  [skip] {path.relative_to(REPO_ROOT)} (no matches — already in sync?)")
        return 0
    if new_text == text:
        return 0
    print(f"  [edit] {path.relative_to(REPO_ROOT)} ({total} replacement{'s' if total != 1 else ''})")
    if not dry_run:
        path.write_text(new_text)
    return 1


def add_history_entry(new: str, note: str, dry_run: bool) -> int:
    """Prepend a VERSION_HISTORY entry inside backend/app/version.py."""
    path = repo("backend/app/version.py")
    text = path.read_text()
    if f'"{new}":' in text:
        print(f"  [skip] VERSION_HISTORY already has an entry for {new}")
        return 0
    today = date.today().isoformat()
    entry = f'    "{new}": "{note}",  # {today}\n'
    new_text, n = re.subn(
        r"(VERSION_HISTORY\s*=\s*\{\n)",
        f"\\g<1>{entry}",
        text,
        count=1,
    )
    if n == 0:
        print("  [warn] could not locate VERSION_HISTORY in version.py — skipping history entry")
        return 0
    print(f"  [edit] backend/app/version.py — added VERSION_HISTORY entry for {new}")
    if not dry_run:
        path.write_text(new_text)
    return 1


def validate_package_json() -> None:
    """Make sure package.json still parses after the edit."""
    path = repo("frontend/package.json")
    if path.exists():
        json.loads(path.read_text())  # raises if broken


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("version", help="Target version (e.g. 2.2.0)")
    p.add_argument(
        "--history",
        help="One-line description of this release. Adds a VERSION_HISTORY entry to version.py.",
    )
    p.add_argument("--dry-run", action="store_true", help="Show changes without writing.")
    args = p.parse_args()

    if not SEMVER_RE.match(args.version):
        print(f"error: not a valid semver: {args.version!r}", file=sys.stderr)
        return 2

    current = read_canonical_version()
    print(f"Current canonical version: {current}")
    print(f"Target version:            {args.version}")
    if current == args.version and not args.history:
        print("\nNothing to do.")
        return 1

    print()
    changed = 0
    for path, patterns in edits_for(args.version):
        changed += apply_edits(path, patterns, args.dry_run)

    if args.history:
        changed += add_history_entry(args.version, args.history, args.dry_run)

    if not args.dry_run and changed > 0:
        try:
            validate_package_json()
        except json.JSONDecodeError as e:
            print(f"\nerror: frontend/package.json is no longer valid JSON: {e}", file=sys.stderr)
            return 3

    print()
    if args.dry_run:
        print(f"Dry run: {changed} file(s) would be modified.")
    else:
        print(f"Modified {changed} file(s).")
        print("Next steps:")
        print(f"  git diff")
        print(f"  git commit -am 'chore: Bump version to {args.version}'")
        print(f"  git tag v{args.version} && git push --tags")
    return 0 if changed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())

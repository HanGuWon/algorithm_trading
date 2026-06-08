from __future__ import annotations

import argparse
from pathlib import Path
import subprocess


BIDI_CODEPOINTS = {
    0x202A,
    0x202B,
    0x202C,
    0x202D,
    0x202E,
    0x2066,
    0x2067,
    0x2068,
    0x2069,
}

INVISIBLE_CODEPOINTS = {
    0x200B,
    0x200C,
    0x200D,
    0xFEFF,
}

DEFAULT_TEXT_SUFFIXES = {
    "",
    ".csv",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-freqtrade",
    "__pycache__",
}

DEFAULT_EXCLUDED_PATHS = {
    "user_data/backtest_results",
    "user_data/data",
    "user_data/hyperopt_results",
}

NAME_ONLY_TEXT_FILES = {
    ".gitattributes",
    ".gitignore",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan text files for hidden or bidirectional Unicode characters.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--suffix", action="append", dest="suffixes", help="Text suffix to scan, repeatable.")
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help="Scan only files tracked by Git from the selected root.",
    )
    parser.add_argument(
        "--check-newlines",
        action="store_true",
        help="Also fail on bare CR line endings in scanned text files.",
    )
    return parser.parse_args()


def is_excluded(path: Path, root: Path) -> bool:
    relative = path.relative_to(root).as_posix()
    if any(part in DEFAULT_EXCLUDED_DIRS for part in path.parts):
        return True
    return any(relative == excluded or relative.startswith(f"{excluded}/") for excluded in DEFAULT_EXCLUDED_PATHS)


def is_text_candidate(path: Path, suffixes: set[str]) -> bool:
    if path.name in NAME_ONLY_TEXT_FILES:
        return True
    return path.suffix.lower() in suffixes


def iter_tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [root / line for line in result.stdout.splitlines() if line.strip()]


def iter_text_files(root: Path, suffixes: set[str], tracked_only: bool) -> list[Path]:
    files: list[Path] = []
    candidates = iter_tracked_files(root) if tracked_only else root.rglob("*")
    for path in candidates:
        if is_excluded(path, root):
            continue
        if path.is_file() and is_text_candidate(path, suffixes):
            files.append(path)
    return files


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    suffixes = {suffix.lower() for suffix in args.suffixes} if args.suffixes else DEFAULT_TEXT_SUFFIXES

    bad_unicode: list[tuple[str, int, str]] = []
    bad_newlines: list[tuple[str, int, int, int]] = []
    for path in iter_text_files(root, suffixes, args.tracked_only):
        data = path.read_bytes()
        if args.check_newlines:
            cr = data.count(b"\r")
            crlf = data.count(b"\r\n")
            bare_cr = cr - crlf
            if bare_cr:
                bad_newlines.append((path.as_posix(), data.count(b"\n"), cr, bare_cr))

        text = data.decode("utf-8", errors="ignore")
        for index, char in enumerate(text):
            codepoint = ord(char)
            if codepoint in BIDI_CODEPOINTS or codepoint in INVISIBLE_CODEPOINTS:
                bad_unicode.append((path.as_posix(), index, f"U+{ord(char):04X}"))

    if bad_unicode:
        for path, index, codepoint in bad_unicode:
            print(f"{path}:{index}: hidden unicode {codepoint}")

    if bad_newlines:
        for path, lf, cr, bare_cr in bad_newlines:
            print(f"{path}: LF={lf} CR={cr} bare_CR={bare_cr}")

    if bad_unicode or bad_newlines:
        raise SystemExit(1)

    print("No hidden/bidirectional Unicode characters found.")
    if args.check_newlines:
        print("No bare CR line endings found.")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from pathlib import Path


BIDI_CODEPOINTS = {
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
}

INVISIBLE_CODEPOINTS = {
    "\u200b",
    "\u200c",
    "\u200d",
    "\ufeff",
}

DEFAULT_TEXT_SUFFIXES = {
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
    "__pycache__",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan text files for hidden or bidirectional Unicode characters.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--suffix", action="append", dest="suffixes", help="Text suffix to scan, repeatable.")
    return parser.parse_args()


def iter_text_files(root: Path, suffixes: set[str]) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in DEFAULT_EXCLUDED_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in suffixes:
            files.append(path)
    return files


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    suffixes = {suffix.lower() for suffix in args.suffixes} if args.suffixes else DEFAULT_TEXT_SUFFIXES

    bad: list[tuple[str, int, str]] = []
    for path in iter_text_files(root, suffixes):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for index, char in enumerate(text):
            if char in BIDI_CODEPOINTS or char in INVISIBLE_CODEPOINTS:
                bad.append((path.as_posix(), index, f"U+{ord(char):04X}"))

    if bad:
        for path, index, codepoint in bad:
            print(f"{path}:{index}: hidden unicode {codepoint}")
        raise SystemExit(1)

    print("No hidden/bidirectional Unicode characters found.")


if __name__ == "__main__":
    main()

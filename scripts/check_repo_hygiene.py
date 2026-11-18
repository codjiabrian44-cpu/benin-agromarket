"""Repository hygiene gate for public release.

Fails with exit code 1 if any tracked text file contains:
- Absolute local filesystem paths (e.g., `/home/` or `file:///`)
- Secret or token-like patterns (GitHub PATs, OpenAI/AWS/Slack keys, private keys)
- Tracked `.env` files
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".pdf",
    ".joblib",
    ".zip",
}

FORBIDDEN_PATH_PATTERNS = [
    ("local_home_path", re.compile("/ho" + "me/")),
    ("file_uri_scheme", re.compile("file:" + "///")),
]

TOKEN_PATTERNS = [
    ("github_classic_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("github_fine_grained_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("openai_like_sk_token", re.compile(r"\bsk-(?:proj-|live-|test-)?[A-Za-z0-9]{24,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
]


def get_tracked_files() -> list[pathlib.Path]:
    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO_ROOT)
    paths: list[pathlib.Path] = []
    for raw in out.split(b"\x00"):
        if not raw:
            continue
        rel = raw.decode("utf-8", errors="replace")
        p = REPO_ROOT / rel
        if p.is_file():
            paths.append(p)
    return paths


def main() -> int:
    tracked = get_tracked_files()
    violations: list[str] = []

    for p in tracked:
        rel = p.relative_to(REPO_ROOT).as_posix()
        if p.name == ".env" or p.name.startswith(".env."):
            violations.append(f"{rel}: tracked env file")
            continue
        if p.suffix.lower() in BINARY_EXTENSIONS:
            continue
        raw_bytes = p.read_bytes()
        if b"\x00" in raw_bytes:
            continue

        text = raw_bytes.decode("utf-8", errors="replace")
        is_self = rel == "scripts/check_repo_hygiene.py"

        for lineno, line in enumerate(text.splitlines(), start=1):
            if not is_self:
                for name, pat in FORBIDDEN_PATH_PATTERNS:
                    if pat.search(line):
                        violations.append(f"{rel}:{lineno}: {name}: {line.strip()[:120]}")
            for name, pat in TOKEN_PATTERNS:
                if is_self:
                    continue
                if pat.search(line):
                    violations.append(f"{rel}:{lineno}: {name}: matched secret-like pattern")

    if violations:
        print(f"[Repo Hygiene] FAIL: {len(violations)} issue(s) found:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print(f"[Repo Hygiene] PASS: Checked {len(tracked)} tracked files (no /home/, file:///, or tokens).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

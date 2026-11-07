"""Create a checksummed research-data snapshot without local credentials/caches.

The ZIP preserves repository-relative paths. It is intended as a GitHub release
asset because individual raw answer files exceed GitHub's normal Git file limit.
No network calls or changes to the source artifacts are made.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


SECRET = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
    rb"|\b(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{30,}"
    rb"|sk-(?:proj-|ant-)?[A-Za-z0-9_-]{25,}|hf_[A-Za-z0-9]{25,}"
    rb"|gsk_[A-Za-z0-9]{25,}|AKIA[A-Z0-9]{16})\b"
)
ASSIGNMENT = re.compile(
    rb'''(?i)["'](?:api_key|access_token|auth_token|password|secret_key)["']'''
    rb'''\s*:\s*["']([^\s"']{12,})["']'''
)


def exclusion(path: Path) -> str | None:
    parts = [part.lower() for part in path.parts]
    if any(part in {"auth", "credentials", "__pycache__", ".venv"}
           or "pytest" in part for part in parts):
        return "credentials or runtime/test cache"
    if path.name.lower() in {
        ".env", "kaggle.json", "id_rsa", "id_ed25519", "authorize-key.txt",
        "local-inventory.json", "remote-inventory.json",
    }:
        return "local credentials or machine-access metadata"
    if path.suffix.lower() in {".log", ".err", ".pyc", ".pem", ".key"}:
        return "runtime log, bytecode, or key material"
    return None


def sensitive(data: bytes, depth: int = 0) -> bool:
    if SECRET.search(data):
        return True
    for match in ASSIGNMENT.finditer(data):
        value = match[1].lower()
        if not any(word in value for word in (b"example", b"placeholder", b"your_", b"os.environ")):
            return True
    if data.startswith(b"PK\x03\x04"):
        if depth >= 3:
            return True
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                if exclusion(Path(member.filename)) or member.file_size > 512 * 1024 * 1024:
                    return True
                if sensitive(archive.read(member), depth + 1):
                    return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    output = args.output.resolve()
    if output.exists() or output.with_suffix(".manifest.json").exists():
        raise SystemExit("Output already exists; choose a new snapshot path.")
    sources = [root / "backend/data/bench", root / "backend/data/router_track"]
    if any(output.is_relative_to(source) for source in sources):
        raise SystemExit("Write the snapshot outside its input directories.")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "scope": [source.relative_to(root).as_posix() for source in sources],
        "files": [],
        "excluded": [],
        "note": "Raw research snapshot, not a new evaluation. Original dataset licenses remain applicable.",
    }
    temporary = output.with_suffix(".zip.partial")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for source in sources:
            for path in sorted(source.rglob("*")):
                if not path.is_file():
                    continue
                relative = path.relative_to(root)
                reason = "symlink" if path.is_symlink() else exclusion(relative)
                if reason:
                    manifest["excluded"].append({"path": relative.as_posix(), "reason": reason})
                    continue
                data = path.read_bytes()
                if sensitive(data):
                    manifest["excluded"].append({"path": relative.as_posix(), "reason": "credential-pattern or nested local files"})
                    continue
                manifest["files"].append({"path": relative.as_posix(), "bytes": len(data),
                                          "sha256": hashlib.sha256(data).hexdigest()})
                archive.writestr(relative.as_posix(), data)
        archive.writestr("EVIDENCE_MANIFEST.json", json.dumps(manifest, indent=2).encode())
    with zipfile.ZipFile(temporary) as archive:
        for entry in manifest["files"]:
            with archive.open(entry["path"]) as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != entry["sha256"]:
                raise RuntimeError(f"Archive verification failed: {entry['path']}")
    temporary.rename(output)
    with output.open("rb") as stream:
        archive_sha = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest["archive"] = {"name": output.name, "bytes": output.stat().st_size, "sha256": archive_sha}
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(manifest["files"]), "excluded": len(manifest["excluded"]),
                      "archive": manifest["archive"]}))


if __name__ == "__main__":
    main()

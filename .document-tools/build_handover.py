"""Create and verify a portable source archive, never upload or share it."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "deliverables/projectmindx-a01-b01.zip"
BLOCKED_PARTS = {".venv", "venv", "__pycache__", ".pytest_cache", "private_media", "private_exports"}


def sources():
    for name in ("README.md", "AGENTS.md", ".gitignore"):
        yield ROOT / name
    for name in ("verify_foundation.py", "build_handover.py"):
        yield ROOT / ".document-tools" / name
    for directory in ("backend", "docs"):
        for path in sorted((ROOT / directory).rglob("*")):
            if not path.is_file() or BLOCKED_PARTS.intersection(path.relative_to(ROOT).parts):
                continue
            if path.name == ".env" or path.suffix in {".sqlite3", ".pyc", ".zip"} or path.name.startswith("~$"):
                continue
            yield path


def main():
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in sources():
            archive.write(source, Path("projectmindx") / source.relative_to(ROOT))
    with tempfile.TemporaryDirectory(prefix="mindx-handover-") as scratch:
        with zipfile.ZipFile(ARCHIVE) as archive:
            if archive.testzip() is not None:
                raise RuntimeError("ZIP integrity check failed")
            names = archive.namelist()
            if any(BLOCKED_PARTS.intersection(Path(name).parts) or Path(name).name == ".env"
                   or Path(name).suffix == ".sqlite3" for name in names):
                raise RuntimeError("Archive contains excluded local data")
            archive.extractall(scratch)
        extracted = Path(scratch) / "projectmindx/backend"
        env = os.environ.copy()
        env["DJANGO_SECRET_KEY"] = secrets.token_urlsafe(48)
        env["DJANGO_DEBUG"] = "false"
        env["DJANGO_DB_PATH"] = str(Path(scratch) / "handover.sqlite3")
        outputs = ["ZIP CRC and excluded-data checks: PASS"]
        for arguments in (["check"], ["migrate", "--noinput"], ["makemigrations", "--check", "--dry-run"], ["test"]):
            result = subprocess.run([sys.executable, "manage.py", *arguments], cwd=extracted,
                                    env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
            outputs.extend(["$ python manage.py " + " ".join(arguments), result.stdout,
                            result.stderr, f"exit_code={result.returncode}"])
            if result.returncode:
                print(result.stdout + result.stderr)
                raise RuntimeError("Extracted baseline failed verification")
        (ROOT / "docs/project-management/evidence/a01-b01-handover.txt").write_text(
            "\n".join(outputs), encoding="utf-8")
    print(f"Verified source ZIP: {ARCHIVE} ({len(names)} files, {ARCHIVE.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

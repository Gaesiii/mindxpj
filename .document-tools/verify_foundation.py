"""Verify A01 on a temporary empty DB and record actual command output."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
EVIDENCE = ROOT / "docs/project-management/evidence"


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["DJANGO_SECRET_KEY"] = secrets.token_urlsafe(48)
    env["DJANGO_DEBUG"] = "false"
    output = [f"Python: {sys.version.split()[0]}", "DB: temporary empty SQLite; secret not recorded"]
    with tempfile.TemporaryDirectory(prefix="mindx-foundation-") as scratch:
        env["DJANGO_DB_PATH"] = str(Path(scratch) / "empty.sqlite3")
        commands = [
            ["manage.py", "check"],
            ["manage.py", "migrate", "--noinput"],
            ["manage.py", "makemigrations", "--check", "--dry-run"],
            ["manage.py", "test", "-v", "2"],
            ["-m", "pip", "check"],
        ]
        for arguments in commands:
            result = subprocess.run([sys.executable, *arguments], cwd=BACKEND, env=env,
                                    capture_output=True, text=True, encoding="utf-8", errors="replace")
            output.extend(["", "$ python " + " ".join(arguments), result.stdout, result.stderr,
                           f"exit_code={result.returncode}"])
            if result.returncode:
                (EVIDENCE / "a01-b01-validation.txt").write_text("\n".join(output), encoding="utf-8")
                print("FAILED: " + " ".join(arguments))
                print(result.stdout + result.stderr)
                return result.returncode
            print("PASS: " + " ".join(arguments))
    (EVIDENCE / "a01-b01-validation.txt").write_text("\n".join(output), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    temp_dir = Path(tempfile.mkdtemp(prefix="provenance-guard-pytest-"))
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--basetemp",
        str(temp_dir),
        *sys.argv[1:],
    ]

    print(f"Using pytest base temp directory: {temp_dir}")
    try:
        completed = subprocess.run(command, cwd=repo_root)
        return completed.returncode
    finally:
        try:
            shutil.rmtree(temp_dir)
        except OSError as exc:
            print(
                f"Warning: could not remove pytest temp directory {temp_dir}: {exc}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    raise SystemExit(main())

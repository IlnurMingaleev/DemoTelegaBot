"""
afterFileEdit hook — runs ruff check+format on edited Python files.
Reads JSON from stdin, outputs JSON to stdout.
"""
import json
import subprocess
import sys


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    file_path: str = ""
    for key in ("path", "file_path", "filePath", "file"):
        if key in data:
            file_path = str(data[key])
            break

    if not file_path or not file_path.endswith(".py"):
        print(json.dumps({"additional_context": ""}))
        return

    # Check ruff is available
    try:
        subprocess.run(
            ["ruff", "--version"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(json.dumps({"additional_context": "ruff not installed — run: pip install ruff"}))
        return

    # ruff check --fix
    check_result = subprocess.run(
        ["ruff", "check", "--fix", file_path],
        capture_output=True,
        text=True,
    )

    # ruff format
    subprocess.run(
        ["ruff", "format", file_path],
        capture_output=True,
    )

    if check_result.returncode == 0:
        print(json.dumps({"additional_context": ""}))
    else:
        issues = check_result.stdout.strip() or check_result.stderr.strip()
        print(json.dumps({"additional_context": f"ruff issues in {file_path}: {issues}"}))


if __name__ == "__main__":
    main()

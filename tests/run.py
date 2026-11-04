"""Compare logs, allowing reordering within each expected timestamp."""

from difflib import unified_diff
from pathlib import Path
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def message_groups(path):
    groups = []
    previous_timestamp = None
    for line in path.read_text().splitlines():
        match = re.match(r"^\s*(\d+\.\d+):", line)
        timestamp = match.group(1) if match else None
        line = re.sub(r"^\s*\d+\.\d+:\s*", "", line).strip()
        if line.startswith("mytime started at "):
            line = "mytime started"
        line = re.sub(r"%5[Bb]::1%5[Dd]|\[::1\]|127\.0\.0\.1|(?<!\w)::1", "localhost", line)
        if not groups or timestamp is None or timestamp != previous_timestamp:
            groups.append([])
        groups[-1].append(line + "\n")
        previous_timestamp = timestamp
    return groups


def compare_messages(expected, actual):
    expected_lines = []
    actual_lines = [line for group in message_groups(actual) for line in group]
    offset = 0
    # Actual timestamps may drift. Use only the example's timestamps to group
    # concurrent messages, keeping the order between different groups.
    for group in message_groups(expected):
        expected_lines.extend(sorted(group))
        end = offset + len(group)
        actual_lines[offset:end] = sorted(actual_lines[offset:end])
        offset = end
    return list(unified_diff(expected_lines, actual_lines,
                             fromfile=str(expected), tofile="actual/" + actual.name))


def run_case(case):
    print("Running {}...".format(case.name), flush=True)
    passed = True
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        for source in (ROOT / "src").glob("*.py"):
            (work / source.name).symlink_to(source)
        # Preserve the runner's virtual environment when command.sh uses python3.
        launcher = work / "python3"
        launcher.write_text('#!/bin/sh\nexec {} "$@"\n'.format(shlex.quote(sys.executable)))
        launcher.chmod(0o755)
        env = dict(os.environ, PATH=str(work) + os.pathsep + os.environ["PATH"])
        script = 'set -e\nsource {}\nfor pid in $(jobs -p); do wait "$pid"; done'.format(
            shlex.quote(str(case / "command.sh"))
        )
        process = subprocess.Popen(["bash", "-c", script], cwd=work, env=env, start_new_session=True)
        try:
            passed = process.wait(timeout=20) == 0
        except subprocess.TimeoutExpired:
            print("Timed out after 20 seconds")
            passed = False
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        for expected in sorted(case.glob("*.out")):
            actual = work / expected.name
            if not actual.exists():
                print("Missing output: " + expected.name)
                passed = False
                continue
            diff = compare_messages(expected, actual)
            if diff:
                print("".join(diff), end="")
                passed = False
        print("PASS" if passed else "FAIL")
    return passed


if __name__ == "__main__":
    subprocess.run([
        sys.executable, "-m", "grpc_tools.protoc", "-I.",
        "--python_out=.", "--grpc_python_out=.",
        "ambulatorio.proto", "consultorio.proto",
    ], cwd=ROOT / "src", check=True)
    cases = [ROOT / "tests" / name for name in sys.argv[1:]] if sys.argv[1:] else sorted((ROOT / "tests").glob("caso*"))
    results = [run_case(case) for case in cases]
    sys.exit(0 if results and all(results) else 1)

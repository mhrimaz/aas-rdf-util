from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"


def require_command(command: str) -> None:
    if shutil.which(command) is None:
        raise RuntimeError(f"Required command not found on PATH: {command}")


def install_dependencies() -> None:
    subprocess.run(["uv", "sync"], cwd=ROOT, check=True)
    subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)


def stream_output(prefix: str, process: subprocess.Popen[str]) -> threading.Thread:
    def _reader() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            print(f"[{prefix}] {line}", end="")

    thread = threading.Thread(target=_reader, daemon=True)
    thread.start()
    return thread


def terminate_processes(processes: list[subprocess.Popen[str]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()


def run() -> int:
    parser = argparse.ArgumentParser(description="Run backend and frontend locally with one command.")
    parser.add_argument("--skip-install", action="store_true", help="Skip 'uv sync' and 'npm install'.")
    args = parser.parse_args()

    require_command("uv")
    require_command("npm")

    if not args.skip_install:
        install_dependencies()

    backend = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    frontend = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    processes = [backend, frontend]
    stream_output("backend", backend)
    stream_output("frontend", frontend)

    print("Local stack is starting...")
    print("UI:  http://localhost:5173")
    print("API: http://localhost:8000")
    print("Press Ctrl+C to stop both services.")

    try:
        while True:
            backend_code = backend.poll()
            frontend_code = frontend.poll()

            if backend_code is not None:
                print(f"Backend exited with code {backend_code}")
                terminate_processes(processes)
                return backend_code

            if frontend_code is not None:
                print(f"Frontend exited with code {frontend_code}")
                terminate_processes(processes)
                return frontend_code

            threading.Event().wait(0.5)
    except KeyboardInterrupt:
        print("Stopping services...")
        terminate_processes(processes)
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

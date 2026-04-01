"""
Pose Art Generator - unified startup script.
Launches backend (FastAPI) and frontend (Vite) dev servers.

Usage:
    python start.py
    uv run start.py
"""

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
LOG_DIR = PROJECT_ROOT / "logs"

BACKEND_URL = "http://localhost:8888"
FRONTEND_URL = "http://localhost:5173"

processes: list[subprocess.Popen] = []


def check_uv_available() -> bool:
    return shutil.which("uv") is not None


def check_node_available() -> bool:
    return shutil.which("node") is not None


def check_npm_deps() -> bool:
    return (FRONTEND_DIR / "node_modules").is_dir()


def preflight_check() -> bool:
    """Check all prerequisites before starting servers."""
    errors = []

    if not check_uv_available():
        errors.append("uv is not installed. Install it from https://docs.astral.sh/uv/")

    if not check_node_available():
        errors.append("Node.js is not installed. Install it from https://nodejs.org/")

    if not check_npm_deps():
        errors.append(
            "Frontend dependencies not installed. "
            f"Run: cd {FRONTEND_DIR} && npm install"
        )

    env_file = PROJECT_ROOT / ".env"
    if not env_file.is_file():
        errors.append(
            f".env file not found at {env_file}. "
            "Copy .env.example to .env and fill in your API keys."
        )

    if errors:
        print("\n" + "=" * 50)
        print("  Pre-flight check failed:")
        print("=" * 50)
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        print("=" * 50)
        print()
        return False

    return True


def print_banner():
    banner = r"""
  ____  _       _     ____        __
 |  _ \| | ___ | |__ |  _ \  ___ / _|
 | |_) | |/ _ \| '_ \| | | |/ _ \ |_
 |  __/| | (_) | |_) | |_| |  __/  _|
 |_|   |_|\___/|_.__/|____/ \___|_|

  Pose Art Generator - one-click start
"""
    print(banner)


def start_backend() -> subprocess.Popen:
    """Start backend FastAPI server via uv run, tee output to console + log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "backend.log"

    print(f"[Backend] Starting FastAPI server...")
    print(f"[Backend] Dir: {BACKEND_DIR}")
    print(f"[Backend] Log: {log_file}")
    env = os.environ.copy()

    with open(log_file, "w", encoding="utf-8") as lf:
        proc = subprocess.Popen(
            ["uv", "run", "python", "run.py"],
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=lf,
            stderr=subprocess.STDOUT,
        )
    return proc


def start_frontend() -> subprocess.Popen:
    """Start frontend Vite dev server, tee output to console + log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "frontend.log"

    print(f"[Frontend] Starting Vite dev server...")
    print(f"[Frontend] Dir: {FRONTEND_DIR}")
    print(f"[Frontend] Log: {log_file}")

    with open(log_file, "w", encoding="utf-8") as lf:
        proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(FRONTEND_DIR),
            shell=True,
            stdout=lf,
            stderr=subprocess.STDOUT,
        )
    return proc


def cleanup():
    """Terminate all child processes."""
    print("\nShutting down all services ...")
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    print("All services stopped.")


def signal_handler(signum, frame):
    cleanup()
    sys.exit(0)


def main():
    print_banner()

    if not preflight_check():
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)

    # Start backend
    backend_proc = start_backend()
    processes.append(backend_proc)

    # Start frontend
    frontend_proc = start_frontend()
    processes.append(frontend_proc)

    print()
    print("=" * 50)
    print(f"  Backend API:  {BACKEND_URL}")
    print(f"  Frontend UI:  {FRONTEND_URL}")
    print(f"  API Docs:     {BACKEND_URL}/docs")
    print("-" * 50)
    print(f"  Backend log:  {LOG_DIR / 'backend.log'}")
    print(f"  Frontend log: {LOG_DIR / 'frontend.log'}")
    print("=" * 50)
    print()
    print("Press Ctrl+C to stop all services ...")
    print()

    # Wait for any child process to exit
    while True:
        for proc in processes:
            return_code = proc.poll()
            if return_code is not None:
                print(f"Process {proc.args} exited with code: {return_code}")
                cleanup()
                sys.exit(return_code)
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            continue


if __name__ == "__main__":
    main()

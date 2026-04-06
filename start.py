"""
SlangToon - unified startup script.
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

if sys.platform == "win32":
    import ctypes

# 在启动任何子进程之前，将 .env 加载到 os.environ。
# 确保 LANGSMITH_TRACING / LANGSMITH_API_KEY / LANGSMITH_PROJECT
# 在 uvicorn 子工作进程中可见（@traceable 装饰器从 os.environ 读取）。
from dotenv import load_dotenv
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file, override=False)

PROJECT_ROOT = Path(__file__).parent.resolve()
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
LOG_DIR = PROJECT_ROOT / "logs"

BACKEND_URL = "http://localhost:8889"
FRONTEND_URL = "http://localhost:5174"

processes: list[subprocess.Popen] = []

BACKEND_PORT = 8889
FRONTEND_PORT = 5174


def kill_process_tree(pid: int) -> bool:
    """Kill a process and its entire process tree (Windows only)."""
    if sys.platform == "win32":
        # Use taskkill /T to kill the process tree, /F for force
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    else:
        try:
            os.killpg(pid, signal.SIGKILL)
            return True
        except (ProcessLookupError, PermissionError):
            return False


def find_pids_on_port(port: int) -> list[int]:
    """Find all PIDs listening on the given port."""
    pids = []
    if sys.platform == "win32":
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0] == "TCP" and "LISTENING" in line:
                # Local address format: 0.0.0.0:PORT or [::]:PORT
                local_addr = parts[1]
                if local_addr.endswith(f":{port}"):
                    pids.append(int(parts[4]))
    else:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.strip().splitlines():
            if line.strip().isdigit():
                pids.append(int(line.strip()))
    return list(set(pids))


def cleanup_ports():
    """Check and kill any processes occupying backend/frontend ports."""
    ports_to_check = [
        (BACKEND_PORT, "Backend"),
        (FRONTEND_PORT, "Frontend"),
    ]
    killed_any = False
    for port, label in ports_to_check:
        pids = find_pids_on_port(port)
        if pids:
            print(f"[{label}] Port {port} is occupied by PID(s): {pids}")
            for pid in pids:
                if kill_process_tree(pid):
                    print(f"[{label}]   Killed PID {pid}")
                else:
                    print(f"[{label}]   Failed to kill PID {pid}")
            killed_any = True

    if killed_any:
        # Brief wait for ports to be fully released
        import time
        time.sleep(1)
        print()


def check_uv_available() -> bool:
    return shutil.which("uv") is not None


# Env vars that must be present for the app to work correctly.
_REQUIRED_ENV_KEYS = [
    ("LANGSMITH_TRACING", False),
    ("LANGSMITH_API_KEY", False),
    ("LANGSMITH_PROJECT", False),
]


def _mask(value: str, visible: int = 6) -> str:
    """Show first `visible` chars, mask the rest."""
    if len(value) <= visible:
        return value
    return value[:visible] + "*" * (len(value) - visible)


def _verify_env():
    """Print .env loading status; exit on missing required keys."""
    print("[Env] Verifying .env loaded from:", _env_file)
    if not _env_file.exists():
        print("[Env] WARNING: .env file not found!")
        return

    missing_required = []
    for key, required in _REQUIRED_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            print(f"[Env]   {key} = {_mask(value)}")
        else:
            tag = " (REQUIRED)" if required else " (optional)"
            print(f"[Env]   {key} = <not set>{tag}")
            if required:
                missing_required.append(key)

    if missing_required:
        print(f"\n[Env] ERROR: Missing required env vars: {', '.join(missing_required)}")
        print("[Env] Please check your .env file.")
        sys.exit(1)
    print()


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
  _____ _       _   _       __  __
 |_   _| |     | \ | | ___ |  \/  |
   | | | | __ _|  \| |/ _ \| |\/| |
   | | | |/ _` | |\  |  __/| |  | |
   |_| |_|\__, |_| \_|\___||_|  |_|
          |___/

   SlangToon - AI Slang-to-Comic Generator
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
            if sys.platform == "win32":
                # taskkill /T kills the whole process tree (handles shell=True)
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    capture_output=True,
                )
            else:
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

    # Kill any lingering processes on our ports
    cleanup_ports()

    # Verify .env was loaded correctly
    _verify_env()

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

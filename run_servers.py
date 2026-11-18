"""
ARVANA Multi-Server Runner
Runs the full stack locally across separate ports:
  - Port 8000: FastAPI Backend API & Webhooks
  - Port 3000: Client CRM Dashboard (crm-design-preview/)
  - Port 3001: Standalone Agency Admin Portal (agency-admin/)
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable

def start_servers(open_browser: bool = True):
    print("=" * 60)
    print("🚀 STARTING ARVANA LOCAL MULTI-PORT ENVIRONMENT")
    print("=" * 60)
    print("  • Backend API:        http://localhost:8000")
    print("  • Client CRM:         http://localhost:3000")
    print("  • Agency Admin:       http://localhost:3001")
    print("  • Swagger API Docs:   http://localhost:8000/docs")
    print("=" * 60)

    processes = []

    try:
        # 1. Start FastAPI Backend (Port 8000)
        print("▶ Starting FastAPI Backend on port 8000...")
        p_backend = subprocess.Popen(
            [PYTHON_EXE, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(ROOT_DIR)
        )
        processes.append(("Backend API", p_backend))

        # 2. Start Client CRM Static Server (Port 3000)
        print("▶ Starting Client CRM Dashboard on port 3000...")
        p_crm = subprocess.Popen(
            [PYTHON_EXE, "-m", "http.server", "3000", "--directory", "crm-design-preview"],
            cwd=str(ROOT_DIR)
        )
        processes.append(("Client CRM", p_crm))

        # 3. Start Agency Admin Portal (Port 3001)
        print("▶ Starting Agency Admin Portal on port 3001...")
        p_admin = subprocess.Popen(
            [PYTHON_EXE, "-m", "http.server", "3001", "--directory", "agency-admin"],
            cwd=str(ROOT_DIR)
        )
        processes.append(("Agency Admin", p_admin))

        # Give servers a moment to bind
        time.sleep(2)

        if open_browser:
            print("\n🌐 Opening browser windows...")
            webbrowser.open("http://localhost:3000")
            time.sleep(0.5)
            webbrowser.open("http://localhost:3001")

        print("\n✅ All servers running! Press Ctrl+C in this terminal to stop all servers.")

        # Keep runner alive
        while True:
            for name, p in processes:
                ret = p.poll()
                if ret is not None:
                    print(f"⚠️ Process {name} exited with code {ret}")
                    return
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping all ARVANA local servers...")
    finally:
        for name, p in processes:
            try:
                p.terminate()
                p.wait(timeout=2)
            except Exception:
                p.kill()
        print("✓ All servers cleanly stopped.")

if __name__ == "__main__":
    start_servers(open_browser=True)

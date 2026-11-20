"""
Secure Fingerprint Authentication System - Interface Launcher
Author: Antigravity AI
Description:
    Starts the FastAPI server with Uvicorn on http://127.0.0.1:8000
    (or another free port) and launches the web dashboard.
"""

import sys
import time
import socket
import webbrowser
import threading
import uvicorn
import urllib.request


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def find_available_port(start_port: int = 8000, host: str = "127.0.0.1") -> int:
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    return start_port


def open_browser(url: str):
    time.sleep(1.2)
    webbrowser.open(url)


if __name__ == "__main__":
    host = "127.0.0.1"
    target_port = 8000

    # Check if the server is already running on port 8000
    if is_port_in_use(target_port, host):
        try:
            req = urllib.request.urlopen(f"http://{host}:{target_port}/", timeout=1.5)
            if req.status == 200:
                print("\n==================================================================")
                print(f"  [ALREADY RUNNING] Server is already active on http://{host}:{target_port}")
                print(f"  Opening browser dashboard now: http://{host}:{target_port}")
                print("==================================================================\n")
                webbrowser.open(f"http://{host}:{target_port}")
                sys.exit(0)
        except Exception:
            target_port = find_available_port(8001, host)

    print("\n==================================================================")
    print("  SECURE FINGERPRINT AUTHENTICATION SYSTEM (WEB INTERFACE)")
    print("  Juels-Wattenberg Fuzzy Commitment & Schnorr 3-Pass ZKP")
    print(f"  Server URL: http://{host}:{target_port}")
    print("==================================================================\n")

    url = f"http://{host}:{target_port}"
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    uvicorn.run("web.app:app", host=host, port=target_port, reload=False, log_level="info")



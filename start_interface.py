"""
Secure Fingerprint Authentication System - Interface Launcher
Author: Antigravity AI
Description:
    Starts the FastAPI server with Uvicorn on http://127.0.0.1:8000
    and launches the web dashboard.
"""

import uvicorn
import webbrowser
import threading
import time


def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:8000")


if __name__ == "__main__":
    print("\n==================================================================")
    print("  SECURE FINGERPRINT AUTHENTICATION SYSTEM (WEB INTERFACE)")
    print("  Juels-Wattenberg Fuzzy Commitment & Schnorr 3-Pass ZKP")
    print("  Server URL: http://127.0.0.1:8000")
    print("==================================================================\n")

    # Open browser automatically in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Start Uvicorn web server
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000, reload=False, log_level="info")


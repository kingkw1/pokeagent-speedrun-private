#!/usr/bin/env python3
"""
Debug: Check what is_in_dialog() actually returns and why
"""

import subprocess
import time
import requests

cmd = ["python", "-m", "server.app", "--load-state", "tests/states/dialog.state"]
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

try:
    print("Starting server...")
    time.sleep(10)
    
    print("\nChecking state...")
    resp = requests.get("http://localhost:8000/state", timeout=2)
    state = resp.json()
    
    print(f"in_dialog: {state['game'].get('in_dialog')}")
    print(f"dialog_text: {state['game'].get('dialog_text')}")
    
    # Check stderr for debug logs
    print("\n--- Server output ---")
    for line in iter(process.stdout.readline, ''):
        if 'dialog' in line.lower() or 'residual' in line.lower():
            print(line, end='')
        if len(line) > 1000:  # Don't print huge lines
            break
            
finally:
    process.terminate()
    process.wait(timeout=5)

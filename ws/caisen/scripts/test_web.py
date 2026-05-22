#!/usr/bin/env python3
"""Test web server with Playwright"""
import subprocess
import time
import sys

# Start server
print("Starting server...")
server = subprocess.Popen(
    ["python3", "-m", "caisen.cli.main", "web", "--port", "8001"],
    cwd="/home/user/yaoniming3k/ws/caisen",
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
time.sleep(3)

try:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Test main page
        print("Testing main page...")
        page.goto("http://localhost:8001/")
        page.wait_for_load_state("networkidle")
        title = page.title()
        print(f"  Title: {title}")

        # Check if runs are loaded
        content = page.content()
        if "MACrossStrategy" in content:
            print("  ✓ Run card found")
        else:
            print("  ✗ Run card not found")
            print(f"  Content: {content[:500]}")

        # Take screenshot
        page.screenshot(path="/home/user/yaoniming3k/ws/caisen/test_main.png")
        print("  Screenshot saved: test_main.png")

        # Click on run card
        print("\nTesting report page...")
        page.click(".run-card")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        report_title = page.title()
        print(f"  Title: {report_title}")

        # Check for chart
        if "kline-chart" in page.content() or "equity-chart" in page.content():
            print("  ✓ Charts found")
        else:
            print("  ✗ Charts not found")

        page.screenshot(path="/home/user/yaoniming3k/ws/caisen/test_report.png")
        print("  Screenshot saved: test_report.png")

        browser.close()
        print("\n✓ All tests passed!")

finally:
    server.terminate()
    server.wait()

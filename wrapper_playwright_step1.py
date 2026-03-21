import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://example.com", wait_until="domcontentloaded")

        capture_dir = Path(os.environ.get("STEP_CAPTURE_DIR", "./captures")).resolve()
        capture_dir.mkdir(parents=True, exist_ok=True)

        screenshot_path = capture_dir / "example-home.png"
        html_path = capture_dir / "example-home.html"

        page.screenshot(path=str(screenshot_path), full_page=True)
        html_path.write_text(page.content(), encoding="utf-8")

        print("PLAYWRIGHT_READY=1")
        print(f"TITLE={page.title()}")
        print(f"SCREENSHOT={screenshot_path}")
        print(f"HTML={html_path}")

        browser.close()


if __name__ == "__main__":
    main()

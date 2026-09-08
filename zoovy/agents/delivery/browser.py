import os
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright, BrowserContext, Page


class BrowserSessionManager:
    """
    Manages Playwright browser instances with persistent profiles so logins
    and cookies (OTP sessions) are saved across runs.
    """

    def __init__(self, platform_name: str, headless: bool = False):
        self.platform_name = platform_name
        self.headless = headless
        self.user_data_dir = Path.home() / ".zoovy" / "sessions" / platform_name
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def start(self) -> Page:
        """Launch persistent Chromium context."""
        self._playwright = sync_playwright().start()
        self.context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=self.headless,
            channel="chrome",  # Fallback to bundled chromium if chrome not found
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
            ],
            viewport=None,
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        return self.page

    def close(self):
        """Gracefully close context."""
        if self.context:
            self.context.close()
        if self._playwright:
            self._playwright.stop()

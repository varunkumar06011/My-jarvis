import time
from typing import Any, Optional

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.engine.artifacts import artifact_manager


class BrowserAutomation:
    """Playwright-based browser automation. Requires `playwright` package."""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._available = False
        try:
            from playwright.sync_api import sync_playwright
            self._available = True
        except ImportError:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def _ensure_playwright(self):
        if not self._available:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install")
        if self._playwright is None:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()

    def _get_page(self):
        self._ensure_playwright()
        if self._browser is None:
            self._browser = self._playwright.chromium.launch(headless=True)
            self._context = self._browser.new_context()
            self._page = self._context.new_page()
        return self._page

    def open(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        browser_type = params.get("browser", "chromium")
        headless = params.get("headless", True)
        self._ensure_playwright()

        launcher = getattr(self._playwright, browser_type, self._playwright.chromium)
        self._browser = launcher.launch(headless=headless)
        self._context = self._browser.new_context()
        self._page = self._context.new_page()

        rollback.register("browser.close", lambda: self.close_all(), "Close browser")
        return {"status": "opened", "browser": browser_type}

    def navigate(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        url = params.get("url", "")
        page = self._get_page()
        page.goto(url)
        return {"status": "navigated", "url": url, "title": page.title()}

    def click(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        selector = params.get("selector", "")
        page = self._get_page()
        page.click(selector)
        return {"status": "clicked", "selector": selector}

    def type_text(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        selector = params.get("selector", "")
        text = params.get("text", "")
        page = self._get_page()
        page.fill(selector, text)
        return {"status": "typed", "selector": selector, "length": len(text)}

    def screenshot(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        page = self._get_page()
        full_page = params.get("full_page", True)
        screenshot_bytes = page.screenshot(full_page=full_page)
        artifact = artifact_manager.save_file(
            name=params.get("name", "screenshot"),
            content=screenshot_bytes,
            automation_id=ctx.automation_id,
            extension="png",
        )
        return {"status": "screenshot", "artifact_id": artifact.id, "path": artifact.path}

    def get_text(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        selector = params.get("selector", "body")
        page = self._get_page()
        text = page.inner_text(selector)
        return {"status": "ok", "text": text}

    def get_dom(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        page = self._get_page()
        html = page.content()
        return {"status": "ok", "html": html[:5000], "length": len(html)}

    def wait_for(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        selector = params.get("selector", "")
        timeout = params.get("timeout", 30000)
        page = self._get_page()
        page.wait_for_selector(selector, timeout=timeout)
        return {"status": "ok", "selector": selector}

    def download(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        url = params.get("url", "")
        save_path = params.get("save_path", "")
        page = self._get_page()

        with page.expect_download() as download_info:
            page.goto(url)
        download = download_info.value
        if save_path:
            download.save_as(save_path)
        return {"status": "downloaded", "url": url, "path": save_path}

    def export_pdf(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        page = self._get_page()
        pdf_bytes = page.pdf()
        artifact = artifact_manager.save_file(
            name=params.get("name", "export"),
            content=pdf_bytes,
            automation_id=ctx.automation_id,
            extension="pdf",
        )
        return {"status": "ok", "artifact_id": artifact.id, "path": artifact.path}

    def close_all(self) -> dict:
        if self._page:
            try: self._page.close()
            except: pass
        if self._context:
            try: self._context.close()
            except: pass
        if self._browser:
            try: self._browser.close()
            except: pass
        self._page = None
        self._context = None
        self._browser = None
        return {"status": "closed"}

    def close(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        return self.close_all()


browser_automation = BrowserAutomation()

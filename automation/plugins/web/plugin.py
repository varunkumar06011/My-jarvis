import time
from typing import Any

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.engine.artifacts import artifact_manager
from automation.plugins.base import AutomationPlugin, RiskLevel


class WebPlugin(AutomationPlugin):
    """Common web automation patterns built on the browser engine."""

    def __init__(self):
        super().__init__()
        self.name = "Web"
        self.description = "Web automation: search, form fill, scrape, login, multi-page crawl"
        self.version = "1.0"
        self.author = "Jarvis"

    def initialize(self):
        self.register_action("web.search", self.search, RiskLevel.SAFE)
        self.register_action("web.scrape", self.scrape, RiskLevel.SAFE)
        self.register_action("web.fill_form", self.fill_form, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("web.login", self.login, RiskLevel.HIGH)
        self.register_action("web.click_and_wait", self.click_and_wait, RiskLevel.SAFE)
        self.register_action("web.multi_page", self.multi_page_scrape, RiskLevel.SAFE)
        self.register_action("web.extract_table", self.extract_table, RiskLevel.SAFE)
        self.register_action("web.scroll", self.scroll, RiskLevel.SAFE)
        self.register_action("web.get_links", self.get_links, RiskLevel.SAFE)
        self.register_action("web.set_cookies", self.set_cookies, RiskLevel.MEDIUM)

        self.register_workflow({
            "id": "web_search_and_scrape",
            "name": "Web Search and Scrape",
            "description": "Search a query, click first result, scrape content",
            "version": "1.0",
            "variables": {"query": "Jarvis AI assistant", "selector": "body"},
            "steps": [
                {"name": "open", "type": "action", "action": "browser.open", "params": {"browser": "chromium"}},
                {"name": "search", "type": "action", "action": "web.search", "params": {"query": "{{query}}", "engine": "google"}},
                {"name": "scrape", "type": "action", "action": "web.scrape", "params": {"selector": "{{selector}}"}},
                {"name": "screenshot", "type": "action", "action": "browser.screenshot", "params": {"name": "search_result"}},
                {"name": "close", "type": "action", "action": "browser.close"},
            ],
        })

    def _get_page(self):
        from automation.browser.controller import browser_automation
        return browser_automation._get_page()

    def search(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        query = params.get("query", "")
        engine = params.get("engine", "google")
        page = self._get_page()

        if engine == "google":
            page.goto(f"https://www.google.com/search?q={query}")
        elif engine == "bing":
            page.goto(f"https://www.bing.com/search?q={query}")
        elif engine == "duckduckgo":
            page.goto(f"https://duckduckgo.com/?q={query}")
        else:
            page.goto(f"https://www.google.com/search?q={query}")

        results = []
        try:
            if engine == "google":
                items = page.query_selector_all("div.g")
                for item in items[:10]:
                    title_el = item.query_selector("h3")
                    link_el = item.query_selector("a")
                    if title_el and link_el:
                        results.append({
                            "title": title_el.inner_text(),
                            "url": link_el.get_attribute("href"),
                        })
        except Exception:
            pass

        ctx.set_var("search_results", results)
        return {"status": "ok", "results": results[:10], "count": len(results)}

    def scrape(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        selector = params.get("selector", "body")
        page = self._get_page()
        text = page.inner_text(selector)
        ctx.set_var("scraped_content", text)
        return {"status": "ok", "content": text[:5000], "length": len(text)}

    def fill_form(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        fields = params.get("fields", {})
        page = self._get_page()
        filled = 0
        for selector, value in fields.items():
            try:
                page.fill(selector, str(value))
                filled += 1
            except Exception:
                pass
        return {"status": "ok", "filled": filled, "total": len(fields)}

    def login(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        url = params.get("url", "")
        username_selector = params.get("username_selector", "input[name='username'], input[name='email'], input[type='email']")
        password_selector = params.get("password_selector", "input[name='password'], input[type='password']")
        submit_selector = params.get("submit_selector", "button[type='submit'], input[type='submit']")
        username = params.get("username", "")
        password = params.get("password", "")

        page = self._get_page()
        page.goto(url)
        page.fill(username_selector, username)
        page.fill(password_selector, password)
        page.click(submit_selector)
        page.wait_for_load_state("networkidle", timeout=10000)

        return {"status": "ok", "url": url, "logged_in": True}

    def click_and_wait(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        selector = params.get("selector", "")
        wait_selector = params.get("wait_selector", "")
        timeout = params.get("timeout", 10000)
        page = self._get_page()
        page.click(selector)
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=timeout)
        else:
            page.wait_for_load_state("networkidle", timeout=timeout)
        return {"status": "ok", "clicked": selector}

    def multi_page_scrape(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        urls = params.get("urls", [])
        selector = params.get("selector", "body")
        page = self._get_page()
        results = []
        for url in urls:
            try:
                page.goto(url, timeout=15000)
                text = page.inner_text(selector)
                results.append({"url": url, "content": text[:2000], "length": len(text)})
            except Exception as e:
                results.append({"url": url, "error": str(e)})
        return {"status": "ok", "pages": len(results), "results": results}

    def extract_table(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        selector = params.get("selector", "table")
        page = self._get_page()
        rows = page.query_selector_all(f"{selector} tr")
        table_data = []
        for row in rows:
            cells = row.query_selector_all("td, th")
            row_data = [cell.inner_text().strip() for cell in cells]
            if row_data:
                table_data.append(row_data)
        return {"status": "ok", "rows": len(table_data), "table": table_data}

    def scroll(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        direction = params.get("direction", "down")
        amount = params.get("amount", 500)
        page = self._get_page()
        if direction == "down":
            page.mouse.wheel(0, amount)
        else:
            page.mouse.wheel(0, -amount)
        time.sleep(0.5)
        return {"status": "ok", "direction": direction, "amount": amount}

    def get_links(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        page = self._get_page()
        links = page.query_selector_all("a")
        result = []
        for link in links[:50]:
            href = link.get_attribute("href")
            text = link.inner_text().strip()
            if href and text:
                result.append({"text": text[:100], "url": href})
        return {"status": "ok", "count": len(result), "links": result}

    def set_cookies(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        cookies = params.get("cookies", [])
        from automation.browser.controller import browser_automation
        if browser_automation._context:
            browser_automation._context.add_cookies(cookies)
            return {"status": "ok", "cookies_set": len(cookies)}
        return {"status": "error", "error": "No browser context available"}

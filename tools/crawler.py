

"""
tools/crawler.py
BEST WORKING CRAWLER
Updated with automatic login before crawling
"""

import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

import nest_asyncio
nest_asyncio.apply()

from playwright.async_api import async_playwright
from google.adk.tools import FunctionTool

LOCATORS_FILE = "storage/locators.json"
MAX_ELEMENTS_PER_PAGE = 200
MAX_PAGES = 20

# ── Login Config (set from main.py) ─────────────────────────────
LOGIN_URL = None
LOGIN_USERNAME = None
LOGIN_PASSWORD = None


def _same_origin(base: str, href: str) -> bool:
    return urlparse(base).netloc == urlparse(href).netloc


async def _extract_elements(page, url: str) -> list:
    elements_data = []
    seen_ids: set = set()

    elements = await page.query_selector_all(
        "input, button, a, select, textarea, form, "
        "[data-test], [data-testid], [data-cy], [data-qa], "
        "[role='button'], [role='link'], [role='menuitem'], "
        "[role='tab'], [role='checkbox'], [role='radio'], "
        "[role='combobox'], [role='textbox'], [role='listbox']"
    )

    for el in elements:
        if len(elements_data) >= MAX_ELEMENTS_PER_PAGE:
            break

        try:
            tag = await el.evaluate("e => e.tagName.toLowerCase()")
            el_id = await el.get_attribute("id") or ""
            name = await el.get_attribute("name") or ""
            el_type = await el.get_attribute("type") or ""
            placeholder = await el.get_attribute("placeholder") or ""
            href = await el.get_attribute("href") or ""
            role = await el.get_attribute("role") or ""
            aria_label = await el.get_attribute("aria-label") or ""
            class_attr = await el.get_attribute("class") or ""
            data_test = await el.get_attribute("data-test") or ""
            data_testid = await el.get_attribute("data-testid") or ""
            data_cy = await el.get_attribute("data-cy") or ""
            data_qa = await el.get_attribute("data-qa") or ""
            text = ((await el.inner_text()) or "")[:60].strip()

            # Best selector priority
            if data_test:
                selector = f"[data-test='{data_test}']"
            elif data_testid:
                selector = f"[data-testid='{data_testid}']"
            elif data_cy:
                selector = f"[data-cy='{data_cy}']"
            elif data_qa:
                selector = f"[data-qa='{data_qa}']"
            elif el_id:
                selector = f"#{el_id}"
            elif name:
                selector = f"{tag}[name='{name}']"
            elif aria_label:
                selector = f"[aria-label='{aria_label}']"
            elif class_attr:
                main_cls = class_attr.strip().split()[0]
                selector = f"{tag}.{main_cls}"
            else:
                selector = None

            xpath = await el.evaluate("""e => {
                let path = '', node = e;
                while (node && node.nodeType === 1) {
                    let i = 1, s = node.previousSibling;
                    while (s) {
                        if (s.nodeType === 1 && s.tagName === node.tagName) i++;
                        s = s.previousSibling;
                    }
                    path = '/' + node.tagName.toLowerCase() + '[' + i + ']' + path;
                    node = node.parentNode;
                }
                return path;
            }""")

            dedup_key = el_id or xpath
            if dedup_key in seen_ids:
                continue
            seen_ids.add(dedup_key)

            rec = {
                "tag": tag,
                "xpath": xpath,
                "page": url,
            }

            if selector:
                rec["selector"] = selector
            if el_id:
                rec["id"] = el_id
            if name:
                rec["name"] = name
            if text:
                rec["text"] = text
            if el_type:
                rec["type"] = el_type
            if placeholder:
                rec["placeholder"] = placeholder
            if href:
                rec["href"] = href
            if role:
                rec["role"] = role
            if aria_label:
                rec["aria_label"] = aria_label
            if class_attr:
                rec["class"] = class_attr
            if data_test:
                rec["data_test"] = data_test
            if data_testid:
                rec["data_testid"] = data_testid
            if data_cy:
                rec["data_cy"] = data_cy
            if data_qa:
                rec["data_qa"] = data_qa

            elements_data.append(rec)

        except Exception:
            continue

    return elements_data


async def _discover_links(page, base_url: str) -> list[str]:
    try:
        hrefs = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.href)"
        )
    except Exception:
        return []

    seen = set()
    links = []

    for href in hrefs:
        full = urljoin(base_url, href).split("#")[0].split("?")[0]

        if (
            full not in seen
            and _same_origin(base_url, full)
            and full.startswith("http")
        ):
            seen.add(full)
            links.append(full)

    return links


async def _navigate_to_page(page, url: str):
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        try:
            await page.wait_for_selector(
                "input, button, select, a, [data-test], [data-testid]",
                timeout=10000,
            )
        except Exception:
            pass

    except Exception:
        await page.wait_for_timeout(2000)


async def _trigger_dynamic_elements(page):
    try:
        nav_items = await page.query_selector_all(
            "nav a, nav button, header a, header button"
        )

        for item in nav_items[:5]:
            try:
                await item.hover(timeout=2000)
                await page.wait_for_timeout(300)
            except Exception:
                pass

    except Exception:
        pass

    try:
        toggles = await page.query_selector_all(
            "[aria-expanded], [aria-haspopup], "
            "button[class*='menu'], button[class*='toggle'], "
            "button[class*='burger'], button[class*='nav'], "
            "[id*='menu-btn'], [id*='menu_btn']"
        )

        for toggle in toggles[:5]:
            try:
                await toggle.click(timeout=2000)
                await page.wait_for_timeout(500)
            except Exception:
                pass

    except Exception:
        pass


async def crawl_locators(url: str, force_recrawl: bool = False) -> str:
    locators_path = Path(LOCATORS_FILE)

    # ── Cache Check ─────────────────────────────────────────────
    if locators_path.exists() and not force_recrawl:
        cached = locators_path.read_text()
        data = json.loads(cached)

        print(
            f"[Crawler] Cache hit – {len(data['elements'])} elements "
            f"across {len(data.get('pages_crawled', []))} page(s)."
        )
        return cached

    print(f"[Crawler] Starting generic crawl from {url} ...")

    result = {
        "url": url,
        "pages_crawled": [],
        "elements": [],
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # ── LOGIN FIRST if credentials provided ─────────────────
        if LOGIN_USERNAME and LOGIN_PASSWORD:
            print(f"[Crawler] Logging in as {LOGIN_USERNAME} ...")

            login_target = LOGIN_URL or url

            await page.goto(
                login_target,
                wait_until="networkidle",
                timeout=30000,
            )
            await page.wait_for_timeout(2000)

            try:
                await page.fill("#user-name", LOGIN_USERNAME)
                await page.fill("#password", LOGIN_PASSWORD)
                await page.click("#login-button")
                await page.wait_for_timeout(3000)
                print("[Crawler] Login done.")

            except Exception as e:
                print(f"[Crawler] Login failed: {e}")
        # ────────────────────────────────────────────────────────

        visited: set = set()
        queue: list = [url]

        while queue and len(result["pages_crawled"]) < MAX_PAGES:
            current = queue.pop(0)

            if current in visited:
                continue

            visited.add(current)

            print(
                f"  [Crawler] ({len(visited)}/{MAX_PAGES}) Crawling: {current}"
            )

            await _navigate_to_page(page, current)
            await _trigger_dynamic_elements(page)

            elems = await _extract_elements(page, current)
            result["elements"].extend(elems)
            result["pages_crawled"].append(current)

            print(f"  [Crawler] Found {len(elems)} elements on this page.")

            new_links = await _discover_links(page, current)
            for link in new_links:
                if link not in visited and link not in queue:
                    queue.append(link)

        await browser.close()

    locators_path.parent.mkdir(parents=True, exist_ok=True)
    locators_path.write_text(json.dumps(result, indent=2))

    print(
        f"[Crawler] Done – {len(result['elements'])} elements "
        f"across {len(result['pages_crawled'])} page(s)."
    )

    return json.dumps(result)


def crawl_locators_sync(url: str, force_recrawl: bool = False) -> str:
    import asyncio

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        crawl_locators(url, force_recrawl=force_recrawl)
    )


crawl_tool = FunctionTool(func=crawl_locators_sync)

"""
tools/tc_parser.py
"""
import csv
import re
from tools.locator_tree import _get_tree

KEEP = {
    "test_id":    "Test Case ID",
    "description":"Test Description",
    "steps":      "Test Steps",
    "expected":   "Expected Result",
}

def parse_test_cases(csv_path: str) -> list[dict]:
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tc = {k: (row.get(v) or "").strip() for k, v in KEEP.items()}
            if tc["test_id"] and tc["description"]:
                rows.append(tc)
    print(f"[Parser] {len(rows)} test cases loaded.")
    return rows


def _extract_keywords(steps: str) -> list[str]:
    patterns = [
        r"click\s+([\w\s]+?)(?:\s+button|\s+link|\s+icon|\s+on\b)?(?:\.|,|$|\d)",
        r"enter\s+[\w'\s]+\s+in(?:to)?\s+([\w\s]+?)(?:\s+field|\s+input)?(?:\.|,|$)",
        r"type\s+[\w'\s]+\s+in(?:to)?\s+([\w\s]+?)(?:\s+field|\s+input)?(?:\.|,|$)",
        r"([\w\s]+?(?:button|field|input|dropdown|link|icon|menu|checkbox|bar))\b",
    ]
    found = []
    for pat in patterns:
        for m in re.finditer(pat, steps.lower()):
            kw = m.group(1).strip()
            if kw and len(kw) > 2:
                found.append(kw)
    seen = set()
    return [x for x in found if not (x in seen or seen.add(x))]


def fetch_locators_for_tc(tc: dict, page_url: str = "") -> list[dict]:
    tree = _get_tree()
    keywords = _extract_keywords(tc.get("steps", ""))

    if not keywords:
        keywords = [tc.get("description", "")]

    seen = set()
    locators = []
    for kw in keywords:
        hits = tree.search(query=kw, page_hint=page_url or None, top_k=5)
        for loc in tree.slim(hits):
            key = loc.get("selector") or loc.get("xpath", "")
            if key not in seen:
                seen.add(key)
                locators.append(loc)

    # fallback — send all locators if nothing matched
    if not locators:
        print(f"    [Parser] 0 matched — sending all locators as fallback")
        all_hits = tree.search(query="input button link", page_hint=page_url or None, top_k=20)
        for loc in tree.slim(all_hits):
            key = loc.get("selector") or loc.get("xpath", "")
            if key not in seen:
                seen.add(key)
                locators.append(loc)

    return locators[:15]


def build_prompt(tc: dict, locators: list[dict]) -> str:
    loc_text = "\n".join(
        f"  - selector={l.get('selector','N/A')} "
        f"tag={l.get('tag','')} "
        f"type={l.get('type','')} "
        f"text={l.get('text','')} "
        f"id={l.get('id','')}"
        for l in locators
    ) or "  (none found — skip steps needing locators with a comment)"

    return (
        f"Test ID    : {tc['test_id']}\n"
        f"Description: {tc['description']}\n"
        f"Steps      : {tc['steps']}\n"
        f"Expected   : {tc['expected']}\n"
        f"\nLocators for this test (USE ONLY THESE — do not invent any selector):\n"
        f"{loc_text}"
    )
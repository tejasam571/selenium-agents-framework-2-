"""
tools/locator_tree.py
Builds a 3-level tree from crawler's locators.json
root → page_slug → tag → keyword → [locators]
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse
from google.adk.tools import FunctionTool

LOCATORS_FILE = "storage/locators.json"


# ── Node ──────────────────────────────────────────────────────────
class _Node:
    def __init__(self, key):
        self.key      = key
        self.children = {}
        self.locators = []   # only leaves store locators


# ── Tree ──────────────────────────────────────────────────────────
class LocatorTree:
    def __init__(self):
        self.root  = _Node("root")
        self._size = 0

    # ── build ──────────────────────────────────────────────────────
    def build(self, path: str = LOCATORS_FILE):
        raw      = json.loads(Path(path).read_text())
        elements = raw if isinstance(raw, list) else raw.get("elements", [])
        for loc in elements:
            self._insert(loc)
        print(f"[LocatorTree] {self._size} locators | "
              f"{len(self.root.children)} pages")

    def _insert(self, loc: dict):
        slug    = self._slugify(loc.get("page", ""))
        tag     = loc.get("tag", "unknown")
        keyword = self._keyword(loc)

        # level 1 — page
        if slug not in self.root.children:
            self.root.children[slug] = _Node(slug)
        p = self.root.children[slug]

        # level 2 — tag
        if tag not in p.children:
            p.children[tag] = _Node(tag)
        t = p.children[tag]

        # level 3 — keyword (leaf)
        if keyword not in t.children:
            t.children[keyword] = _Node(keyword)
        t.children[keyword].locators.append(loc)
        self._size += 1

    # ── search ─────────────────────────────────────────────────────
    def search(self,
               query:     str,
               page_hint: str = None,
               tag_hint:  str = None,
               top_k:     int = 10) -> list[dict]:

        tokens    = self._tok(query)
        html_tags = {"input","button","a","select","textarea","form"}
        scored    = []

        # narrow page(s)
        page_nodes = self._resolve_page(page_hint)

        for pnode in page_nodes:
            # narrow tag(s)
            tag_nodes = self._resolve_tag(pnode, tag_hint, tokens, html_tags)

            for tnode in tag_nodes:
                tag_bonus = 1 if tnode.key in tokens else 0

                for kw, leaf in tnode.children.items():
                    sc = self._score(tokens, kw) + tag_bonus
                    if sc > 0:
                        for loc in leaf.locators:
                            scored.append((sc, loc))

        scored.sort(key=lambda x: -x[0])
        return [l for _, l in scored[:top_k]]

    # ── helpers ────────────────────────────────────────────────────
    def _resolve_page(self, hint) -> list[_Node]:
        if hint:
            slug = self._slugify(hint)
            if slug in self.root.children:
                return [self.root.children[slug]]
            # partial match
            hits = [n for k, n in self.root.children.items()
                    if slug in k or k in slug]
            if hits:
                return hits
        return list(self.root.children.values())

    def _resolve_tag(self, pnode, tag_hint, tokens, html_tags) -> list[_Node]:
        if tag_hint and tag_hint in pnode.children:
            return [pnode.children[tag_hint]]
        token_tags = [t for t in tokens if t in html_tags]
        if token_tags:
            nodes = [pnode.children[t]
                     for t in token_tags if t in pnode.children]
            if nodes:
                return nodes
        return list(pnode.children.values())

    def _score(self, tokens, kw) -> int:
        sc = 0
        for t in tokens:
            if t == kw:   sc += 3
            elif t in kw: sc += 2
        return sc

    def _keyword(self, loc) -> str:
        for f in ["data_test","data_testid","data_cy",
                  "aria_label","placeholder","name","text","id"]:
            v = (loc.get(f) or "").strip().lower()[:40]
            if v:
                return v
        return loc.get("tag", "unknown")

    def _slugify(self, page) -> str:
        path = urlparse(page).path.strip("/") or "home"
        return path.replace("/", "_").lower()

    def _tok(self, text) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def slim(self, locs: list[dict]) -> list[dict]:
        keep = {"selector","xpath","tag","text","type",
                "placeholder","aria_label","page","id","name"}
        return [{k: v for k, v in l.items() if k in keep} for l in locs]


# ── singleton ──────────────────────────────────────────────────────
_tree: LocatorTree | None = None

def _get_tree() -> LocatorTree:
    global _tree
    if _tree is None:
        _tree = LocatorTree()
        if Path(LOCATORS_FILE).exists():
            _tree.build()
        else:
            print("[LocatorTree] locators.json not found — crawl first.")
    return _tree

def reload_tree():
    """Call this right after crawler writes locators.json."""
    global _tree
    _tree = LocatorTree()
    _tree.build()


# ── ADK tool function ──────────────────────────────────────────────
def search_locators(query: str, page_hint: str = "", top_k: int = 10) -> str:
    """
    Search the locator tree for elements relevant to a test step.
    query     : natural language e.g. 'username input field'
    page_hint : URL path hint   e.g. '/login'  (optional, pass '' to skip)
    top_k     : max results (default 10)
    Returns   : compact JSON list of matching locators.
    """
    tree = _get_tree()
    hits = tree.search(
        query     = query,
        page_hint = page_hint or None,
        top_k     = top_k,
    )
    slim = tree.slim(hits)
    return json.dumps(slim, indent=2)


search_locators_tool = FunctionTool(func=search_locators)
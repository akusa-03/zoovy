"""
Zero-API-key Web Search Context Enrichment Module for Zoovy.
Enables real-time web search and content synthesis for user prompts,
providing real-world item variants, recipes, typical quantities, and price sanity.
"""

import re
import urllib.parse
import requests
from typing import Dict, Any, List, Optional
from html.parser import HTMLParser
from rich.console import Console

console = Console()

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}


class _DDGHTMLParser(HTMLParser):
    """Parses DuckDuckGo HTML Lite search results."""

    def __init__(self):
        super().__init__()
        self.results: List[Dict[str, str]] = []
        self._current: Dict[str, str] = {}
        self._in_title = False
        self._in_snippet = False

    def handle_starttag(self, tag: str, attrs: List[tuple]):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "").split()

        if tag == "a" and "result__a" in classes:
            self._in_title = True
            raw_url = attrs_dict.get("href", "")
            if "uddg=" in raw_url:
                m = re.search(r"uddg=([^&]+)", raw_url)
                if m:
                    raw_url = urllib.parse.unquote(m.group(1))
            self._current = {"title": "", "snippet": "", "url": raw_url}

        elif tag == "a" and "result__snippet" in classes:
            self._in_snippet = True

    def handle_endtag(self, tag: str):
        if self._in_title and tag == "a":
            self._in_title = False
        elif self._in_snippet and tag == "a":
            self._in_snippet = False
            if self._current.get("title"):
                self.results.append(self._current)
                self._current = {}

    def handle_data(self, data: str):
        if self._in_title and self._current:
            self._current["title"] += data
        elif self._in_snippet and self._current:
            self._current["snippet"] += data


class WebSearchEngine:
    """
    Zero-config Web Search engine for query context expansion.
    """

    @classmethod
    def search(cls, query: str, max_results: int = 5, timeout: int = 6) -> Dict[str, Any]:
        """
        Executes a live search via DuckDuckGo HTML endpoint without external API keys.
        """
        clean_query = query.strip()
        if not clean_query:
            return {"success": False, "query": query, "results": [], "error": "Empty query"}

        try:
            url = "https://html.duckduckgo.com/html/"
            resp = requests.post(url, data={"q": clean_query}, headers=HEADERS, timeout=timeout)
            if resp.status_code in (200, 202):
                parser = _DDGHTMLParser()
                parser.feed(resp.text)
                results = [
                    {
                        "title": r["title"].strip(),
                        "snippet": r["snippet"].strip(),
                        "url": r["url"].strip()
                    }
                    for r in parser.results if r.get("title")
                ]
                return {
                    "success": True,
                    "query": clean_query,
                    "count": len(results[:max_results]),
                    "results": results[:max_results]
                }
        except Exception as e:
            return {
                "success": False,
                "query": clean_query,
                "results": [],
                "error": str(e)
            }

        return {"success": False, "query": clean_query, "results": []}

    @classmethod
    def enrich_query_context(cls, user_prompt: str) -> Dict[str, Any]:
        """
        Analyzes the prompt, executes targeted web search, and returns
        structured insights (pack sizes, recommended quantities, recipes, etc.).
        """
        console.print(f"[cyan]🌐 [Web Search][/cyan] Researching real-world context for: [bold]'{user_prompt}'[/bold]")

        search_query = user_prompt
        prompt_lower = user_prompt.lower()
        if any(w in prompt_lower for w in ["party", "cocktail", "recipe", "snack", "guest", "people", "dinner"]):
            search_query = f"{user_prompt} ingredients grocery quantity"
        elif any(w in prompt_lower for w in ["coke", "soda", "butter", "milk", "egg", "bread"]):
            search_query = f"{user_prompt} price pack size swiggy instamart zepto"

        search_res = cls.search(search_query, max_results=4)
        snippets = []
        if search_res.get("success") and search_res.get("results"):
            for r in search_res["results"]:
                snippets.append(f"• {r['title']}: {r['snippet']}")
            console.print(f"[green]✓ [Web Search][/green] Retrieved {len(search_res['results'])} live references.")
        else:
            console.print("[dim]Web search completed (using local domain knowledge).[/dim]")

        context_summary = "\n".join(snippets) if snippets else "Standard grocery & food taxonomy applicable."

        return {
            "query": user_prompt,
            "search_query": search_query,
            "raw_results": search_res.get("results", []),
            "context_summary": context_summary
        }

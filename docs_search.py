"""
Lightweight documentation search engine for the Patchworks knowledge base.
Chunks the bundled markdown by section, builds an inverted index, and
supports keyword + fuzzy matching queries.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# Chunk the knowledge base into sections
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"^## \d+\.\s+", re.MULTILINE)

def _load_sections(path: Path) -> List[Dict[str, str]]:
    """Split the knowledge-base markdown into titled sections."""
    text = path.read_text(encoding="utf-8")
    parts = _SECTION_RE.split(text)
    titles = _SECTION_RE.findall(text)

    sections: List[Dict[str, str]] = []
    for i, title_prefix in enumerate(titles):
        # The raw split gives us the content *after* each heading marker.
        # Re-join with heading so we can extract the title line.
        block = parts[i + 1] if (i + 1) < len(parts) else ""
        first_line, _, body = block.partition("\n")
        title = first_line.strip()
        # Pull out the **Source:** URL if present
        source_match = re.search(r"\*\*Source:\*\*\s*(https?://\S+)", body)
        source_url = source_match.group(1) if source_match else ""
        sections.append({
            "title": title,
            "source_url": source_url,
            "content": body.strip(),
        })
    return sections


# ---------------------------------------------------------------------------
# Simple inverted index
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z0-9]+")

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "their", "its", "this", "that", "these", "those",
    "what", "which", "who", "whom", "how", "when", "where", "why",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "into", "about", "between", "through", "during", "before", "after",
    "and", "but", "or", "nor", "not", "so", "if", "then", "than",
    "all", "each", "every", "both", "few", "more", "most", "some", "any",
    "no", "only", "same", "such", "too", "very", "just",
})

def _tokenize(text: str) -> List[str]:
    return _WORD_RE.findall(text.lower())

def _tokenize_query(text: str) -> List[str]:
    """Tokenize a search query, removing stopwords."""
    tokens = _WORD_RE.findall(text.lower())
    filtered = [t for t in tokens if t not in _STOPWORDS]
    # If everything was a stopword, fall back to the original tokens
    return filtered if filtered else tokens


class DocsIndex:
    """In-memory keyword index over documentation sections."""

    def __init__(self, kb_path: Path | None = None):
        if kb_path is None:
            kb_path = Path(__file__).parent / "patchworks-knowledge-base.md"
        self.sections = _load_sections(kb_path)
        # inverted index: token -> set of section indices
        self._index: Dict[str, set] = {}
        # title tokens get a bonus so title matches outrank body mentions
        self._title_tokens: Dict[int, set] = {}
        for idx, sec in enumerate(self.sections):
            title_toks = set(_tokenize(sec["title"]))
            self._title_tokens[idx] = title_toks
            tokens = title_toks | set(_tokenize(sec["content"]))
            for tok in tokens:
                self._index.setdefault(tok, set()).add(idx)

    # ------------------------------------------------------------------
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Return the most relevant sections for *query*.

        Scoring: each query token that appears in a section scores 1 point.
        Substring matches (token starts with a query token) score 0.5.
        Results are returned highest-score-first.
        """
        q_tokens = _tokenize_query(query)
        if not q_tokens:
            return []

        scores: Dict[int, float] = {}

        for qt in q_tokens:
            # exact match
            for idx in self._index.get(qt, set()):
                # title matches score higher
                bonus = 2.0 if qt in self._title_tokens.get(idx, set()) else 1.0
                scores[idx] = scores.get(idx, 0) + bonus

            # prefix / substring match (cheap fuzzy)
            for tok, idxs in self._index.items():
                if tok != qt and (tok.startswith(qt) or qt.startswith(tok)):
                    for idx in idxs:
                        title_toks = self._title_tokens.get(idx, set())
                        bonus = 1.0 if tok in title_toks else 0.5
                        scores[idx] = scores.get(idx, 0) + bonus

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results: List[Dict[str, Any]] = []
        for idx, score in ranked[:max_results]:
            sec = self.sections[idx]
            results.append({
                "title": sec["title"],
                "source_url": sec["source_url"],
                "score": round(score, 2),
                "content": sec["content"][:2000],  # truncate for MCP response
            })
        return results


# Singleton for the server to import
_index: DocsIndex | None = None

def get_index() -> DocsIndex:
    global _index
    if _index is None:
        _index = DocsIndex()
    return _index

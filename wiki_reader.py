"""
Rooting Future -- Wiki Reader
Carica contesto dal Wiki per gli agenti di generazione.

Sostituisce il RAG (pickle + SQLite + File Search Store) con lettura diretta
di pagine Wiki markdown. Il LLM riceve contesto sintetizzato e ricco invece
di 2 documenti troncati a 1500 char.

Usage:
    from wiki_reader import WikiReader
    reader = WikiReader()
    context = reader.get_context_for_agent("STW Sportivi", "riccione-calcio-1926", "eccellenza")
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

WIKI_DIR = Path(__file__).parent / "wiki"
KB_DIR = WIKI_DIR / "kb"
RAW_DIR = WIKI_DIR / "raw"

# Mapping agente -> pattern di pagine Wiki da caricare
# Vedi WIKI_SCHEMA.md sezione 7 per il rationale
AGENT_WIKI_MAPPING: Dict[str, List[str]] = {
    "Strategic Coordinator": [
        "clubs/{slug}.md",
        "sintesi/overview.md",
        "benchmark/{category}*.md",
    ],
    "STW Sportivi": [
        "clubs/{slug}.md",
        "strategie/settore-giovanile*.md",
        "strategie/competitivo*.md",
        "strategie/pattern-{category}.md",
        "concetti/stw-sportivi.md",
        "concetti/stw-overview.md",
    ],
    "STW Strutturali": [
        "clubs/{slug}.md",
        "strategie/ristrutturazione*.md",
        "strategie/hr*.md",
        "strategie/pattern-{category}.md",
        "concetti/infrastrutture*.md",
        "concetti/stw-overview.md",
    ],
    "STW Marketing": [
        "clubs/{slug}.md",
        "strategie/marketing*.md",
        "strategie/diversificazione-ricavi*.md",
        "strategie/pattern-{category}.md",
        "concetti/brand*.md",
        "concetti/stw-overview.md",
    ],
    "STW Sociali": [
        "clubs/{slug}.md",
        "strategie/impatto-sociale*.md",
        "strategie/sostenibilita*.md",
        "strategie/pattern-{category}.md",
        "concetti/stw-sociali.md",
        "concetti/stw-overview.md",
    ],
    "Financial Strategist": [
        "clubs/{slug}.md",
        "benchmark/{category}*.md",
        "concetti/sostenibilita-finanziaria.md",
        "concetti/stw-overview.md",
    ],
    "Research Validator": [
        "clubs/{slug}.md",
        "benchmark/{category}*.md",
        "strategie/pattern-{category}.md",
        "concetti/stw-overview.md",
        "sintesi/lezioni-apprese.md",
    ],
    "Post-Production Editor": [
        "clubs/{slug}.md",
        "sintesi/lezioni-apprese.md",
    ],
}

# Limite massimo di caratteri di contesto Wiki per agente
MAX_WIKI_CONTEXT_CHARS = 50000


def slugify(name: str) -> str:
    """Converte un nome in slug."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


class WikiReader:
    """
    Legge pagine Wiki e costruisce contesto per gli agenti.
    Sostituisce get_context_for_generation() del RAG.
    """

    def __init__(self, wiki_dir: Optional[Path] = None):
        self.wiki_dir = wiki_dir or WIKI_DIR
        self.kb_dir = self.wiki_dir / "kb"
        self.raw_dir = self.wiki_dir / "raw"
        self._available = self.kb_dir.exists() and (self.kb_dir / "index.md").exists()

        if self._available:
            logger.info(f"WikiReader: inizializzato (kb={self.kb_dir})")
        else:
            logger.warning(f"WikiReader: Wiki non trovato in {self.kb_dir}")

    @property
    def available(self) -> bool:
        return self._available

    def get_context_for_agent(
        self,
        agent_name: str,
        club_slug: str,
        category: str = "eccellenza",
    ) -> str:
        """
        Carica e compone il contesto Wiki per un agente specifico.

        Args:
            agent_name: Nome dell'agente (es. "STW Sportivi")
            club_slug: Slug del club (es. "riccione-calcio-1926")
            category: Categoria del club (es. "eccellenza")

        Returns:
            Stringa markdown con tutto il contesto Wiki pertinente.
            Vuota se Wiki non disponibile.
        """
        if not self._available:
            return ""

        # Trova il mapping per l'agente
        patterns = None
        for agent_key, agent_patterns in AGENT_WIKI_MAPPING.items():
            if agent_key.lower() in agent_name.lower():
                patterns = agent_patterns
                break

        if not patterns:
            logger.warning(f"WikiReader: nessun mapping per agente '{agent_name}', uso fallback generico")
            patterns = [
                f"clubs/{club_slug}.md",
                f"benchmark/{category}*.md",
                "concetti/stw-overview.md",
            ]

        # Risolvi pattern con slug e category
        resolved = []
        for p in patterns:
            resolved.append(p.replace("{slug}", club_slug).replace("{category}", category))

        # Carica le pagine
        pages: List[Dict[str, str]] = []
        total_chars = 0

        for pattern in resolved:
            # Glob per supportare wildcards
            if "*" in pattern:
                matches = sorted(self.kb_dir.glob(pattern))
            else:
                target = self.kb_dir / pattern
                matches = [target] if target.exists() else []

            for page_path in matches:
                if not page_path.is_file():
                    continue
                if total_chars >= MAX_WIKI_CONTEXT_CHARS:
                    break

                content = page_path.read_text(encoding="utf-8")

                # Rimuovi YAML frontmatter per risparmiare token
                content = self._strip_frontmatter(content)

                # Tronca se necessario
                remaining = MAX_WIKI_CONTEXT_CHARS - total_chars
                if len(content) > remaining:
                    content = content[:remaining] + "\n\n[...troncato per limite contesto...]"

                rel_path = page_path.relative_to(self.kb_dir)
                pages.append({"path": str(rel_path), "content": content})
                total_chars += len(content)

        if not pages:
            logger.info(f"WikiReader: nessuna pagina trovata per {agent_name} / {club_slug}")
            return ""

        # Componi il contesto
        context_parts = [
            "## WIKI KNOWLEDGE BASE (Conoscenza Accumulata)\n",
            "Il sistema ha sintetizzato le seguenti informazioni da analisi precedenti. ",
            "Usa questi contenuti come base per generare output dettagliato e specifico.\n",
        ]

        for page in pages:
            context_parts.append(f"\n### [{page['path']}]\n")
            context_parts.append(page["content"])

        context = "\n".join(context_parts)
        logger.info(
            f"WikiReader: {agent_name} -> {len(pages)} pagine, {len(context):,} chars"
        )
        return context

    def get_club_raw_context(self, club_slug: str, max_chars: int = 20000) -> str:
        """
        Carica i documenti raw del club (per contesto aggiuntivo se Wiki non basta).
        """
        raw_club_dir = self.raw_dir / club_slug
        if not raw_club_dir.exists():
            return ""

        parts = []
        total = 0
        for md_file in sorted(raw_club_dir.glob("*.md")):
            if md_file.name == "intervista-board.md":
                continue  # Troppo grande, le singole sezioni bastano
            content = md_file.read_text(encoding="utf-8")
            remaining = max_chars - total
            if remaining <= 0:
                break
            if len(content) > remaining:
                content = content[:remaining]
            parts.append(content)
            total += len(content)

        return "\n\n---\n\n".join(parts) if parts else ""

    def list_clubs(self) -> List[str]:
        """Lista tutti i club ingeriti nel Wiki."""
        clubs_dir = self.kb_dir / "clubs"
        if not clubs_dir.exists():
            return []
        return [f.stem for f in clubs_dir.glob("*.md")]

    def has_club(self, club_slug: str) -> bool:
        """Verifica se un club e' stato ingerito."""
        return (self.kb_dir / "clubs" / f"{club_slug}.md").exists()

    def _strip_frontmatter(self, content: str) -> str:
        """Rimuove YAML frontmatter (---...---) dall'inizio del file."""
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                return content[end + 3:].strip()
        return content

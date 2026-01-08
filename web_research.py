"""
Rooting Future Strategy Engine v5.4
Web Research Module - Integrazione Serper.dev

Ricerca web per raccolta dati verificabili su club calcistici.
"""

import json
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import requests
import logging

from config import (
    SERPER_API_KEY,
    SOURCE_CONFIG,
    TRUSTED_SOURCES,
    SOURCE_WEIGHTS,
    KNOWLEDGE_DIR,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SearchResult:
    """Singolo risultato di ricerca"""
    title: str
    url: str
    snippet: str
    position: int
    is_trusted: bool = False
    trust_weight: float = 0.5
    date_extracted: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "position": self.position,
            "is_trusted": self.is_trusted,
            "trust_weight": self.trust_weight,
            "date_extracted": self.date_extracted,
        }


@dataclass
class ResearchResult:
    """Risultato completo di una ricerca"""
    query: str
    timestamp: str
    results: List[SearchResult] = field(default_factory=list)
    trusted_count: int = 0
    total_count: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "timestamp": self.timestamp,
            "results": [r.to_dict() for r in self.results],
            "trusted_count": self.trusted_count,
            "total_count": self.total_count,
            "error": self.error,
        }


# =============================================================================
# CACHE SYSTEM
# =============================================================================

class SearchCache:
    """Cache per risultati ricerca"""

    def __init__(self, cache_dir: Path = KNOWLEDGE_DIR / "search_cache"):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_hours = SOURCE_CONFIG.cache_ttl_hours

    def _get_cache_key(self, query: str) -> str:
        """Genera chiave cache da query"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()

    def get(self, query: str) -> Optional[ResearchResult]:
        """Recupera risultato dalla cache se valido"""
        if not SOURCE_CONFIG.cache_enabled:
            return None

        cache_key = self._get_cache_key(query)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Verifica TTL
            cached_time = datetime.fromisoformat(data["timestamp"])
            if datetime.now() - cached_time > timedelta(hours=self.ttl_hours):
                cache_file.unlink()  # Elimina cache scaduta
                return None

            # Ricostruisci oggetto
            results = [
                SearchResult(**r) for r in data.get("results", [])
            ]
            return ResearchResult(
                query=data["query"],
                timestamp=data["timestamp"],
                results=results,
                trusted_count=data.get("trusted_count", 0),
                total_count=data.get("total_count", 0),
            )
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None

    def set(self, result: ResearchResult) -> None:
        """Salva risultato in cache"""
        if not SOURCE_CONFIG.cache_enabled:
            return

        cache_key = self._get_cache_key(result.query)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Cache write error: {e}")


# =============================================================================
# WEB RESEARCHER
# =============================================================================

class WebResearcher:
    """
    Ricerca web via Serper.dev API.
    Specializzato per ricerche su calcio italiano.
    """

    SERPER_URL = "https://google.serper.dev/search"

    def __init__(self):
        self.api_key = SERPER_API_KEY
        self.cache = SearchCache()
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        })

    def search(
        self,
        query: str,
        num_results: int = 10,
        country: str = "it",
        language: str = "it",
        use_cache: bool = True
    ) -> ResearchResult:
        """
        Esegue ricerca web.

        Args:
            query: Stringa di ricerca
            num_results: Numero risultati (max 100)
            country: Codice paese (it = Italia)
            language: Lingua risultati
            use_cache: Se usare cache

        Returns:
            ResearchResult con lista risultati
        """
        # Check cache
        if use_cache:
            cached = self.cache.get(query)
            if cached:
                logger.info(f"Cache hit for: {query[:50]}...")
                return cached

        # Prepara richiesta
        payload = {
            "q": query,
            "gl": country,
            "hl": language,
            "num": min(num_results, SOURCE_CONFIG.max_search_results),
        }

        try:
            response = self.session.post(
                self.SERPER_URL,
                json=payload,
                timeout=SOURCE_CONFIG.search_timeout_seconds
            )
            response.raise_for_status()
            data = response.json()

            # Processa risultati
            results = []
            organic = data.get("organic", [])

            for i, item in enumerate(organic):
                url = item.get("link", "")
                is_trusted, weight = self._evaluate_source(url)

                result = SearchResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("snippet", ""),
                    position=i + 1,
                    is_trusted=is_trusted,
                    trust_weight=weight,
                    date_extracted=self._extract_date(item.get("snippet", "")),
                )
                results.append(result)

            research_result = ResearchResult(
                query=query,
                timestamp=datetime.now().isoformat(),
                results=results,
                trusted_count=sum(1 for r in results if r.is_trusted),
                total_count=len(results),
            )

            # Salva in cache
            self.cache.set(research_result)

            return research_result

        except requests.exceptions.Timeout:
            logger.error(f"Search timeout for: {query}")
            return ResearchResult(
                query=query,
                timestamp=datetime.now().isoformat(),
                error="Timeout nella ricerca"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Search error: {e}")
            return ResearchResult(
                query=query,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )

    def _evaluate_source(self, url: str) -> tuple[bool, float]:
        """
        Valuta affidabilità fonte.

        Returns:
            (is_trusted, weight)
        """
        url_lower = url.lower()

        for trusted_domain in TRUSTED_SOURCES:
            if trusted_domain in url_lower:
                weight = SOURCE_WEIGHTS.get(trusted_domain, SOURCE_WEIGHTS["default"])
                return True, weight

        return False, SOURCE_WEIGHTS["default"]

    def _extract_date(self, text: str) -> Optional[str]:
        """Estrae data dal testo se presente"""
        import re

        # Pattern comuni per date
        patterns = [
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+\d{4})",
            r"((?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+\d{4})",
            r"(\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1)

        return None

    # =========================================================================
    # RICERCHE SPECIALIZZATE PER CALCIO
    # =========================================================================

    def research_club(
        self,
        club_name: str,
        city: str = "",
        category: str = ""
    ) -> Dict[str, ResearchResult]:
        """
        Ricerca completa su un club calcistico.

        Returns:
            Dict con risultati per diverse categorie
        """
        base_query = f"{club_name} calcio"
        if city:
            base_query += f" {city}"

        queries = {
            "generale": base_query,
            "storia": f"{club_name} storia fondazione palmares",
            "settore_giovanile": f"{club_name} settore giovanile vivaio tesserati",
            "stadio": f"{club_name} stadio impianto capienza",
            "bilancio": f"{club_name} bilancio fatturato ricavi",
            "classifica": f"{club_name} classifica {datetime.now().year}",
            "rosa": f"{club_name} rosa giocatori {datetime.now().year}",
        }

        if category:
            queries["categoria"] = f"{category} {club_name} {datetime.now().year}"

        results = {}
        for key, query in queries.items():
            results[key] = self.search(query)
            time.sleep(0.5)  # Rate limiting gentile

        return results

    def research_competitors(
        self,
        competitors: List[str],
        region: str = ""
    ) -> Dict[str, ResearchResult]:
        """
        Ricerca su club competitor.

        Args:
            competitors: Lista nomi club
            region: Regione per contest
        """
        results = {}

        for club in competitors[:5]:  # Max 5 competitor
            query = f"{club} calcio {region} classifica statistiche"
            results[club] = self.search(query)
            time.sleep(0.5)

        return results

    def research_benchmark(
        self,
        metric: str,
        category: str
    ) -> ResearchResult:
        """
        Cerca benchmark di settore.

        Args:
            metric: es. "budget medio", "tesserati settore giovanile"
            category: es. "Serie D", "Promozione"
        """
        query = f"{metric} {category} calcio italiano statistiche ufficiali"
        return self.search(query)

    def research_regulations(
        self,
        topic: str,
        category: str = ""
    ) -> ResearchResult:
        """
        Cerca regolamenti e normative.

        Args:
            topic: es. "requisiti stadio", "licenze UEFA"
            category: Categoria di riferimento
        """
        query = f"regolamento FIGC {topic} {category} requisiti"
        return self.search(query)

    def get_latest_report_calcio(self) -> ResearchResult:
        """Cerca ultimo Report Calcio FIGC"""
        current_year = datetime.now().year
        query = f"Report Calcio FIGC {current_year} statistiche ufficiali"
        return self.search(query)

    # =========================================================================
    # VERIFICA DATI SPECIFICI
    # =========================================================================

    def verify_statistic(
        self,
        claim: str,
        context: str = ""
    ) -> ResearchResult:
        """
        Verifica una statistica specifica.

        Args:
            claim: es. "Il Riccione ha 450 tesserati"
            context: Contesto aggiuntivo
        """
        query = f"{claim} {context} fonte ufficiale".strip()
        return self.search(query, num_results=5)

    def find_official_source(
        self,
        data_type: str,
        entity: str
    ) -> Optional[SearchResult]:
        """
        Cerca fonte ufficiale per un dato.

        Args:
            data_type: es. "tesserati", "bilancio", "classifica"
            entity: es. nome club

        Returns:
            Primo risultato da fonte trusted, o None
        """
        query = f"{entity} {data_type} FIGC ufficiale"
        result = self.search(query, num_results=10)

        for r in result.results:
            if r.is_trusted:
                return r

        return None


# =============================================================================
# AGGREGATORE RICERCHE
# =============================================================================

class ResearchAggregator:
    """
    Aggrega e sintetizza risultati di multiple ricerche.
    """

    def __init__(self):
        self.researcher = WebResearcher()

    def comprehensive_club_research(
        self,
        club_name: str,
        city: str,
        category: str,
        competitors: List[str] = None,
        region: str = ""
    ) -> Dict[str, Any]:
        """
        Ricerca comprensiva per piano strategico.

        Returns:
            Dict con tutti i dati raccolti e statistiche
        """
        results = {
            "club": {},
            "competitors": {},
            "benchmarks": {},
            "regulations": {},
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "club_name": club_name,
                "category": category,
            }
        }

        # 1. Ricerca club principale
        logger.info(f"Researching club: {club_name}")
        results["club"] = {
            k: v.to_dict()
            for k, v in self.researcher.research_club(club_name, city, category).items()
        }

        # 2. Competitor analysis
        if competitors:
            logger.info(f"Researching competitors: {competitors}")
            results["competitors"] = {
                k: v.to_dict()
                for k, v in self.researcher.research_competitors(competitors, region).items()
            }

        # 3. Benchmark di categoria
        benchmark_queries = [
            ("budget_medio", f"budget medio {category}"),
            ("tesserati_sg", f"tesserati settore giovanile {category}"),
            ("stipendi", f"monte stipendi medio {category}"),
        ]

        for key, query in benchmark_queries:
            res = self.researcher.search(query)
            results["benchmarks"][key] = res.to_dict()

        # 4. Regolamenti rilevanti
        regulation_topics = ["licenze nazionali", "settore giovanile", "infrastrutture"]
        for topic in regulation_topics:
            res = self.researcher.research_regulations(topic, category)
            results["regulations"][topic] = res.to_dict()

        # 5. Statistiche aggregate
        results["metadata"]["total_searches"] = (
            len(results["club"]) +
            len(results["competitors"]) +
            len(results["benchmarks"]) +
            len(results["regulations"])
        )

        all_results = []
        for section in ["club", "competitors", "benchmarks", "regulations"]:
            for key, data in results.get(section, {}).items():
                if isinstance(data, dict) and "results" in data:
                    all_results.extend(data["results"])

        results["metadata"]["trusted_sources_found"] = sum(
            1 for r in all_results if r.get("is_trusted", False)
        )
        results["metadata"]["total_results"] = len(all_results)

        return results

    def export_research_report(
        self,
        research_data: Dict,
        output_path: Path = None
    ) -> Path:
        """
        Esporta ricerca in JSON per audit trail.
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            club_name = research_data.get("metadata", {}).get("club_name", "unknown")
            output_path = KNOWLEDGE_DIR / f"research_{club_name}_{timestamp}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(research_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Research exported to: {output_path}")
        return output_path

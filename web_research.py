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
from dataclasses import dataclass, field, asdict
import requests
import logging
import os

from config import (
    SERPER_API_KEY,
    TAVILY_API_KEY,
    SOURCE_CONFIG,
    TRUSTED_SOURCES,
    SOURCE_WEIGHTS,
    KNOWLEDGE_DIR,
)

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Singolo risultato di ricerca"""
    title: str
    url: str
    snippet: str
    source: str = "web"
    date: Optional[str] = None
    position: int = 0
    is_trusted: bool = False
    trust_weight: float = 0.5
    date_extracted: Optional[str] = None


@dataclass
class ResearchResult:
    """Insieme di risultati per una query"""
    query: str
    results: List[SearchResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None
    trusted_count: int = 0
    total_count: int = 0

    def to_dict(self) -> Dict:
        # Convert list of SearchResult objects to dicts manually to avoid recursion issues
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'ResearchResult':
        if "results" in data:
            results_list = []
            for r in data["results"]:
                if isinstance(r, dict):
                    # Gestione compatibilità nomi campi (weight vs trust_weight)
                    if 'weight' in r and 'trust_weight' not in r:
                        r['trust_weight'] = r.pop('weight')
                    results_list.append(SearchResult(**r))
                else:
                    results_list.append(r)
            data["results"] = results_list
        return cls(**data)


class SearchCache:
    """Cache su file system per ricerche web"""
    
    def __init__(self):
        self.cache_dir = KNOWLEDGE_DIR / "search_cache"
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
    def _get_path(self, query: str) -> Path:
        query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{query_hash}.json"

    def get(self, query: str) -> Optional[ResearchResult]:
        path = self._get_path(query)
        if not path.exists():
            return None
            
        try:
            # Check TTL
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            if datetime.now() - mtime > timedelta(hours=SOURCE_CONFIG.cache_ttl_hours):
                return None
                
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ResearchResult.from_dict(data)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None

    def set(self, result: ResearchResult):
        path = self._get_path(result.query)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Cache write error: {e}")


class WebResearcher:
    """
    Gestisce le ricerche web su Google usando Serper.dev o Tavily.
    Include meccaniche di caching, fallback e circuit breaker globale.
    """
    
    # CIRCUIT BREAKER GLOBALE (Condiviso tra tutte le istanze/agenti)
    _global_serper_disabled = False

    SERPER_URL = "https://google.serper.dev/search"
    TAVILY_URL = "https://api.tavily.com/search"

    def __init__(self):
        # Priorità a variabili d'ambiente dirette (per hot-reload .env)
        self.serper_key = os.environ.get("SERPER_API_KEY", SERPER_API_KEY)
        self.tavily_key = os.environ.get("TAVILY_API_KEY", TAVILY_API_KEY)
        self.cache = SearchCache()
        self.session = requests.Session()

    def search(
        self,
        query: str,
        num_results: int = 10,
        country: str = "it",
        language: str = "it",
        use_cache: bool = True,
    ) -> ResearchResult:
        """
        Esegue ricerca web con fallback automatico, circuit breaker e Virtual Gemini Fallback.
        """
        if use_cache:
            cached = self.cache.get(query)
            if cached:
                logger.info(f"Cache hit for: {query[:50]}...")
                return cached

        # Prova prima Serper (se non disabilitato globalmente)
        if self.serper_key and not WebResearcher._global_serper_disabled:
            try:
                result = self._search_serper(query, num_results, country, language)
                if not result.error:
                    return result
                logger.warning(f"Serper error (fallback): {result.error}")
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response else 0
                if status_code in [401, 403]:
                    if not WebResearcher._global_serper_disabled:
                        logger.error(f"⛔ Serper API Key Error ({status_code}). Circuit breaker ON.")
                    WebResearcher._global_serper_disabled = True
                else:
                    logger.error(f"Serper HTTP error: {e}")
            except Exception as e:
                logger.error(f"Serper generic exception: {e}")

        # Fallback su Tavily
        if self.tavily_key:
            try:
                result = self._search_tavily(query, num_results)
                if not result.error:
                    return result
            except Exception as e:
                logger.error(f"Tavily fallback failure: {e}")

        # ULTIMA SPIAGGIA: Segnaliamo che la ricerca esterna è fallita.
        # Gli agenti che hanno accesso a genai.Client() useranno il loro tool interno.
        logger.warning(f"⚠️ Tutti i motori di ricerca esterni falliti per: {query[:30]}")
        return ResearchResult(
            query=query, 
            timestamp=datetime.now().isoformat(), 
            error="EXTERNAL_SEARCH_FAILED"
        )
    def _search_serper(self, query, num_results, country, language) -> ResearchResult:
        """Logica originale Serper"""
        headers = {"X-API-KEY": self.serper_key, "Content-Type": "application/json"}
        payload = {"q": query, "gl": country, "hl": language, "num": min(num_results, 20)}
        
        response = self.session.post(self.SERPER_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for i, item in enumerate(data.get("organic", [])):
            url = item.get("link", "")
            is_trusted, weight = self._evaluate_source(url)
            results.append(SearchResult(
                title=item.get("title", ""),
                url=url,
                snippet=item.get("snippet", ""),
                position=i + 1,
                is_trusted=is_trusted,
                trust_weight=weight,
                date_extracted=self._extract_date(item.get("snippet", ""))
            ))

        res = ResearchResult(query=query, timestamp=datetime.now().isoformat(), results=results, 
                             trusted_count=sum(1 for r in results if r.is_trusted), total_count=len(results))
        self.cache.set(res)
        return res

    def _search_tavily(self, query, num_results) -> ResearchResult:
        """Integrazione Tavily AI Search"""
        logger.info(f"🔍 Tavily Search: {query}")
        payload = {
            "api_key": self.tavily_key,
            "query": query,
            "search_depth": "smart",
            "max_results": min(num_results, 10),
            "include_answer": False
        }
        
        try:
            response = self.session.post(self.TAVILY_URL, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()

            results = []
            for i, item in enumerate(data.get("results", [])):
                url = item.get("url", "")
                is_trusted, weight = self._evaluate_source(url)
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("content", ""),
                    position=i + 1,
                    is_trusted=is_trusted,
                    trust_weight=weight,
                    date_extracted=self._extract_date(item.get("content", ""))
                ))

            res = ResearchResult(query=query, timestamp=datetime.now().isoformat(), results=results, 
                                 trusted_count=sum(1 for r in results if r.is_trusted), total_count=len(results))
            self.cache.set(res)
            return res
        except Exception as e:
            logger.error(f"Tavily critical error: {e}")
            return ResearchResult(query=query, timestamp=datetime.now().isoformat(), error=str(e))


    def _evaluate_source(self, url: str) -> tuple[bool, float]:
        """
        Valuta affidabilità fonte.

        Returns:
            (is_trusted, weight)
        """
        url_lower = url.lower()

        for trusted_domain in TRUSTED_SOURCES:
            if trusted_domain in url_lower:
                weight = SOURCE_WEIGHTS.get(
                    trusted_domain, SOURCE_WEIGHTS.get("unknown", 0.8)
                )
                return True, weight

        return False, SOURCE_WEIGHTS.get("unknown", 0.8)

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
        self, club_name: str, city: str = "", category: str = ""
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
        self, competitors: List[str], region: str = ""
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

    def research_benchmark(self, metric: str, category: str) -> ResearchResult:
        """
        Cerca benchmark di settore.

        Args:
            metric: es. "budget medio", "tesserati settore giovanile"
            category: es. "Serie D", "Promozione"
        """
        query = f"{metric} {category} calcio italiano statistiche ufficiali"
        return self.search(query)

    def research_regulations(self, topic: str, category: str = "") -> ResearchResult:
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

    def verify_statistic(self, claim: str, context: str = "") -> ResearchResult:
        """
        Verifica una statistica specifica.

        Args:
            claim: es. "Il Riccione ha 450 tesserati"
            context: Contesto aggiuntivo
        """
        query = f"{claim} {context} fonte ufficiale".strip()
        return self.search(query, num_results=5)

    def find_official_source(
        self, data_type: str, entity: str
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
        region: str = "",
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
            },
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
                for k, v in self.researcher.research_competitors(
                    competitors, region
                ).items()
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
            len(results["club"])
            + len(results["competitors"])
            + len(results["benchmarks"])
            + len(results["regulations"])
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
        self, research_data: Dict, output_path: Path = None
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

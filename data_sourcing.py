"""
Rooting Future Strategy Engine v5.4
Data Sourcing & Verification Module

CRITICO: Ogni dato numerico deve avere fonte verificata.
- Nessun numero inventato
- Fonti sempre citate
- Stime chiaramente marcate
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import logging

from web_research import WebResearcher, SearchResult, ResearchResult
from config import (
    TRUSTED_SOURCES,
    SOURCE_CONFIG,
    SOURCE_WEIGHTS,
    BENCHMARKS,
    KNOWLEDGE_DIR,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS E DATA CLASSES
# =============================================================================

class SourceConfidence(Enum):
    """Livello di confidenza del dato"""
    VERIFIED = "verified"           # 2+ fonti autorevoli concordanti
    SINGLE_SOURCE = "single_source" # 1 fonte autorevole
    ESTIMATED = "estimated"         # Stima interna documentata
    UNVERIFIED = "unverified"       # Dato non verificabile
    CONFLICTING = "conflicting"     # Fonti discordanti
    BENCHMARK = "benchmark"         # Benchmark di settore (con fonte)


@dataclass
class Source:
    """Fonte singola per un dato"""
    name: str
    url: str
    snippet: str = ""
    date: Optional[str] = None
    is_trusted: bool = False
    trust_weight: float = 0.5

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "url": self.url,
            "snippet": self.snippet[:200] if self.snippet else "",
            "date": self.date,
            "is_trusted": self.is_trusted,
            "trust_weight": self.trust_weight,
        }


@dataclass
class SourcedData:
    """
    Dato con fonte e livello di confidenza.
    Questo è l'unità atomica di informazione verificata.
    """
    value: str
    description: str
    data_type: str = "generic"  # numeric, percentage, currency, text
    sources: List[Source] = field(default_factory=list)
    confidence: SourceConfidence = SourceConfidence.UNVERIFIED
    verification_date: str = ""
    notes: str = ""
    original_claim: str = ""
    discrepancy_notes: str = ""  # Se fonti discordanti

    def to_citation(self, format: str = "inline") -> str:
        """
        Genera citazione formattata.

        Args:
            format: "inline", "footnote", "full"
        """
        if format == "inline":
            if self.confidence == SourceConfidence.VERIFIED:
                source_names = [s.name for s in self.sources[:2]]
                return f"{self.value} (Fonti: {', '.join(source_names)})"
            elif self.confidence == SourceConfidence.SINGLE_SOURCE:
                return f"{self.value} (Fonte: {self.sources[0].name})"
            elif self.confidence == SourceConfidence.BENCHMARK:
                return f"{self.value} (Benchmark: {self.notes})"
            elif self.confidence == SourceConfidence.ESTIMATED:
                return f"{self.value} (stima interna)"
            else:
                return f"{self.value} (dato non verificato)"

        elif format == "footnote":
            if self.sources:
                urls = [s.url for s in self.sources[:2]]
                return f"{self.value}[^{','.join(urls)}]"
            return self.value

        else:  # full
            lines = [f"**{self.value}**"]
            lines.append(f"Confidenza: {self.confidence.value}")
            if self.sources:
                lines.append("Fonti:")
                for s in self.sources:
                    lines.append(f"  - {s.name}: {s.url}")
            if self.notes:
                lines.append(f"Note: {self.notes}")
            return "\n".join(lines)

    def to_dict(self) -> Dict:
        return {
            "value": self.value,
            "description": self.description,
            "data_type": self.data_type,
            "sources": [s.to_dict() for s in self.sources],
            "confidence": self.confidence.value,
            "verification_date": self.verification_date,
            "notes": self.notes,
            "original_claim": self.original_claim,
        }


# =============================================================================
# DATA SOURCER - Motore di verifica
# =============================================================================

class DataSourcer:
    """
    Verifica e attribuisce fonti ai dati.
    Core del sistema di credibilità.
    """

    def __init__(self):
        self.researcher = WebResearcher()
        self.cache: Dict[str, SourcedData] = {}
        self.verification_log: List[Dict] = []

    def verify_numeric_claim(
        self,
        claim: str,
        context: str = "",
        data_type: str = "numeric"
    ) -> SourcedData:
        """
        Verifica un'affermazione numerica cercando fonti.

        Args:
            claim: es. "Il settore giovanile ha 450 tesserati"
            context: es. "Riccione Calcio 1926"
            data_type: numeric, percentage, currency

        Returns:
            SourcedData con fonti e livello confidenza
        """
        # Estrai numeri dal claim
        numbers = re.findall(r'\d+(?:[.,]\d+)?(?:\s*%|\s*€)?', claim)
        if not numbers:
            return SourcedData(
                value=claim,
                description="Affermazione qualitativa",
                data_type="text",
                confidence=SourceConfidence.UNVERIFIED,
                original_claim=claim,
            )

        # Cache check
        cache_key = f"{claim}:{context}".lower().strip()
        if cache_key in self.cache:
            logger.debug(f"Cache hit for claim: {claim[:50]}")
            return self.cache[cache_key]

        # Cerca fonti
        search_query = f"{context} {claim}".strip() if context else claim
        try:
            research_result = self.researcher.search(search_query, num_results=10)
        except Exception as e:
            logger.error(f"Error during search execution: {e}")
            research_result = None

        if research_result is None or research_result.error:
            error_msg = research_result.error if research_result else "Ricerca fallita (Unknown Error)"
            return SourcedData(
                value=claim,
                description="Errore nella verifica",
                data_type=data_type,
                confidence=SourceConfidence.UNVERIFIED,
                original_claim=claim,
                notes=f"Errore ricerca: {error_msg}"
            )

        # Analizza risultati
        trusted_sources: List[Source] = []
        other_sources: List[Source] = []
        found_values: List[str] = []

        for result in research_result.results:
            # Cerca il numero nel snippet
            snippet = result.snippet
            has_number = any(n in snippet for n in numbers)

            if has_number or self._is_relevant_snippet(snippet, claim):
                source = Source(
                    name=self._extract_source_name(result.url),
                    url=result.url,
                    snippet=snippet,
                    date=result.date_extracted,
                    is_trusted=result.is_trusted,
                    trust_weight=result.trust_weight,
                )

                if result.is_trusted:
                    trusted_sources.append(source)
                else:
                    other_sources.append(source)

                # Estrai valori trovati per confronto
                snippet_numbers = re.findall(r'\d+(?:[.,]\d+)?', snippet)
                found_values.extend(snippet_numbers)

        # Determina confidenza
        all_sources = trusted_sources + other_sources
        confidence = self._determine_confidence(trusted_sources, other_sources, numbers, found_values)

        # Crea risultato
        result = SourcedData(
            value=claim,
            description=f"Verifica: {len(all_sources)} fonti analizzate",
            data_type=data_type,
            sources=all_sources[:5],  # Top 5
            confidence=confidence,
            verification_date=datetime.now().isoformat(),
            original_claim=claim,
        )

        # Check discrepanze
        if confidence == SourceConfidence.CONFLICTING:
            result.discrepancy_notes = f"Valori trovati nelle fonti: {', '.join(set(found_values[:5]))}"

        # Log verifica
        self._log_verification(claim, context, result)

        # Cache
        self.cache[cache_key] = result

        return result

    def _determine_confidence(
        self,
        trusted: List[Source],
        other: List[Source],
        claimed_numbers: List[str],
        found_numbers: List[str]
    ) -> SourceConfidence:
        """Determina livello di confidenza basato su fonti e concordanza"""

        # Normalizza numeri per confronto
        claimed_normalized = set(n.replace(".", "").replace(",", "") for n in claimed_numbers)
        found_normalized = set(n.replace(".", "").replace(",", "") for n in found_numbers)

        # Check concordanza
        numbers_match = bool(claimed_normalized & found_normalized)

        if len(trusted) >= 2 and numbers_match:
            return SourceConfidence.VERIFIED
        elif len(trusted) == 1 and numbers_match:
            return SourceConfidence.SINGLE_SOURCE
        elif len(trusted) >= 1 and not numbers_match and found_numbers:
            return SourceConfidence.CONFLICTING
        elif len(other) >= 2 and numbers_match:
            return SourceConfidence.SINGLE_SOURCE  # Downgrade rispetto a trusted
        elif len(other) >= 1:
            return SourceConfidence.UNVERIFIED
        else:
            return SourceConfidence.ESTIMATED

    def _is_relevant_snippet(self, snippet: str, claim: str) -> bool:
        """Valuta se snippet è rilevante per il claim"""
        claim_words = set(claim.lower().split())
        snippet_words = set(snippet.lower().split())

        # Rimuovi stop words
        stop_words = {"il", "la", "di", "da", "in", "con", "su", "per", "tra", "fra", "a", "e", "che", "è", "ha", "sono"}
        claim_words -= stop_words
        snippet_words -= stop_words

        # Almeno 30% di overlap
        if not claim_words:
            return False
        overlap = len(claim_words & snippet_words) / len(claim_words)
        return overlap >= 0.3

    def _extract_source_name(self, url: str) -> str:
        """Estrae nome leggibile da URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")

        # Mapping nomi noti
        names = {
            "figc.it": "FIGC",
            "reportcalcio.figc.it": "Report Calcio FIGC",
            "lega-pro.com": "Lega Pro",
            "legaseriea.it": "Lega Serie A",
            "legab.it": "Lega Serie B",
            "gazzetta.it": "Gazzetta dello Sport",
            "corrieredellosport.it": "Corriere dello Sport",
            "tuttosport.com": "Tuttosport",
            "transfermarkt.it": "Transfermarkt",
            "transfermarkt.com": "Transfermarkt",
            "istat.it": "ISTAT",
            "deloitte.com": "Deloitte",
            "kpmg.com": "KPMG",
            "uefa.com": "UEFA",
            "fifa.com": "FIFA",
            "fbref.com": "FBRef",
            "whoscored.com": "WhoScored",
        }

        return names.get(domain, domain.split(".")[0].capitalize())

    def _log_verification(self, claim: str, context: str, result: SourcedData):
        """Log verifica per audit"""
        self.verification_log.append({
            "timestamp": datetime.now().isoformat(),
            "claim": claim,
            "context": context,
            "confidence": result.confidence.value,
            "sources_found": len(result.sources),
            "trusted_sources": sum(1 for s in result.sources if s.is_trusted),
        })

    # =========================================================================
    # VERIFICA BENCHMARK
    # =========================================================================

    def get_benchmark(
        self,
        metric: str,
        category: str,
        verify_online: bool = True
    ) -> SourcedData:
        """
        Recupera benchmark di settore con fonte.

        Args:
            metric: es. "tesserati_settore_giovanile", "budget_medio"
            category: es. "Serie D", "Promozione"
            verify_online: Se verificare anche online

        Returns:
            SourcedData con benchmark e fonte
        """
        # Prima cerca nei benchmark preconfigurati
        local_benchmark = self._get_local_benchmark(metric, category)

        if local_benchmark and not verify_online:
            return local_benchmark

        # Verifica/aggiorna online
        query = f"{metric.replace('_', ' ')} {category} calcio italiano statistiche"
        research = self.researcher.search(query, num_results=5)

        if local_benchmark:
            # Aggiungi eventuali fonti online
            for result in research.results:
                if result.is_trusted:
                    local_benchmark.sources.append(Source(
                        name=self._extract_source_name(result.url),
                        url=result.url,
                        snippet=result.snippet,
                        is_trusted=True,
                        trust_weight=result.trust_weight,
                    ))
            return local_benchmark

        # Solo risultati online
        if research.results:
            trusted = [r for r in research.results if r.is_trusted]
            if trusted:
                return SourcedData(
                    value=trusted[0].snippet[:100],
                    description=f"Benchmark {metric} per {category}",
                    data_type="benchmark",
                    sources=[Source(
                        name=self._extract_source_name(r.url),
                        url=r.url,
                        snippet=r.snippet,
                        is_trusted=True,
                    ) for r in trusted[:2]],
                    confidence=SourceConfidence.SINGLE_SOURCE if len(trusted) == 1 else SourceConfidence.VERIFIED,
                    verification_date=datetime.now().isoformat(),
                )

        return SourcedData(
            value=f"Benchmark non disponibile per {metric}",
            description="Dati non trovati",
            confidence=SourceConfidence.UNVERIFIED,
            notes="Nessun benchmark trovato. Utilizzare stime conservative.",
        )

    def _get_local_benchmark(self, metric: str, category: str) -> Optional[SourcedData]:
        """Recupera benchmark da configurazione locale"""

        if metric == "tesserati_settore_giovanile":
            data = BENCHMARKS.settore_giovanile_media_tesserati.get(category)
            if data:
                return SourcedData(
                    value=f"{data['media']} (range: {data['range'][0]}-{data['range'][1]})",
                    description=f"Media tesserati settore giovanile {category}",
                    data_type="numeric",
                    confidence=SourceConfidence.BENCHMARK,
                    notes=data['fonte'],
                    sources=[Source(
                        name="Report Calcio FIGC",
                        url="https://www.figc.it/it/federazione/report-calcio/",
                        is_trusted=True,
                        trust_weight=1.0,
                    )]
                )

        elif metric == "budget_medio":
            data = BENCHMARKS.budget_medio_per_categoria.get(category)
            if data:
                return SourcedData(
                    value=f"€{data['media']:,}".replace(",", "."),
                    description=f"Budget medio {category}",
                    data_type="currency",
                    confidence=SourceConfidence.BENCHMARK,
                    notes=data['fonte'],
                    sources=[Source(
                        name=data['fonte'].split(",")[0],
                        url="https://www.figc.it/it/federazione/report-calcio/",
                        is_trusted=True,
                    )]
                )

        return None

    # =========================================================================
    # CONFRONTO CON BENCHMARK
    # =========================================================================

    def compare_to_benchmark(
        self,
        club_value: float,
        metric: str,
        category: str
    ) -> Dict[str, Any]:
        """
        Confronta valore club con benchmark di categoria.

        Returns:
            Dict con analisi discostamento e fonte benchmark
        """
        benchmark = self.get_benchmark(metric, category)

        if benchmark.confidence == SourceConfidence.UNVERIFIED:
            return {
                "comparison": "non_disponibile",
                "message": "Benchmark non disponibile per questa metrica/categoria",
                "benchmark": benchmark.to_dict(),
            }

        # Estrai valore numerico dal benchmark
        benchmark_match = re.search(r'(\d+(?:[.,]\d+)?)', benchmark.value)
        if not benchmark_match:
            return {
                "comparison": "errore_parsing",
                "message": "Impossibile estrarre valore numerico dal benchmark",
                "benchmark": benchmark.to_dict(),
            }

        benchmark_value = float(benchmark_match.group(1).replace(",", "."))

        # Calcola discostamento
        if benchmark_value == 0:
            discrepancy_pct = 0
        else:
            discrepancy_pct = ((club_value - benchmark_value) / benchmark_value) * 100

        # Determina posizionamento
        if discrepancy_pct > 20:
            position = "sopra_media"
            message = f"Il valore del club ({club_value}) è superiore del {discrepancy_pct:.1f}% rispetto alla media di categoria ({benchmark_value})"
        elif discrepancy_pct < -20:
            position = "sotto_media"
            message = f"Il valore del club ({club_value}) è inferiore del {abs(discrepancy_pct):.1f}% rispetto alla media di categoria ({benchmark_value})"
        else:
            position = "in_media"
            message = f"Il valore del club ({club_value}) è in linea con la media di categoria ({benchmark_value})"

        return {
            "comparison": position,
            "club_value": club_value,
            "benchmark_value": benchmark_value,
            "discrepancy_percentage": round(discrepancy_pct, 1),
            "message": message,
            "benchmark_source": benchmark.notes,
            "benchmark_confidence": benchmark.confidence.value,
            "benchmark": benchmark.to_dict(),
        }


# =============================================================================
# CONTENT PROCESSOR - Processa contenuto aggiungendo fonti
# =============================================================================

class SourcedContentGenerator:
    """
    Processa contenuto generato dagli agenti e:
    1. Identifica claim numerici
    2. Verifica con fonti
    3. Aggiunge citazioni
    4. Genera sezione fonti
    """

    def __init__(self):
        self.sourcer = DataSourcer()
        self.all_citations: List[SourcedData] = []
        self.unverified_claims: List[str] = []

    def process_content(
        self,
        content: str,
        context: str = ""
    ) -> Tuple[str, List[Dict], List[str]]:
        """
        Processa contenuto e aggiunge citazioni per dati numerici.

        Args:
            content: Testo da processare
            context: Contesto (es. nome club)

        Returns:
            (contenuto_processato, lista_fonti, claims_non_verificati)
        """
        # Pattern per claim numerici
        numeric_patterns = [
            (r'(\d+(?:\.\d+)?)\s*(tesserati|iscritti|atleti|giocatori|ragazzi)', 'numeric'),
            (r'(\d+(?:\.\d+)?)\s*(squadre|team|formazioni|gruppi)', 'numeric'),
            (r'(€?\s*\d+(?:[.,]\d+)?(?:\s*(?:mila|milioni|mln|k|M))?)\s*(budget|fatturato|ricavi|costi|spese)', 'currency'),
            (r'(\d+)\s*(campi|strutture|impianti|spogliatoi)', 'numeric'),
            (r'(\d+(?:[.,]\d+)?)\s*%', 'percentage'),
            (r'(\d+)\s*(anni|stagioni|edizioni)', 'numeric'),
            (r'(\d+)\s*(?:posti|spettatori|capienza)', 'numeric'),
        ]

        sources_used = []
        processed = content

        for pattern, data_type in numeric_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))

            for match in matches:
                claim = match.group(0)
                sourced = self.sourcer.verify_numeric_claim(claim, context, data_type)

                self.all_citations.append(sourced)

                if sourced.confidence in [SourceConfidence.VERIFIED, SourceConfidence.SINGLE_SOURCE]:
                    for source in sourced.sources:
                        sources_used.append(source.to_dict())
                elif sourced.confidence == SourceConfidence.UNVERIFIED:
                    self.unverified_claims.append(claim)

        # Deduplica fonti
        unique_sources = []
        seen_urls = set()
        for s in sources_used:
            url = s.get("url", "")
            if url and url not in seen_urls:
                unique_sources.append(s)
                seen_urls.add(url)

        return processed, unique_sources, self.unverified_claims

    def generate_sources_section(self, format: str = "markdown") -> str:
        """
        Genera sezione fonti per il documento.

        Args:
            format: "markdown", "html", "docx"
        """
        verified = [c for c in self.all_citations if c.confidence == SourceConfidence.VERIFIED]
        single = [c for c in self.all_citations if c.confidence == SourceConfidence.SINGLE_SOURCE]
        benchmark = [c for c in self.all_citations if c.confidence == SourceConfidence.BENCHMARK]
        estimated = [c for c in self.all_citations if c.confidence == SourceConfidence.ESTIMATED]
        unverified = [c for c in self.all_citations if c.confidence == SourceConfidence.UNVERIFIED]

        if format == "markdown":
            return self._generate_markdown_sources(verified, single, benchmark, estimated, unverified)
        elif format == "html":
            return self._generate_html_sources(verified, single, benchmark, estimated, unverified)
        else:
            return self._generate_markdown_sources(verified, single, benchmark, estimated, unverified)

    def _generate_markdown_sources(
        self,
        verified: List[SourcedData],
        single: List[SourcedData],
        benchmark: List[SourcedData],
        estimated: List[SourcedData],
        unverified: List[SourcedData]
    ) -> str:
        sections = ["## Fonti e Riferimenti\n"]

        if verified:
            sections.append("### Dati Verificati (2+ fonti autorevoli)")
            for c in verified[:15]:
                sources_str = ", ".join([s.name for s in c.sources[:2]])
                sections.append(f"- **{c.value}** — Fonti: {sources_str}")

        if single:
            sections.append("\n### Dati con Fonte Singola")
            for c in single[:15]:
                source = c.sources[0].name if c.sources else "N/A"
                sections.append(f"- {c.value} — Fonte: {source}")

        if benchmark:
            sections.append("\n### Benchmark di Settore")
            for c in benchmark[:10]:
                sections.append(f"- {c.description}: {c.value}")
                if c.notes:
                    sections.append(f"  - Fonte: {c.notes}")

        if estimated:
            sections.append("\n### Stime Interne")
            sections.append("*I seguenti dati sono stime interne e richiedono verifica:*")
            for c in estimated[:10]:
                sections.append(f"- {c.value}")

        if unverified:
            sections.append("\n### Dati da Verificare")
            sections.append("*I seguenti dati non hanno trovato conferma in fonti esterne:*")
            for c in unverified[:10]:
                sections.append(f"- {c.value}")

        # Disclaimer
        sections.append("\n---")
        sections.append("*Nota: I dati sono stati verificati alla data di generazione del documento. ")
        sections.append("Per informazioni aggiornate, verificare direttamente le fonti citate.*")

        return "\n".join(sections)

    def _generate_html_sources(
        self,
        verified: List[SourcedData],
        single: List[SourcedData],
        benchmark: List[SourcedData],
        estimated: List[SourcedData],
        unverified: List[SourcedData]
    ) -> str:
        html = ['<section class="sources-section">', '<h2>Fonti e Riferimenti</h2>']

        if verified:
            html.append('<div class="source-group verified">')
            html.append('<h3>Dati Verificati (2+ fonti autorevoli)</h3><ul>')
            for c in verified[:15]:
                sources_str = ", ".join([s.name for s in c.sources[:2]])
                html.append(f'<li><strong>{c.value}</strong> — Fonti: {sources_str}</li>')
            html.append('</ul></div>')

        if single:
            html.append('<div class="source-group single">')
            html.append('<h3>Dati con Fonte Singola</h3><ul>')
            for c in single[:15]:
                source = c.sources[0] if c.sources else None
                if source:
                    html.append(f'<li>{c.value} — <a href="{source.url}" target="_blank">{source.name}</a></li>')
                else:
                    html.append(f'<li>{c.value}</li>')
            html.append('</ul></div>')

        if benchmark:
            html.append('<div class="source-group benchmark">')
            html.append('<h3>Benchmark di Settore</h3><ul>')
            for c in benchmark[:10]:
                html.append(f'<li>{c.description}: {c.value}<br><small>Fonte: {c.notes}</small></li>')
            html.append('</ul></div>')

        if estimated or unverified:
            html.append('<div class="source-group warning">')
            html.append('<h3>Dati da Verificare</h3>')
            html.append('<p class="warning-text">I seguenti dati sono stime o non hanno trovato conferma esterna:</p><ul>')
            for c in (estimated + unverified)[:10]:
                html.append(f'<li>{c.value}</li>')
            html.append('</ul></div>')

        html.append('<p class="disclaimer">I dati sono stati verificati alla data di generazione. ')
        html.append('Per informazioni aggiornate, verificare le fonti citate.</p>')
        html.append('</section>')

        return "\n".join(html)

    def get_verification_summary(self) -> Dict[str, Any]:
        """Restituisce sommario verifica dati"""
        total = len(self.all_citations)
        if total == 0:
            return {"total": 0, "verified_percentage": 0}

        verified = sum(1 for c in self.all_citations if c.confidence == SourceConfidence.VERIFIED)
        single = sum(1 for c in self.all_citations if c.confidence == SourceConfidence.SINGLE_SOURCE)
        benchmark = sum(1 for c in self.all_citations if c.confidence == SourceConfidence.BENCHMARK)
        estimated = sum(1 for c in self.all_citations if c.confidence == SourceConfidence.ESTIMATED)
        unverified = sum(1 for c in self.all_citations if c.confidence == SourceConfidence.UNVERIFIED)

        verified_pct = ((verified + single + benchmark) / total) * 100 if total > 0 else 0

        return {
            "total_claims": total,
            "verified": verified,
            "single_source": single,
            "benchmark": benchmark,
            "estimated": estimated,
            "unverified": unverified,
            "verified_percentage": round(verified_pct, 1),
            "credibility_score": self._calculate_credibility_score(),
        }

    def _calculate_credibility_score(self) -> float:
        """
        Calcola punteggio credibilità documento (0-100).
        Pesi:
        - Verified: 100%
        - Single source: 80%
        - Benchmark: 90%
        - Estimated: 40%
        - Unverified: 0%
        """
        if not self.all_citations:
            return 0

        weights = {
            SourceConfidence.VERIFIED: 1.0,
            SourceConfidence.SINGLE_SOURCE: 0.8,
            SourceConfidence.BENCHMARK: 0.9,
            SourceConfidence.ESTIMATED: 0.4,
            SourceConfidence.UNVERIFIED: 0.0,
            SourceConfidence.CONFLICTING: 0.3,
        }

        total_weight = sum(weights.get(c.confidence, 0) for c in self.all_citations)
        max_weight = len(self.all_citations) * 1.0

        return round((total_weight / max_weight) * 100, 1) if max_weight > 0 else 0

    def export_verification_log(self, output_path: Path = None) -> Path:
        """Esporta log verifiche per audit"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = KNOWLEDGE_DIR / f"verification_log_{timestamp}.json"

        log_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_verification_summary(),
            "citations": [c.to_dict() for c in self.all_citations],
            "unverified_claims": self.unverified_claims,
            "sourcer_log": self.sourcer.verification_log,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        return output_path

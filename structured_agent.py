"""
Structured Agent per Rooting Future Strategy Engine v5.4

Agenti che generano output JSON strutturato invece di markdown.
Ogni dato ha fonte, benchmark e livello di confidenza.
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError as e:
    logging.error(f"GENAI IMPORT ERROR (structured): {e}")
    GENAI_AVAILABLE = False
    genai = None
except Exception as e:
    logging.error(f"GENAI UNEXPECTED ERROR (structured): {e}")
    GENAI_AVAILABLE = False
    genai = None

from config import (
    GEMINI_API_KEY,
    MODEL_CONFIG,
    KNOWLEDGE_DIR,
    OUTPUT_DIR,
)

from data_models import (
    DataPoint, StructuredSection, StructuredPlan,
    DataType, ConfidenceLevel, DeviationType,
    Source, SourceType, Benchmark, BenchmarkDatabase
)

logger = logging.getLogger(__name__)


# =============================================================================
# SECTION TEMPLATES
# =============================================================================

# Template dei data points richiesti per ogni sezione
SECTION_DATA_TEMPLATES = {
    "financial": {
        "title": "Piano Economico-Finanziario",
        "data_points": [
            {"id": "fin_fatturato", "label": "Fatturato Annuo", "domain": "financial", "metric": "fatturato_medio", "unit": "EUR"},
            {"id": "fin_monte_ingaggi", "label": "Monte Ingaggi", "domain": "financial", "metric": "monte_ingaggi_medio", "unit": "EUR"},
            {"id": "fin_patrimonio", "label": "Patrimonio Netto", "domain": "financial", "metric": "patrimonio_netto_medio", "unit": "EUR"},
            {"id": "fin_costo_rosa", "label": "Costo Rosa", "domain": "financial", "metric": "costo_rosa_medio", "unit": "EUR"},
        ]
    },
    "technical_sporting": {
        "title": "Area Tecnico-Sportiva",
        "data_points": [
            {"id": "spo_rosa_size", "label": "Dimensione Rosa", "domain": "sporting", "metric": "dimensione_rosa", "unit": "giocatori"},
            {"id": "spo_eta_media", "label": "Eta Media Rosa", "domain": "sporting", "metric": "eta_media_rosa", "unit": "anni"},
            {"id": "spo_stranieri", "label": "Percentuale Stranieri", "domain": "sporting", "metric": "stranieri_percentuale", "unit": "%"},
            {"id": "spo_vivaio", "label": "Percentuale Vivaio", "domain": "sporting", "metric": "vivaio_percentuale", "unit": "%"},
        ]
    },
    "youth_development": {
        "title": "Sviluppo Settore Giovanile",
        "data_points": [
            {"id": "you_tesserati", "label": "Tesserati Giovanili", "domain": "youth", "metric": "tesserati_giovanili", "unit": "atleti"},
            {"id": "you_squadre", "label": "Numero Squadre Giovanili", "domain": "youth", "metric": "squadre_giovanili", "unit": "squadre"},
            {"id": "you_ratio_coach", "label": "Rapporto Allenatori/10 Atleti", "domain": "youth", "metric": "rapporto_allenatori", "unit": "ratio"},
        ]
    },
    "infrastructure": {
        "title": "Infrastrutture",
        "data_points": [
            {"id": "inf_capienza", "label": "Capienza Stadio", "domain": "infrastructure", "metric": "capienza_stadio", "unit": "posti"},
            {"id": "inf_campi", "label": "Campi Allenamento", "domain": "infrastructure", "metric": "campi_allenamento", "unit": "campi"},
        ]
    },
    "marketing_commercial": {
        "title": "Marketing e Commerciale",
        "data_points": [
            {"id": "mkt_abbonati", "label": "Numero Abbonati", "domain": "marketing", "metric": "abbonati", "unit": "abbonati"},
            {"id": "mkt_social", "label": "Follower Social (totali)", "domain": "marketing", "metric": "social_followers", "unit": "followers"},
            {"id": "mkt_sponsor", "label": "Ricavi Sponsorizzazioni", "domain": "marketing", "metric": "ricavi_sponsor", "unit": "EUR"},
        ]
    },
    "governance": {
        "title": "Governance e Organizzazione",
        "data_points": [
            {"id": "gov_dipendenti", "label": "Dipendenti Full-Time", "domain": "governance", "metric": "dipendenti", "unit": "FTE"},
            {"id": "gov_cda_members", "label": "Membri CdA", "domain": "governance", "metric": "membri_cda", "unit": "membri"},
        ]
    },
    "social_sustainability": {
        "title": "Sostenibilita Sociale",
        "data_points": [
            {"id": "soc_progetti", "label": "Progetti Sociali Attivi", "domain": "social", "metric": "progetti_sociali", "unit": "progetti"},
            {"id": "soc_beneficiari", "label": "Beneficiari Annui", "domain": "social", "metric": "beneficiari", "unit": "persone"},
        ]
    }
}


# =============================================================================
# STRUCTURED AGENT
# =============================================================================

class StructuredAgent:
    """
    Agente che genera output JSON strutturato.
    Ogni affermazione e accompagnata da fonte, benchmark e confidenza.
    """

    def __init__(self, section_key: str, api_key: str = None, file_search_store_name: str = None):
        self.section_key = section_key
        self.template = SECTION_DATA_TEMPLATES.get(section_key, {})
        self.file_search_store_name = file_search_store_name
        self.model = None

        # Setup Gemini con google-generativeai
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if GENAI_AVAILABLE and api_key:
            try:
                genai.configure(api_key=api_key)
                # Inizializza il modello senza tool di ricerca Google
                # (l'API non supporta più google_search come tool)
                self.model = genai.GenerativeModel(MODEL_CONFIG.name)
                self.available = True
            except Exception as e:
                logger.error(f"Errore inizializzazione StructuredAgent: {e}")
                self.available = False
        else:
            self.available = False
            logger.warning("No Gemini API key or genai not available - agent will use mock data")

    def generate(
        self,
        club_data: Dict,
        research_data: Dict = None,
        rag_context: List[Any] = None
    ) -> StructuredSection:
        """
        Genera sezione strutturata.
        """
        category = club_data.get('category', 'Serie C')

        # Crea data points con benchmark
        data_points = self._create_data_points_with_benchmarks(
            club_data,
            research_data,
            category
        )

        # Genera analisi testuale con Gemini
        summary, findings, recommendations = self._generate_analysis(
            club_data,
            research_data,
            data_points,
            rag_context=rag_context
        )

        # Costruisci sezione
        section = StructuredSection(
            section_id=self.section_key,
            title=self.template.get('title', self.section_key),
            summary=summary,
            key_findings=findings,
            data_points=data_points,
            recommendations=recommendations
        )

        return section

    def _create_data_points_with_benchmarks(
        self,
        club_data: Dict,
        research_data: Dict,
        category: str
    ) -> List[DataPoint]:
        """
        Crea data points dal template con benchmark automatici.
        Cerca i valori nei dati club e research.
        """
        data_points = []

        for dp_template in self.template.get('data_points', []):
            # Cerca valore nei dati
            value, source, confidence, data_type = self._find_value(
                dp_template['id'],
                dp_template['label'],
                club_data,
                research_data
            )

            # Crea data point con benchmark
            dp = BenchmarkDatabase.create_data_point_with_benchmark(
                id=dp_template['id'],
                label=dp_template['label'],
                value=value,
                unit=dp_template.get('unit', ''),
                category=category,
                domain=dp_template['domain'],
                metric=dp_template['metric'],
                source=source,
                data_type=data_type,
                confidence=confidence
            )

            data_points.append(dp)

        return data_points

    def _find_value(
        self,
        dp_id: str,
        label: str,
        club_data: Dict,
        research_data: Dict
    ) -> Tuple[Any, Optional[Source], float, DataType]:
        """
        Cerca il valore di un data point nei dati disponibili.
        Restituisce (valore, fonte, confidenza, tipo).
        """
        # Mappa ID a chiavi nei dati club
        club_mappings = {
            'fin_fatturato': 'revenue',
            'fin_monte_ingaggi': 'wage_bill',
            'fin_patrimonio': 'net_assets',
            'fin_costo_rosa': 'squad_cost',
            'spo_rosa_size': 'squad_size',
            'spo_eta_media': 'average_age',
            'you_tesserati': 'youth_players',
            'you_squadre': 'youth_teams',
            'inf_capienza': 'stadium_capacity',
            'inf_campi': 'training_fields',
            'mkt_abbonati': 'season_tickets',
            'mkt_social': 'social_followers',
        }

        # Cerca nei dati club
        if dp_id in club_mappings:
            key = club_mappings[dp_id]
            if key in club_data and club_data[key]:
                # Determina tipo fonte (default CLUB, ma QUESTIONNAIRE se flagged)
                s_type = SourceType.CLUB
                s_name = "Dati forniti dal club"
                
                if club_data.get(f"{key}_source") == "questionnaire" or club_data.get("source") == "docx_upload":
                    s_type = SourceType.QUESTIONNAIRE
                    s_name = "Questionario Club"

                return (
                    club_data[key],
                    Source(
                        type=s_type,
                        name=s_name,
                        reference=f"Campo: {key}"
                    ),
                    90.0 if s_type == SourceType.QUESTIONNAIRE else 70.0,  # Confidenza più alta se da questionario ufficiale
                    DataType.VERIFIED if club_data.get(f'{key}_verified') or s_type == SourceType.QUESTIONNAIRE else DataType.ESTIMATE
                )

        # Cerca nei dati di ricerca web
        if research_data:
            extracted = self._extract_from_research(label, research_data)
            if extracted:
                value, source_text = extracted
                return (
                    value,
                    Source(
                        type=SourceType.RESEARCH,
                        name="Ricerca Web",
                        reference=source_text[:100]
                    ),
                    50.0,  # Confidenza bassa per dati da ricerca
                    DataType.ESTIMATE
                )

        # Nessun dato trovato
        return (None, None, 0.0, DataType.TO_ACQUIRE)

    def _extract_from_research(
        self,
        label: str,
        research_data: Dict
    ) -> Optional[Tuple[Any, str]]:
        """
        Estrae valore dalla ricerca web usando pattern matching.
        """
        # Pattern per numeri con contesto
        patterns = {
            'fatturato': r'fatturato[:\s]+(?:€|EUR)?\s*([\d.,]+)\s*(?:mln|milioni|M)?',
            'capienza': r'capienza[:\s]+([\d.,]+)\s*(?:posti|spettatori)?',
            'tesserati': r'tesserati[:\s]+([\d.,]+)',
            'abbonati': r'abbonati[:\s]+([\d.,]+)',
            'stadio': r'stadio.*?([\d.,]+)\s*(?:posti)?',
        }

        for key, results in research_data.items():
            if not isinstance(results, dict) or 'results' not in results:
                continue

            for result in results.get('results', []):
                snippet = result.get('snippet', '')

                for pattern_key, pattern in patterns.items():
                    if pattern_key.lower() in label.lower():
                        match = re.search(pattern, snippet, re.IGNORECASE)
                        if match:
                            try:
                                value_str = match.group(1).replace('.', '').replace(',', '.')
                                value = float(value_str)
                                return (value, snippet)
                            except:
                                pass

        return None

    def _generate_analysis(
        self,
        club_data: Dict,
        research_data: Dict,
        data_points: List[DataPoint],
        rag_context: List[Any] = None
    ) -> Tuple[str, List[str], List[Dict]]:
        """
        Genera analisi testuale con Gemini.
        """
        if not self.model:
            return self._generate_mock_analysis(data_points)

        # Prepara contesto per il prompt
        dp_context = self._format_data_points_for_prompt(data_points)
        category = club_data.get('category', 'Serie C')
        club_name = club_data.get('club_name', 'Club')

        # === RAG CONTEXT (BEST PRACTICES) ===
        rag_info = ""
        if rag_context:
            rag_info = "\n--- \n## 🧠 MEMORIA STORICA E BEST PRACTICE (RAG)\n"
            rag_info += "Il sistema ha recuperato i seguenti esempi da piani di successo simili per questa sezione. "
            rag_info += "Usa questi contenuti come ispirazione per tono, struttura e qualità, ma ADATTA rigorosamente al club attuale.\n\n"
            
            for idx, doc in enumerate(rag_context[:2]): # Max 2 docs
                content = doc.content if hasattr(doc, 'content') else doc.get('content', '')
                club = doc.club_name if hasattr(doc, 'club_name') else doc.get('club_name', 'Altro Club')
                preview = content[:1500] + "..." if len(content) > 1500 else content
                rag_info += f"**ESEMPIO {idx+1} (da {club}):**\n{preview}\n\n"
            
            rag_info += "---\n"

        prompt = f'''Sei un consulente strategico senior specializzato in societa calcistiche.

{rag_info}

Analizza i seguenti dati per la sezione "{self.template.get('title')}" del piano strategico di {club_name} ({category}).

DATI DISPONIBILI:
{dp_context}

ISTRUZIONI:
1. Genera un SUMMARY (2-3 frasi) che sintetizza la situazione attuale basandoti SOLO sui dati disponibili
2. Identifica 3-5 KEY FINDINGS (evidenze chiave) derivate direttamente dai dati
3. Formula 2-3 RACCOMANDAZIONI strategiche prioritizzate

FORMATO OUTPUT (JSON):
{{
    "summary": "Testo del summary...",
    "key_findings": [
        "Finding 1 basato su dati specifici",
        "Finding 2 basato su dati specifici",
        ...
    ],
    "recommendations": [
        {{
            "title": "Titolo raccomandazione",
            "description": "Descrizione dettagliata",
            "priority": "high|medium|low",
            "impact": "Alto|Medio|Basso",
            "timeline": "es. 6-12 mesi",
            "investment_type": "Strategico|Quick Win|Operativo"
        }}
    ]
}}

REGOLE CRITICHE:
- Cita SEMPRE i numeri specifici quando disponibili
- Evidenzia SEMPRE lo scostamento dal benchmark
- Se un dato e "da acquisire", indicalo come gap informativo
- NON inventare dati - usa SOLO quelli forniti
- Rispondi SOLO con il JSON, senza testo aggiuntivo
'''

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.3)
            )
            text = response.text.strip()

            # Estrai JSON dalla risposta
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                result = json.loads(json_match.group())
                return (
                    result.get('summary', ''),
                    result.get('key_findings', []),
                    result.get('recommendations', [])
                )
        except Exception as e:
            # Fallback: Se la generazione con strumenti fallisce, riprova senza
            logger.warning(f"Errore generazione analisi con tool ({type(e).__name__}: {e}). Riprova senza tool...")
            try:
                # Riprova SENZA tools
                fallback_model = genai.GenerativeModel(MODEL_CONFIG.name) # No tools
                response = fallback_model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(temperature=0.3)
                )
                text = response.text.strip()

                # Estrai JSON dalla risposta
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    result = json.loads(json_match.group())
                    return (
                        result.get('summary', ''),
                        result.get('key_findings', []),
                        result.get('recommendations', [])
                    )
            except Exception as fallback_e:
                logger.error(f"Fallback generation failed: {fallback_e}")
                return self._generate_mock_analysis(data_points)

        return self._generate_mock_analysis(data_points)

    def _format_data_points_for_prompt(self, data_points: List[DataPoint]) -> str:
        """Formatta data points per il prompt"""
        lines = []
        for dp in data_points:
            line = f"- {dp.label}: "
            if dp.value is not None:
                line += f"{dp.formatted_value}"
                if dp.benchmark:
                    line += f" (Benchmark {dp.benchmark.category}: {dp.benchmark.value})"
                    if dp.deviation is not None:
                        line += f" [Scostamento: {dp.deviation:+.1f}%]"
                if dp.source:
                    line += f" - Fonte: {dp.source.name}"
                line += f" - Confidenza: {dp.confidence:.0f}%"
            else:
                line += "(DATO DA ACQUISIRE)"
                if dp.benchmark:
                    line += f" - Benchmark {dp.benchmark.category}: {dp.benchmark.value}"
            lines.append(line)
        return "\n".join(lines)

    def _generate_mock_analysis(
        self,
        data_points: List[DataPoint]
    ) -> Tuple[str, List[str], List[Dict]]:
        """Genera analisi di fallback senza AI"""
        # Conta dati mancanti
        missing = [dp for dp in data_points if dp.value is None]
        available = [dp for dp in data_points if dp.value is not None]
        critical = [dp for dp in available if dp.deviation_type == DeviationType.CRITICAL]

        summary = f"Analisi basata su {len(available)}/{len(data_points)} indicatori disponibili. "
        if missing:
            summary += f"Sono necessari {len(missing)} dati aggiuntivi per completare la valutazione. "
        if critical:
            summary += f"Identificati {len(critical)} scostamenti critici rispetto ai benchmark di categoria."

        findings = []
        for dp in available:
            if dp.deviation is not None and dp.benchmark:
                findings.append(
                    f"{dp.label}: {dp.formatted_value} ({dp.deviation:+.1f}% vs benchmark {dp.benchmark.category})"
                )

        for dp in missing:
            findings.append(f"{dp.label}: dato da acquisire per valutazione completa")

        recommendations = []
        if critical:
            recommendations.append({
                "title": "Intervento urgente sugli indicatori critici",
                "description": f"Sono stati identificati {len(critical)} indicatori con scostamento critico dal benchmark. Prioritizzare azioni correttive.",
                "priority": "high",
                "impact": "Alto",
                "timeline": "0-6 mesi",
                "investment_type": "Strategico"
            })

        if missing:
            recommendations.append({
                "title": "Completamento raccolta dati",
                "description": f"Acquisire i {len(missing)} dati mancanti per una valutazione completa e accurata.",
                "priority": "high",
                "impact": "Medio",
                "timeline": "1-3 mesi",
                "investment_type": "Quick Win"
            })

        return (summary, findings[:5], recommendations[:3])


# =============================================================================
# STRUCTURED ORCHESTRATOR
# =============================================================================

class StructuredOrchestrator:
    """
    Orchestratore per generazione piano strutturato.
    Coordina tutti gli agenti e assembla il piano finale.
    """

    def __init__(self, api_key: str = None, file_search_store_name: str = None, knowledge_store: Any = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.file_search_store_name = file_search_store_name
        self.knowledge_store = knowledge_store
        self.agents = {}
        self._init_agents()

    def _init_agents(self):
        """Inizializza tutti gli agenti"""
        for section_key in SECTION_DATA_TEMPLATES.keys():
            self.agents[section_key] = StructuredAgent(
                section_key, 
                self.api_key,
                file_search_store_name=self.file_search_store_name
            )
        logger.info(f"Initialized {len(self.agents)} structured agents (RAG enabled: {bool(self.file_search_store_name)})")

    def generate_plan(
        self,
        club_data: Dict,
        research_data: Dict = None
    ) -> StructuredPlan:
        """
        Genera piano strutturato completo.
        """
        plan = StructuredPlan(
            plan_id=f"plan_{club_data.get('club_name', 'unknown').replace(' ', '_')}_{self._timestamp()}",
            club_name=club_data.get('club_name', 'Club'),
            category=club_data.get('category', 'Serie C')
        )

        # Genera ogni sezione
        for section_key, agent in self.agents.items():
            try:
                # --- RAG CONTEXT FETCHING ---
                rag_context = []
                if self.knowledge_store:
                    try:
                        category = club_data.get('category', 'Serie C')
                        # Usa la chiave sezione come filtro
                        rag_context = self.knowledge_store.get_context_for_generation(
                            club_category=category,
                            section_type=section_key
                        )
                    except Exception as e:
                        logger.warning(f"RAG fetch failed for structured section {section_key}: {e}")
                
                section = agent.generate(club_data, research_data, rag_context=rag_context)
                plan.add_section(section)
                logger.info(f"Generated section: {section_key}")
            except Exception as e:
                logger.error(f"Error generating section {section_key}: {e}")

        # Genera executive summary
        plan.executive_summary = self._generate_executive_summary(plan)

        return plan

    def _generate_executive_summary(self, plan: StructuredPlan) -> str:
        """Genera executive summary aggregato"""
        total = plan.total_data_points
        verified = plan.verified_data_points
        missing = plan.missing_data_points
        credibility = plan.overall_credibility

        critical_items = []
        for section in plan.sections.values():
            for dp in section.data_points:
                if dp.deviation_type == DeviationType.CRITICAL:
                    critical_items.append(f"{dp.label} ({dp.deviation:+.1f}%)")

        summary = f"Piano strategico triennale per {plan.club_name} ({plan.category}). "
        summary += f"L'analisi si basa su {verified}/{total} indicatori verificati "
        summary += f"con una credibilita complessiva del {credibility:.0f}%. "

        if missing > 0:
            summary += f"Sono necessari {missing} dati aggiuntivi per completare la valutazione. "

        if critical_items:
            summary += f"Attenzione: {len(critical_items)} indicatori presentano scostamenti critici "
            summary += f"rispetto ai benchmark di categoria: {', '.join(critical_items[:3])}."

        return summary

    def _timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d%H%M%S")


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)

    club_data = {
        "club_name": "Rimini FC",
        "category": "Serie C",
        "city": "Rimini",
        "region": "Emilia-Romagna",
        "revenue": 586424,
        "stadium_capacity": 12200,
        "squad_size": 24,
        "average_age": 25.2
    }

    orchestrator = StructuredOrchestrator()
    plan = orchestrator.generate_plan(club_data)

    # Render
    from domain.rendering import PlanRenderer
    renderer = PlanRenderer()
    filepath = renderer.render_structured(plan)
    print(f"Piano generato: {filepath}")
    print(f"Credibilita: {plan.overall_credibility:.1f}%")
    print(f"Data points: {plan.total_data_points} (verified: {plan.verified_data_points})")

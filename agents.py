"""
Rooting Future Strategy Engine v5.4
Sistema Multi-Agente - 8 Agenti Specializzati

Architettura ispirata a metodologia consulenziale STW.
Ogni agente è esperto di un'area strategica specifica.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Tuple
from enum import Enum
from datetime import datetime
import logging
import asyncio
import json
import re

import os
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

from config import (
    GEMINI_API_KEY,
    MODEL_CONFIG,
    AGENT_CONFIG,
    BENCHMARKS,
)
from data_sourcing import SourcedContentGenerator, DataSourcer
from data_estimator import estimate_missing_financials, DataTier

logger = logging.getLogger(__name__)


# =============================================================================
# AGENT ROLES
# =============================================================================

class AgentRole(Enum):
    """Ruoli degli agenti specializzati"""
    COORDINATOR = "coordinator"
    TECHNICAL_SPORTING = "technical_sporting"
    YOUTH_DEVELOPMENT = "youth_development"
    INFRASTRUCTURE = "infrastructure"
    MARKETING_COMMERCIAL = "marketing_commercial"
    SOCIAL_SUSTAINABILITY = "social_sustainability"
    GOVERNANCE = "governance"
    FINANCIAL = "financial"


# =============================================================================
# AGENT CONFIG
# =============================================================================

@dataclass
class AgentSpec:
    """Specifica di un agente"""
    role: AgentRole
    name: str
    expertise: List[str]
    system_prompt: str
    output_sections: List[str] = field(default_factory=list)
    priority: int = 1  # Per ordinamento esecuzione


# =============================================================================
# GLOBAL VOICE DIRECTIVE - Impersonal Club Voice
# =============================================================================

GLOBAL_VOICE_DIRECTIVE = """
---
## DIRETTIVA VOCE ISTITUZIONALE (OBBLIGATORIA)

Scrivi SEMPRE a nome del CLUB come istituzione, MAI a nome di singoli stakeholder o soci.

**REGOLE FONDAMENTALI:**
1. **NESSUN NOME PROPRIO**: Non menzionare MAI nomi di soci, presidente, DG o altri individui.
2. **VOCE ISTITUZIONALE**: Usa sempre "Il Club", "La Società", "La Direzione", "L'Organo Amministrativo".
3. **DECISIONI COLLEGIALI**: Presenta ogni decisione come frutto di analisi strategica, non di opinioni personali.
   - SBAGLIATO: "Il presidente Carnevali vuole la Serie D"
   - CORRETTO: "La direzione strategica prevede un percorso verso la Serie D"
4. **CONFLITTI → SINTESI**: Se esistono visioni divergenti tra stakeholder, sintetizzale in UNA direzione strategica chiara.
   - SBAGLIATO: "Alcuni soci preferiscono X, altri Y"
   - CORRETTO: "L'analisi comparata ha portato alla definizione di un approccio bilanciato che..."
5. **TONO CONSULENZIALE**: Scrivi come se fossi McKinsey/BCG che presenta al board, non come verbale di assemblea.

**FORMULE DA USARE:**
- "Il Club ha stabilito..."
- "La direzione strategica prevede..."
- "L'analisi condotta evidenzia..."
- "Si raccomanda l'adozione di..."
- "La Società intende perseguire..."
- "Il piano triennale delinea..."
---
"""


# =============================================================================
# AGENT SPECIFICATIONS - 8 AGENTI
# =============================================================================

AGENT_SPECS: Dict[AgentRole, AgentSpec] = {
    AgentRole.COORDINATOR: AgentSpec(
        role=AgentRole.COORDINATOR,
        name="Strategic Coordinator",
        expertise=["sintesi strategica", "executive summary", "visione d'insieme"],
        priority=0,
        output_sections=["executive_summary"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + """
Sei il COORDINATORE STRATEGICO. Il tuo compito è creare un Executive Summary che sintetizzi le analisi degli altri agenti in una VOCE UNICA E ISTITUZIONALE del club.

**STRUTTURA OBBLIGATORIA DELL'EXECUTIVE SUMMARY:**
1.  **Visione Strategica Triennale:** Definisci la visione del club a 3 anni come decisione unitaria della Società.
2.  **Sintesi Aree Chiave:** Riassumi in un paragrafo per area i punti salienti (Sportivo, Strutturale, Marketing, Sociale).
3.  **Obiettivi Macro Prioritari:** Elenca i 3-5 obiettivi MACRO come priorità strategiche del Club.
4.  **Azioni Micro Immediate (Quick Wins):** Identifica 3-4 azioni MICRO ad alto impatto da avviare entro 6 mesi.
5.  **Conclusioni e Prossimi Passi:** Chiudi con una call to action per l'esecuzione.

**STILE E FORMATO (OBBLIGATORIO):**
- Tono da consulting firm d'elite (McKinsey, BCG, Bain).
- ZERO riferimenti a singoli individui o loro opinioni.
- Presenta il piano come DECISIONE STRATEGICA UNITARIA del Club.
- Usa: "Il Club", "La Direzione", "La Società", "Il Management".
- Lessico: "valorizzazione asset", "mitigazione rischio", "execution roadmap".
"""
    ),

    AgentRole.TECHNICAL_SPORTING: AgentSpec(
        role=AgentRole.TECHNICAL_SPORTING,
        name="Technical-Sporting Analyst",
        expertise=["prima squadra", "staff tecnico", "metodologia", "scouting"],
        priority=1,
        output_sections=["technical_sporting_plan"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + """
Sei l'ANALISTA TECNICO-SPORTIVO. Redigi il piano strategico per l'Area Sportiva a nome del Club.

**STRUTTURA DI OUTPUT OBBLIGATORIA:**

## OBIETTIVI SPORTIVI

### 1. CREAZIONE E SVILUPPO IDENTITÀ TECNICA
    - **1.1 ORGANIGRAMMA TECNICO:** Figure attuali e gap da colmare.
    - **1.2 PIANO FORMAZIONE STAFF:** Aggiornamento continuo e licenze.

### 2. POTENZIAMENTO STRUTTURA SPORTIVA
    - **2.1 PROGRAMMI PER TESSERATI:** Offerta tecnica, medica, fisioterapica.
    - **2.2 STANDARD DIRIGENZIALI:** Criteri selezione e formazione.

### 3. MIGLIORAMENTO COMPETITIVO
    - **3.1 MODELLO DI GIOCO UNIFICATO:** Prima squadra e giovanili.
    - **3.2 QUALIFICAZIONE ALLENATORI:** Obiettivi licenze UEFA.
    - **3.3 RETE SCOUTING:** Struttura, budget, KPI.

**STILE:** Tono istituzionale. Usa "Il Club prevede", "La Società implementerà".
Dati mancanti: indicare come `(dato da acquisire)`.
"""
    ),

    AgentRole.INFRASTRUCTURE: AgentSpec(
        role=AgentRole.INFRASTRUCTURE,
        name="Infrastructure & HR Strategist",
        expertise=["stadio", "centro sportivo", "risorse umane", "processi"],
        priority=3,
        output_sections=["infrastructure_hr_plan"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + """
Sei lo STRATEGA INFRASTRUTTURALE E HR. Redigi il piano a nome della Società.

## OBIETTIVI STRUTTURALI E INFRASTRUTTURALI

### 1. RINNOVAMENTO E SVILUPPO IMPIANTI
    - **1.1 STATO ATTUALE:** Analisi campi e strutture esistenti.
    - **1.2 PIANO INVESTIMENTI:** Nuovi impianti, retail store, sede.
    - **1.3 TIMELINE E COSTI:** Stime con range e fonti.

### 2. RISORSE UMANE
    - **2.1 POLICY HR:** Standardizzazione processi.
    - **2.2 PERFORMANCE MANAGEMENT:** Strumenti e KPI.
    - **2.3 WELFARE AZIENDALE:** Programmi benessere.

**STILE:** Voce istituzionale. Costi indicati come range con fonte.
"""
    ),

    AgentRole.MARKETING_COMMERCIAL: AgentSpec(
        role=AgentRole.MARKETING_COMMERCIAL,
        name="Marketing & Commercial Director",
        expertise=["comunicazione", "marketing", "brand identity", "commerciale"],
        priority=4,
        output_sections=["marketing_commercial_plan"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + """
Sei il DIRETTORE MARKETING E COMMERCIALE. Redigi il piano a nome del Club.

## OBIETTIVI MARKETING E COMMERCIALI

### 1. COMUNICAZIONE
    - **1.1 UFFICIO STAMPA:** Struttura e strumenti.
    - **1.2 KPI COMUNICAZIONE:** Reach, engagement, sentiment.

### 2. MARKETING
    - **2.1 RESPONSABILE MARKETING:** Profilo e competenze.
    - **2.2 PIANO ANNUALE:** Componenti chiave.
    - **2.3 CRM E AUTOMATION:** Strategia implementativa.

### 3. BRAND IDENTITY
    - **3.1 HERITAGE:** Valorizzazione storia del Club.
    - **3.2 MERCHANDISING:** Analisi e sviluppo.

### 4. AREA COMMERCIALE
    - **4.1 PIANO RICAVI:** Struttura e obiettivi.
    - **4.2 ORGANIGRAMMA COMMERCIALE:** Figure e responsabilità.

**STILE:** Voce istituzionale. Usa benchmark di mercato.
"""
    ),

    AgentRole.SOCIAL_SUSTAINABILITY: AgentSpec(
        role=AgentRole.SOCIAL_SUSTAINABILITY,
        name="Social Impact & Sustainability Manager",
        expertise=["CSR", "impatto sociale", "inclusione", "ambiente"],
        priority=5,
        output_sections=["social_sustainability_plan"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + """
Sei il RESPONSABILE IMPATTO SOCIALE E SOSTENIBILITÀ. Scrivi a nome della Società.

## OBIETTIVI SOCIALI E AMBIENTALI

### 1. INCLUSIONE E DIVERSITÀ
    - Anti-razzismo, protezione minori, accessibilità.

### 2. IMPATTO TERRITORIALE
    - Progetti scuole, salute, solidarietà.

### 3. SOSTENIBILITÀ AMBIENTALE
    - Economia circolare, riduzione impatto, green initiatives.

**STILE:** Quantifica sempre l'impatto (es. "500 beneficiari", "-20% plastica").
Voce istituzionale: "Il Club si impegna a...", "La Società promuove...".
"""
    ),

    AgentRole.GOVERNANCE: AgentSpec(
        role=AgentRole.GOVERNANCE,
        name="Governance & Organization Expert",
        expertise=["organigramma", "governance", "compliance", "processi"],
        priority=6,
        output_sections=["governance_plan"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + """
Sei l'ESPERTO DI GOVERNANCE. Analizza e proponi miglioramenti a nome del Club.

## OBIETTIVI GOVERNANCE

### 1. STRUTTURA ORGANIZZATIVA
    - Organigramma, ruoli, responsabilità.

### 2. PROCESSI DECISIONALI
    - Flussi, deleghe, reporting.

### 3. COMPLIANCE
    - Normative federali, statuto, regolamenti.

### 4. DIGITALIZZAZIONE
    - Sistemi informativi, workflow digitali.

**STILE:** Voce istituzionale. Tono consulenziale d'elite.
"""
    ),

    AgentRole.FINANCIAL: AgentSpec(
        role=AgentRole.FINANCIAL,
        name="Financial Strategist",
        expertise=["bilancio", "budget", "investimenti", "sostenibilità economica"],
        priority=7,
        output_sections=["financial_plan"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + """
Sei lo STRATEGA FINANZIARIO. Redigi l'analisi economico-finanziaria a nome della Società.

## PIANO ECONOMICO-FINANZIARIO

### 1. ANALISI SITUAZIONE ATTUALE
    - Ricavi, costi, margini (solo dati verificati o benchmark).

### 2. BUDGET PREVISIONALE TRIENNALE
    - Proiezioni basate su assunzioni esplicite.

### 3. PIANO INVESTIMENTI
    - Priorità, timeline, fonti di finanziamento.

### 4. SOSTENIBILITÀ ECONOMICA
    - Break-even, cash flow, rischi finanziari.

**REGOLA CRITICA**: MAI inventare numeri. Dati non noti = `(dato riservato)`.
**STILE:** Voce istituzionale. Proiezioni con assunzioni chiare.
"""
    ),
}


# =============================================================================
# STRATEGIC AGENT
# =============================================================================

class StrategicAgent:
    """
    Singolo agente specializzato.
    Usa il File Search Tool di Gemini per basare le risposte sulla knowledge base.
    Supporta conflict-aware generation basata su alignment score stakeholder.
    """

    def __init__(self, spec: AgentSpec, file_search_store_name: str | None = None):
        self.spec = spec
        self.sourcer = SourcedContentGenerator()
        self.file_search_store_name = file_search_store_name
        self.model = None

        api_key = GEMINI_API_KEY or os.environ.get("GOOGLE_API_KEY")
        if GENAI_AVAILABLE and api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(MODEL_CONFIG.name)
                self.available = True
            except Exception as e:
                logger.error(f"Errore durante l'inizializzazione del client Gemini: {e}")
                self.model = None
                self.available = False
        else:
            self.model = None
            self.available = False
            logger.warning(f"Agent {spec.name}: Gemini non disponibile o API key mancante.")

    def _get_tone_directive(self, alignment_score: float, conflicts: list = None) -> str:
        """
        Genera direttive di tono basate sull'alignment score stakeholder.

        Args:
            alignment_score: Score 0-100 di coesione tra stakeholder
            conflicts: Lista di conflitti rilevati

        Returns:
            Direttiva testuale per modulare il tono
        """
        if alignment_score >= 90:
            return """
**TONO DIRETTIVO - ALTO ALLINEAMENTO STAKEHOLDER (>90%)**
Gli stakeholder sono altamente allineati. Usa un tono deciso e propositivo:
- Afferma con sicurezza le raccomandazioni
- Usa linguaggio assertivo: "si procederà", "è necessario", "la strategia prevede"
- Evita condizionali e cautele eccessive
- Focus sull'execution immediata
"""
        elif alignment_score >= 70:
            return """
**TONO BILANCIATO - ALLINEAMENTO MODERATO (70-90%)**
C'è consenso sostanziale con alcune divergenze minori. Tono equilibrato:
- Presenta raccomandazioni con sicurezza ma riconosci alternative
- Usa: "si raccomanda", "l'analisi suggerisce"
- Evidenzia le aree di consenso come prioritarie
"""
        elif alignment_score >= 50:
            return f"""
**TONO PRUDENTE - ALLINEAMENTO BASSO (50-70%)**
Esistono divergenze significative tra gli stakeholder. Procedi con cautela:
- Usa linguaggio condizionale: "si suggerisce di valutare", "potrebbe essere opportuno"
- Evidenzia esplicitamente le aree che richiedono allineamento interno
- Proponi opzioni alternative dove c'è disaccordo
- Includi raccomandazioni per workshop di allineamento

{self._format_conflict_warnings(conflicts) if conflicts else ""}
"""
        else:
            return f"""
**TONO MOLTO PRUDENTE - BASSO ALLINEAMENTO (<50%)**
⚠️ ATTENZIONE: Gli stakeholder presentano visioni fortemente divergenti.
Prima di procedere con azioni strategiche, è CRITICO:
1. Organizzare sessioni di allineamento tra ownership e management
2. Definire priorità condivise attraverso processo strutturato
3. Risolvere i conflitti emersi prima di investire risorse

Le raccomandazioni di questa sezione sono da considerarsi PRELIMINARI
e soggette a revisione post-allineamento.

{self._format_conflict_warnings(conflicts) if conflicts else ""}
"""

    def _format_conflict_warnings(self, conflicts: list) -> str:
        """Formatta i conflitti come warning per l'agente."""
        if not conflicts:
            return ""

        warnings = ["**CONFLITTI RILEVATI DA GESTIRE:**"]
        for c in conflicts[:3]:  # Max 3 conflitti
            area = c.get('area', c.area if hasattr(c, 'area') else 'N/A')
            description = c.get('description', c.description if hasattr(c, 'description') else '')
            severity = c.get('severity', c.severity if hasattr(c, 'severity') else 'medium')

            severity_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(severity, '⚪')
            warnings.append(f"- {severity_icon} **{area}**: {description}")

        return "\n".join(warnings)

    def generate(
        self,
        club_data: Dict,
        research_data: Dict = None,
        context: Dict = None,
        stakeholder_meta: Dict = None
    ) -> Dict[str, Any]:
        """
        Genera output per l'area di competenza, usando il File Search Tool.

        Args:
            club_data: Dati del club
            research_data: Dati da ricerca web
            context: Output di altri agenti (per coordinator)
            stakeholder_meta: Metadati stakeholder per conflict-aware generation
                - alignment_score: Score 0-100
                - conflicts: Lista conflitti
                - synthesized_vision: Visione sintetizzata
        """
        if not self.available:
            return self._generate_mock(club_data)

        prompt_content = self._build_simple_prompt(club_data, research_data, context, stakeholder_meta)

        try:
            logger.debug(f"Invio richiesta a Gemini per {self.spec.name}")
            response = self.model.generate_content(
                prompt_content,
                generation_config=genai.types.GenerationConfig(
                    temperature=MODEL_CONFIG.temperature,
                    max_output_tokens=MODEL_CONFIG.max_tokens,
                )
            )
            raw_content = response.text
            citations = []

        except Exception as e:
            logger.error(f"Agent {self.spec.name} generation error: {e}")
            return {'content': f"Errore: {e}", 'sources': [], 'unverified_claims': [], 'metadata': {}}

        cleaned = self._post_process(raw_content)
        content, sources, unverified = self.sourcer.process_content(cleaned, context=club_data.get('club_name', ''))

        if citations:
            sources.append({"name": f"Riferimenti da Knowledge Base ({len(citations)} doc.)", "url": ", ".join(citations), "is_trusted": True})

        return {
            'content': content,
            'sources': sources,
            'unverified_claims': unverified,
            'metadata': {'agent': self.spec.name, 'role': self.spec.role.value}
        }

    def _build_simple_prompt(
        self,
        club_data: Dict,
        research_data: Dict = None,
        context: Dict = None,
        stakeholder_meta: Dict = None
    ) -> str:
        """
        Costruisce un prompt semplificato con supporto per conflict-aware generation.

        Args:
            club_data: Dati del club
            research_data: Dati da ricerca web
            context: Output altri agenti (per coordinator)
            stakeholder_meta: Metadati stakeholder (alignment_score, conflicts, vision)
        """
        club_info = f"DATI CLUB:\n- Nome: {club_data.get('club_name', 'N/A')}\n- Categoria: {club_data.get('category', 'N/A')}"
        benchmark_info = self._get_relevant_benchmarks(club_data.get('category', ''))

        # === STAKEHOLDER CONTEXT (Multi-Stakeholder Conflict Awareness) ===
        stakeholder_info = ""
        tone_directive = ""

        if stakeholder_meta:
            alignment_score = stakeholder_meta.get('alignment_score', 100)
            conflicts = stakeholder_meta.get('conflicts', [])
            synthesized_vision = stakeholder_meta.get('synthesized_vision', '')
            swot = stakeholder_meta.get('swot_aggregated', {})
            priorities = stakeholder_meta.get('priority_ranking', [])

            # Direttiva di tono basata su alignment
            tone_directive = self._get_tone_directive(alignment_score, conflicts)

            # Info stakeholder per il prompt
            stakeholder_info = f"""
---
## CONTESTO MULTI-STAKEHOLDER

**Alignment Score:** {alignment_score:.0f}/100
**Stakeholder consultati:** {stakeholder_meta.get('stakeholder_count', 'N/A')}

{tone_directive}
"""
            # Aggiungi visione sintetizzata se presente
            if synthesized_vision:
                # Tronca se troppo lunga
                vision_preview = synthesized_vision[:800] + '...' if len(synthesized_vision) > 800 else synthesized_vision
                stakeholder_info += f"""
**VISIONE STRATEGICA SINTETIZZATA (da stakeholder):**
{vision_preview}
"""
            # Aggiungi SWOT aggregato
            if swot:
                stakeholder_info += "\n**SWOT AGGREGATO (consenso stakeholder):**\n"
                for category, items in swot.items():
                    if items:
                        items_list = items[:3] if isinstance(items[0], str) else [i[0] for i in items[:3]]
                        stakeholder_info += f"- {category.title()}: {', '.join(items_list)}\n"

            # Aggiungi priorità
            if priorities:
                prio_list = priorities[:5] if isinstance(priorities[0], str) else [p[0] for p in priorities[:5]]
                stakeholder_info += f"\n**PRIORITÀ STRATEGICHE (weighted ranking):** {', '.join(prio_list)}\n"

            stakeholder_info += "---\n"

        # Dati sintetizzati dal webhook (se presenti in club_data)
        synthesized_from_club = ""
        if club_data.get('synthesized_vision'):
            synthesized_from_club = f"\n**VISIONE STRATEGICA SINTETIZZATA:**\n{club_data['synthesized_vision'][:600]}\n"
        if club_data.get('swot_aggregated'):
            synthesized_from_club += "\n**SWOT AGGREGATO:**\n"
            for cat, items in club_data['swot_aggregated'].items():
                if items:
                    synthesized_from_club += f"- {cat.title()}: {', '.join(items[:3])}\n"
        if club_data.get('priority_ranking'):
            synthesized_from_club += f"\n**PRIORITÀ:** {', '.join(club_data['priority_ranking'][:5])}\n"

        research_info = ""
        if research_data:
            research_text = json.dumps(research_data, indent=2, ensure_ascii=False)
            research_info = f"\nDATI DA RICERCA WEB (sintesi):\n{research_text[:1000]}"

        context_info = ""
        if context:
            context_text = json.dumps(context, indent=2, ensure_ascii=False)
            context_info = f"\nOUTPUT ALTRI AGENTI (per sintesi):\n{context_text[:1500]}"

        return f"{self.spec.system_prompt}\n\n{stakeholder_info}{club_info}\n{synthesized_from_club}{benchmark_info}\n{research_info}\n{context_info}"
        
    def _get_relevant_benchmarks(self, category: str) -> str:
        """Recupera benchmark rilevanti per la categoria"""
        lines = ["\nBENCHMARK DI CATEGORIA:"]
        sg_data = BENCHMARKS.settore_giovanile_media_tesserati.get(category)
        if sg_data: lines.append(f"- Tesserati SG media: {sg_data['media']}")
        budget_data = BENCHMARKS.budget_medio_per_categoria.get(category)
        if budget_data: lines.append(f"- Budget medio: €{budget_data['media']:,}".replace(",", "."))
        return "\n".join(lines) if len(lines) > 1 else ""

    def _post_process(self, text: str) -> str:
        """Pulizia linguistica del testo generato."""
        # Guard contro None o tipi non validi
        if text is None:
            logger.warning(f"Agent {self.spec.name} returned None content")
            return f"## {self.spec.name}\n\nContenuto non disponibile - riprovare la generazione."
        if not isinstance(text, str):
            logger.warning(f"Agent {self.spec.name} returned non-string: {type(text)}")
            return str(text) if text else f"## {self.spec.name}\n\nContenuto non disponibile."
        # Pattern da rimuovere
        chatbot_patterns = [r'^OK\.?\s*', r'^Ecco[^.]+\.\s*', r'^Certo[,!.]?\s*']
        for pattern in chatbot_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

        # Rimuovi spazi e newline eccessivi
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text).strip()
        return text

    def _generate_mock(self, club_data: Dict) -> Dict[str, Any]:
        """Genera output mock quando Gemini non disponibile"""
        return {
            'content': f"## {self.spec.name}\nSezione generata in modalità demo.",
            'sources': [], 'unverified_claims': [], 'metadata': {'mock': True}
        }


# =============================================================================
# MULTI-AGENT ORCHESTRATOR
# =============================================================================

class MultiAgentOrchestrator:
    """
    Orchestratore del sistema multi-agente.
    Usa il File Search Tool per il grounding.
    """

    def __init__(self, knowledge_store=None, file_search_store_name: str | None = None):
        self.agents: Dict[AgentRole, StrategicAgent] = {}
        self.knowledge_store = knowledge_store
        self.file_search_store_name = file_search_store_name
        self._init_agents()

    def _init_agents(self):
        """Inizializza agenti con il nome dello store RAG."""
        for role, spec in AGENT_SPECS.items():
            self.agents[role] = StrategicAgent(spec, file_search_store_name=self.file_search_store_name)
        logger.info(f"Initialized {len(self.agents)} agents (RAG learning enabled: {bool(self.file_search_store_name)})")

    def generate_strategic_plan(
        self,
        club_data: Dict,
        research_data: Dict = None,
        parallel: bool = True
    ) -> Dict[str, Any]:
        """
        Genera piano strategico completo.

        Args:
            club_data: Dati del club
            research_data: Dati da web research
            parallel: Se eseguire agenti in parallelo

        Returns:
            {
                'plan': Dict[str, str],  # Sezioni del piano
                'sources': List[Dict],    # Tutte le fonti
                'metadata': Dict
            }
        """
        logger.info(f"Generating strategic plan for: {club_data.get('club_name', 'Unknown')}")

        if parallel and AGENT_CONFIG.parallel_execution:
            return self._generate_parallel(club_data, research_data)
        else:
            return self._generate_sequential(club_data, research_data)

    def _generate_sequential(
        self,
        club_data: Dict,
        research_data: Dict = None
    ) -> Dict[str, Any]:
        """Esecuzione sequenziale agenti"""
        results = {}
        all_sources = []
        all_unverified = []

        # Ordina per priorità
        sorted_agents = sorted(
            [(role, agent) for role, agent in self.agents.items() if role != AgentRole.COORDINATOR],
            key=lambda x: AGENT_SPECS[x[0]].priority
        )

        # Esegui agenti specializzati
        for role, agent in sorted_agents:
            logger.info(f"Running agent: {agent.spec.name}")
            output = agent.generate(club_data, research_data)

            results[role.value] = output['content']
            all_sources.extend(output.get('sources', []))
            all_unverified.extend(output.get('unverified_claims', []))

        # Esegui coordinator con contesto
        coordinator = self.agents[AgentRole.COORDINATOR]
        coord_output = coordinator.generate(
            club_data,
            research_data,
            context=results
        )
        results['executive_summary'] = coord_output['content']
        all_sources.extend(coord_output.get('sources', []))

        # Calcola stime finanziarie con sistema Tier 1/2/3
        category = club_data.get('category', 'Serie D')
        financial_estimates = estimate_missing_financials(club_data, category)

        # Converti EstimatedValue in dict serializzabili
        estimates_dict = {}
        estimated_fields = {}
        for key, est in financial_estimates.items():
            estimates_dict[key] = {
                'value': est.value,
                'tier': est.tier.value,
                'confidence': est.confidence,
                'source': est.source
            }
            estimated_fields[key] = est.tier.value  # Per sezione metodologia

        return {
            'plan': results,
            'sources': self._deduplicate_sources(all_sources),
            'unverified_claims': list(set(all_unverified)),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'club_name': club_data.get('club_name', ''),
                'category': category,
                'agents_count': len(self.agents),
                'financial_estimates': estimates_dict,
                'estimated_fields': estimated_fields,
                'primary_color': club_data.get('primary_color', '#1a365d'),
                'secondary_color': club_data.get('secondary_color', '#ffffff'),
            }
        }

    def _generate_parallel(
        self,
        club_data: Dict,
        research_data: Dict = None
    ) -> Dict[str, Any]:
        """Esecuzione parallela agenti (async)"""
        import asyncio

        async def run_agent(role: AgentRole, agent: StrategicAgent) -> tuple:
            # Simula async (Gemini è sync)
            output = agent.generate(club_data, research_data)
            return role.value, output

        async def run_all():
            tasks = []
            for role, agent in self.agents.items():
                if role != AgentRole.COORDINATOR:
                    tasks.append(run_agent(role, agent))

            results = await asyncio.gather(*tasks)
            return dict(results)

        # Run async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            agent_results = loop.run_until_complete(run_all())
        finally:
            loop.close()

        # Estrai contenuti e fonti
        plan = {}
        all_sources = []
        all_unverified = []

        for role_value, output in agent_results.items():
            plan[role_value] = output['content']
            all_sources.extend(output.get('sources', []))
            all_unverified.extend(output.get('unverified_claims', []))

        # Coordinator
        coordinator = self.agents[AgentRole.COORDINATOR]
        coord_output = coordinator.generate(club_data, research_data, context=plan)
        plan['executive_summary'] = coord_output['content']
        all_sources.extend(coord_output.get('sources', []))

        # Calcola stime finanziarie con sistema Tier 1/2/3
        category = club_data.get('category', 'Serie D')
        financial_estimates = estimate_missing_financials(club_data, category)

        # Converti EstimatedValue in dict serializzabili
        estimates_dict = {}
        estimated_fields = {}
        for key, est in financial_estimates.items():
            estimates_dict[key] = {
                'value': est.value,
                'tier': est.tier.value,
                'confidence': est.confidence,
                'source': est.source
            }
            estimated_fields[key] = est.tier.value

        return {
            'plan': plan,
            'sources': self._deduplicate_sources(all_sources),
            'unverified_claims': list(set(all_unverified)),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'club_name': club_data.get('club_name', ''),
                'category': category,
                'agents_count': len(self.agents),
                'parallel_execution': True,
                'financial_estimates': estimates_dict,
                'estimated_fields': estimated_fields,
                'primary_color': club_data.get('primary_color', '#1a365d'),
                'secondary_color': club_data.get('secondary_color', '#ffffff'),
            }
        }

    def _deduplicate_sources(self, sources: List[Dict]) -> List[Dict]:
        """Rimuove fonti duplicate"""
        seen = set()
        unique = []
        for s in sources:
            url = s.get('url', '')
            if url and url not in seen:
                unique.append(s)
                seen.add(url)
        return unique

    def generate_single_section(
        self,
        section: str,
        club_data: Dict,
        research_data: Dict = None
    ) -> Dict[str, Any]:
        """
        Genera singola sezione del piano.
        Utile per rigenerazione/editing.

        Args:
            section: Nome sezione (es. "technical_sporting")
            club_data: Dati club
            research_data: Dati ricerca

        Returns:
            Output agente per quella sezione
        """
        role_map = {
            'executive_summary': AgentRole.COORDINATOR,
            'technical_sporting': AgentRole.TECHNICAL_SPORTING,
            'youth_development': AgentRole.YOUTH_DEVELOPMENT,
            'infrastructure': AgentRole.INFRASTRUCTURE,
            'marketing_commercial': AgentRole.MARKETING_COMMERCIAL,
            'social_sustainability': AgentRole.SOCIAL_SUSTAINABILITY,
            'governance': AgentRole.GOVERNANCE,
            'financial': AgentRole.FINANCIAL,
        }

        role = role_map.get(section)
        if not role:
            raise ValueError(f"Unknown section: {section}")

        agent = self.agents[role]
        return agent.generate(club_data, research_data)

    def get_agent_info(self) -> List[Dict]:
        """Info su tutti gli agenti"""
        return [
            {
                'role': role.value,
                'name': agent.spec.name,
                'expertise': agent.spec.expertise,
                'available': agent.available,
            }
            for role, agent in self.agents.items()
        ]

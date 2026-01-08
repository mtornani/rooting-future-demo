"""
Data Ingestor Module - Multi-Stakeholder Conflict Resolution
=============================================================

Gestisce l'ingestion di dati da molteplici stakeholder (Presidente, DG, Soci, etc.)
e applica algoritmi di conflict resolution per sintetizzare visioni divergenti.

Funzionalita principali:
1. Parsing payload n8n multi-stakeholder
2. Aggregazione SWOT con frequency weighting
3. Sintesi intelligente delle visioni
4. Generazione prompt unificato per AI
5. Conflict detection e reporting

Autore: Rooting Future Strategy Engine
"""

import os
import re
import json
import logging
import io
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from collections import Counter
from enum import Enum

# python-docx per estrazione documenti Word
try:
    from docx import Document
    from docx.table import Table
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    Document = None

logger = logging.getLogger(__name__)


# =============================================================================
# DOCUMENT TYPE DETECTION KEYWORDS
# =============================================================================

DOCUMENT_TYPE_KEYWORDS = {
    'SWOT': {
        'primary': ['swot', 'punti di forza', 'punti di debolezza', 'opportunità', 'minacce',
                    'strengths', 'weaknesses', 'opportunities', 'threats'],
        'secondary': ['analisi swot', 'matrice swot', 'forza', 'debolezza']
    },
    'PEST': {
        'primary': ['pest', 'pestel', 'politico', 'economico', 'sociale', 'tecnologico',
                    'political', 'economic', 'social', 'technological'],
        'secondary': ['analisi pest', 'fattori esterni', 'macroambiente', 'ambiente esterno']
    },
    'VISION': {
        'primary': ['visione', 'vision', 'missione', 'mission', 'valori', 'values'],
        'secondary': ['obiettivi strategici', 'traguardo', 'aspirazioni', 'scopo']
    },
    'STAKEHOLDER': {
        'primary': ['stakeholder', 'portatori di interesse', 'azionisti', 'soci'],
        'secondary': ['presidente', 'direttore generale', 'consiglio', 'proprietà']
    },
    'BUDGET': {
        'primary': ['budget', 'bilancio', 'conto economico', 'ricavi', 'costi'],
        'secondary': ['fatturato', 'spese', 'investimenti', 'finanziario']
    }
}


# =============================================================================
# DATA MODELS
# =============================================================================

class StakeholderRole(Enum):
    """Ruoli stakeholder con peso decisionale."""
    PRESIDENTE = ("Presidente", 1.0)
    VICEPRESIDENTE = ("Vice Presidente", 0.9)
    AD = ("Amministratore Delegato", 0.95)
    DG = ("Direttore Generale", 0.9)
    DS = ("Direttore Sportivo", 0.85)
    CFO = ("CFO/Direttore Finanziario", 0.85)
    SOCIO_MAGGIORANZA = ("Socio di Maggioranza", 0.8)
    SOCIO = ("Socio", 0.6)
    CONSIGLIERE = ("Consigliere", 0.5)
    STAFF = ("Staff Dirigenziale", 0.4)
    CONSULENTE = ("Consulente Esterno", 0.3)

    def __init__(self, label: str, weight: float):
        self.label = label
        self.weight = weight

    @classmethod
    def from_string(cls, role_str: str) -> 'StakeholderRole':
        """Converte stringa in enum, con fallback."""
        role_map = {
            'presidente': cls.PRESIDENTE,
            'vice presidente': cls.VICEPRESIDENTE,
            'vicepresidente': cls.VICEPRESIDENTE,
            'ad': cls.AD,
            'amministratore delegato': cls.AD,
            'dg': cls.DG,
            'direttore generale': cls.DG,
            'ds': cls.DS,
            'direttore sportivo': cls.DS,
            'cfo': cls.CFO,
            'direttore finanziario': cls.CFO,
            'socio maggioranza': cls.SOCIO_MAGGIORANZA,
            'socio di maggioranza': cls.SOCIO_MAGGIORANZA,
            'socio': cls.SOCIO,
            'consigliere': cls.CONSIGLIERE,
            'staff': cls.STAFF,
            'consulente': cls.CONSULENTE,
        }
        normalized = role_str.lower().strip()
        return role_map.get(normalized, cls.SOCIO)


@dataclass
class StakeholderInput:
    """Input singolo stakeholder."""
    name: str
    role: StakeholderRole
    vision: str = ""
    swot_strengths: List[str] = field(default_factory=list)
    swot_weaknesses: List[str] = field(default_factory=list)
    swot_opportunities: List[str] = field(default_factory=list)
    swot_threats: List[str] = field(default_factory=list)
    priorities: List[str] = field(default_factory=list)
    budget_opinion: Optional[str] = None
    timeline_preference: Optional[str] = None
    additional_notes: str = ""

    @property
    def weight(self) -> float:
        """Peso decisionale basato sul ruolo."""
        return self.role.weight

    @classmethod
    def from_dict(cls, data: Dict) -> 'StakeholderInput':
        """Crea da dizionario (payload n8n)."""
        role_str = data.get('role', 'Socio')
        return cls(
            name=data.get('name', 'Anonimo'),
            role=StakeholderRole.from_string(role_str),
            vision=data.get('vision', ''),
            swot_strengths=data.get('swot_strengths', []),
            swot_weaknesses=data.get('swot_weaknesses', []),
            swot_opportunities=data.get('swot_opportunities', []),
            swot_threats=data.get('swot_threats', []),
            priorities=data.get('priorities', []),
            budget_opinion=data.get('budget_opinion'),
            timeline_preference=data.get('timeline_preference'),
            additional_notes=data.get('additional_notes', '')
        )


@dataclass
class ConflictReport:
    """Report dei conflitti rilevati."""
    area: str
    description: str
    stakeholders_involved: List[str]
    severity: str  # 'low', 'medium', 'high'
    resolution_applied: str


@dataclass
class SynthesizedData:
    """Dati sintetizzati dopo conflict resolution."""
    unified_vision: str
    swot_aggregated: Dict[str, List[Tuple[str, float, int]]]  # item, score, count
    priority_ranking: List[Tuple[str, float]]  # priority, weighted_score
    conflicts_detected: List[ConflictReport]
    stakeholder_alignment_score: float  # 0-100
    synthesis_metadata: Dict[str, Any]


# =============================================================================
# SWOT AGGREGATOR - Frequency + Weight Based
# =============================================================================

class SWOTAggregator:
    """
    Aggrega SWOT da multipli stakeholder con:
    - Frequency weighting (item ripetuto = piu importante)
    - Role weighting (Presidente > Socio)
    - Semantic clustering (item simili = merge)
    """

    # Parole chiave per clustering semantico
    SEMANTIC_CLUSTERS = {
        'passione': ['passione', 'entusiasmo', 'motivazione', 'dedizione', 'cuore'],
        'tifosi': ['tifosi', 'tifoseria', 'supporters', 'ultras', 'pubblico', 'fan'],
        'giovani': ['giovani', 'settore giovanile', 'vivaio', 'primavera', 'giovanili'],
        'stadio': ['stadio', 'impianto', 'struttura', 'arena'],
        'finanze': ['soldi', 'budget', 'finanze', 'risorse', 'capitale', 'fondi'],
        'sponsor': ['sponsor', 'sponsorizzazioni', 'partner', 'partnership'],
        'storia': ['storia', 'tradizione', 'storico', 'blasone', 'heritage'],
        'territorio': ['territorio', 'locale', 'citta', 'comunita', 'radicamento'],
        'debiti': ['debiti', 'passivo', 'deficit', 'rosso', 'esposizione'],
        'strutture': ['strutture', 'infrastrutture', 'impianti', 'facilities'],
    }

    def __init__(self):
        self.items_by_category: Dict[str, List[Tuple[str, float, str]]] = {
            'strengths': [],
            'weaknesses': [],
            'opportunities': [],
            'threats': []
        }

    def add_stakeholder_swot(self, stakeholder: StakeholderInput):
        """Aggiunge SWOT di uno stakeholder."""
        weight = stakeholder.weight
        name = stakeholder.name

        for s in stakeholder.swot_strengths:
            self.items_by_category['strengths'].append((s, weight, name))
        for w in stakeholder.swot_weaknesses:
            self.items_by_category['weaknesses'].append((w, weight, name))
        for o in stakeholder.swot_opportunities:
            self.items_by_category['opportunities'].append((o, weight, name))
        for t in stakeholder.swot_threats:
            self.items_by_category['threats'].append((t, weight, name))

    def _normalize_item(self, item: str) -> str:
        """Normalizza item per confronto."""
        return item.lower().strip()

    def _find_cluster(self, item: str) -> Optional[str]:
        """Trova cluster semantico per item."""
        normalized = self._normalize_item(item)
        for cluster_name, keywords in self.SEMANTIC_CLUSTERS.items():
            for kw in keywords:
                if kw in normalized:
                    return cluster_name
        return None

    def _cluster_items(self, items: List[Tuple[str, float, str]]) -> Dict[str, List[Tuple[str, float, str]]]:
        """Raggruppa items per cluster semantico."""
        clusters: Dict[str, List[Tuple[str, float, str]]] = {}
        unclustered: List[Tuple[str, float, str]] = []

        for item, weight, source in items:
            cluster = self._find_cluster(item)
            if cluster:
                if cluster not in clusters:
                    clusters[cluster] = []
                clusters[cluster].append((item, weight, source))
            else:
                unclustered.append((item, weight, source))

        # Aggiungi items non clusterizzati con chiave univoca
        for idx, item_tuple in enumerate(unclustered):
            clusters[f"_unclustered_{idx}"] = [item_tuple]

        return clusters

    def aggregate(self) -> Dict[str, List[Tuple[str, float, int]]]:
        """
        Aggrega tutti gli items con scoring.

        Returns:
            Dict con liste di (item_rappresentativo, score_pesato, conteggio)
        """
        result = {}

        for category, items in self.items_by_category.items():
            if not items:
                result[category] = []
                continue

            # Cluster items
            clusters = self._cluster_items(items)

            aggregated = []
            for cluster_name, cluster_items in clusters.items():
                # Scegli item rappresentativo (quello del ruolo piu alto)
                cluster_items_sorted = sorted(cluster_items, key=lambda x: x[1], reverse=True)
                representative = cluster_items_sorted[0][0]

                # Calcola score pesato
                total_weight = sum(weight for _, weight, _ in cluster_items)
                count = len(cluster_items)

                # Score = somma pesi * bonus frequenza
                frequency_bonus = 1 + (count - 1) * 0.2  # +20% per ogni occorrenza extra
                final_score = total_weight * frequency_bonus

                aggregated.append((representative, round(final_score, 2), count))

            # Ordina per score decrescente
            aggregated.sort(key=lambda x: x[1], reverse=True)
            result[category] = aggregated

        return result


# =============================================================================
# VISION SYNTHESIZER - AI-Ready Prompt Generation
# =============================================================================

class VisionSynthesizer:
    """
    Sintetizza visioni multiple in una visione unificata.
    Genera prompt strutturato per Claude/GPT.
    """

    def __init__(self, stakeholders: List[StakeholderInput]):
        self.stakeholders = stakeholders
        self.conflicts: List[ConflictReport] = []

    def _detect_conflicts(self) -> List[ConflictReport]:
        """Rileva conflitti tra visioni stakeholder."""
        conflicts = []

        # Conflict detection keywords
        ambition_keywords = {
            'high': ['serie a', 'serie b', 'promozione', 'vertice', 'campionato', 'titolo'],
            'low': ['mantenimento', 'salvezza', 'consolidamento', 'stabilita']
        }

        timeline_keywords = {
            'aggressive': ['subito', 'immediato', '1 anno', 'prossima stagione'],
            'conservative': ['lungo termine', '5 anni', 'graduale', 'step by step']
        }

        # Analizza ambizioni
        high_ambition = []
        low_ambition = []

        for s in self.stakeholders:
            vision_lower = s.vision.lower()

            if any(kw in vision_lower for kw in ambition_keywords['high']):
                high_ambition.append(s.name)
            if any(kw in vision_lower for kw in ambition_keywords['low']):
                low_ambition.append(s.name)

        if high_ambition and low_ambition:
            conflicts.append(ConflictReport(
                area="Obiettivi Sportivi",
                description="Divergenza tra visione ambiziosa e conservativa",
                stakeholders_involved=high_ambition + low_ambition,
                severity="medium",
                resolution_applied="Weighted average: priorita a stakeholder con peso maggiore"
            ))

        return conflicts

    def _weight_visions(self) -> List[Tuple[str, float, str]]:
        """Ordina visioni per peso stakeholder."""
        weighted = []
        for s in self.stakeholders:
            if s.vision.strip():
                weighted.append((s.vision, s.weight, s.name))
        weighted.sort(key=lambda x: x[1], reverse=True)
        return weighted

    def synthesize(self) -> str:
        """
        Genera visione unificata.

        Strategia:
        - Visione principale dal ruolo piu alto
        - Arricchita con elementi chiave dagli altri
        - Conflitti segnalati ma risolti per peso
        """
        weighted_visions = self._weight_visions()

        if not weighted_visions:
            return "Visione strategica da definire in collaborazione con gli stakeholder."

        # Visione base dal top stakeholder
        primary_vision, primary_weight, primary_name = weighted_visions[0]

        # Estrai elementi chiave dagli altri
        secondary_elements = []
        for vision, weight, name in weighted_visions[1:]:
            # Estrai prima frase significativa
            sentences = re.split(r'[.!?]', vision)
            if sentences and len(sentences[0].strip()) > 20:
                secondary_elements.append(f"({name}: {sentences[0].strip()})")

        # Componi visione unificata
        unified = f"""VISIONE STRATEGICA UNIFICATA

Visione Principale ({primary_name}):
{primary_vision}

"""

        if secondary_elements:
            unified += f"""Contributi Stakeholder:
{chr(10).join('- ' + e for e in secondary_elements[:3])}
"""

        return unified

    def get_conflicts(self) -> List[ConflictReport]:
        """Ritorna conflitti rilevati."""
        if not self.conflicts:
            self.conflicts = self._detect_conflicts()
        return self.conflicts


# =============================================================================
# PRIORITY RANKER - Weighted Voting
# =============================================================================

class PriorityRanker:
    """
    Classifica priorita con weighted voting.
    Ogni stakeholder vota, peso basato su ruolo.
    """

    def __init__(self):
        self.votes: Dict[str, float] = {}  # priority -> total_weight
        self.vote_counts: Dict[str, int] = {}

    def add_votes(self, stakeholder: StakeholderInput):
        """Aggiungi voti stakeholder."""
        weight = stakeholder.weight

        for priority in stakeholder.priorities:
            normalized = priority.lower().strip()
            self.votes[normalized] = self.votes.get(normalized, 0) + weight
            self.vote_counts[normalized] = self.vote_counts.get(normalized, 0) + 1

    def get_ranking(self, top_n: int = 10) -> List[Tuple[str, float, int]]:
        """
        Ritorna ranking priorita.

        Returns:
            Lista di (priority, weighted_score, vote_count)
        """
        ranked = []
        for priority, score in self.votes.items():
            count = self.vote_counts[priority]
            ranked.append((priority, round(score, 2), count))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_n]


# =============================================================================
# MAIN INGESTOR CLASS
# =============================================================================

class DataIngestor:
    """
    Classe principale per ingestion multi-stakeholder.

    Workflow:
    1. Parse payload n8n
    2. Crea StakeholderInput per ogni stakeholder
    3. Aggrega SWOT
    4. Sintetizza visioni
    5. Classifica priorita
    6. Genera report conflitti
    7. Produce dati unificati per generazione piano
    """

    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload
        self.project_id = payload.get('project_id', f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.club_name = payload.get('club_name', 'Club')
        self.request_mode = payload.get('request_mode', 'production')
        self.stakeholders: List[StakeholderInput] = []
        self.hard_data = payload.get('hard_data', {})

        # Parse stakeholders
        self._parse_stakeholders()

    def _parse_stakeholders(self):
        """Parse stakeholders dal payload."""
        stakeholders_data = self.payload.get('stakeholders_inputs', [])

        for s_data in stakeholders_data:
            try:
                stakeholder = StakeholderInput.from_dict(s_data)
                self.stakeholders.append(stakeholder)
                logger.info(f"Parsed stakeholder: {stakeholder.name} ({stakeholder.role.label})")
            except Exception as e:
                logger.warning(f"Errore parsing stakeholder: {e}")

    def process(self) -> SynthesizedData:
        """
        Processa tutti i dati e ritorna sintesi.
        """
        logger.info(f"Processing {len(self.stakeholders)} stakeholders for {self.club_name}")

        # 1. Aggrega SWOT
        swot_aggregator = SWOTAggregator()
        for s in self.stakeholders:
            swot_aggregator.add_stakeholder_swot(s)
        swot_aggregated = swot_aggregator.aggregate()

        # 2. Sintetizza visioni
        vision_synth = VisionSynthesizer(self.stakeholders)
        unified_vision = vision_synth.synthesize()
        conflicts = vision_synth.get_conflicts()

        # 3. Classifica priorita
        priority_ranker = PriorityRanker()
        for s in self.stakeholders:
            priority_ranker.add_votes(s)
        priority_ranking = priority_ranker.get_ranking()

        # 4. Calcola alignment score
        alignment_score = self._calculate_alignment_score(swot_aggregated, conflicts)

        # 5. Metadata
        metadata = {
            'project_id': self.project_id,
            'club_name': self.club_name,
            'stakeholders_count': len(self.stakeholders),
            'stakeholders_roles': [s.role.label for s in self.stakeholders],
            'hard_data': self.hard_data,
            'processed_at': datetime.now().isoformat(),
            'request_mode': self.request_mode
        }

        return SynthesizedData(
            unified_vision=unified_vision,
            swot_aggregated=swot_aggregated,
            priority_ranking=[(p, s) for p, s, _ in priority_ranking],
            conflicts_detected=conflicts,
            stakeholder_alignment_score=alignment_score,
            synthesis_metadata=metadata
        )

    def _calculate_alignment_score(
        self,
        swot: Dict[str, List],
        conflicts: List[ConflictReport]
    ) -> float:
        """
        Calcola score di allineamento stakeholder (0-100).

        Alto = stakeholder concordano
        Basso = molti conflitti
        """
        base_score = 100.0

        # Penalita per conflitti
        for c in conflicts:
            if c.severity == 'high':
                base_score -= 15
            elif c.severity == 'medium':
                base_score -= 8
            else:
                base_score -= 3

        # Bonus per SWOT con alta frequenza (consenso)
        for category, items in swot.items():
            for item, score, count in items[:3]:  # Top 3 per categoria
                if count >= 3:  # 3+ stakeholder concordano
                    base_score += 2

        return max(0, min(100, base_score))

    def generate_ai_prompt(self, synthesized: SynthesizedData) -> str:
        """
        Genera prompt strutturato per AI (Claude/GPT).
        Usato per la generazione del piano strategico.
        """
        prompt = f"""# BRIEF STRATEGICO: {self.club_name}
## Project ID: {self.project_id}

---

## 1. CONTESTO STAKEHOLDER

Numero stakeholder consultati: {len(self.stakeholders)}
Ruoli coinvolti: {', '.join(set(s.role.label for s in self.stakeholders))}
Score di allineamento: {synthesized.stakeholder_alignment_score:.0f}/100

---

## 2. VISIONE STRATEGICA SINTETIZZATA

{synthesized.unified_vision}

---

## 3. ANALISI SWOT AGGREGATA (Multi-Stakeholder)

### PUNTI DI FORZA (Strengths)
"""
        for item, score, count in synthesized.swot_aggregated.get('strengths', [])[:5]:
            consensus = "consenso forte" if count >= 3 else f"{count} voti"
            prompt += f"- {item} (score: {score}, {consensus})\n"

        prompt += "\n### PUNTI DI DEBOLEZZA (Weaknesses)\n"
        for item, score, count in synthesized.swot_aggregated.get('weaknesses', [])[:5]:
            consensus = "consenso forte" if count >= 3 else f"{count} voti"
            prompt += f"- {item} (score: {score}, {consensus})\n"

        prompt += "\n### OPPORTUNITA (Opportunities)\n"
        for item, score, count in synthesized.swot_aggregated.get('opportunities', [])[:5]:
            consensus = "consenso forte" if count >= 3 else f"{count} voti"
            prompt += f"- {item} (score: {score}, {consensus})\n"

        prompt += "\n### MINACCE (Threats)\n"
        for item, score, count in synthesized.swot_aggregated.get('threats', [])[:5]:
            consensus = "consenso forte" if count >= 3 else f"{count} voti"
            prompt += f"- {item} (score: {score}, {consensus})\n"

        prompt += "\n---\n\n## 4. PRIORITA STRATEGICHE (Weighted Ranking)\n\n"
        for idx, (priority, score) in enumerate(synthesized.priority_ranking[:5], 1):
            prompt += f"{idx}. {priority.title()} (score pesato: {score})\n"

        if synthesized.conflicts_detected:
            prompt += "\n---\n\n## 5. CONFLITTI RILEVATI E RISOLUZIONE\n\n"
            for c in synthesized.conflicts_detected:
                prompt += f"""### {c.area}
- Descrizione: {c.description}
- Stakeholder coinvolti: {', '.join(c.stakeholders_involved)}
- Severita: {c.severity}
- Risoluzione: {c.resolution_applied}

"""

        # Hard data
        if self.hard_data:
            prompt += "\n---\n\n## 6. DATI OGGETTIVI (Hard Data)\n\n"
            for key, value in self.hard_data.items():
                prompt += f"- {key.replace('_', ' ').title()}: {value}\n"

        prompt += """
---

## ISTRUZIONI PER LA GENERAZIONE

Sulla base di questo brief multi-stakeholder, genera un Piano Strategico Triennale che:

1. **Rispetti la visione sintetizzata** - priorita alla visione dei ruoli con peso maggiore
2. **Affronti i punti di debolezza** emersi con consenso
3. **Sfrutti le opportunita** identificate dagli stakeholder
4. **Mitighi le minacce** segnalate
5. **Segua le priorita** nel ranking pesato
6. **Risolva i conflitti** seguendo le indicazioni di risoluzione

Il piano deve essere concreto, con KPI misurabili e timeline realistiche.
"""

        return prompt

    def to_generation_params(self, synthesized: SynthesizedData) -> Dict[str, Any]:
        """
        Converte dati sintetizzati in parametri per /api/generate.
        """
        # Estrai categoria dai hard_data
        category = self.hard_data.get('current_league', 'Serie D')

        # Prepara additional_data con SWOT
        additional_data = {
            'swot': {
                'strengths': [item for item, _, _ in synthesized.swot_aggregated.get('strengths', [])[:5]],
                'weaknesses': [item for item, _, _ in synthesized.swot_aggregated.get('weaknesses', [])[:5]],
                'opportunities': [item for item, _, _ in synthesized.swot_aggregated.get('opportunities', [])[:5]],
                'threats': [item for item, _, _ in synthesized.swot_aggregated.get('threats', [])[:5]],
            },
            'priorities': [p for p, _ in synthesized.priority_ranking[:5]],
            'unified_vision': synthesized.unified_vision,
            'stakeholder_alignment': synthesized.stakeholder_alignment_score,
            'conflicts_summary': [
                {'area': c.area, 'severity': c.severity}
                for c in synthesized.conflicts_detected
            ]
        }

        # Merge hard_data
        additional_data.update(self.hard_data)

        return {
            'club_name': self.club_name,
            'category': category,
            'city': self.hard_data.get('city', ''),
            'region': self.hard_data.get('region', ''),
            'enable_research': self.request_mode == 'production',
            'additional_data': additional_data,
            'source': 'n8n_multi_stakeholder',
            'project_id': self.project_id
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def process_n8n_webhook_payload(payload: Dict[str, Any]) -> Tuple[SynthesizedData, Dict[str, Any]]:
    """
    Funzione helper per processare payload n8n.

    Args:
        payload: JSON payload da n8n

    Returns:
        Tuple di (SynthesizedData, generation_params)
    """
    ingestor = DataIngestor(payload)
    synthesized = ingestor.process()
    generation_params = ingestor.to_generation_params(synthesized)

    return synthesized, generation_params


def generate_conflict_report_html(conflicts: List[ConflictReport]) -> str:
    """
    Genera HTML per visualizzare conflitti nel piano.
    """
    if not conflicts:
        return ""

    html = """
    <div class="conflict-report" style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 15px; margin: 15px 0;">
        <h4 style="color: #856404; margin-top: 0;">Conflitti Stakeholder Rilevati</h4>
        <p style="font-size: 0.9em; color: #856404;">
            Durante la sintesi delle visioni sono emersi i seguenti punti di divergenza,
            risolti secondo il peso decisionale degli stakeholder.
        </p>
        <ul style="margin: 10px 0;">
    """

    for c in conflicts:
        severity_color = {'high': '#dc3545', 'medium': '#fd7e14', 'low': '#28a745'}
        html += f"""
            <li style="margin-bottom: 8px;">
                <strong>{c.area}</strong>
                <span style="color: {severity_color.get(c.severity, '#6c757d')}; font-size: 0.8em;">
                    [{c.severity.upper()}]
                </span>
                <br><em style="font-size: 0.85em;">{c.description}</em>
            </li>
        """

    html += """
        </ul>
    </div>
    """

    return html


# =============================================================================
# DOCX INGESTOR - Word Document Parser
# =============================================================================

@dataclass
class ExtractedDocxData:
    """Dati estratti da un documento Word."""
    filename: str
    document_type: str  # SWOT, PEST, VISION, STAKEHOLDER, BUDGET, UNKNOWN
    stakeholder_name: Optional[str] = None
    stakeholder_role: Optional[str] = None

    # SWOT data
    swot_strengths: List[str] = field(default_factory=list)
    swot_weaknesses: List[str] = field(default_factory=list)
    swot_opportunities: List[str] = field(default_factory=list)
    swot_threats: List[str] = field(default_factory=list)

    # PEST data
    pest_political: List[str] = field(default_factory=list)
    pest_economic: List[str] = field(default_factory=list)
    pest_social: List[str] = field(default_factory=list)
    pest_technological: List[str] = field(default_factory=list)

    # Vision data
    vision_statement: str = ""
    mission_statement: str = ""
    values: List[str] = field(default_factory=list)

    # Generic data
    priorities: List[str] = field(default_factory=list)
    notes: str = ""
    raw_tables: List[Dict[str, Any]] = field(default_factory=list)
    raw_paragraphs: List[str] = field(default_factory=list)

    # Metadata
    confidence_score: float = 0.0


class DocxIngestor:
    """
    Parser per documenti Word (.docx) contenenti template SWOT, PEST, VISION.

    Funzionalità:
    1. Rilevamento automatico tipo documento
    2. Estrazione tabelle (SWOT matrix, PEST matrix)
    3. Estrazione paragrafi (Vision, Mission, Notes)
    4. Mapping a StakeholderInput per integrazione con DataIngestor
    5. Supporto multi-file
    """

    # Mapping intestazioni tabella -> categoria SWOT
    SWOT_HEADER_MAP = {
        # Italiano
        'punti di forza': 'strengths',
        'forza': 'strengths',
        'forze': 'strengths',
        's': 'strengths',
        'strengths': 'strengths',

        'punti di debolezza': 'weaknesses',
        'debolezza': 'weaknesses',
        'debolezze': 'weaknesses',
        'w': 'weaknesses',
        'weaknesses': 'weaknesses',

        'opportunità': 'opportunities',
        'opportunita': 'opportunities',
        'o': 'opportunities',
        'opportunities': 'opportunities',

        'minacce': 'threats',
        'rischi': 'threats',
        't': 'threats',
        'threats': 'threats',
    }

    # Mapping intestazioni tabella -> categoria PEST
    PEST_HEADER_MAP = {
        'politico': 'political',
        'politici': 'political',
        'p': 'political',
        'political': 'political',

        'economico': 'economic',
        'economici': 'economic',
        'e': 'economic',
        'economic': 'economic',

        'sociale': 'social',
        'sociali': 'social',
        's': 'social',
        'social': 'social',

        'tecnologico': 'technological',
        'tecnologici': 'technological',
        't': 'technological',
        'technological': 'technological',
    }

    def __init__(self):
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx non installato. Eseguire: pip install python-docx")

    def detect_document_type(self, doc: 'Document', filename: str = "") -> Tuple[str, float]:
        """
        Rileva il tipo di documento basandosi su keywords.

        Returns:
            Tuple di (document_type, confidence_score)
        """
        # Concatena tutto il testo del documento
        all_text = []

        # Paragraphs
        for para in doc.paragraphs:
            all_text.append(para.text.lower())

        # Tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    all_text.append(cell.text.lower())

        full_text = ' '.join(all_text)

        # Anche dal filename
        full_text += ' ' + filename.lower()

        # Score per ogni tipo
        type_scores = {}

        for doc_type, keywords in DOCUMENT_TYPE_KEYWORDS.items():
            score = 0

            # Primary keywords: +3 punti
            for kw in keywords['primary']:
                if kw in full_text:
                    score += 3

            # Secondary keywords: +1 punto
            for kw in keywords['secondary']:
                if kw in full_text:
                    score += 1

            type_scores[doc_type] = score

        # Trova tipo con score massimo
        if not type_scores or max(type_scores.values()) == 0:
            return 'UNKNOWN', 0.0

        best_type = max(type_scores, key=type_scores.get)
        max_score = type_scores[best_type]

        # Calcola confidence (normalizzata)
        # Max teorico: 5 primary * 3 + 5 secondary * 1 = 20
        confidence = min(100.0, (max_score / 10) * 100)

        return best_type, confidence

    def extract_stakeholder_info(self, doc: 'Document') -> Tuple[Optional[str], Optional[str]]:
        """
        Estrae nome e ruolo stakeholder dal documento.
        Cerca pattern come "Nome: Mario Rossi" o "Ruolo: Presidente".
        """
        name = None
        role = None

        name_patterns = [
            r'nome[:\s]+([A-Za-zÀ-ÿ\s]+)',
            r'compilato da[:\s]+([A-Za-zÀ-ÿ\s]+)',
            r'stakeholder[:\s]+([A-Za-zÀ-ÿ\s]+)',
        ]

        role_patterns = [
            r'ruolo[:\s]+([A-Za-zÀ-ÿ\s]+)',
            r'posizione[:\s]+([A-Za-zÀ-ÿ\s]+)',
            r'carica[:\s]+([A-Za-zÀ-ÿ\s]+)',
        ]

        for para in doc.paragraphs[:20]:  # Solo primi 20 paragrafi
            text = para.text.lower()

            for pattern in name_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    name = match.group(1).strip().title()
                    break

            for pattern in role_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    role = match.group(1).strip().title()
                    break

            if name and role:
                break

        return name, role

    def extract_tables(self, doc: 'Document') -> List[Dict[str, Any]]:
        """
        Estrae tutte le tabelle dal documento.

        Returns:
            Lista di dizionari con struttura tabella
        """
        tables_data = []

        for table_idx, table in enumerate(doc.tables):
            table_data = {
                'index': table_idx,
                'rows': [],
                'headers': [],
                'is_swot_matrix': False,
                'is_pest_matrix': False,
            }

            for row_idx, row in enumerate(table.rows):
                row_data = []
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    row_data.append(cell_text)

                if row_idx == 0:
                    table_data['headers'] = row_data

                table_data['rows'].append(row_data)

            # Detect if SWOT matrix
            headers_lower = [h.lower() for h in table_data['headers']]
            swot_matches = sum(1 for h in headers_lower if h in self.SWOT_HEADER_MAP)
            if swot_matches >= 2:
                table_data['is_swot_matrix'] = True

            # Detect if PEST matrix
            pest_matches = sum(1 for h in headers_lower if h in self.PEST_HEADER_MAP)
            if pest_matches >= 2:
                table_data['is_pest_matrix'] = True

            tables_data.append(table_data)

        return tables_data

    def parse_swot_table(self, table_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Parsa una tabella SWOT e ritorna le 4 categorie.

        Gestisce vari formati:
        1. Tabella 2x2 con S/W in prima riga, O/T in seconda
        2. Tabella con header e liste sotto
        3. Tabella con colonne separate per ogni categoria
        """
        result = {
            'strengths': [],
            'weaknesses': [],
            'opportunities': [],
            'threats': []
        }

        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])

        if not rows:
            return result

        # Mappa header -> categoria
        header_to_category = {}
        for idx, header in enumerate(headers):
            header_lower = header.lower().strip()
            if header_lower in self.SWOT_HEADER_MAP:
                header_to_category[idx] = self.SWOT_HEADER_MAP[header_lower]

        # Se abbiamo header mappati, estrai per colonna
        if header_to_category:
            for row in rows[1:]:  # Skip header row
                for col_idx, cell_text in enumerate(row):
                    if col_idx in header_to_category and cell_text.strip():
                        category = header_to_category[col_idx]
                        # Split per newline o bullet points
                        items = self._split_cell_items(cell_text)
                        result[category].extend(items)
        else:
            # Fallback: analizza struttura 2x2
            # Prima riga: S | W
            # Seconda riga: O | T
            if len(rows) >= 2 and len(rows[0]) >= 2:
                result['strengths'].extend(self._split_cell_items(rows[0][0]))
                result['weaknesses'].extend(self._split_cell_items(rows[0][1] if len(rows[0]) > 1 else ""))

                if len(rows) > 1:
                    result['opportunities'].extend(self._split_cell_items(rows[1][0]))
                    result['threats'].extend(self._split_cell_items(rows[1][1] if len(rows[1]) > 1 else ""))

        return result

    def parse_pest_table(self, table_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Parsa una tabella PEST e ritorna le 4 categorie.
        """
        result = {
            'political': [],
            'economic': [],
            'social': [],
            'technological': []
        }

        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])

        if not rows:
            return result

        # Mappa header -> categoria
        header_to_category = {}
        for idx, header in enumerate(headers):
            header_lower = header.lower().strip()
            if header_lower in self.PEST_HEADER_MAP:
                header_to_category[idx] = self.PEST_HEADER_MAP[header_lower]

        # Estrai per colonna
        if header_to_category:
            for row in rows[1:]:  # Skip header row
                for col_idx, cell_text in enumerate(row):
                    if col_idx in header_to_category and cell_text.strip():
                        category = header_to_category[col_idx]
                        items = self._split_cell_items(cell_text)
                        result[category].extend(items)

        return result

    def _split_cell_items(self, cell_text: str) -> List[str]:
        """
        Divide il contenuto di una cella in items individuali.
        Gestisce: newlines, bullet points, numeri, trattini.
        """
        if not cell_text:
            return []

        # Prima dividi per newline
        lines = cell_text.split('\n')

        items = []
        for line in lines:
            # Rimuovi bullet points, numeri, trattini iniziali
            cleaned = re.sub(r'^[\s•\-\*\d\.\)\]]+', '', line).strip()
            if cleaned and len(cleaned) > 2:  # Ignora items troppo corti
                items.append(cleaned)

        return items

    def extract_vision_mission(self, doc: 'Document') -> Tuple[str, str, List[str]]:
        """
        Estrae Vision, Mission e Valori dai paragrafi.
        """
        vision = ""
        mission = ""
        values: List[str] = []

        current_section: Optional[str] = None
        section_content: List[str] = []

        vision_triggers = ['visione', 'vision', 'la nostra visione']
        mission_triggers = ['missione', 'mission', 'la nostra missione']
        values_triggers = ['valori', 'values', 'i nostri valori']

        for para in doc.paragraphs:
            text = para.text.strip()
            text_lower = text.lower()

            # Detect section headers e salva sezione precedente
            if any(trigger in text_lower for trigger in vision_triggers):
                # Salva sezione precedente se presente
                if current_section == 'mission' and section_content:
                    mission = ' '.join(section_content)
                elif current_section == 'values' and section_content:
                    values = section_content[:]
                current_section = 'vision'
                section_content = []
                continue

            if any(trigger in text_lower for trigger in mission_triggers):
                # Salva sezione vision se presente
                if current_section == 'vision' and section_content:
                    vision = ' '.join(section_content)
                elif current_section == 'values' and section_content:
                    values = section_content[:]
                current_section = 'mission'
                section_content = []
                continue

            if any(trigger in text_lower for trigger in values_triggers):
                # Salva sezione precedente
                if current_section == 'mission' and section_content:
                    mission = ' '.join(section_content)
                elif current_section == 'vision' and section_content:
                    vision = ' '.join(section_content)
                current_section = 'values'
                section_content = []
                continue

            # Add content to current section
            if current_section and text:
                section_content.append(text)

        # Save last section
        if current_section == 'vision' and section_content:
            vision = ' '.join(section_content)
        elif current_section == 'mission' and section_content:
            mission = ' '.join(section_content)
        elif current_section == 'values' and section_content:
            values = section_content[:]

        return vision, mission, values

    def extract_priorities(self, doc: 'Document') -> List[str]:
        """
        Estrae priorità strategiche dal documento.
        """
        priorities = []

        priority_triggers = ['priorità', 'priorities', 'obiettivi prioritari',
                            'azioni prioritarie', 'priorita strategiche']

        in_priority_section = False

        for para in doc.paragraphs:
            text = para.text.strip()
            text_lower = text.lower()

            if any(trigger in text_lower for trigger in priority_triggers):
                in_priority_section = True
                continue

            if in_priority_section:
                # Stop at next section header (all caps or starts with number)
                if text.isupper() and len(text) > 10:
                    in_priority_section = False
                    continue

                # Extract bulleted/numbered items
                items = self._split_cell_items(text)
                priorities.extend(items)

                # Limit
                if len(priorities) >= 10:
                    break

        return priorities[:10]

    def ingest_file(self, file_path: Union[str, Path, io.BytesIO],
                    filename: str = "") -> ExtractedDocxData:
        """
        Ingestion completa di un singolo file .docx.

        Args:
            file_path: Path al file o BytesIO stream
            filename: Nome del file (per detection tipo)

        Returns:
            ExtractedDocxData con tutti i dati estratti
        """
        # Apri documento
        if isinstance(file_path, io.BytesIO):
            doc = Document(file_path)
            if not filename:
                filename = "uploaded_document.docx"
        else:
            doc = Document(file_path)
            if not filename:
                filename = Path(file_path).name

        logger.info(f"Processing DOCX: {filename}")

        # Detect document type
        doc_type, confidence = self.detect_document_type(doc, filename)
        logger.info(f"Detected type: {doc_type} (confidence: {confidence:.0f}%)")

        # Extract stakeholder info
        stakeholder_name, stakeholder_role = self.extract_stakeholder_info(doc)

        # Extract tables
        tables = self.extract_tables(doc)

        # Extract paragraphs
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

        # Initialize result
        result = ExtractedDocxData(
            filename=filename,
            document_type=doc_type,
            stakeholder_name=stakeholder_name,
            stakeholder_role=stakeholder_role,
            confidence_score=confidence,
            raw_tables=tables,
            raw_paragraphs=paragraphs
        )

        # Parse based on document type
        if doc_type == 'SWOT':
            for table in tables:
                if table.get('is_swot_matrix'):
                    swot_data = self.parse_swot_table(table)
                    result.swot_strengths.extend(swot_data['strengths'])
                    result.swot_weaknesses.extend(swot_data['weaknesses'])
                    result.swot_opportunities.extend(swot_data['opportunities'])
                    result.swot_threats.extend(swot_data['threats'])

        elif doc_type == 'PEST':
            for table in tables:
                if table.get('is_pest_matrix'):
                    pest_data = self.parse_pest_table(table)
                    result.pest_political.extend(pest_data['political'])
                    result.pest_economic.extend(pest_data['economic'])
                    result.pest_social.extend(pest_data['social'])
                    result.pest_technological.extend(pest_data['technological'])

        elif doc_type == 'VISION':
            vision, mission, values = self.extract_vision_mission(doc)
            result.vision_statement = vision
            result.mission_statement = mission
            result.values = values

        # Always try to extract priorities
        result.priorities = self.extract_priorities(doc)

        # Collect notes from unstructured paragraphs
        notes_paras = [p for p in paragraphs if len(p) > 50 and not p.isupper()]
        result.notes = '\n'.join(notes_paras[:5])  # Max 5 paragraphs

        logger.info(f"Extraction complete: {len(result.swot_strengths)} strengths, "
                   f"{len(result.swot_weaknesses)} weaknesses, "
                   f"{len(result.priorities)} priorities")

        return result

    def ingest_multiple_files(self, files: List[Union[str, Path, Tuple[io.BytesIO, str]]]) -> List[ExtractedDocxData]:
        """
        Ingestion di multipli file .docx.

        Args:
            files: Lista di path o tuple (BytesIO, filename)

        Returns:
            Lista di ExtractedDocxData
        """
        results = []

        for file_item in files:
            try:
                if isinstance(file_item, tuple):
                    stream, filename = file_item
                    result = self.ingest_file(stream, filename)
                else:
                    result = self.ingest_file(file_item)

                results.append(result)

            except Exception as e:
                logger.error(f"Errore processing file {file_item}: {e}")
                continue

        return results

    def merge_to_stakeholder_inputs(self, extracted_data: List[ExtractedDocxData]) -> List[StakeholderInput]:
        """
        Converte dati estratti da DOCX in StakeholderInput per integrazione con DataIngestor.

        Args:
            extracted_data: Lista di ExtractedDocxData

        Returns:
            Lista di StakeholderInput pronti per processing
        """
        stakeholder_inputs = []

        for idx, data in enumerate(extracted_data):
            # Determina nome stakeholder
            name = data.stakeholder_name or f"Stakeholder {idx + 1}"

            # Determina ruolo
            if data.stakeholder_role:
                role = StakeholderRole.from_string(data.stakeholder_role)
            else:
                role = StakeholderRole.SOCIO

            # Costruisci vision da varie fonti
            vision_parts = []
            if data.vision_statement:
                vision_parts.append(f"Visione: {data.vision_statement}")
            if data.mission_statement:
                vision_parts.append(f"Missione: {data.mission_statement}")
            if data.notes:
                vision_parts.append(data.notes[:500])

            vision = '\n'.join(vision_parts) if vision_parts else ""

            # Crea StakeholderInput
            stakeholder = StakeholderInput(
                name=name,
                role=role,
                vision=vision,
                swot_strengths=data.swot_strengths[:10],
                swot_weaknesses=data.swot_weaknesses[:10],
                swot_opportunities=data.swot_opportunities[:10],
                swot_threats=data.swot_threats[:10],
                priorities=data.priorities[:5],
                additional_notes=f"Documento: {data.filename}\nTipo: {data.document_type}"
            )

            stakeholder_inputs.append(stakeholder)

        logger.info(f"Merged {len(stakeholder_inputs)} stakeholder inputs from DOCX files")
        return stakeholder_inputs


# =============================================================================
# MULTI-FILE PROCESSOR
# =============================================================================

def process_docx_files_to_payload(
    files: List[Union[str, Path, Tuple[io.BytesIO, str]]],
    club_name: str = "Club",
    project_id: Optional[str] = None,
    hard_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Processa multipli file DOCX e genera payload compatibile con DataIngestor.

    Questa è la funzione principale da usare per integrare l'upload DOCX
    con il workflow esistente di generazione piano strategico.

    Args:
        files: Lista di file paths o tuple (BytesIO, filename)
        club_name: Nome del club
        project_id: ID progetto (generato se non fornito)
        hard_data: Dati oggettivi aggiuntivi

    Returns:
        Dict payload pronto per DataIngestor
    """
    if not DOCX_AVAILABLE:
        raise ImportError("python-docx non installato. Eseguire: pip install python-docx")

    # Inizializza ingestor
    docx_ingestor = DocxIngestor()

    # Estrai dati da tutti i file
    extracted_data = docx_ingestor.ingest_multiple_files(files)

    # Converti in StakeholderInput
    stakeholder_inputs = docx_ingestor.merge_to_stakeholder_inputs(extracted_data)

    # Genera project_id se non fornito
    if not project_id:
        project_id = f"docx_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Costruisci payload
    payload = {
        'project_id': project_id,
        'club_name': club_name,
        'request_mode': 'production',
        'stakeholders_inputs': [
            {
                'name': s.name,
                'role': s.role.label,
                'vision': s.vision,
                'swot_strengths': s.swot_strengths,
                'swot_weaknesses': s.swot_weaknesses,
                'swot_opportunities': s.swot_opportunities,
                'swot_threats': s.swot_threats,
                'priorities': s.priorities,
                'additional_notes': s.additional_notes
            }
            for s in stakeholder_inputs
        ],
        'hard_data': hard_data or {},
        'source': 'docx_upload',
        'files_processed': [d.filename for d in extracted_data],
        'document_types_detected': list(set(d.document_type for d in extracted_data))
    }

    logger.info(f"Generated payload from {len(files)} DOCX files for {club_name}")
    return payload

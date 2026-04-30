"""
Rooting Future Strategy Engine v5.4
Post-Production Editor

Sistema di editing post-generazione per:
- Revisione contenuti sezione per sezione
- Correzione dati non verificati
- Rigenerazione selettiva
- Approvazione workflow
- Gestione 200+ piani senza impazzire
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import logging
import hashlib
import threading

from config import OUTPUT_DIR, KNOWLEDGE_DIR
from knowledge_store import SQLiteKnowledgeStore, PlanRecord
from agents import MultiAgentOrchestrator, AgentRole
from file_search_manager import FileSearchManager
from data_sourcing import SourcedContentGenerator, SourceConfidence

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS E STATUS
# =============================================================================

class SectionStatus(Enum):
    """Status di una sezione"""
    DRAFT = "draft"                 # Generato, non revisionato
    NEEDS_REVIEW = "needs_review"   # Contiene dati non verificati
    REVIEWED = "reviewed"           # Revisionato da umano
    APPROVED = "approved"           # Approvato per export
    REGENERATING = "regenerating"   # In fase di rigenerazione


class PlanStatus(Enum):
    """Status globale del piano"""
    GENERATING = "generating"       # In generazione
    DRAFT = "draft"                 # Generato, in revisione
    IN_REVIEW = "in_review"         # Review in corso
    READY = "ready"                 # Pronto per export
    EXPORTED = "exported"           # Esportato
    ARCHIVED = "archived"           # Archiviato


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SectionEdit:
    """Singola modifica a una sezione"""
    timestamp: str
    editor: str
    field: str
    old_value: str
    new_value: str
    reason: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SectionReview:
    """Review di una sezione"""
    section_id: str
    section_title: str
    content: str
    status: SectionStatus = SectionStatus.DRAFT
    unverified_claims: List[str] = field(default_factory=list)
    sources_count: int = 0
    credibility_score: float = 0.0
    edit_history: List[SectionEdit] = field(default_factory=list)
    notes: str = ""
    last_edited: str = ""
    last_editor: str = ""

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['status'] = self.status.value
        return d


@dataclass
class PlanReview:
    """Review completa di un piano"""
    plan_id: str
    club_name: str
    category: str
    status: PlanStatus = PlanStatus.DRAFT
    sections: Dict[str, SectionReview] = field(default_factory=dict)
    created_at: str = ""
    last_modified: str = ""
    assigned_to: str = ""
    approval_notes: str = ""
    export_count: int = 0
    owner_id: Optional[int] = None
    # Branding del club (opzionale - se None usa auto-detect da club_identity)
    primary_color: str = None
    secondary_color: str = None
    # Variabili che tracciano se il piano è sincronizzato con i dati club attuali
    sync_variables: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['status'] = self.status.value
        d['sections'] = {k: v.to_dict() for k, v in self.sections.items()}
        return d


# =============================================================================
# POST PRODUCTION EDITOR
# =============================================================================

class PostProductionEditor:
    """
    Editor post-produzione per piani strategici.
    Permette revisione, editing e approvazione sezione per sezione.
    """

    def __init__(self):
        self.store = SQLiteKnowledgeStore()
        # Lock per accesso al file JSON delle review
        self.review_lock = threading.Lock()
        # Usa File Search per RAG
        self.file_search_manager = FileSearchManager()
        self.orchestrator = MultiAgentOrchestrator(
            file_search_store_name=self.file_search_manager.get_store_name()
        )
        self.reviews: Dict[str, PlanReview] = {}
        self._load_reviews()

    def mark_sections_for_resync(self, plan_id: str, changed_vars: List[str]):
        """
        Segna le sezioni che dipendono da variabili cambiate come 'NEEDS_REVIEW'.
        """
        review = self.reviews.get(plan_id)
        if not review: return

        # Mapping dipendenze variabili -> sezioni
        dependencies = {
            'category': ['technical_sporting', 'youth_development', 'financial', 'executive_summary'],
            'budget': ['financial', 'marketing_commercial', 'infrastructure', 'executive_summary'],
            'city': ['infrastructure', 'marketing_commercial', 'social_sustainability'],
            'vision': ['executive_summary', 'governance']
        }

        affected_sections = set()
        for var in changed_vars:
            if var in dependencies:
                affected_sections.update(dependencies[var])

        var_str = ", ".join(changed_vars)
        for sec_id in affected_sections:
            if sec_id in review.sections:
                review.sections[sec_id].status = SectionStatus.NEEDS_REVIEW
                review.sections[sec_id].notes += f"\n[{datetime.now().strftime('%Y-%m-%d')}] SISTEMA: Variabili '{var_str}' cambiate. Verificare coerenza contenuto."
        
        review.last_modified = datetime.now().isoformat()
        self._save_reviews()

    def _load_reviews(self):
        """Carica review salvate con lock di sicurezza"""
        reviews_file = KNOWLEDGE_DIR / "plan_reviews.json"
        if reviews_file.exists():
            with self.review_lock:
                try:
                    with open(reviews_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for plan_id, review_data in data.items():
                            self.reviews[plan_id] = self._dict_to_review(review_data)
                except Exception as e:
                    logger.warning(f"Error loading reviews: {e}")

    def _save_reviews(self):
        """Salva review su disco con lock di sicurezza"""
        reviews_file = KNOWLEDGE_DIR / "plan_reviews.json"
        with self.review_lock:
            # Rileggi file per evitare di perdere review salvate da altri processi (se presenti)
            # ma qui siamo nello stesso processo Flask, quindi review_lock basta per i thread.
            data = {k: v.to_dict() for k, v in self.reviews.items()}
            try:
                with open(reviews_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Error saving reviews: {e}")

    def _dict_to_review(self, data: Dict) -> PlanReview:
        """Converte dict in PlanReview"""
        sections = {}
        for section_id, section_data in data.get('sections', {}).items():
            sections[section_id] = SectionReview(
                section_id=section_data.get('section_id', section_id),
                section_title=section_data.get('section_title', ''),
                content=section_data.get('content', ''),
                status=SectionStatus(section_data.get('status', 'draft')),
                unverified_claims=section_data.get('unverified_claims', []),
                sources_count=section_data.get('sources_count', 0),
                credibility_score=section_data.get('credibility_score', 0),
                notes=section_data.get('notes', ''),
                last_edited=section_data.get('last_edited', ''),
                last_editor=section_data.get('last_editor', ''),
            )

        return PlanReview(
            plan_id=data.get('plan_id', ''),
            club_name=data.get('club_name', ''),
            category=data.get('category', ''),
            status=PlanStatus(data.get('status', 'draft')),
            sections=sections,
            created_at=data.get('created_at', ''),
            last_modified=data.get('last_modified', ''),
            assigned_to=data.get('assigned_to', ''),
            owner_id=data.get('owner_id'),
            primary_color=data.get('primary_color'),
            secondary_color=data.get('secondary_color'),
        )

    # =========================================================================
    # CREAZIONE REVIEW
    # =========================================================================

    def create_review_from_plan(
        self,
        plan_data: Dict,
        club_name: str,
        sources: List[Dict] = None,
        metadata: Dict = None,
        owner_id: int = None
    ) -> PlanReview:
        """
        Crea review da piano generato.

        Args:
            plan_data: Output dal multi-agent orchestrator
            club_name: Nome club
            sources: Fonti raccolte
            metadata: Metadati generazione
            owner_id: ID utente proprietario

        Returns:
            PlanReview pronto per editing
        """
        plan_id = self._generate_plan_id(club_name)
        now = datetime.now().isoformat()

        sections = {}
        section_titles = {
            # Legacy keys (keep for backward compatibility)
            'executive_summary': 'Executive Summary',
            'technical_sporting': 'Area Tecnico-Sportiva',
            'youth_development': 'Sviluppo Settore Giovanile',
            'infrastructure': 'Infrastrutture',
            'marketing_commercial': 'Marketing e Commerciale',
            'social_sustainability': 'Sostenibilità Sociale',
            'governance': 'Governance e Organizzazione',
            'financial': 'Piano Economico-Finanziario',
            'financial_plan': 'Piano Economico-Finanziario', # Alias

            # NEW STW KEYS (Orchestrator output)
            'stw_sportivi': 'Area Sportiva (STW)',
            'stw_strutturali': 'Infrastrutture & HR (STW)',
            'stw_struttura_org': 'Struttura Organizzativa (STW)',
            'stw_relazioni_ist': 'Relazioni Istituzionali (STW)',
            'stw_marketing': 'Marketing & Commerciale (STW)',
            'stw_sociali': 'Sostenibilità Sociale (STW)',
        }

        # Analizza ogni sezione
        for section_id, content in plan_data.items():
            if section_id not in section_titles:
                continue

            # Conta fonti per questa sezione
            section_sources = [s for s in (sources or []) if section_id in str(s)]

            # Identifica claims non verificati
            sourcer = SourcedContentGenerator()
            _, _, unverified = sourcer.process_content(content, club_name)

            # Calcola credibility score sezione
            verification = sourcer.get_verification_summary()
            credibility = verification.get('credibility_score', 0)

            # Determina status
            if unverified:
                status = SectionStatus.NEEDS_REVIEW
            else:
                status = SectionStatus.DRAFT

            sections[section_id] = SectionReview(
                section_id=section_id,
                section_title=section_titles[section_id],
                content=content,
                status=status,
                unverified_claims=unverified[:10],  # Top 10
                sources_count=len(section_sources),
                credibility_score=credibility,
                last_edited=now,
            )

        # Estrai colori custom dal metadata (se forniti dalla dashboard)
        primary_color = None
        secondary_color = None
        if metadata:
            primary_color = metadata.get('primary_color')
            secondary_color = metadata.get('secondary_color')
            # Ignora colori default (quelli della dashboard vuota)
            if primary_color == '#1A365D' or primary_color == '#1a365d':
                primary_color = None
            if secondary_color == '#FFFFFF' or secondary_color == '#ffffff':
                secondary_color = None

        review = PlanReview(
            plan_id=plan_id,
            club_name=club_name,
            category=metadata.get('category', '') if metadata else '',
            status=PlanStatus.DRAFT,
            sections=sections,
            created_at=now,
            last_modified=now,
            owner_id=owner_id,
            primary_color=primary_color,
            secondary_color=secondary_color,
        )

        self.reviews[plan_id] = review
        self._save_reviews()

        logger.info(f"Created review for plan: {plan_id}")
        return review

    def _generate_plan_id(self, club_name: str) -> str:
        """Genera ID univoco per piano"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        name_hash = hashlib.md5(club_name.encode()).hexdigest()[:6]
        return f"plan_{name_hash}_{timestamp}"

    # =========================================================================
    # EDITING SEZIONI
    # =========================================================================

    def get_section(self, plan_id: str, section_id: str) -> Optional[SectionReview]:
        """Recupera sezione per editing"""
        review = self.reviews.get(plan_id)
        if review:
            return review.sections.get(section_id)
        return None

    def update_section_content(
        self,
        plan_id: str,
        section_id: str,
        new_content: str,
        editor: str = "user",
        reason: str = ""
    ) -> bool:
        """
        Aggiorna contenuto sezione.

        Args:
            plan_id: ID piano
            section_id: ID sezione
            new_content: Nuovo contenuto
            editor: Chi sta editando
            reason: Motivo modifica

        Returns:
            True se aggiornato
        """
        review = self.reviews.get(plan_id)
        if not review:
            return False

        section = review.sections.get(section_id)
        if not section:
            return False

        # Salva edit nella history
        edit = SectionEdit(
            timestamp=datetime.now().isoformat(),
            editor=editor,
            field="content",
            old_value=section.content[:200] + "...",  # Solo preview
            new_value=new_content[:200] + "...",
            reason=reason
        )
        section.edit_history.append(edit)

        # Aggiorna contenuto
        section.content = new_content
        section.last_edited = datetime.now().isoformat()
        section.last_editor = editor
        section.status = SectionStatus.REVIEWED

        review.last_modified = datetime.now().isoformat()

        self._save_reviews()
        return True

    def add_section_note(
        self,
        plan_id: str,
        section_id: str,
        note: str,
        editor: str = "user"
    ) -> bool:
        """Aggiunge nota a sezione"""
        section = self.get_section(plan_id, section_id)
        if not section:
            return False

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        section.notes += f"\n[{timestamp}] {editor}: {note}"
        section.last_edited = datetime.now().isoformat()

        self._save_reviews()
        return True

    def approve_section(
        self,
        plan_id: str,
        section_id: str,
        approver: str = "user"
    ) -> bool:
        """Approva sezione"""
        section = self.get_section(plan_id, section_id)
        if not section:
            return False

        section.status = SectionStatus.APPROVED
        section.last_edited = datetime.now().isoformat()
        section.last_editor = approver

        # Check se tutte le sezioni sono approvate
        review = self.reviews[plan_id]
        all_approved = all(
            s.status == SectionStatus.APPROVED
            for s in review.sections.values()
        )
        if all_approved:
            review.status = PlanStatus.READY

        self._save_reviews()
        return True

    # =========================================================================
    # RIGENERAZIONE SELETTIVA
    # =========================================================================

    def regenerate_section(
        self,
        plan_id: str,
        section_id: str,
        club_data: Dict,
        additional_context: str = ""
    ) -> Optional[str]:
        """
        Rigenera singola sezione.

        Args:
            plan_id: ID piano
            section_id: ID sezione da rigenerare
            club_data: Dati club
            additional_context: Contesto aggiuntivo per rigenerazione

        Returns:
            Nuovo contenuto sezione
        """
        section = self.get_section(plan_id, section_id)
        if not section:
            return None

        section.status = SectionStatus.REGENERATING
        self._save_reviews()

        try:
            # Aggiungi contesto per migliorare
            if additional_context:
                club_data['regeneration_notes'] = additional_context

            # Rigenera con l'agente specifico
            result = self.orchestrator.generate_single_section(
                section=section_id,
                club_data=club_data
            )

            new_content = result.get('content', '')

            # Aggiorna sezione
            section.content = new_content
            section.status = SectionStatus.DRAFT
            section.last_edited = datetime.now().isoformat()
            section.last_editor = "system_regeneration"

            # Ricalcola unverified claims
            sourcer = SourcedContentGenerator()
            _, _, unverified = sourcer.process_content(new_content, club_data.get('club_name', ''))
            section.unverified_claims = unverified[:10]

            self._save_reviews()
            return new_content

        except Exception as e:
            logger.error(f"Regeneration failed: {e}")
            section.status = SectionStatus.NEEDS_REVIEW
            section.notes += f"\n[ERROR] Regeneration failed: {e}"
            self._save_reviews()
            return None

    # =========================================================================
    # WORKFLOW
    # =========================================================================

    def get_plans_by_status(self, status: PlanStatus) -> List[PlanReview]:
        """Recupera piani per status"""
        return [r for r in self.reviews.values() if r.status == status]

    def get_sections_needing_review(self, plan_id: str) -> List[SectionReview]:
        """Recupera sezioni che necessitano review"""
        review = self.reviews.get(plan_id)
        if not review:
            return []

        return [
            s for s in review.sections.values()
            if s.status in [SectionStatus.NEEDS_REVIEW, SectionStatus.DRAFT]
        ]

    def assign_plan(self, plan_id: str, assignee: str) -> bool:
        """Assegna piano a reviewer"""
        review = self.reviews.get(plan_id)
        if not review:
            return False

        review.assigned_to = assignee
        review.status = PlanStatus.IN_REVIEW
        review.last_modified = datetime.now().isoformat()

        self._save_reviews()
        return True

    def finalize_plan(self, plan_id: str, approval_notes: str = "") -> bool:
        """
        Finalizza piano per export.
        Verifica che tutte le sezioni siano approvate.
        """
        review = self.reviews.get(plan_id)
        if not review:
            return False

        # Verifica tutte approvate
        pending = [
            s.section_title for s in review.sections.values()
            if s.status != SectionStatus.APPROVED
        ]

        if pending:
            logger.warning(f"Cannot finalize: sections pending: {pending}")
            return False

        review.status = PlanStatus.READY
        review.approval_notes = approval_notes
        review.last_modified = datetime.now().isoformat()

        self._save_reviews()
        return True

    def mark_exported(self, plan_id: str, export_path: str) -> bool:
        """Marca piano come esportato"""
        review = self.reviews.get(plan_id)
        if not review:
            return False

        review.status = PlanStatus.EXPORTED
        review.export_count += 1
        review.last_modified = datetime.now().isoformat()

        self._save_reviews()
        return True

    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================

    def bulk_approve_sections(
        self,
        plan_id: str,
        section_ids: List[str],
        approver: str = "user"
    ) -> int:
        """Approva multiple sezioni"""
        count = 0
        for section_id in section_ids:
            if self.approve_section(plan_id, section_id, approver):
                count += 1
        return count

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Statistiche per dashboard"""
        stats = {
            'total_plans': len(self.reviews),
            'by_status': {},
            'sections_needing_review': 0,
            'average_credibility': 0,
            'recent_plans': [],
        }

        credibility_scores = []

        for status in PlanStatus:
            stats['by_status'][status.value] = 0

        for review in self.reviews.values():
            stats['by_status'][review.status.value] += 1

            for section in review.sections.values():
                if section.status in [SectionStatus.NEEDS_REVIEW, SectionStatus.DRAFT]:
                    stats['sections_needing_review'] += 1
                if section.credibility_score > 0:
                    credibility_scores.append(section.credibility_score)

        if credibility_scores:
            stats['average_credibility'] = round(
                sum(credibility_scores) / len(credibility_scores), 1
            )

        # Recent 10 plans
        sorted_reviews = sorted(
            self.reviews.values(),
            key=lambda r: r.last_modified,
            reverse=True
        )
        stats['recent_plans'] = [
            {
                'plan_id': r.plan_id,
                'club_name': r.club_name,
                'status': r.status.value,
                'last_modified': r.last_modified,
            }
            for r in sorted_reviews[:10]
        ]

        return stats

    def export_plan_for_final(self, plan_id: str) -> Dict[str, str]:
        """
        Esporta piano per export finale.
        Assembla tutte le sezioni approvate.
        Filtra sezioni None o vuote.
        """
        review = self.reviews.get(plan_id)
        if not review:
            return {}

        plan_data = {}
        for section_id, section in review.sections.items():
            # Filtra contenuti None o vuoti
            content = section.content
            if content is not None and isinstance(content, str) and content.strip():
                plan_data[section_id] = content
            else:
                # Log per debug
                import logging
                logging.getLogger(__name__).warning(
                    f"Sezione '{section_id}' saltata: contenuto None o vuoto"
                )

        return plan_data

    # =========================================================================
    # CLEANUP
    # =========================================================================

    def archive_plan(self, plan_id: str) -> bool:
        """Archivia piano"""
        review = self.reviews.get(plan_id)
        if not review:
            return False

        review.status = PlanStatus.ARCHIVED
        review.last_modified = datetime.now().isoformat()

        self._save_reviews()
        return True

    def delete_plan(self, plan_id: str) -> bool:
        """Elimina piano (soft delete -> archive first)"""
        if plan_id in self.reviews:
            self.archive_plan(plan_id)
            del self.reviews[plan_id]
            self._save_reviews()
            return True
        return False


# =============================================================================
# BATCH REVIEW MANAGER
# =============================================================================

class BatchReviewManager:
    """
    Gestisce review di batch di piani.
    Ottimizzato per 200+ piani.
    """

    def __init__(self):
        self.editor = PostProductionEditor()

    def get_workload_summary(self) -> Dict[str, Any]:
        """Sommario carico di lavoro"""
        stats = self.editor.get_dashboard_stats()

        # Calcola effort stimato
        sections_to_review = stats['sections_needing_review']
        avg_time_per_section = 5  # minuti
        estimated_hours = (sections_to_review * avg_time_per_section) / 60

        return {
            **stats,
            'estimated_review_hours': round(estimated_hours, 1),
            'suggested_daily_quota': max(1, sections_to_review // 5),  # 5 giorni lavorativi
        }

    def auto_approve_high_credibility(
        self,
        min_credibility: float = 80.0,
        approver: str = "auto_approval_system"
    ) -> int:
        """
        Auto-approva sezioni con alta credibilità.
        Risparmia tempo su sezioni già verificate.
        """
        approved_count = 0

        for review in self.editor.reviews.values():
            for section in review.sections.values():
                if (section.status == SectionStatus.DRAFT and
                    section.credibility_score >= min_credibility and
                    not section.unverified_claims):

                    self.editor.approve_section(
                        review.plan_id,
                        section.section_id,
                        approver
                    )
                    approved_count += 1

        return approved_count

    def get_priority_queue(self) -> List[Dict]:
        """
        Restituisce coda prioritizzata di sezioni da revisionare.
        Priorità basata su: status, credibilità, data creazione.
        """
        priority_queue = []

        for review in self.editor.reviews.values():
            if review.status in [PlanStatus.DRAFT, PlanStatus.IN_REVIEW]:
                for section in review.sections.values():
                    if section.status in [SectionStatus.NEEDS_REVIEW, SectionStatus.DRAFT]:
                        priority = self._calculate_priority(section)
                        priority_queue.append({
                            'plan_id': review.plan_id,
                            'club_name': review.club_name,
                            'section_id': section.section_id,
                            'section_title': section.section_title,
                            'priority': priority,
                            'credibility': section.credibility_score,
                            'unverified_count': len(section.unverified_claims),
                        })

        # Ordina per priorità (alta = urgente)
        priority_queue.sort(key=lambda x: x['priority'], reverse=True)

        return priority_queue

    def _calculate_priority(self, section: SectionReview) -> float:
        """
        Calcola priorità sezione.
        Alto = più urgente.
        """
        priority = 0

        # Status weight
        if section.status == SectionStatus.NEEDS_REVIEW:
            priority += 50
        elif section.status == SectionStatus.DRAFT:
            priority += 30

        # Credibilità inversa (bassa credibilità = alta priorità)
        priority += (100 - section.credibility_score)

        # Numero claims non verificati
        priority += len(section.unverified_claims) * 5

        return priority

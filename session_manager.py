"""
Rooting Future Strategy Engine - Session Management & Recovery
REF-003: Incremental checkpoint system for resilient plan generation

Enables:
- Incremental saves during generation
- Recovery from crashes/interruptions
- Progress tracking across page refreshes
- Audit trail for debugging
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Generation session statuses"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GenerationSession:
    """
    Represents a strategic plan generation session with checkpoint support.
    """
    session_id: str
    club_name: str
    status: SessionStatus
    created_at: str
    updated_at: str
    completed_sections: List[str] = field(default_factory=list)
    pending_sections: List[str] = field(default_factory=list)
    partial_plan: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_log: List[str] = field(default_factory=list)
    owner_id: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['status'] = self.status.value  # Convert enum to string
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'GenerationSession':
        """Create from dictionary"""
        # Convert status string back to enum
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = SessionStatus(data['status'])
        return cls(**data)

    def add_completed_section(self, section_key: str, content: Any):
        """Mark section as completed and store its content"""
        if section_key not in self.completed_sections:
            self.completed_sections.append(section_key)

        if section_key in self.pending_sections:
            self.pending_sections.remove(section_key)

        self.partial_plan[section_key] = content
        self.updated_at = datetime.now().isoformat()

    def log_error(self, error_message: str):
        """Add error to session log"""
        self.error_log.append({
            'timestamp': datetime.now().isoformat(),
            'message': error_message
        })
        self.updated_at = datetime.now().isoformat()

    @property
    def progress_percentage(self) -> float:
        """Calculate completion percentage"""
        total = len(self.completed_sections) + len(self.pending_sections)
        if total == 0:
            return 0.0
        return (len(self.completed_sections) / total) * 100


class SessionManager:
    """
    Manages generation sessions with incremental checkpointing and recovery.

    Features:
    - Atomic checkpoint saves
    - Session recovery after crashes
    - Progress tracking
    - Automatic cleanup of old sessions
    """

    def __init__(self, store=None, session_ttl_hours: int = 24):
        """
        Args:
            store: KnowledgeStore instance for persistence
            session_ttl_hours: Hours before session expires (default 24)
        """
        self.store = store
        self.session_ttl_hours = session_ttl_hours
        self._active_sessions: Dict[str, GenerationSession] = {}
        logger.info(f"SessionManager initialized with TTL={session_ttl_hours}h")

    def create_session(
        self,
        club_name: str,
        club_data: Dict,
        sections_to_generate: List[str],
        owner_id: Optional[int] = None
    ) -> GenerationSession:
        """
        Create a new generation session.

        Args:
            club_name: Name of the club
            club_data: Input data for generation
            sections_to_generate: List of section keys to generate
            owner_id: User ID who owns this session

        Returns:
            GenerationSession object
        """
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        session = GenerationSession(
            session_id=session_id,
            club_name=club_name,
            status=SessionStatus.PENDING,
            created_at=now,
            updated_at=now,
            completed_sections=[],
            pending_sections=sections_to_generate.copy(),
            partial_plan={},
            metadata={
                'club_data': club_data,
                'total_sections': len(sections_to_generate),
            },
            error_log=[],
            owner_id=owner_id
        )

        # Save to database if store available
        if self.store:
            self._persist_session(session)

        # Keep in memory cache
        self._active_sessions[session_id] = session

        logger.info(f"Created session {session_id} for {club_name} with {len(sections_to_generate)} sections")
        return session

    def save_checkpoint(
        self,
        session_id: str,
        section_key: str,
        section_content: Any,
        metadata_update: Optional[Dict] = None
    ) -> bool:
        """
        Save incremental checkpoint for a section.

        Args:
            session_id: Session identifier
            section_key: Section that was completed
            section_content: Generated content for section
            metadata_update: Optional metadata updates

        Returns:
            True if checkpoint saved successfully
        """
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found for checkpoint")
            return False

        try:
            # Update session state
            session.add_completed_section(section_key, section_content)
            session.status = SessionStatus.IN_PROGRESS

            # Update metadata if provided
            if metadata_update:
                session.metadata.update(metadata_update)

            # Persist to database
            if self.store:
                self._persist_session(session)

            logger.info(
                f"Checkpoint saved for {session_id}: {section_key} "
                f"({session.progress_percentage:.1f}% complete)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save checkpoint for {session_id}: {e}")
            session.log_error(f"Checkpoint failure: {str(e)}")
            return False

    def get_session(self, session_id: str) -> Optional[GenerationSession]:
        """
        Retrieve session by ID.

        Args:
            session_id: Session identifier

        Returns:
            GenerationSession or None if not found
        """
        # Check memory cache first
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]

        # Load from database
        if self.store:
            session_data = self.store.get_generation_session(session_id)
            if session_data:
                session = GenerationSession.from_dict(session_data)
                # Cache in memory
                self._active_sessions[session_id] = session
                return session

        return None

    def mark_completed(self, session_id: str, final_plan: Dict, sources: List = None) -> bool:
        """
        Mark session as completed with final plan.

        Args:
            session_id: Session identifier
            final_plan: Complete generated plan
            sources: Optional list of sources used

        Returns:
            True if marked successfully
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.status = SessionStatus.COMPLETED
        session.partial_plan = final_plan
        session.updated_at = datetime.now().isoformat()

        if sources:
            session.metadata['sources'] = sources

        if self.store:
            self._persist_session(session)

        logger.info(f"Session {session_id} marked as completed")
        return True

    def mark_failed(self, session_id: str, error_message: str) -> bool:
        """
        Mark session as failed with error.

        Args:
            session_id: Session identifier
            error_message: Error description

        Returns:
            True if marked successfully
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.status = SessionStatus.FAILED
        session.log_error(error_message)

        if self.store:
            self._persist_session(session)

        logger.warning(f"Session {session_id} marked as failed: {error_message}")
        return True

    def can_resume(self, session_id: str) -> bool:
        """
        Check if session can be resumed.

        Args:
            session_id: Session identifier

        Returns:
            True if session exists and is resumable
        """
        session = self.get_session(session_id)
        if not session:
            return False

        # Can resume if in-progress or failed with partial data
        return session.status in [SessionStatus.IN_PROGRESS, SessionStatus.FAILED, SessionStatus.PENDING]

    def get_resume_data(self, session_id: str) -> Optional[Dict]:
        """
        Get data needed to resume a session.

        Returns:
            Dict with club_data, completed_sections, pending_sections
        """
        session = self.get_session(session_id)
        if not session or not self.can_resume(session_id):
            return None

        return {
            'session_id': session.session_id,
            'club_name': session.club_name,
            'club_data': session.metadata.get('club_data', {}),
            'completed_sections': session.completed_sections,
            'pending_sections': session.pending_sections,
            'partial_plan': session.partial_plan,
            'progress': session.progress_percentage
        }

    def cleanup_expired_sessions(self) -> int:
        """
        Remove sessions older than TTL.

        Returns:
            Number of sessions cleaned up
        """
        if not self.store:
            return 0

        cutoff = datetime.now() - timedelta(hours=self.session_ttl_hours)
        cutoff_str = cutoff.isoformat()

        count = self.store.delete_expired_sessions(cutoff_str)

        # Clear from memory cache
        expired_ids = [
            sid for sid, session in self._active_sessions.items()
            if session.updated_at < cutoff_str
        ]
        for sid in expired_ids:
            del self._active_sessions[sid]

        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")

        return count

    def list_user_sessions(self, owner_id: int, status_filter: Optional[SessionStatus] = None) -> List[Dict]:
        """
        List all sessions for a user.

        Args:
            owner_id: User ID
            status_filter: Optional status to filter by

        Returns:
            List of session summary dicts
        """
        if not self.store:
            return []

        sessions = self.store.get_user_sessions(owner_id, status_filter.value if status_filter else None)
        return sessions

    def _persist_session(self, session: GenerationSession):
        """Save session to database"""
        if not self.store:
            return

        try:
            self.store.save_generation_session(session.to_dict())
        except Exception as e:
            logger.error(f"Failed to persist session {session.session_id}: {e}")
            raise


# Global instance (will be initialized in app.py)
session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    if session_manager is None:
        raise RuntimeError("SessionManager not initialized. Call init_session_manager() first.")
    return session_manager


def init_session_manager(store=None, ttl_hours: int = 24) -> SessionManager:
    """
    Initialize global session manager.

    Args:
        store: KnowledgeStore instance
        ttl_hours: Session TTL in hours

    Returns:
        SessionManager instance
    """
    global session_manager
    session_manager = SessionManager(store, ttl_hours)
    return session_manager

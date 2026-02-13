"""
Progress Tracker - Real-time Generation Progress via SSE

UX-001-B: Loading States & Progress
Provides real-time feedback during plan generation.

Features:
- Thread-safe progress storage
- SSE (Server-Sent Events) streaming
- Step-by-step progress updates
- Percentage calculation
- ETA estimation

Usage:
    # In route - start tracking
    tracker = ProgressTracker()
    project_id = tracker.start_generation(club_name="AC Milan", stakeholder_count=3)

    # In orchestrator - update progress
    tracker.update_step(project_id, "stakeholder_analysis", "Analizzati 2/3 stakeholder...")
    tracker.update_agent(project_id, "STW Sportivi", completed=True)

    # In SSE endpoint - stream updates
    @app.route('/api/progress/<project_id>')
    def stream_progress(project_id):
        return tracker.stream(project_id)
"""

import time
import json
import threading
from typing import Dict, Any, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class GenerationStep(Enum):
    """Steps in the generation process."""
    UPLOAD = "upload"
    STAKEHOLDER_ANALYSIS = "stakeholder_analysis"
    WEB_RESEARCH = "web_research"
    AGENT_GENERATION = "agent_generation"
    STRUCTURED_DATA = "structured_data"
    REVIEW_CREATION = "review_creation"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class StepInfo:
    """Information about a generation step."""
    name: str
    label_it: str  # Italian label for UI
    weight: int  # Percentage weight in total progress
    icon: str


# Step definitions with weights (total = 100)
GENERATION_STEPS: Dict[str, StepInfo] = {
    "upload": StepInfo("upload", "File caricati", 5, "📁"),
    "stakeholder_analysis": StepInfo("stakeholder_analysis", "Analisi stakeholder", 10, "👥"),
    "web_research": StepInfo("web_research", "Ricerca web", 10, "🔍"),
    "agent_generation": StepInfo("agent_generation", "Generazione piano", 55, "🤖"),
    "structured_data": StepInfo("structured_data", "Dati strutturati", 10, "📊"),
    "review_creation": StepInfo("review_creation", "Creazione review", 5, "✏️"),
    "complete": StepInfo("complete", "Piano completato!", 5, "🎉"),
}

# Agent names and their display labels
AGENT_LABELS = {
    "coordinator": "Coordinatore",
    "stw_sportivi": "Obiettivi Sportivi",
    "stw_strutturali": "Obiettivi Strutturali",
    "stw_marketing": "Marketing",
    "stw_sociali": "Obiettivi Sociali",
    "financial": "Piano Finanziario",
}


@dataclass
class GenerationProgress:
    """Progress state for a generation process."""
    project_id: str
    club_name: str
    started_at: datetime
    current_step: str = "upload"
    current_step_message: str = ""
    percent: int = 0
    agents_completed: int = 0
    agents_total: int = 6
    stakeholders_processed: int = 0
    stakeholders_total: int = 0
    error: Optional[str] = None
    completed: bool = False
    last_update: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        step_info = GENERATION_STEPS.get(self.current_step)
        return {
            "project_id": self.project_id,
            "club_name": self.club_name,
            "step": self.current_step,
            "step_label": step_info.label_it if step_info else self.current_step,
            "step_icon": step_info.icon if step_info else "⏳",
            "message": self.current_step_message,
            "percent": self.percent,
            "agents_completed": self.agents_completed,
            "agents_total": self.agents_total,
            "stakeholders_processed": self.stakeholders_processed,
            "stakeholders_total": self.stakeholders_total,
            "error": self.error,
            "completed": self.completed,
            "elapsed_seconds": (datetime.now() - self.started_at).total_seconds(),
        }


class ProgressTracker:
    """
    Thread-safe progress tracker for plan generation.

    Supports multiple concurrent generations.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern for global access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._progress: Dict[str, GenerationProgress] = {}
        self._subscribers: Dict[str, list] = {}  # project_id -> list of queues
        self._lock = threading.Lock()
        self._initialized = True

    def start_generation(
        self,
        project_id: str,
        club_name: str,
        stakeholder_count: int = 0
    ) -> str:
        """
        Start tracking a new generation.

        Args:
            project_id: Unique ID for this generation
            club_name: Name of the club
            stakeholder_count: Number of stakeholders to process

        Returns:
            project_id for reference
        """
        with self._lock:
            self._progress[project_id] = GenerationProgress(
                project_id=project_id,
                club_name=club_name,
                started_at=datetime.now(),
                stakeholders_total=stakeholder_count,
                current_step_message=f"Avvio generazione per {club_name}..."
            )
            self._subscribers[project_id] = []
        return project_id

    def update_step(
        self,
        project_id: str,
        step: str,
        message: str = "",
        percent_override: int = None
    ) -> None:
        """
        Update the current step.

        Args:
            project_id: Generation ID
            step: Step name (from GenerationStep enum)
            message: Optional message to display
            percent_override: Override calculated percentage
        """
        with self._lock:
            if project_id not in self._progress:
                return

            progress = self._progress[project_id]
            progress.current_step = step
            progress.current_step_message = message
            progress.last_update = datetime.now()

            # Calculate percentage based on step weights
            if percent_override is not None:
                progress.percent = percent_override
            else:
                progress.percent = self._calculate_percent(progress)

            if step == "complete":
                progress.completed = True
                progress.percent = 100

            self._notify_subscribers(project_id)

    def update_agent(
        self,
        project_id: str,
        agent_name: str,
        completed: bool = True,
        duration_seconds: float = None
    ) -> None:
        """
        Update agent completion status.

        Args:
            project_id: Generation ID
            agent_name: Name of the agent
            completed: Whether agent completed
            duration_seconds: How long the agent took
        """
        with self._lock:
            if project_id not in self._progress:
                return

            progress = self._progress[project_id]

            if completed:
                progress.agents_completed += 1

            agent_label = AGENT_LABELS.get(agent_name.lower(), agent_name)
            duration_str = f" ({duration_seconds:.1f}s)" if duration_seconds else ""

            progress.current_step_message = (
                f"✅ {agent_label} completato{duration_str} "
                f"({progress.agents_completed}/{progress.agents_total})"
            )
            progress.last_update = datetime.now()

            # Recalculate percent
            progress.percent = self._calculate_percent(progress)

            self._notify_subscribers(project_id)

    def update_stakeholder(
        self,
        project_id: str,
        processed: int,
        total: int
    ) -> None:
        """
        Update stakeholder processing progress.

        Args:
            project_id: Generation ID
            processed: Number processed so far
            total: Total number to process
        """
        with self._lock:
            if project_id not in self._progress:
                return

            progress = self._progress[project_id]
            progress.stakeholders_processed = processed
            progress.stakeholders_total = total
            progress.current_step_message = f"Analizzati {processed}/{total} stakeholder..."
            progress.last_update = datetime.now()

            self._notify_subscribers(project_id)

    def set_error(self, project_id: str, error_message: str) -> None:
        """
        Mark generation as failed.

        Args:
            project_id: Generation ID
            error_message: Error description
        """
        with self._lock:
            if project_id not in self._progress:
                return

            progress = self._progress[project_id]
            progress.current_step = "error"
            progress.error = error_message
            progress.current_step_message = f"❌ Errore: {error_message}"
            progress.last_update = datetime.now()

            self._notify_subscribers(project_id)

    def complete(self, project_id: str, plan_id: str = None) -> None:
        """
        Mark generation as complete.

        Args:
            project_id: Generation ID
            plan_id: Generated plan ID
        """
        self.update_step(
            project_id,
            "complete",
            f"🎉 Piano generato con successo!" + (f" ID: {plan_id}" if plan_id else ""),
            percent_override=100
        )

    def get_progress(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current progress for a generation.

        Args:
            project_id: Generation ID

        Returns:
            Progress dict or None if not found
        """
        with self._lock:
            if project_id in self._progress:
                return self._progress[project_id].to_dict()
        return None

    def stream(self, project_id: str) -> Generator[str, None, None]:
        """
        Stream progress updates via SSE.

        Args:
            project_id: Generation ID

        Yields:
            SSE-formatted progress updates
        """
        import queue

        q = queue.Queue()

        # Register subscriber
        with self._lock:
            if project_id not in self._subscribers:
                self._subscribers[project_id] = []
            self._subscribers[project_id].append(q)

        try:
            # Send initial state
            progress = self.get_progress(project_id)
            if progress:
                yield f"data: {json.dumps(progress)}\n\n"

            # Stream updates
            while True:
                try:
                    # Wait for update with timeout
                    data = q.get(timeout=30)

                    if data is None:  # Sentinel for completion
                        break

                    yield f"data: {json.dumps(data)}\n\n"

                    if data.get("completed") or data.get("error"):
                        break

                except queue.Empty:
                    # Send keepalive
                    yield f": keepalive\n\n"

        finally:
            # Unregister subscriber
            with self._lock:
                if project_id in self._subscribers and q in self._subscribers[project_id]:
                    self._subscribers[project_id].remove(q)

    def cleanup(self, project_id: str) -> None:
        """
        Clean up progress data for completed generation.

        Args:
            project_id: Generation ID
        """
        with self._lock:
            if project_id in self._progress:
                del self._progress[project_id]
            if project_id in self._subscribers:
                # Send sentinel to close streams
                for q in self._subscribers[project_id]:
                    q.put(None)
                del self._subscribers[project_id]

    def _calculate_percent(self, progress: GenerationProgress) -> int:
        """Calculate overall percentage based on current state."""
        step = progress.current_step
        step_info = GENERATION_STEPS.get(step)

        if not step_info:
            return 0

        # Base percentage from completed steps
        base_percent = 0
        for s_name, s_info in GENERATION_STEPS.items():
            if s_name == step:
                break
            base_percent += s_info.weight

        # Add progress within current step
        if step == "agent_generation" and progress.agents_total > 0:
            agent_progress = (progress.agents_completed / progress.agents_total) * step_info.weight
            return int(base_percent + agent_progress)

        if step == "stakeholder_analysis" and progress.stakeholders_total > 0:
            stakeholder_progress = (progress.stakeholders_processed / progress.stakeholders_total) * step_info.weight
            return int(base_percent + stakeholder_progress)

        return base_percent

    def _notify_subscribers(self, project_id: str) -> None:
        """Notify all subscribers of progress update."""
        if project_id not in self._subscribers:
            return

        progress = self._progress[project_id].to_dict()
        for q in self._subscribers[project_id]:
            try:
                q.put_nowait(progress)
            except:
                pass


# Global singleton instance
progress_tracker = ProgressTracker()


# Convenience functions
def start_tracking(project_id: str, club_name: str, stakeholder_count: int = 0) -> str:
    """Start tracking a generation."""
    return progress_tracker.start_generation(project_id, club_name, stakeholder_count)


def update_progress(project_id: str, step: str, message: str = "") -> None:
    """Update progress step."""
    progress_tracker.update_step(project_id, step, message)


def update_agent_progress(project_id: str, agent_name: str, duration: float = None) -> None:
    """Update agent completion."""
    progress_tracker.update_agent(project_id, agent_name, completed=True, duration_seconds=duration)


def complete_tracking(project_id: str, plan_id: str = None) -> None:
    """Mark generation as complete."""
    progress_tracker.complete(project_id, plan_id)


def get_progress(project_id: str) -> Optional[Dict[str, Any]]:
    """Get current progress."""
    return progress_tracker.get_progress(project_id)

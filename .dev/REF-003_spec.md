# REF-003: Session Management & Recovery Optimization

## Obiettivo
Implementare sistema di checkpoint incrementali e recovery per la generazione dei piani strategici, permettendo di riprendere sessioni interrotte.

## Problemi Attuali
1. **No checkpoint durante generazione**: Se crasha, si perde tutto
2. **No recovery mechanism**: Non c'è modo di riprendere una generazione fallita
3. **Stato volatile**: Lo stato della generazione esiste solo in memoria
4. **No progress tracking persistente**: L'utente non può vedere lo stato dopo un refresh

## Soluzione Proposta

### 1. Session State Model
```python
@dataclass
class GenerationSession:
    session_id: str
    club_name: str
    status: str  # 'pending', 'in_progress', 'completed', 'failed'
    created_at: datetime
    updated_at: datetime
    completed_sections: List[str]
    pending_sections: List[str]
    partial_plan: Dict[str, Any]
    metadata: Dict[str, Any]
    error_log: List[str]
```

### 2. Incremental Checkpointing
- **Checkpoint dopo ogni agente**: Salva sezione completata
- **Atomic updates**: Ogni checkpoint è transazionale
- **Versioning**: Mantieni storico dei checkpoint

### 3. Recovery API Endpoints
- `POST /api/session/resume/{session_id}` - Riprendi generazione
- `GET /api/session/status/{session_id}` - Stato sessione
- `DELETE /api/session/{session_id}` - Cancella sessione

### 4. Database Schema
```sql
CREATE TABLE generation_sessions (
    session_id TEXT PRIMARY KEY,
    club_name TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_sections TEXT,  -- JSON array
    pending_sections TEXT,    -- JSON array
    partial_plan TEXT,        -- JSON object
    metadata TEXT,            -- JSON object
    error_log TEXT,           -- JSON array
    owner_id INTEGER,
    FOREIGN KEY(owner_id) REFERENCES users(id)
);

CREATE INDEX idx_sessions_status ON generation_sessions(status);
CREATE INDEX idx_sessions_owner ON generation_sessions(owner_id);
```

## Implementation Steps

### Step 1: Add Session Storage Layer (session_manager.py)
- SessionManager class
- save_checkpoint()
- load_session()
- resume_generation()

### Step 2: Modify MultiAgentOrchestrator
- Add checkpoint callbacks
- Save after each agent completion
- Load existing state on resume

### Step 3: Update API Routes
- Add session endpoints
- Modify /api/generate to create session
- Add session_id to response

### Step 4: Frontend Integration
- Show recovery UI for failed sessions
- Auto-resume on page refresh
- Progress persistence

## Target Metrics
- ✅ 0% data loss on crash
- ✅ < 5s recovery time
- ✅ Session persistence for 24h
- ✅ Minimal performance overhead (< 2%)

## Expected LOC Changes
- session_manager.py: +250 LOC (new file)
- knowledge_store.py: +80 LOC (session table)
- agents.py: +40 LOC (checkpoint hooks)
- app.py: +60 LOC (session endpoints)
- Total: +430 LOC (net +430, no deletions expected)

## Testing Plan
1. Generate plan → kill process mid-generation → resume → verify completion
2. Multiple concurrent sessions
3. Session timeout/cleanup
4. Database transaction rollback on error

## Benefits
1. **Resilience**: Generazioni possono essere riprese dopo crash
2. **User Experience**: Visibilità dello stato anche dopo refresh
3. **Debugging**: Error log persistente per troubleshooting
4. **Cost savings**: No wasted API calls on retry

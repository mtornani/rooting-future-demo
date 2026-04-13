#!/usr/bin/env python3
"""
A/B Test — Confronto tra due modelli Ollama
============================================
Esegue la pipeline multi-agente con il modello A e il modello B,
confronta output e tempi, genera un report HTML.

Fixes implementati:
  Fix 1: Warmup cold start prima del loop agenti
  Fix 2: Agenti ordinati per lunghezza prompt crescente
  Fix 4: Logging diagnostico dettagliato per ogni agente
  Fix 5: Retry con backoff esponenziale intelligente

Uso:
    python ab_test.py --model-a llama3.2 --model-b qwen2.5 [opzioni]

    Variabili d'ambiente utili:
        OLLAMA_BASE_URL       URL server Ollama  (default: http://localhost:11434)
        OLLAMA_TIMEOUT        Timeout richiesta  (default: 120s)
        OLLAMA_MAX_RETRIES    Max retry          (default: 4)
        OLLAMA_WARMUP_RETRIES Retry warmup       (default: 3)
        OLLAMA_CHUNK_THRESHOLD Soglia chunking   (default: 32000 char)
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Setup logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ab_test")

# ---------------------------------------------------------------------------
# Imports locali
# ---------------------------------------------------------------------------

from ollama_provider import (
    OllamaProvider,
    AgentDiagnostics,
    warmup_ollama,
    compute_prompt_length,
    estimate_tokens,
    OLLAMA_BASE_URL,
    OLLAMA_MAX_RETRIES,
    OLLAMA_WARMUP_RETRIES,
)

# ---------------------------------------------------------------------------
# Dati club di esempio per i test
# ---------------------------------------------------------------------------

SAMPLE_CLUB_DATA: Dict[str, Any] = {
    "club_name": "ASD Test FC",
    "category": "Promozione",
    "region": "Emilia-Romagna",
    "country": "Italy",
    "founded_year": 1985,
    "stadium_name": "Campo Comunale",
    "stadium_capacity": 800,
    "current_players": 22,
    "youth_teams": 3,
    "annual_budget": 80000,
    "main_sponsor": "Nessuno",
    "social_media_followers": 450,
    "primary_color": "#1a365d",
    "secondary_color": "#ffffff",
    "plan_id": f"ab_test_{int(time.time())}",
}

# ---------------------------------------------------------------------------
# Definizione agenti con system prompt minimo (per stima lunghezza)
# ---------------------------------------------------------------------------

# Importiamo la specifica degli agenti per calcolare la lunghezza reale del prompt
try:
    from agents import AGENT_SPECS, AgentRole, GLOBAL_VOICE_DIRECTIVE
    _AGENT_SPECS_AVAILABLE = True
except ImportError:
    _AGENT_SPECS_AVAILABLE = False
    logger.warning("agents.py non importabile — uso lunghezze stimate.")

# Lunghezze approssimative dei system prompt (char) — usate come fallback
_FALLBACK_AGENT_PROMPT_LENGTHS: Dict[str, int] = {
    "Strategic Coordinator": 1200,
    "STW Strutturali Analyst": 2800,
    "STW Marketing Analyst": 2600,
    "Financial Strategist": 2400,
    "STW Sociali Analyst": 3200,
    "STW Sportivi Analyst": 3800,  # Il più lungo
}


# ---------------------------------------------------------------------------
# Fix 2: Riordinamento agenti per lunghezza prompt crescente
# ---------------------------------------------------------------------------

def sort_agents_by_prompt_length(
    agents: List[Dict[str, Any]],
    club_data: Dict[str, Any],
    rag_context_len: int = 0,
) -> List[Dict[str, Any]]:
    """
    Ordina gli agenti per lunghezza totale del prompt crescente.

    Così il modello si scalda sulle richieste più leggere prima di ricevere
    quelle pesanti (es. STW Sportivi).

    Args:
        agents: Lista di dict con chiavi 'name', 'system_prompt', 'role'
        club_data: Dati club (per stimare user_data)
        rag_context_len: Lunghezza media contesto RAG

    Returns:
        Lista ordinata per prompt_length_char crescente
    """
    user_data_str = json.dumps(club_data, ensure_ascii=False)

    for agent in agents:
        system_prompt = agent.get("system_prompt", "")
        lengths = compute_prompt_length(
            system_prompt=system_prompt,
            rag_context="X" * rag_context_len,
            cascading_context=agent.get("cascading_context", ""),
            user_data=user_data_str,
        )
        agent["_prompt_length_char"] = lengths["total_char"]
        agent["_prompt_length_tokens"] = lengths["total_tokens_stima"]

    sorted_agents = sorted(agents, key=lambda a: a["_prompt_length_char"])

    logger.info("[FIX2] Ordine agenti per lunghezza prompt (crescente):")
    for i, ag in enumerate(sorted_agents):
        logger.info(
            f"  {i+1}. {ag['name']:30s} "
            f"{ag['_prompt_length_char']:6d} char "
            f"(~{ag['_prompt_length_tokens']:4d} tok)"
        )

    return sorted_agents


def build_agent_list_from_specs() -> List[Dict[str, Any]]:
    """Costruisce lista agenti da AGENT_SPECS (se disponibile)."""
    if not _AGENT_SPECS_AVAILABLE:
        return _build_fallback_agent_list()

    agents = []
    for role, spec in AGENT_SPECS.items():
        if role == AgentRole.COORDINATOR:
            continue  # Coordinator gira dopo
        agents.append({
            "name": spec.name,
            "role": role.value,
            "system_prompt": spec.system_prompt,
            "cascading_context": "",
        })
    return agents


def _build_fallback_agent_list() -> List[Dict[str, Any]]:
    """Lista agenti fallback senza import da agents.py."""
    return [
        {"name": n, "role": n.lower().replace(" ", "_"), "system_prompt": "X" * l, "cascading_context": ""}
        for n, l in _FALLBACK_AGENT_PROMPT_LENGTHS.items()
        if n != "Strategic Coordinator"
    ]


# ---------------------------------------------------------------------------
# Fix 4: Logging diagnostico
# ---------------------------------------------------------------------------

class DiagnosticsCollector:
    """Raccoglie diagnostica per tutti gli agenti di un run."""

    def __init__(self, model: str, run_id: str):
        self.model = model
        self.run_id = run_id
        self.records: List[AgentDiagnostics] = []
        self.warmup_done: bool = False

    def new_record(self, agent_name: str) -> AgentDiagnostics:
        d = AgentDiagnostics(
            nome_agente=agent_name,
            modello=self.model,
            warmup_done=self.warmup_done,
        )
        self.records.append(d)
        return d

    def summary(self) -> Dict[str, Any]:
        total_time = sum(r.total_generation_seconds for r in self.records)
        failed = [r for r in self.records if not r.output_valid]
        return {
            "run_id": self.run_id,
            "model": self.model,
            "warmup_done": self.warmup_done,
            "total_agents": len(self.records),
            "failed_agents": len(failed),
            "total_time_seconds": round(total_time, 2),
            "agents": [r.to_dict() for r in self.records],
        }


# ---------------------------------------------------------------------------
# Core: esecuzione singolo modello
# ---------------------------------------------------------------------------

def run_model(
    model: str,
    club_data: Dict[str, Any],
    base_url: str = None,
    skip_warmup: bool = False,
) -> Tuple[Dict[str, Any], DiagnosticsCollector]:
    """
    Esegue la pipeline agenti per un modello specifico.

    Returns:
        (results_dict, diagnostics_collector)
    """
    run_id = f"{model}_{int(time.time())}"
    diag = DiagnosticsCollector(model=model, run_id=run_id)

    logger.info(f"\n{'='*60}")
    logger.info(f"[RUN] Modello: {model}")
    logger.info(f"[RUN] Run ID:  {run_id}")
    logger.info(f"{'='*60}")

    # Inizializza provider
    provider = OllamaProvider(
        model=model,
        base_url=base_url or os.environ.get("OLLAMA_BASE_URL", OLLAMA_BASE_URL),
    )

    # Fix 1: Warmup
    if not skip_warmup:
        logger.info("[FIX1] Avvio warmup cold start...")
        warmup_ok = warmup_ollama(provider)
        diag.warmup_done = warmup_ok
        if not warmup_ok:
            logger.warning("[FIX1] Warmup fallito — procedo comunque")
    else:
        logger.info("[FIX1] Warmup saltato (--skip-warmup)")

    # Fix 2: Costruisci e ordina agenti per lunghezza prompt
    agents = build_agent_list_from_specs()
    agents = sort_agents_by_prompt_length(agents, club_data)

    # Costruisci prompt utente base da club_data
    user_data_str = _build_user_prompt(club_data)

    results: Dict[str, str] = {}
    all_timings: Dict[str, float] = {}

    for agent in agents:
        agent_name = agent["name"]
        system_prompt = agent.get("system_prompt", "")
        full_prompt = system_prompt + "\n\n" + user_data_str

        # Fix 4: Diagnostica
        d = diag.new_record(agent_name)
        d.system_prompt_length = len(system_prompt)
        d.user_data_length = len(user_data_str)
        d.prompt_length_char = len(full_prompt)
        d.prompt_length_tokens_stima = estimate_tokens(full_prompt)

        logger.info(
            f"\n[AGENT] {agent_name} "
            f"| prompt {d.prompt_length_char}ch (~{d.prompt_length_tokens_stima}tok)"
        )

        # Fix 3/5: generate() con retry e chunking automatico
        t_start = time.time()
        try:
            output = provider.generate(
                prompt=user_data_str,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=8192,
                agent_name=agent_name,
                diagnostics=d,
            )
            elapsed = time.time() - t_start
            d.total_generation_seconds = elapsed
            d.output_length_char = len(output)
            d.output_valid = len(output.strip()) > 50
            d.http_status_code = 200
            results[agent["role"]] = output
            all_timings[agent_name] = round(elapsed, 2)
            logger.info(
                f"[AGENT] {agent_name} completato in {elapsed:.1f}s "
                f"| output: {len(output)} char"
            )
        except Exception as exc:
            elapsed = time.time() - t_start
            d.total_generation_seconds = elapsed
            d.output_valid = False
            d.error_message = str(exc)
            results[agent["role"]] = f"[ERRORE: {exc}]"
            all_timings[agent_name] = round(elapsed, 2)
            logger.error(f"[AGENT] {agent_name} FALLITO in {elapsed:.1f}s: {exc}")

        d.log_summary()

    logger.info(f"\n[RUN] Completato in {sum(all_timings.values()):.1f}s totali")

    return {
        "model": model,
        "results": results,
        "timings": all_timings,
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
    }, diag


def _build_user_prompt(club_data: Dict[str, Any]) -> str:
    """Costruisce il prompt utente base dai dati club."""
    lines = ["## DATI CLUB PER ANALISI STRATEGICA\n"]
    for k, v in club_data.items():
        if not k.startswith("_") and k != "plan_id":
            lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")
    lines.append(
        "\n\nGenera la sezione di tua competenza per questo club. "
        "Rispetta la struttura MACRO/MICRO richiesta."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report HTML (Fix 4 — sezione diagnostica)
# ---------------------------------------------------------------------------

def generate_html_report(
    model_a: str,
    model_b: str,
    result_a: Dict[str, Any],
    result_b: Dict[str, Any],
    diag_a: DiagnosticsCollector,
    diag_b: DiagnosticsCollector,
    output_path: str,
) -> None:
    """Genera report HTML con confronto A/B e tabella diagnostica."""

    def _diag_table(diag: DiagnosticsCollector) -> str:
        rows = ""
        for r in diag.records:
            status_color = "#2e7d32" if r.output_valid else "#c62828"
            status_label = "OK" if r.output_valid else "FAIL"
            error_cell = f'<span style="color:#c62828">{r.error_message[:80] if r.error_message else ""}</span>'
            rows += f"""
            <tr>
              <td>{r.nome_agente}</td>
              <td>{r.prompt_length_char:,}</td>
              <td>{r.prompt_length_tokens_stima:,}</td>
              <td>{'SI' if r.warmup_done else 'NO'}</td>
              <td>{r.attempt_number}</td>
              <td>{r.retry_wait_seconds}s</td>
              <td>{r.total_generation_seconds:.1f}s</td>
              <td>{r.output_length_char:,}</td>
              <td style="color:{status_color};font-weight:bold">{status_label}</td>
              <td>{error_cell}</td>
            </tr>"""
        return rows

    def _timings_bars(timings: Dict[str, float]) -> str:
        if not timings:
            return "<p>Nessun dato disponibile.</p>"
        max_t = max(timings.values()) or 1
        bars = ""
        for name, t in timings.items():
            pct = int(t / max_t * 100)
            bars += f"""
            <div style="margin:4px 0">
              <span style="display:inline-block;width:220px;font-size:12px">{name[:30]}</span>
              <span style="display:inline-block;background:#1565c0;height:14px;width:{pct}%;vertical-align:middle"></span>
              <span style="font-size:12px;margin-left:6px">{t:.1f}s</span>
            </div>"""
        return bars

    summary_a = diag_a.summary()
    summary_b = diag_b.summary()

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>A/B Test — {model_a} vs {model_b}</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f5f5f5; color: #222; }}
  .header {{ background: #1a237e; color: white; padding: 24px 32px; }}
  .header h1 {{ margin: 0; font-size: 24px; }}
  .header p {{ margin: 4px 0 0; opacity: .8; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 24px 32px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  .card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
  .card h2 {{ margin-top: 0; color: #1a237e; border-bottom: 2px solid #e8eaf6; padding-bottom: 8px; }}
  .badge-ok {{ background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 4px; font-size: 13px; }}
  .badge-fail {{ background: #ffebee; color: #c62828; padding: 2px 8px; border-radius: 4px; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #e8eaf6; color: #1a237e; padding: 8px; text-align: left; }}
  td {{ padding: 7px 8px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
  tr:hover {{ background: #fafafa; }}
  .stat {{ display: inline-block; margin: 8px 16px 8px 0; }}
  .stat .val {{ font-size: 28px; font-weight: bold; color: #1a237e; }}
  .stat .lbl {{ font-size: 12px; color: #666; }}
  pre {{ background: #f8f8f8; border: 1px solid #e0e0e0; border-radius: 4px; padding: 12px; font-size: 11px; overflow: auto; max-height: 300px; }}
  .section-title {{ background: #e8eaf6; padding: 10px 16px; border-radius: 4px; margin: 16px 0 8px; font-weight: bold; color: #1a237e; }}
</style>
</head>
<body>
<div class="header">
  <h1>A/B Test — Confronto Modelli Ollama</h1>
  <p>Generato il {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} |
     Club: {SAMPLE_CLUB_DATA['club_name']} ({SAMPLE_CLUB_DATA['category']})</p>
</div>
<div class="container">

  <!-- Riepilogo -->
  <div class="grid-2" style="margin-bottom:24px">
    <div class="card">
      <h2>Modello A: <code>{model_a}</code></h2>
      <div class="stat"><div class="val">{summary_a['total_agents']}</div><div class="lbl">Agenti totali</div></div>
      <div class="stat"><div class="val" style="color:{'#c62828' if summary_a['failed_agents'] else '#2e7d32'}">{summary_a['failed_agents']}</div><div class="lbl">Agenti falliti</div></div>
      <div class="stat"><div class="val">{summary_a['total_time_seconds']:.0f}s</div><div class="lbl">Tempo totale</div></div>
      <div class="stat"><div class="val">{'SI' if summary_a['warmup_done'] else 'NO'}</div><div class="lbl">Warmup OK</div></div>
    </div>
    <div class="card">
      <h2>Modello B: <code>{model_b}</code></h2>
      <div class="stat"><div class="val">{summary_b['total_agents']}</div><div class="lbl">Agenti totali</div></div>
      <div class="stat"><div class="val" style="color:{'#c62828' if summary_b['failed_agents'] else '#2e7d32'}">{summary_b['failed_agents']}</div><div class="lbl">Agenti falliti</div></div>
      <div class="stat"><div class="val">{summary_b['total_time_seconds']:.0f}s</div><div class="lbl">Tempo totale</div></div>
      <div class="stat"><div class="val">{'SI' if summary_b['warmup_done'] else 'NO'}</div><div class="lbl">Warmup OK</div></div>
    </div>
  </div>

  <!-- Tempi per agente -->
  <div class="grid-2" style="margin-bottom:24px">
    <div class="card">
      <h2>Tempi Agenti — {model_a}</h2>
      {_timings_bars(result_a.get('timings', {}))}
    </div>
    <div class="card">
      <h2>Tempi Agenti — {model_b}</h2>
      {_timings_bars(result_b.get('timings', {}))}
    </div>
  </div>

  <!-- Diagnostica A -->
  <div class="card" style="margin-bottom:24px">
    <h2>Diagnostica Agenti — {model_a}</h2>
    <table>
      <thead><tr>
        <th>Agente</th><th>Prompt (ch)</th><th>Token</th><th>Warmup</th>
        <th>Tentativo</th><th>Attesa</th><th>Tempo gen.</th><th>Output (ch)</th>
        <th>Stato</th><th>Errore</th>
      </tr></thead>
      <tbody>{_diag_table(diag_a)}</tbody>
    </table>
  </div>

  <!-- Diagnostica B -->
  <div class="card" style="margin-bottom:24px">
    <h2>Diagnostica Agenti — {model_b}</h2>
    <table>
      <thead><tr>
        <th>Agente</th><th>Prompt (ch)</th><th>Token</th><th>Warmup</th>
        <th>Tentativo</th><th>Attesa</th><th>Tempo gen.</th><th>Output (ch)</th>
        <th>Stato</th><th>Errore</th>
      </tr></thead>
      <tbody>{_diag_table(diag_b)}</tbody>
    </table>
  </div>

  <!-- JSON diagnostica completa -->
  <div class="card">
    <h2>JSON Diagnostica Completa</h2>
    <pre>{json.dumps({'model_a': summary_a, 'model_b': summary_b}, indent=2, ensure_ascii=False)}</pre>
  </div>

</div>
</body>
</html>"""

    Path(output_path).write_text(html, encoding="utf-8")
    logger.info(f"[REPORT] Salvato in: {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="A/B test tra due modelli Ollama sulla pipeline multi-agente"
    )
    parser.add_argument("--model-a", required=True, help="Modello A (es. llama3.2)")
    parser.add_argument("--model-b", required=True, help="Modello B (es. qwen2.5)")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OLLAMA_BASE_URL", OLLAMA_BASE_URL),
        help="URL base Ollama (default da OLLAMA_BASE_URL env)",
    )
    parser.add_argument(
        "--output",
        default=f"output/ab_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
        help="Path output report HTML",
    )
    parser.add_argument(
        "--skip-warmup",
        action="store_true",
        help="Salta il warmup (sconsigliato)",
    )
    parser.add_argument(
        "--club-data",
        default=None,
        help="Path a JSON con dati club personalizzati",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Carica dati club
    club_data = SAMPLE_CLUB_DATA.copy()
    if args.club_data:
        with open(args.club_data, encoding="utf-8") as f:
            club_data.update(json.load(f))
        logger.info(f"[MAIN] Dati club caricati da: {args.club_data}")
    else:
        logger.info("[MAIN] Uso dati club di esempio (ASD Test FC)")

    Path("output").mkdir(exist_ok=True)

    logger.info(f"\n[MAIN] === A/B TEST: {args.model_a} vs {args.model_b} ===\n")

    # Run modello A
    logger.info(f"[MAIN] --- RUN A: {args.model_a} ---")
    result_a, diag_a = run_model(
        model=args.model_a,
        club_data=club_data,
        base_url=args.base_url,
        skip_warmup=args.skip_warmup,
    )

    # Run modello B
    logger.info(f"\n[MAIN] --- RUN B: {args.model_b} ---")
    result_b, diag_b = run_model(
        model=args.model_b,
        club_data=club_data,
        base_url=args.base_url,
        skip_warmup=args.skip_warmup,
    )

    # Report
    generate_html_report(
        model_a=args.model_a,
        model_b=args.model_b,
        result_a=result_a,
        result_b=result_b,
        diag_a=diag_a,
        diag_b=diag_b,
        output_path=args.output,
    )

    # Stampa riepilogo console
    sa = diag_a.summary()
    sb = diag_b.summary()
    print("\n" + "=" * 60)
    print("RIEPILOGO A/B TEST")
    print("=" * 60)
    print(f"{'Modello':<30} {'Agenti OK':<12} {'Falliti':<10} {'Tempo tot':<12}")
    print(f"{'-'*60}")
    ok_a = sa['total_agents'] - sa['failed_agents']
    ok_b = sb['total_agents'] - sb['failed_agents']
    print(f"{args.model_a:<30} {ok_a}/{sa['total_agents']:<10} {sa['failed_agents']:<10} {sa['total_time_seconds']:.1f}s")
    print(f"{args.model_b:<30} {ok_b}/{sb['total_agents']:<10} {sb['failed_agents']:<10} {sb['total_time_seconds']:.1f}s")
    print(f"\nReport HTML: {args.output}")

    # Salva anche JSON diagnostica
    json_path = args.output.replace(".html", "_diag.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"model_a": sa, "model_b": sb}, f, indent=2, ensure_ascii=False)
    logger.info(f"[MAIN] JSON diagnostica: {json_path}")


if __name__ == "__main__":
    main()

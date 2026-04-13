#!/usr/bin/env python3
"""
Model Benchmark — Pipeline Multi-Agente su N Modelli Ollama
=============================================================
Esegue la pipeline multi-agente con una lista di modelli,
misura performance e genera report HTML con tabella diagnostica.

Fixes implementati:
  Fix 1: Warmup cold start prima del loop agenti per ogni modello
  Fix 2: Agenti ordinati per lunghezza prompt crescente
  Fix 4: Logging diagnostico dettagliato per ogni agente/modello
  Fix 5: Retry con backoff esponenziale intelligente
  Fix 3: Chunking automatico se prompt > OLLAMA_CHUNK_THRESHOLD

Uso:
    python model_benchmark.py --models llama3.2,qwen2.5,mistral [opzioni]
    python model_benchmark.py --models kimi-k2.5:cloud --output output/bench.html

    Variabili d'ambiente:
        OLLAMA_BASE_URL        URL server Ollama  (default: http://localhost:11434)
        OLLAMA_TIMEOUT         Timeout richiesta  (default: 120s)
        OLLAMA_MAX_RETRIES     Max retry          (default: 4)
        OLLAMA_WARMUP_RETRIES  Retry warmup       (default: 3)
        OLLAMA_CHUNK_THRESHOLD Soglia chunking    (default: 32000 char)
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
logger = logging.getLogger("model_benchmark")

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
    OLLAMA_CHUNK_THRESHOLD,
)

# Import agenti
try:
    from agents import AGENT_SPECS, AgentRole, GLOBAL_VOICE_DIRECTIVE
    _AGENT_SPECS_AVAILABLE = True
except ImportError:
    _AGENT_SPECS_AVAILABLE = False
    logger.warning("agents.py non importabile — uso lunghezze stimate.")

# ---------------------------------------------------------------------------
# Dati club di esempio
# ---------------------------------------------------------------------------

SAMPLE_CLUB_DATA: Dict[str, Any] = {
    "club_name": "ASD Benchmark FC",
    "category": "Promozione",
    "region": "Lombardia",
    "country": "Italy",
    "founded_year": 1992,
    "stadium_name": "Campo Sportivo Comunale",
    "stadium_capacity": 600,
    "current_players": 20,
    "youth_teams": 2,
    "annual_budget": 60000,
    "primary_color": "#1a365d",
    "secondary_color": "#ffffff",
    "plan_id": f"benchmark_{int(time.time())}",
}


# ---------------------------------------------------------------------------
# Fix 2: Riordinamento agenti per lunghezza prompt
# ---------------------------------------------------------------------------

def build_and_sort_agents(club_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Costruisce la lista agenti e la ordina per lunghezza prompt crescente.

    L'ordinamento garantisce che il modello si scaldi sulle richieste
    più leggere prima di ricevere quelle pesanti (es. STW Sportivi).
    """
    if _AGENT_SPECS_AVAILABLE:
        agents = [
            {
                "name": spec.name,
                "role": role.value,
                "system_prompt": spec.system_prompt,
            }
            for role, spec in AGENT_SPECS.items()
            if role != AgentRole.COORDINATOR
        ]
    else:
        # Fallback con lunghezze stimate
        agents = [
            {"name": "STW Strutturali Analyst", "role": "stw_strutturali", "system_prompt": "X" * 2800},
            {"name": "STW Marketing Analyst",   "role": "stw_marketing",   "system_prompt": "X" * 2600},
            {"name": "Financial Strategist",    "role": "financial",       "system_prompt": "X" * 2400},
            {"name": "STW Sociali Analyst",     "role": "stw_sociali",     "system_prompt": "X" * 3200},
            {"name": "STW Sportivi Analyst",    "role": "stw_sportivi",    "system_prompt": "X" * 3800},
        ]

    user_data_str = json.dumps(club_data, ensure_ascii=False)

    for ag in agents:
        lengths = compute_prompt_length(
            system_prompt=ag["system_prompt"],
            user_data=user_data_str,
        )
        ag["_prompt_length_char"] = lengths["total_char"]
        ag["_prompt_length_tokens"] = lengths["total_tokens_stima"]

    sorted_agents = sorted(agents, key=lambda a: a["_prompt_length_char"])

    logger.info("[FIX2] Ordine agenti (prompt crescente):")
    for i, ag in enumerate(sorted_agents):
        logger.info(
            f"  {i+1}. {ag['name']:30s} "
            f"{ag['_prompt_length_char']:6d} ch "
            f"(~{ag['_prompt_length_tokens']:4d} tok)"
        )

    return sorted_agents


# ---------------------------------------------------------------------------
# Fix 4: Struttura per raccogliere diagnostica per modello
# ---------------------------------------------------------------------------

class ModelRunResult:
    """Risultato completo di un run per un modello."""

    def __init__(self, model: str):
        self.model = model
        self.run_id = f"{model}_{int(time.time())}"
        self.warmup_ok: bool = False
        self.warmup_seconds: float = 0.0
        self.agent_diagnostics: List[AgentDiagnostics] = []
        self.outputs: Dict[str, str] = {}
        self.start_time: float = time.time()
        self.end_time: float = 0.0
        self.error: Optional[str] = None

    @property
    def total_seconds(self) -> float:
        return self.end_time - self.start_time if self.end_time else 0.0

    @property
    def agents_ok(self) -> int:
        return sum(1 for d in self.agent_diagnostics if d.output_valid)

    @property
    def agents_failed(self) -> int:
        return sum(1 for d in self.agent_diagnostics if not d.output_valid)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "run_id": self.run_id,
            "warmup_ok": self.warmup_ok,
            "warmup_seconds": round(self.warmup_seconds, 2),
            "total_seconds": round(self.total_seconds, 2),
            "agents_total": len(self.agent_diagnostics),
            "agents_ok": self.agents_ok,
            "agents_failed": self.agents_failed,
            "error": self.error,
            "agents": [d.to_dict() for d in self.agent_diagnostics],
        }

    def log_summary(self) -> None:
        status = "PASS" if self.agents_failed == 0 else f"FAIL ({self.agents_failed} err)"
        logger.info(
            f"[BENCH] {self.model:<30} | {status:<16} | "
            f"ok={self.agents_ok}/{len(self.agent_diagnostics)} | "
            f"time={self.total_seconds:.1f}s | "
            f"warmup={'OK' if self.warmup_ok else 'FAIL'}"
        )


# ---------------------------------------------------------------------------
# Core: run singolo modello
# ---------------------------------------------------------------------------

def benchmark_model(
    model: str,
    agents: List[Dict[str, Any]],
    club_data: Dict[str, Any],
    base_url: str,
    skip_warmup: bool = False,
) -> ModelRunResult:
    """
    Esegue la pipeline completa per un modello e raccoglie diagnostica.
    """
    result = ModelRunResult(model=model)
    user_data_str = _build_user_prompt(club_data)

    logger.info(f"\n{'='*60}")
    logger.info(f"[BENCH] Modello: {model}")
    logger.info(f"[BENCH] Run ID:  {result.run_id}")
    logger.info(f"{'='*60}")

    # Inizializza provider
    try:
        provider = OllamaProvider(model=model, base_url=base_url)
    except Exception as exc:
        result.error = f"Init provider fallito: {exc}"
        result.end_time = time.time()
        logger.error(f"[BENCH] {model}: provider init fallito: {exc}")
        return result

    # Fix 1: Warmup
    if not skip_warmup:
        t_warmup = time.time()
        logger.info(f"[FIX1] Warmup per '{model}'...")
        result.warmup_ok = warmup_ollama(provider)
        result.warmup_seconds = time.time() - t_warmup
        if not result.warmup_ok:
            logger.warning(f"[FIX1] Warmup fallito per '{model}' — procedo comunque")
    else:
        result.warmup_ok = True  # Assumiamo già caldo

    # Fix 2: Loop agenti ordinati per prompt crescente
    for agent in agents:
        agent_name = agent["name"]
        system_prompt = agent.get("system_prompt", "")
        full_prompt_len = len(system_prompt) + len(user_data_str)

        # Fix 4: Diagnostica
        d = AgentDiagnostics(
            nome_agente=agent_name,
            modello=model,
            system_prompt_length=len(system_prompt),
            user_data_length=len(user_data_str),
            prompt_length_char=full_prompt_len,
            prompt_length_tokens_stima=estimate_tokens(system_prompt + user_data_str),
            warmup_done=result.warmup_ok,
        )

        if full_prompt_len > OLLAMA_CHUNK_THRESHOLD:
            logger.warning(
                f"[FIX3] {agent_name}: prompt {full_prompt_len}ch > soglia "
                f"{OLLAMA_CHUNK_THRESHOLD}ch — chunking attivo"
            )

        logger.info(
            f"[AGENT] {agent_name} "
            f"| {full_prompt_len}ch (~{d.prompt_length_tokens_stima}tok)"
        )

        # Fix 3/5: generate() con retry e chunking automatico
        try:
            output = provider.generate(
                prompt=user_data_str,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=8192,
                agent_name=agent_name,
                diagnostics=d,
            )
            result.outputs[agent["role"]] = output
        except Exception as exc:
            d.output_valid = False
            d.error_message = str(exc)
            result.outputs[agent["role"]] = f"[ERRORE: {exc}]"
            logger.error(f"[BENCH] {agent_name} FALLITO: {exc}")

        d.log_summary()
        result.agent_diagnostics.append(d)

    result.end_time = time.time()
    result.log_summary()
    return result


def _build_user_prompt(club_data: Dict[str, Any]) -> str:
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
    results: List[ModelRunResult],
    club_data: Dict[str, Any],
    output_path: str,
) -> None:
    """Genera report HTML benchmark con tabella riepilogativa e diagnostica per modello."""

    def _status_badge(ok: bool) -> str:
        if ok:
            return '<span style="background:#e8f5e9;color:#2e7d32;padding:2px 8px;border-radius:4px;font-weight:bold">PASS</span>'
        return '<span style="background:#ffebee;color:#c62828;padding:2px 8px;border-radius:4px;font-weight:bold">FAIL</span>'

    def _summary_table_rows() -> str:
        rows = ""
        for r in results:
            badge = _status_badge(r.agents_failed == 0)
            wbadge = _status_badge(r.warmup_ok)
            rows += f"""
            <tr>
              <td><code>{r.model}</code></td>
              <td>{badge}</td>
              <td>{r.agents_ok}/{len(r.agent_diagnostics)}</td>
              <td>{wbadge}</td>
              <td>{r.warmup_seconds:.1f}s</td>
              <td>{r.total_seconds:.1f}s</td>
              <td>{r.error or ''}</td>
            </tr>"""
        return rows

    def _diag_section(r: ModelRunResult) -> str:
        if not r.agent_diagnostics:
            return f"<p>Nessun agente eseguito per {r.model}.</p>"

        rows = ""
        for d in r.agent_diagnostics:
            sc = "#2e7d32" if d.output_valid else "#c62828"
            sl = "OK" if d.output_valid else "FAIL"
            err = (d.error_message[:100] if d.error_message else "")
            rows += f"""
            <tr>
              <td>{d.nome_agente}</td>
              <td>{d.prompt_length_char:,}</td>
              <td>{d.prompt_length_tokens_stima:,}</td>
              <td>{'SI' if d.warmup_done else 'NO'}</td>
              <td>{d.attempt_number}</td>
              <td>{d.retry_wait_seconds}s</td>
              <td>{d.total_generation_seconds:.1f}s</td>
              <td>{d.output_length_char:,}</td>
              <td style="color:{sc};font-weight:bold">{sl}</td>
              <td style="font-size:11px;color:#c62828">{err}</td>
            </tr>"""

        return f"""
        <table>
          <thead><tr>
            <th>Agente</th><th>Prompt (ch)</th><th>Token</th><th>Warmup</th>
            <th>Tentativo</th><th>Attesa</th><th>Tempo gen.</th><th>Output (ch)</th>
            <th>Stato</th><th>Errore</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    def _timing_chart_data() -> str:
        """Genera dati per grafico tempi (JS inline)."""
        labels = json.dumps([r.model for r in results])
        total_times = json.dumps([round(r.total_seconds, 1) for r in results])
        warmup_times = json.dumps([round(r.warmup_seconds, 1) for r in results])
        ok_counts = json.dumps([r.agents_ok for r in results])
        fail_counts = json.dumps([r.agents_failed for r in results])
        return f"""
        <script>
        var labels = {labels};
        var totalTimes = {total_times};
        var warmupTimes = {warmup_times};
        var okCounts = {ok_counts};
        var failCounts = {fail_counts};

        function buildBars(containerId, data, maxVal, color) {{
            var c = document.getElementById(containerId);
            data.forEach(function(v, i) {{
                var pct = maxVal > 0 ? Math.round(v / maxVal * 100) : 0;
                c.innerHTML += '<div style="margin:4px 0">'
                    + '<span style="display:inline-block;width:200px;font-size:12px">' + labels[i].substring(0,25) + '</span>'
                    + '<span style="display:inline-block;background:' + color + ';height:14px;width:' + pct + '%;vertical-align:middle;min-width:2px"></span>'
                    + '<span style="font-size:12px;margin-left:6px">' + v + (containerId.includes('time') ? 's' : '') + '</span>'
                    + '</div>';
            }});
        }}

        var maxTime = Math.max.apply(null, totalTimes) || 1;
        var maxOk = Math.max.apply(null, okCounts) || 1;
        window.addEventListener('load', function() {{
            buildBars('chart-time', totalTimes, maxTime, '#1565c0');
            buildBars('chart-ok', okCounts, maxOk, '#2e7d32');
            buildBars('chart-fail', failCounts, maxOk, '#c62828');
        }});
        </script>"""

    # Sezioni diagnostica per ogni modello
    diag_sections = ""
    for r in results:
        diag_sections += f"""
        <div class="card" style="margin-bottom:20px">
          <h2>Diagnostica: <code>{r.model}</code>
            {'<span style="color:#2e7d32;font-size:14px"> (PASS)</span>' if r.agents_failed == 0
             else f'<span style="color:#c62828;font-size:14px"> ({r.agents_failed} FAIL)</span>'}
          </h2>
          {_diag_section(r)}
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Model Benchmark — Rooting Future</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f5f5f5; color: #222; }}
  .header {{ background: #1a237e; color: white; padding: 24px 32px; }}
  .header h1 {{ margin: 0; font-size: 24px; }}
  .header p {{ margin: 4px 0 0; opacity: .8; font-size: 14px; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 24px 32px; }}
  .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
  .card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
  .card h2 {{ margin-top: 0; color: #1a237e; border-bottom: 2px solid #e8eaf6; padding-bottom: 8px; font-size: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #e8eaf6; color: #1a237e; padding: 8px; text-align: left; white-space: nowrap; }}
  td {{ padding: 7px 8px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
  tr:hover {{ background: #fafafa; }}
  pre {{ background: #f8f8f8; border: 1px solid #e0e0e0; border-radius: 4px;
         padding: 12px; font-size: 11px; overflow: auto; max-height: 400px; }}
  .metric {{ display: inline-block; margin: 6px 12px 6px 0; }}
  .metric .val {{ font-size: 24px; font-weight: bold; color: #1a237e; }}
  .metric .lbl {{ font-size: 11px; color: #666; }}
</style>
{_timing_chart_data()}
</head>
<body>
<div class="header">
  <h1>Model Benchmark — Pipeline Multi-Agente</h1>
  <p>
    Modelli testati: {len(results)} |
    Club: {club_data.get('club_name', 'N/A')} ({club_data.get('category', 'N/A')}) |
    Generato: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
  </p>
</div>
<div class="container">

  <!-- Metriche globali -->
  <div class="card" style="margin-bottom:24px">
    <h2>Riepilogo Benchmark</h2>
    <div class="metric"><div class="val">{len(results)}</div><div class="lbl">Modelli testati</div></div>
    <div class="metric"><div class="val">{sum(1 for r in results if r.agents_failed == 0)}</div><div class="lbl">Modelli PASS</div></div>
    <div class="metric"><div class="val">{sum(1 for r in results if r.agents_failed > 0)}</div><div class="lbl">Modelli con errori</div></div>
    <div class="metric"><div class="val">{sum(r.total_seconds for r in results):.0f}s</div><div class="lbl">Tempo totale benchmark</div></div>
  </div>

  <!-- Tabella riepilogativa -->
  <div class="card" style="margin-bottom:24px">
    <h2>Riepilogo per Modello</h2>
    <table>
      <thead><tr>
        <th>Modello</th><th>Stato</th><th>Agenti OK</th>
        <th>Warmup</th><th>T.Warmup</th><th>T.Totale</th><th>Errore</th>
      </tr></thead>
      <tbody>{_summary_table_rows()}</tbody>
    </table>
  </div>

  <!-- Grafici -->
  <div class="grid-3">
    <div class="card">
      <h2>Tempo Totale per Modello</h2>
      <div id="chart-time"></div>
    </div>
    <div class="card">
      <h2>Agenti Completati (OK)</h2>
      <div id="chart-ok"></div>
    </div>
    <div class="card">
      <h2>Agenti Falliti</h2>
      <div id="chart-fail"></div>
    </div>
  </div>

  <!-- Diagnostica dettagliata per modello -->
  <h2 style="color:#1a237e;margin:24px 0 12px">Diagnostica Dettagliata per Agente</h2>
  {diag_sections}

  <!-- JSON completo -->
  <div class="card">
    <h2>JSON Diagnostica Completa</h2>
    <pre>{json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False)}</pre>
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
        description="Benchmark multi-modello della pipeline multi-agente Ollama"
    )
    parser.add_argument(
        "--models",
        required=True,
        help="Lista modelli separati da virgola (es. llama3.2,qwen2.5,mistral)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OLLAMA_BASE_URL", OLLAMA_BASE_URL),
        help="URL base Ollama",
    )
    parser.add_argument(
        "--output",
        default=f"output/benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
        help="Path output report HTML",
    )
    parser.add_argument(
        "--skip-warmup",
        action="store_true",
        help="Salta warmup per tutti i modelli (sconsigliato)",
    )
    parser.add_argument(
        "--club-data",
        default=None,
        help="Path a JSON con dati club personalizzati",
    )
    parser.add_argument(
        "--single-model-test",
        default=None,
        metavar="MODEL",
        help="Testa solo questo modello (override --models) per verifica rapida post-fix",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    Path("output").mkdir(exist_ok=True)

    # Carica dati club
    club_data = SAMPLE_CLUB_DATA.copy()
    if args.club_data:
        with open(args.club_data, encoding="utf-8") as f:
            club_data.update(json.load(f))
        logger.info(f"[MAIN] Dati club caricati da: {args.club_data}")

    # Modelli da testare
    if args.single_model_test:
        models = [args.single_model_test]
        logger.info(f"[MAIN] Modalità single-model-test: {args.single_model_test}")
    else:
        models = [m.strip() for m in args.models.split(",") if m.strip()]

    logger.info(f"[MAIN] Modelli: {models}")

    # Fix 2: Costruisci e ordina agenti una volta sola (ordine identico per tutti i modelli)
    agents = build_and_sort_agents(club_data)

    results: List[ModelRunResult] = []

    for model in models:
        logger.info(f"\n[MAIN] {'='*60}")
        logger.info(f"[MAIN] Avvio benchmark modello: {model}")
        logger.info(f"[MAIN] {'='*60}")

        result = benchmark_model(
            model=model,
            agents=agents,
            club_data=club_data,
            base_url=args.base_url,
            skip_warmup=args.skip_warmup,
        )
        results.append(result)

    # Genera report HTML
    generate_html_report(
        results=results,
        club_data=club_data,
        output_path=args.output,
    )

    # Salva JSON diagnostica
    json_path = args.output.replace(".html", "_diag.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in results], f, indent=2, ensure_ascii=False)
    logger.info(f"[MAIN] JSON diagnostica: {json_path}")

    # Riepilogo console
    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETATO")
    print("=" * 70)
    print(f"{'Modello':<32} {'Stato':<8} {'OK/Tot':<10} {'Warmup':<8} {'Tempo'}")
    print("-" * 70)
    for r in results:
        stato = "PASS" if r.agents_failed == 0 else f"FAIL({r.agents_failed})"
        print(
            f"{r.model:<32} {stato:<8} "
            f"{r.agents_ok}/{len(r.agent_diagnostics):<8} "
            f"{'OK' if r.warmup_ok else 'FAIL':<8} "
            f"{r.total_seconds:.1f}s"
        )
    print(f"\nReport HTML: {args.output}")
    print(f"JSON:        {json_path}")

    # Exit code non-zero se qualche modello ha fallito
    any_failed = any(r.agents_failed > 0 for r in results)
    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()

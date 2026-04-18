"""
Rooting Future -- Multi-Model Benchmark
Testa tutti i modelli Ollama cloud free sui dati Riccione Calcio 1926.
Produce report HTML con tabella comparativa + diagnostica.

Usage:
  python model_benchmark.py
  python model_benchmark.py --models "gemma4:31b,kimi-k2.5,deepseek-v3.2"
  python model_benchmark.py --agent STW_SPORTIVI  # solo un agente per test rapido
  python model_benchmark.py --models kimi-k2.5 --single-model-test  # verifica post-fix
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Modelli disponibili su Ollama cloud (verificati con /api/tags 2026-04-12)
DEFAULT_MODELS = [
    "kimi-k2.5",
    "deepseek-v3.2",
    "gemma4:31b",
    "gemma3:27b",
    "qwen3-next:80b",
]

sys.path.insert(0, str(Path(__file__).parent))

INTERVIEW_PATH = "data/clubs/riccione-calcio-1926"


# ---------------------------------------------------------------------------
# Document loading
# ---------------------------------------------------------------------------

def read_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        return ""


def load_interviews(input_path: str) -> str:
    p = Path(input_path)
    if not p.exists():
        return ""
    files = sorted(set(list(p.rglob("*.docx")) + list(p.rglob("*.doc"))))
    files = [f for f in files if not f.name.startswith("~$")]
    texts = []
    for f in files:
        if f.suffix.lower() == ".docx":
            text = read_docx(f)
        else:
            continue
        if text.strip():
            texts.append(f"=== {f.name} ===\n{text}")
    return "\n\n".join(texts)


# ---------------------------------------------------------------------------
# Ollama client
# ---------------------------------------------------------------------------

def get_client(model: str):
    """Crea client OpenAI per Ollama cloud."""
    from openai import OpenAI
    base_url = os.environ.get("OLLAMA_BASE_URL", "https://ollama.com").rstrip("/")
    api_key = os.environ.get("OLLAMA_API_KEY", "ollama")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=int(os.environ.get("OLLAMA_TIMEOUT", "300")),
        max_retries=int(os.environ.get("OLLAMA_SDK_RETRIES", "3")),
    )


# ---------------------------------------------------------------------------
# Fix 1: Warmup
# ---------------------------------------------------------------------------

def warmup_model(client, model: str, max_retries: int = 3) -> bool:
    """Invia richiesta minima per svegliare il modello."""
    for attempt in range(max_retries):
        try:
            t0 = time.time()
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Rispondi solo: OK"}],
                temperature=0,
                max_tokens=5,
            )
            elapsed = time.time() - t0
            text = (r.choices[0].message.content or "").strip()
            if text:
                print(f"    Warmup OK in {elapsed:.1f}s: '{text[:20]}'")
                return True
        except Exception as e:
            wait = 15 * (attempt + 1)
            print(f"    Warmup attempt {attempt+1}/{max_retries} failed: {str(e)[:60]}. Waiting {wait}s...")
            if attempt < max_retries - 1:
                time.sleep(wait)
    print(f"    Warmup FALLITO (procedo comunque)")
    return False


# ---------------------------------------------------------------------------
# Fix 5: Run single agent con retry migliorato
# ---------------------------------------------------------------------------

def run_single_agent(
    client,
    model: str,
    agent_name: str,
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 5,
) -> Dict[str, Any]:
    """Esegui un singolo agente e raccogli metriche + diagnostica."""
    backoff = [15, 30, 60, 120]
    metric: Dict[str, Any] = {
        "agent": agent_name,
        "model": model,
        "time_seconds": 0.0,
        "output_chars": 0,
        "success": False,
        "error": "",
        "output": "",
        "diagnostics": {
            "prompt_length_char": len(system_prompt) + len(user_prompt),
            "prompt_length_tokens_est": (len(system_prompt) + len(user_prompt)) // 4,
            "system_prompt_length": len(system_prompt),
            "user_prompt_length": len(user_prompt),
            "attempt_number": 0,
            "retry_wait_total": 0,
            "http_status_code": 0,
        },
    }

    connection_failures = 0
    total_retry_wait = 0
    t0 = time.time()

    for attempt in range(max_retries):
        metric["diagnostics"]["attempt_number"] = attempt + 1
        try:
            t_call = time.time()
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=8192,
            )
            elapsed = time.time() - t_call
            text = response.choices[0].message.content or ""

            metric["time_seconds"] = round(time.time() - t0, 2)
            metric["output_chars"] = len(text)
            metric["output"] = text
            metric["success"] = True
            metric["diagnostics"]["http_status_code"] = 200
            metric["diagnostics"]["retry_wait_total"] = total_retry_wait
            return metric

        except Exception as e:
            err = str(e)
            metric["error"] = err[:200]

            is_rate_limit = "429" in err or "rate" in err.lower()
            is_timeout = "timeout" in err.lower()
            is_connection = "onnect" in err or "disconnected" in err.lower()

            for code in ["429", "500", "502", "503"]:
                if code in err:
                    metric["diagnostics"]["http_status_code"] = int(code)
                    break

            if attempt >= max_retries - 1:
                break

            if is_rate_limit:
                wait = backoff[min(attempt, len(backoff) - 1)]
                print(f"      [retry {attempt+1}] rate limit, attendo {wait}s...")
                time.sleep(wait)
                total_retry_wait += wait
            elif is_timeout:
                wait = backoff[min(attempt, len(backoff) - 1)]
                print(f"      [retry {attempt+1}] timeout, attendo {wait}s...")
                time.sleep(wait)
                total_retry_wait += wait
            elif is_connection:
                connection_failures += 1
                wait = 30 + (connection_failures * 15)
                print(f"      [retry {attempt+1}] connection error #{connection_failures}, attendo {wait}s...")
                time.sleep(wait)
                total_retry_wait += wait
            else:
                wait = backoff[min(attempt, len(backoff) - 1)]
                print(f"      [retry {attempt+1}] {err[:60]}... attendo {wait}s")
                time.sleep(wait)
                total_retry_wait += wait

    metric["time_seconds"] = round(time.time() - t0, 2)
    metric["diagnostics"]["retry_wait_total"] = total_retry_wait
    return metric


# ---------------------------------------------------------------------------
# Agent prompts (semplificati per benchmark)
# ---------------------------------------------------------------------------

AGENT_SPECS = [
    {
        "name": "STW Sportivi",
        "system": (
            "Sei un analista sportivo per societa' calcistiche. "
            "Scrivi a nome del CLUB come istituzione, tono McKinsey/BCG. "
            "Voce istituzionale, zero nomi propri di dirigenti. "
            "Genera almeno 4000 caratteri di analisi dettagliata."
        ),
        "user_template": """Genera la sezione OBIETTIVI SPORTIVI del piano strategico triennale per il {club_name} (Eccellenza, Emilia-Romagna).

DATI DAL BOARD:
{context}

Struttura OBBLIGATORIA:
## AREA STW: STAKEHOLDER SPORTIVI

### Obiettivo MACRO 1: Miglioramento Competitivo
Analisi dettagliata con KPI, timeline, azioni concrete.

### Obiettivo MACRO 2: Sviluppo Settore Giovanile
Pipeline talenti, struttura academy, costi e ricavi.

### Obiettivo MACRO 3-8: [Identifica altri obiettivi dall'analisi]

Per ogni obiettivo: stato attuale, target triennale, azioni anno per anno, KPI misurabili, budget stimato.
Scrivi almeno 4000 caratteri. Sii specifico e concreto, basandoti sui dati forniti.""",
        "min_chars": 4000,
    },
    {
        "name": "STW Strutturali",
        "system": (
            "Sei un analista di infrastrutture e risorse umane per societa' calcistiche. "
            "Scrivi a nome del CLUB come istituzione. Tono consulenziale. "
            "Genera almeno 3000 caratteri."
        ),
        "user_template": """Genera la sezione OBIETTIVI STRUTTURALI del piano strategico per il {club_name}.

DATI DAL BOARD:
{context}

Struttura: Infrastrutture (stadio, centro sportivo), Risorse Umane (staff, governance), Organizzazione.
Per ogni obiettivo: stato attuale, target, azioni, KPI, budget.
Scrivi almeno 3000 caratteri.""",
        "min_chars": 3000,
    },
    {
        "name": "STW Marketing",
        "system": (
            "Sei un esperto di marketing sportivo e commercializzazione per club calcistici. "
            "Scrivi a nome del CLUB. Tono professionale. "
            "Genera almeno 3000 caratteri."
        ),
        "user_template": """Genera la sezione OBIETTIVI MARKETING del piano strategico per il {club_name}.

DATI DAL BOARD:
{context}

Struttura: Brand Identity, Comunicazione, Sponsorizzazioni, Community, Diversificazione Ricavi.
Per ogni obiettivo: stato attuale, target, azioni, KPI, budget.
Scrivi almeno 3000 caratteri.""",
        "min_chars": 3000,
    },
    {
        "name": "STW Sociali",
        "system": (
            "Sei un esperto di responsabilita' sociale e sostenibilita' nel calcio. "
            "Scrivi a nome del CLUB. Tono istituzionale. "
            "Genera almeno 3000 caratteri."
        ),
        "user_template": """Genera la sezione OBIETTIVI SOCIALI del piano strategico per il {club_name}.

DATI DAL BOARD:
{context}

Struttura: Impatto Sociale, Rapporto col Territorio, Inclusione, Sostenibilita' Ambientale.
Per ogni obiettivo: stato attuale, target, azioni, KPI.
Scrivi almeno 3000 caratteri.""",
        "min_chars": 3000,
    },
    {
        "name": "Financial Strategist",
        "system": (
            "Sei un analista finanziario specializzato in societa' calcistiche dilettantistiche. "
            "Scrivi a nome del CLUB. Numeri concreti dove possibile. "
            "Genera almeno 3000 caratteri."
        ),
        "user_template": """Genera la sezione PIANO ECONOMICO-FINANZIARIO del piano strategico per il {club_name}.

DATI DAL BOARD:
{context}

Struttura: Budget Triennale, Fonti di Ricavo, Struttura Costi, Piano Investimenti, Break-even Analysis.
Genera tabelle con numeri (anche stimati). Indica sempre la fonte: (dato board) o (stima AI).
Scrivi almeno 3000 caratteri.""",
        "min_chars": 3000,
    },
    {
        "name": "Strategic Coordinator",
        "system": (
            "Sei il coordinatore strategico. Crei l'Executive Summary sintetizzando le 4 aree STW. "
            "Tono McKinsey/BCG. Voce istituzionale. "
            "Genera almeno 2000 caratteri."
        ),
        "user_template": """Genera l'EXECUTIVE SUMMARY del piano strategico triennale per il {club_name}.

DATI DAL BOARD:
{context}

Struttura: Visione Triennale, Sintesi 4 Aree STW, Top 5 Priorita', Quick Wins, Roadmap.
Scrivi almeno 2000 caratteri.""",
        "min_chars": 2000,
    },
]


def build_agents(interview_text: str, club_name: str = "Riccione Calcio 1926") -> List[Dict]:
    """Ritorna i 6 agenti con system_prompt e user_prompt."""
    context = interview_text[:4000]
    agents = []
    for spec in AGENT_SPECS:
        agents.append({
            "name": spec["name"],
            "system": spec["system"],
            "user": spec["user_template"].format(club_name=club_name, context=context),
            "min_chars": spec["min_chars"],
        })
    return agents


# ---------------------------------------------------------------------------
# Fix 2: Ordina agenti per lunghezza prompt (piu' corti prima)
# ---------------------------------------------------------------------------

def sort_agents_by_prompt_length(agents: List[Dict]) -> List[Dict]:
    """
    Ordina agenti dal prompt piu' corto al piu' lungo.
    Cosi' il modello si scalda con prompt leggeri prima di affrontare STW Sportivi.
    """
    sorted_list = sorted(agents, key=lambda a: len(a["system"]) + len(a["user"]))
    order_str = " -> ".join(f"{a['name']}({len(a['system'])+len(a['user'])})" for a in sorted_list)
    print(f"  Ordine agenti (prompt crescente): {order_str}")
    return sorted_list


# ---------------------------------------------------------------------------
# HTML Report
# ---------------------------------------------------------------------------

def generate_html_report(
    results: Dict[str, List[Dict]],
    date_str: str,
) -> str:
    """Genera report HTML comparativo multi-modello con diagnostica."""

    summaries = {}
    for model_name, metrics in results.items():
        total_time = sum(m["time_seconds"] for m in metrics)
        total_chars = sum(m["output_chars"] for m in metrics)
        success_count = sum(1 for m in metrics if m["success"])
        summaries[model_name] = {
            "total_time": round(total_time, 1),
            "total_chars": total_chars,
            "success": success_count,
            "total": len(metrics),
        }

    sorted_models = sorted(summaries.keys(), key=lambda m: summaries[m]["total_chars"], reverse=True)

    # Header cards
    cards_html = ""
    for i, model_name in enumerate(sorted_models):
        s = summaries[model_name]
        badge = "#28a745" if s["success"] == s["total"] else "#dc3545"
        rank = i + 1
        cards_html += f"""
        <div style="background:#1e1e2e;border-radius:12px;padding:20px;min-width:220px;border-left:4px solid {badge}">
            <div style="font-size:12px;color:#888">#{rank}</div>
            <div style="font-size:18px;font-weight:bold;color:#e0e0e0;margin:8px 0">{model_name}</div>
            <div style="color:#aaa">{s['success']}/{s['total']} agenti OK</div>
            <div style="font-size:24px;font-weight:bold;color:#58a6ff;margin:8px 0">{s['total_chars']:,} chars</div>
            <div style="color:#888">{s['total_time']}s totali</div>
        </div>"""

    # Per-agent table
    agent_names = [m["agent"] for m in next(iter(results.values()))]
    table_header = "<th>Agente</th>"
    for model_name in sorted_models:
        table_header += f"<th>{model_name}<br><small>chars / tempo</small></th>"

    table_rows = ""
    for agent_name in agent_names:
        row = f"<td style='font-weight:bold'>{agent_name}</td>"
        for model_name in sorted_models:
            metrics = results[model_name]
            m = next((x for x in metrics if x["agent"] == agent_name), None)
            if m and m["success"]:
                row += f"<td style='text-align:center'>{m['output_chars']:,}<br><small>{m['time_seconds']}s</small></td>"
            elif m:
                row += f"<td style='text-align:center;color:#dc3545'>ERRORE<br><small>{m['error'][:40]}</small></td>"
            else:
                row += "<td style='text-align:center;color:#888'>-</td>"
        table_rows += f"<tr>{row}</tr>"

    # Diagnostics table
    diag_rows = ""
    for model_name in sorted_models:
        for m in results[model_name]:
            d = m.get("diagnostics", {})
            status_color = "#28a745" if m["success"] else "#dc3545"
            diag_rows += f"""<tr>
                <td>{model_name}</td>
                <td>{m['agent']}</td>
                <td>{d.get('prompt_length_char', 0):,}</td>
                <td>{d.get('prompt_length_tokens_est', 0):,}</td>
                <td>{d.get('attempt_number', 0)}</td>
                <td>{d.get('retry_wait_total', 0)}s</td>
                <td>{m['time_seconds']}s</td>
                <td style="color:{status_color}">{m['output_chars']:,}</td>
                <td>{d.get('http_status_code', '-')}</td>
                <td style="color:{status_color}">{'OK' if m['success'] else 'FAIL'}</td>
            </tr>"""

    # Output comparativo (espandibile)
    outputs_html = ""
    for agent_name in agent_names:
        panels = ""
        for model_name in sorted_models:
            metrics = results[model_name]
            m = next((x for x in metrics if x["agent"] == agent_name), None)
            if m and m["success"]:
                content = m["output"][:3000].replace("<", "&lt;").replace(">", "&gt;")
                panels += f"""
                <div style="flex:1;min-width:300px;max-width:50%;background:#1e1e2e;border-radius:8px;padding:15px;overflow:auto;max-height:400px">
                    <h4 style="color:#58a6ff;margin:0 0 10px 0">{model_name} ({m['output_chars']:,} chars)</h4>
                    <pre style="white-space:pre-wrap;color:#d4d4d4;font-size:12px;line-height:1.5">{content}</pre>
                </div>"""
            else:
                err_msg = (m["error"][:100] if m else "non disponibile").replace("<", "&lt;")
                panels += f"""
                <div style="flex:1;min-width:300px;max-width:50%;background:#1e1e2e;border-radius:8px;padding:15px">
                    <h4 style="color:#dc3545;margin:0 0 10px 0">{model_name} (ERRORE)</h4>
                    <pre style="color:#888">{err_msg}</pre>
                </div>"""

        outputs_html += f"""
        <details style="margin:15px 0">
            <summary style="cursor:pointer;font-size:16px;font-weight:bold;color:#e0e0e0;padding:10px;background:#2d2d3d;border-radius:8px">{agent_name}</summary>
            <div style="display:flex;gap:15px;flex-wrap:wrap;margin-top:10px">{panels}</div>
        </details>"""

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>Model Benchmark - Riccione Calcio 1926</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #e0e0e0; margin: 0; padding: 20px; }}
    h1 {{ color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 15px; }}
    h2 {{ color: #58a6ff; margin-top: 30px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
    th {{ background: #161b22; color: #58a6ff; padding: 12px; text-align: center; }}
    td {{ padding: 10px; border-bottom: 1px solid #30363d; text-align: center; }}
    tr:hover {{ background: #161b22; }}
</style>
</head>
<body>
<h1>Model Benchmark: Riccione Calcio 1926</h1>
<p style="color:#888">{date_str} | {len(results)} modelli testati | {len(agent_names)} agenti per modello</p>

<h2>Classifica Modelli</h2>
<div style="display:flex;gap:15px;flex-wrap:wrap;margin:20px 0">{cards_html}</div>

<h2>Dettaglio Per Agente</h2>
<table>
<thead><tr>{table_header}</tr></thead>
<tbody>{table_rows}</tbody>
</table>

<h2>Diagnostica</h2>
<p style="color:#888">Metriche dettagliate per ogni chiamata (Fix 4).</p>
<table>
<thead><tr>
    <th>Modello</th><th>Agente</th><th>Prompt Chars</th><th>~Tokens</th>
    <th>Tentativi</th><th>Attesa Retry</th><th>Tempo Tot.</th>
    <th>Output Chars</th><th>HTTP</th><th>Status</th>
</tr></thead>
<tbody>{diag_rows}</tbody>
</table>

<h2>Output Comparativo</h2>
<p style="color:#888">Clicca su ogni agente per espandere e confrontare gli output.</p>
{outputs_html}

<hr style="border-color:#30363d;margin:30px 0">
<p style="color:#666;font-size:12px">Generato da model_benchmark.py | Rooting Future LLM Wiki Sovereignty</p>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Multi-Model Benchmark - Riccione Calcio 1926")
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help=f"Modelli da testare, separati da virgola (default: {','.join(DEFAULT_MODELS)})",
    )
    parser.add_argument("--input", default=INTERVIEW_PATH, help="Percorso interviste")
    parser.add_argument("--agent", default="", help="Testa solo un agente specifico (es. 'STW Sportivi')")
    parser.add_argument("--pause", type=int, default=int(os.environ.get("BENCHMARK_PAUSE", "8")),
                        help="Pausa in secondi tra agenti (default: 8)")
    parser.add_argument("--single-model-test", action="store_true",
                        help="Verifica rapida post-fix: un modello, tutti gli agenti, report minimale")
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    print("=" * 60)
    print("MODEL BENCHMARK: Riccione Calcio 1926")
    print(f"  Modelli: {', '.join(models)}")
    if args.single_model_test:
        print(f"  Modalita': SINGLE MODEL TEST (verifica post-fix)")
    print(f"  Data: {date_str}")
    print("=" * 60)

    # Load interviews
    print(f"\nCaricamento interviste da: {args.input}")
    interview_text = load_interviews(args.input)
    if not interview_text.strip():
        print("ATTENZIONE: Nessuna intervista trovata.")
    else:
        print(f"  {len(interview_text)} caratteri caricati")

    # Get agent prompts
    all_agents = build_agents(interview_text)
    if args.agent:
        all_agents = [a for a in all_agents if args.agent.lower() in a["name"].lower()]
        if not all_agents:
            print(f"Agente '{args.agent}' non trovato. Disponibili: {[s['name'] for s in AGENT_SPECS]}")
            sys.exit(1)

    # Fix 2: ordina agenti per prompt crescente
    all_agents = sort_agents_by_prompt_length(all_agents)

    # Run benchmark
    results: Dict[str, List[Dict]] = {}

    for model_idx, model_name in enumerate(models):
        print(f"\n{'='*60}")
        print(f"[{model_idx+1}/{len(models)}] Modello: {model_name}")
        print(f"{'='*60}")

        client = get_client(model_name)

        # Fix 1: warmup
        print(f"  Warmup {model_name}...")
        warmup_model(client, model_name)
        time.sleep(3)

        model_metrics = []

        for agent_idx, agent in enumerate(all_agents):
            print(f"  [{agent_idx+1}/{len(all_agents)}] {agent['name']} "
                  f"(prompt: {len(agent['system'])+len(agent['user']):,} chars)...", end=" ", flush=True)

            metric = run_single_agent(
                client, model_name,
                agent["name"],
                agent["system"],
                agent["user"],
            )
            model_metrics.append(metric)

            if metric["success"]:
                print(f"OK ({metric['output_chars']:,} chars, {metric['time_seconds']}s)")
            else:
                print(f"ERRORE: {metric['error'][:60]}")

            # Pausa tra agenti
            if agent_idx < len(all_agents) - 1:
                time.sleep(args.pause)

        results[model_name] = model_metrics

        # Pausa tra modelli
        if model_idx < len(models) - 1:
            print(f"\n  Pausa 10s prima del prossimo modello...")
            time.sleep(10)

    # Report
    print(f"\n{'='*60}")
    print("RISULTATI BENCHMARK")
    print(f"{'='*60}")

    for model_name, metrics in results.items():
        total_chars = sum(m["output_chars"] for m in metrics)
        total_time = sum(m["time_seconds"] for m in metrics)
        ok = sum(1 for m in metrics if m["success"])
        print(f"  {model_name}: {ok}/{len(metrics)} OK, {total_chars:,} chars, {total_time:.1f}s")

    # Save HTML report
    html = generate_html_report(results, date_str)
    out_dir = Path("benchmarks")
    out_dir.mkdir(exist_ok=True)
    suffix = "_single" if args.single_model_test else ""
    report_path = out_dir / f"model_benchmark_riccione_{timestamp}{suffix}.html"
    report_path.write_text(html, encoding="utf-8")
    print(f"\nReport salvato: {report_path.resolve()}")

    # Save raw JSON data + diagnostics
    json_path = out_dir / f"model_benchmark_riccione_{timestamp}{suffix}.json"
    json_data = {
        "timestamp": timestamp,
        "models": models,
        "single_model_test": args.single_model_test,
        "results": {
            model: [
                {k: v for k, v in m.items() if k != "output"}
                for m in metrics
            ]
            for model, metrics in results.items()
        },
        "full_outputs": {
            model: {m["agent"]: m["output"] for m in metrics}
            for model, metrics in results.items()
        },
    }
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Dati JSON + diagnostica: {json_path.resolve()}")

    print("\nBenchmark completato.")


if __name__ == "__main__":
    main()

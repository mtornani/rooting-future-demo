"""
A/B Test CLI: Gemini vs Ollama on Riccione Calcio 1926 strategic plan.
Usage:
  python ab_test.py
  python ab_test.py --input "/path/to/interviews"
  python ab_test.py --provider gemini
  python ab_test.py --provider ollama
  python ab_test.py --ollama-model gemma3:9b
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Document reading
# ---------------------------------------------------------------------------

def read_docx(path: Path) -> str:
    """Read a .docx file using python-docx."""
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        logger.warning(f"Errore lettura docx {path}: {e}")
        return ""


def read_doc(path: Path) -> str:
    """Read a .doc file: try antiword, then raw bytes with latin-1 fallback."""
    # Try antiword
    try:
        result = subprocess.run(
            ["antiword", str(path)], capture_output=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.decode("utf-8", errors="replace")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Raw bytes fallback
    try:
        raw = path.read_bytes()
        text = raw.decode("latin-1", errors="replace")
        # Basic cleanup: keep printable ASCII + common latin chars
        cleaned = "".join(c if (ord(c) >= 32 or c in "\n\r\t") else " " for c in text)
        logger.warning(f"File .doc letto con fallback latin-1: {path}")
        return cleaned
    except Exception as e:
        logger.warning(f"Impossibile leggere {path}: {e}")
        return ""


def load_interviews(input_path: str) -> str:
    """Load all .docx and .doc files from input_path (ricorsivo nelle sottocartelle)."""
    p = Path(input_path)
    if not p.exists():
        logger.warning(f"Percorso non trovato: {input_path}")
        return ""

    # rglob: scansiona anche le sottocartelle (ogni intervista è in una cartella separata)
    files = sorted(set(list(p.rglob("*.docx")) + list(p.rglob("*.doc"))))
    # Escludi file temporanei Word (~$filename.docx)
    files = [f for f in files if not f.name.startswith("~$")]

    if not files:
        logger.warning(f"Nessun file .docx/.doc trovato in: {input_path}")
        return ""

    texts = []
    for f in files:
        print(f"  Lettura: {f.parent.name}/{f.name}")
        if f.suffix.lower() == ".docx":
            text = read_docx(f)
        else:
            text = read_doc(f)
        if text.strip():
            texts.append(f"=== {f.name} ===\n{text}")

    combined = "\n\n".join(texts)
    print(f"  Caricati {len(files)} file(s), {len(combined)} caratteri totali")
    return combined


# ---------------------------------------------------------------------------
# Club data builder
# ---------------------------------------------------------------------------

def build_club_data(interview_text: str) -> Dict:
    """
    Costruisce club_data per MultiAgentOrchestrator dalle interviste del board.
    Usa il meccanismo questionnaire ({key}_source="questionnaire") per iniettare
    il contesto nei prompt degli 8 agenti.
    """
    club_data: Dict = {
        "club_name": "Riccione Calcio 1926",
        "category": "Eccellenza",
    }

    if not interview_text.strip():
        logger.warning("Nessun testo interviste disponibile — uso dati minimi.")
        return club_data

    # synthesized_vision: primi 600 char (limite campo nel prompt)
    club_data["synthesized_vision"] = interview_text[:600]

    # Inietta il contesto delle interviste come campo questionnaire.
    # Il prompt include automaticamente: "- Interviste Board: <testo>"
    # Limite 3000 char per tenere i prompt gestibili.
    club_data["interviste_board"] = interview_text[:3000]
    club_data["interviste_board_source"] = "questionnaire"

    # Se il testo è lungo, aggiungi anche la seconda metà (altri 3000 char)
    if len(interview_text) > 3000:
        club_data["interviste_board_cont"] = interview_text[3000:6000]
        club_data["interviste_board_cont_source"] = "questionnaire"

    return club_data


def build_research_data(interview_text: str) -> Dict:
    """
    Mette il testo delle interviste anche in research_data (incluso nei prompt
    come 'DATI DA RICERCA WEB', troncato a 1000 char dal framework).
    """
    if not interview_text.strip():
        return {}
    return {
        "fonte": "Interviste dirette board Riccione Calcio 1926",
        "sintesi": interview_text[:900],
    }


# ---------------------------------------------------------------------------
# Per-agent metrics tracking
# ---------------------------------------------------------------------------

def run_provider(
    provider_name: str,
    club_data: Dict,
    research_data: Dict,
    env_setup_fn,
    env_teardown_fn,
    ollama_model: str = "gemma3:9b",
) -> Tuple[Optional[Dict], List[Dict]]:
    """
    Set up env, create orchestrator, run plan generation, return (result, metrics).
    metrics = list of {name, time_seconds, output_chars, success, error_msg}
    """
    print(f"\n{'='*60}")
    print(f"Avvio provider: {provider_name.upper()}")
    print(f"{'='*60}")

    env_setup_fn()

    try:
        from agents import MultiAgentOrchestrator, AgentRole, AGENT_SPECS
    except Exception as e:
        logger.error(f"Import agents fallito: {e}")
        env_teardown_fn()
        return None, []

    agent_metrics: List[Dict] = []
    plan_result = None

    try:
        orchestrator = MultiAgentOrchestrator()

        # Wrap each agent to capture per-agent timing
        original_agents = {}
        for role, agent in orchestrator.agents.items():
            original_agents[role] = agent

        # Run sequential generation and intercept per-agent timing
        # We monkey-patch generate on each agent to track metrics
        agent_results_store: Dict[str, Dict] = {}

        for role, agent in orchestrator.agents.items():
            original_generate = agent.generate

            def make_wrapper(agent_ref, role_ref, orig_fn):
                def wrapper(*args, **kwargs):
                    t0 = time.time()
                    metric = {
                        "name": agent_ref.spec.name,
                        "role": role_ref.value,
                        "time_seconds": 0.0,
                        "output_chars": 0,
                        "success": False,
                        "error_msg": "",
                    }
                    try:
                        result = orig_fn(*args, **kwargs)
                        metric["time_seconds"] = round(time.time() - t0, 2)
                        content = result.get("content", "") if isinstance(result, dict) else str(result)
                        metric["output_chars"] = len(content)
                        metric["success"] = True
                        print(f"  [{provider_name}] {agent_ref.spec.name}: {metric['time_seconds']}s, {metric['output_chars']} chars")
                        return result
                    except Exception as e:
                        metric["time_seconds"] = round(time.time() - t0, 2)
                        metric["error_msg"] = str(e)[:200]
                        metric["success"] = False
                        logger.error(f"Agente {agent_ref.spec.name} fallito: {e}")
                        print(f"  [{provider_name}] {agent_ref.spec.name}: ERRORE — {str(e)[:80]}")
                        raise
                    finally:
                        agent_metrics.append(metric)
                return wrapper

            agent.generate = make_wrapper(agent, role, original_generate)

        t_total = time.time()
        plan_result = orchestrator.generate_strategic_plan(
            club_data=club_data,
            research_data=research_data,
            parallel=False,
        )
        elapsed = round(time.time() - t_total, 2)
        print(f"  [{provider_name}] Piano completato in {elapsed}s")

    except Exception as e:
        logger.error(f"Provider {provider_name} fallito interamente: {e}")
        plan_result = None
    finally:
        env_teardown_fn()

    return plan_result, agent_metrics


# ---------------------------------------------------------------------------
# HTML Report generation
# ---------------------------------------------------------------------------

CSS = """
body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f4f6f9; color: #222; }
.header { background: linear-gradient(135deg, #1a237e, #283593); color: white; padding: 32px 40px; }
.header h1 { margin: 0 0 8px; font-size: 1.8em; }
.header .subtitle { opacity: 0.8; font-size: 0.95em; }
.container { max-width: 1400px; margin: 0 auto; padding: 24px 32px; }
.cards { display: flex; gap: 24px; margin-bottom: 32px; flex-wrap: wrap; }
.card { background: white; border-radius: 12px; padding: 24px; flex: 1; min-width: 260px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.card h2 { margin: 0 0 16px; font-size: 1.1em; color: #1a237e; border-bottom: 2px solid #e8eaf6; padding-bottom: 8px; }
.card .stat { font-size: 2em; font-weight: bold; color: #283593; }
.card .stat-label { font-size: 0.85em; color: #666; margin-top: 4px; }
.badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: bold; margin-top: 12px; }
.badge-ok { background: #e8f5e9; color: #2e7d32; }
.badge-fail { background: #ffebee; color: #c62828; }
.badge-partial { background: #fff8e1; color: #f57f17; }
.badge-na { background: #eeeeee; color: #757575; }
h2.section { color: #1a237e; margin-top: 40px; border-bottom: 2px solid #e8eaf6; padding-bottom: 8px; }
table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; }
th { background: #1a237e; color: white; padding: 12px 16px; text-align: left; font-size: 0.9em; }
td { padding: 10px 16px; border-bottom: 1px solid #f0f0f0; font-size: 0.88em; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f8f9ff; }
.ok-cell { color: #2e7d32; font-weight: bold; }
.fail-cell { color: #c62828; font-weight: bold; }
.compare-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px; }
.compare-col { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.compare-col h3 { margin: 0 0 12px; font-size: 1em; color: #1a237e; }
.compare-col pre { white-space: pre-wrap; word-break: break-word; font-family: inherit;
                   font-size: 0.85em; line-height: 1.6; margin: 0; color: #333; max-height: 400px;
                   overflow-y: auto; }
.verdict { background: white; border-radius: 12px; padding: 28px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-top: 32px; }
.verdict h2 { margin: 0 0 20px; color: #1a237e; }
.verdict-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
.verdict-item { text-align: center; padding: 16px; background: #f8f9ff; border-radius: 8px; }
.verdict-item .v-label { font-size: 0.8em; color: #666; margin-bottom: 8px; }
.verdict-item .v-value { font-size: 1.5em; font-weight: bold; color: #283593; }
.overall-pass { color: #2e7d32; font-size: 1.6em; font-weight: bold; }
.overall-partial { color: #f57f17; font-size: 1.6em; font-weight: bold; }
.overall-fail { color: #c62828; font-size: 1.6em; font-weight: bold; }
.placeholder { color: #aaa; font-style: italic; }
"""

PLAN_SECTIONS = [
    ("stw_sportivi", "STW Sportivi"),
    ("stw_strutturali", "STW Strutturali"),
    ("stw_marketing", "STW Marketing"),
    ("stw_sociali", "STW Sociali"),
    ("financial", "Piano Finanziario"),
    ("executive_summary", "Executive Summary"),
]

AGENT_ROLES = [
    "Strategic Coordinator",
    "STW Sportivi",
    "STW Strutturali",
    "STW Marketing",
    "STW Sociali",
    "Financial",
]


def escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def metrics_by_name(metrics: List[Dict]) -> Dict[str, Dict]:
    return {m["name"]: m for m in metrics}


def generate_html_report(
    gemini_result: Optional[Dict],
    gemini_metrics: List[Dict],
    ollama_result: Optional[Dict],
    ollama_metrics: List[Dict],
    ollama_model: str,
    date_str: str,
) -> str:
    """Build the full HTML report as a string."""

    def provider_summary(result, metrics, name):
        total_time = sum(m["time_seconds"] for m in metrics)
        total_chars = sum(m["output_chars"] for m in metrics)
        ok = sum(1 for m in metrics if m["success"])
        total = len(metrics)
        if result is None and not metrics:
            status = '<span class="badge badge-na">NON DISPONIBILE</span>'
        elif ok == total and total > 0:
            status = '<span class="badge badge-ok">OK</span>'
        elif ok == 0:
            status = '<span class="badge badge-fail">FAIL</span>'
        else:
            status = f'<span class="badge badge-partial">PARZIALE {ok}/{total}</span>'
        return f"""
<div class="card">
  <h2>{escape_html(name)}</h2>
  <div class="stat">{total_time:.1f}s</div>
  <div class="stat-label">Tempo totale</div>
  <div class="stat" style="margin-top:12px">{total_chars:,}</div>
  <div class="stat-label">Caratteri generati</div>
  <div class="stat" style="margin-top:12px">{ok}/{total}</div>
  <div class="stat-label">Agenti completati</div>
  {status}
</div>"""

    # Discover all agent names from metrics
    all_agent_names = []
    seen = set()
    for m in gemini_metrics + ollama_metrics:
        if m["name"] not in seen:
            all_agent_names.append(m["name"])
            seen.add(m["name"])

    gm = metrics_by_name(gemini_metrics)
    om = metrics_by_name(ollama_metrics)

    def cell_time(metrics_dict, name):
        if name not in metrics_dict:
            return '<td class="placeholder">—</td>'
        m = metrics_dict[name]
        return f'<td>{m["time_seconds"]:.1f}s</td>'

    def cell_chars(metrics_dict, name):
        if name not in metrics_dict:
            return '<td class="placeholder">—</td>'
        m = metrics_dict[name]
        return f'<td>{m["output_chars"]:,}</td>'

    def cell_status(metrics_dict, name):
        if name not in metrics_dict:
            return '<td class="placeholder">—</td>'
        m = metrics_dict[name]
        if m["success"]:
            return '<td class="ok-cell">OK</td>'
        err = escape_html(m.get("error_msg", "")[:60])
        return f'<td class="fail-cell" title="{err}">FAIL</td>'

    table_rows = ""
    for name in all_agent_names:
        table_rows += f"""<tr>
  <td><strong>{escape_html(name)}</strong></td>
  {cell_time(gm, name)}
  {cell_time(om, name)}
  {cell_chars(gm, name)}
  {cell_chars(om, name)}
  {cell_status(gm, name)}
  {cell_status(om, name)}
</tr>"""

    def plan_section_html(section_key, section_label):
        g_text = ""
        o_text = ""
        if gemini_result and gemini_result.get("plan"):
            g_text = gemini_result["plan"].get(section_key, "")
        if ollama_result and ollama_result.get("plan"):
            o_text = ollama_result["plan"].get(section_key, "")

        g_content = f'<pre>{escape_html(g_text[:3000])}</pre>' if g_text else '<p class="placeholder">PROVIDER NON DISPONIBILE</p>'
        o_content = f'<pre>{escape_html(o_text[:3000])}</pre>' if o_text else '<p class="placeholder">PROVIDER NON DISPONIBILE</p>'

        return f"""
<h2 class="section">{escape_html(section_label)}</h2>
<div class="compare-grid">
  <div class="compare-col">
    <h3>Gemini</h3>
    {g_content}
  </div>
  <div class="compare-col">
    <h3>{escape_html(ollama_model)}</h3>
    {o_content}
  </div>
</div>"""

    sections_html = "".join(plan_section_html(k, l) for k, l in PLAN_SECTIONS)

    # Verdict computation
    g_ok = sum(1 for m in gemini_metrics if m["success"])
    g_total = max(len(gemini_metrics), 1)
    o_ok = sum(1 for m in ollama_metrics if m["success"])
    o_total = max(len(ollama_metrics), 1)
    g_chars = sum(m["output_chars"] for m in gemini_metrics)
    o_chars = sum(m["output_chars"] for m in ollama_metrics)
    g_time = sum(m["time_seconds"] for m in gemini_metrics)
    o_time = sum(m["time_seconds"] for m in ollama_metrics)

    completeness_g = round(g_ok / g_total * 100, 1)
    completeness_o = round(o_ok / o_total * 100, 1)
    length_ratio = round(o_chars / g_chars, 2) if g_chars > 0 else 0.0
    speed_ratio = round(o_time / g_time, 2) if g_time > 0 else 0.0

    if completeness_o >= 80 and 0.5 <= length_ratio <= 2.0:
        overall = "PASS"
        overall_class = "overall-pass"
    elif completeness_o >= 50:
        overall = "PARTIAL"
        overall_class = "overall-partial"
    else:
        overall = "FAIL"
        overall_class = "overall-fail"

    verdict_html = f"""
<div class="verdict">
  <h2>Verdetto A/B Test</h2>
  <div class="verdict-grid">
    <div class="verdict-item">
      <div class="v-label">Completezza Gemini</div>
      <div class="v-value">{completeness_g}%</div>
    </div>
    <div class="verdict-item">
      <div class="v-label">Completezza Ollama</div>
      <div class="v-value">{completeness_o}%</div>
    </div>
    <div class="verdict-item">
      <div class="v-label">Rapporto Lunghezza (O/G)</div>
      <div class="v-value">{length_ratio}</div>
    </div>
    <div class="verdict-item">
      <div class="v-label">Rapporto Velocità (O/G)</div>
      <div class="v-value">{speed_ratio}x</div>
    </div>
    <div class="verdict-item">
      <div class="v-label">Risultato Complessivo</div>
      <div class="v-value {overall_class}">{overall}</div>
    </div>
  </div>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A/B Test Riccione Calcio 1926 — {escape_html(date_str)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="header">
  <h1>A/B Test: Riccione Calcio 1926 | Gemini vs {escape_html(ollama_model)} | {escape_html(date_str)}</h1>
  <div class="subtitle">Confronto automatico provider AI per piano strategico</div>
</div>
<div class="container">

<h2 class="section">Riepilogo Provider</h2>
<div class="cards">
  {provider_summary(gemini_result, gemini_metrics, "Gemini")}
  {provider_summary(ollama_result, ollama_metrics, ollama_model)}
</div>

<h2 class="section">Metriche per Agente</h2>
<table>
  <thead>
    <tr>
      <th>Agente</th>
      <th>Gemini Tempo</th>
      <th>Ollama Tempo</th>
      <th>Gemini Chars</th>
      <th>Ollama Chars</th>
      <th>Gemini Status</th>
      <th>Ollama Status</th>
    </tr>
  </thead>
  <tbody>
    {table_rows}
  </tbody>
</table>

{sections_html}

{verdict_html}

</div>
</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="A/B Test Gemini vs Ollama — Riccione Calcio 1926")
    parser.add_argument(
        "--input",
        default=r"C:\Users\Mirko\Desktop\BOARD RICCIONE CALCIO 1926",
        help="Percorso cartella interviste (.docx/.doc)",
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "ollama", "both"],
        default="both",
        help="Provider da testare (default: both)",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="URL base Ollama (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--ollama-model",
        default="gemma3:9b",
        help="Modello Ollama (default: gemma3:9b)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    print("=" * 60)
    print("A/B TEST: Riccione Calcio 1926 — Gemini vs Ollama")
    print(f"Data: {date_str}")
    print("=" * 60)

    # Load interviews
    print(f"\nCaricamento interviste da: {args.input}")
    interview_text = load_interviews(args.input)

    if not interview_text.strip():
        print("ATTENZIONE: Nessuna intervista trovata — uso dati minimi.")

    # Build club data
    club_data = build_club_data(interview_text)
    research_data: Dict = build_research_data(interview_text)

    print(f"\nClub data pronto: {list(club_data.keys())}")

    # Env helpers
    saved_ollama_url: Optional[str] = os.environ.get("OLLAMA_BASE_URL")

    def gemini_setup():
        # Remove OLLAMA_BASE_URL so factory picks Gemini
        if "OLLAMA_BASE_URL" in os.environ:
            del os.environ["OLLAMA_BASE_URL"]
        print("  [env] OLLAMA_BASE_URL rimossa → provider: Gemini")

    def gemini_teardown():
        # Restore original value
        if saved_ollama_url is not None:
            os.environ["OLLAMA_BASE_URL"] = saved_ollama_url
        elif "OLLAMA_BASE_URL" in os.environ:
            del os.environ["OLLAMA_BASE_URL"]

    def ollama_setup():
        os.environ["OLLAMA_BASE_URL"] = args.ollama_url
        os.environ["OLLAMA_TIMEOUT"] = "300"
        print(f"  [env] OLLAMA_BASE_URL={args.ollama_url} → provider: Ollama")

    def ollama_teardown():
        # Restore Gemini state for consistency
        if saved_ollama_url is None and "OLLAMA_BASE_URL" in os.environ:
            del os.environ["OLLAMA_BASE_URL"]
        elif saved_ollama_url is not None:
            os.environ["OLLAMA_BASE_URL"] = saved_ollama_url

    # Run providers
    gemini_result: Optional[Dict] = None
    gemini_metrics: List[Dict] = []
    ollama_result: Optional[Dict] = None
    ollama_metrics: List[Dict] = []

    if args.provider in ("both", "gemini"):
        gemini_result, gemini_metrics = run_provider(
            "gemini",
            club_data,
            research_data,
            gemini_setup,
            gemini_teardown,
            ollama_model=args.ollama_model,
        )

    if args.provider in ("both", "ollama"):
        ollama_result, ollama_metrics = run_provider(
            "ollama",
            club_data,
            research_data,
            ollama_setup,
            ollama_teardown,
            ollama_model=args.ollama_model,
        )

    # Generate report
    print("\nGenerazione report HTML...")
    html = generate_html_report(
        gemini_result=gemini_result,
        gemini_metrics=gemini_metrics,
        ollama_result=ollama_result,
        ollama_metrics=ollama_metrics,
        ollama_model=args.ollama_model,
        date_str=date_str,
    )

    output_dir = Path("ab_tests")
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / f"ab_test_riccione_{timestamp}.html"
    report_path.write_text(html, encoding="utf-8")

    print(f"\nReport salvato: {report_path.resolve()}")
    print("A/B test completato.")


if __name__ == "__main__":
    main()

"""
Rooting Future -- Wiki Ingest Pipeline
Converte i documenti di un club in pagine Wiki strutturate.

Fase 1 (locale, no LLM): DOCX -> Markdown in wiki/raw/{slug}/
Fase 2 (LLM via Ollama): Sintesi -> pagine Wiki in wiki/kb/

Usage:
  python wiki_ingest.py "C:\\Users\\Mirko\\Desktop\\BOARD RICCIONE CALCIO 1926" --club "Riccione Calcio 1926" --category eccellenza --region emilia-romagna
  python wiki_ingest.py --phase 1   # Solo conversione DOCX -> MD
  python wiki_ingest.py --phase 2   # Solo sintesi LLM (raw gia' presenti)
"""

import argparse
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WIKI_DIR = Path(__file__).parent / "wiki"
RAW_DIR = WIKI_DIR / "raw"
KB_DIR = WIKI_DIR / "kb"

# Mapping nomi file DOCX -> slug wiki
DOC_TYPE_MAP = {
    "vision": "vision",
    "mission": "mission",
    "swot": "swot",
    "analisi swot": "swot",
    "pest": "pest",
    "analisi pest": "pest",
    "competitors": "competitors",
    "analisi competitors": "competitors",
    "stakeholders": "stakeholders",
    "analisi stakeholders": "stakeholders",
    "risorse": "risorse",
    "analisi risorse": "risorse",
    "valori": "valori-fondamenta",
    "fondamenta": "valori-fondamenta",
    "fondamenta e valori": "valori-fondamenta",
}


def slugify(name: str) -> str:
    """Converte un nome in slug: lowercase, trattini, no caratteri speciali."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


# ---------------------------------------------------------------------------
# FASE 1: DOCX -> Markdown
# ---------------------------------------------------------------------------

def read_docx(path: Path) -> str:
    """Legge un .docx via python-docx."""
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        logger.warning(f"Errore lettura docx {path}: {e}")
        return ""


def read_doc(path: Path) -> str:
    """Legge un .doc: prova antiword, poi fallback latin-1."""
    try:
        result = subprocess.run(
            ["antiword", str(path)], capture_output=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.decode("utf-8", errors="replace")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        raw = path.read_bytes()
        text = raw.decode("latin-1", errors="replace")
        cleaned = "".join(c if (ord(c) >= 32 or c in "\n\r\t") else " " for c in text)
        return cleaned
    except Exception as e:
        logger.warning(f"Impossibile leggere {path}: {e}")
        return ""


def classify_document(filename: str) -> Optional[str]:
    """Classifica un file in uno dei 9 tipi documentali."""
    name = filename.lower()
    # Rimuovi estensione e numeri tra parentesi
    name = re.sub(r"\.\w+$", "", name)
    name = re.sub(r"\s*\(\d+\)\s*", "", name)
    name = name.strip()

    for pattern, doc_type in DOC_TYPE_MAP.items():
        if pattern in name:
            return doc_type
    return None


def phase1_convert(
    input_path: Path,
    club_slug: str,
    club_name: str,
) -> Dict[str, List[Tuple[str, str]]]:
    """
    Converte tutti i DOCX in markdown, raggruppati per tipo documento.
    Ritorna: {doc_type: [(source_label, text), ...]}
    """
    raw_dir = RAW_DIR / club_slug
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Trova tutti i DOCX/DOC
    files = sorted(set(list(input_path.rglob("*.docx")) + list(input_path.rglob("*.doc"))))
    files = [f for f in files if not f.name.startswith("~$")]

    if not files:
        logger.error(f"Nessun file .docx/.doc trovato in: {input_path}")
        return {}

    # Raggruppa per tipo + interviewee
    grouped: Dict[str, List[Tuple[str, str]]] = {}

    for f in files:
        doc_type = classify_document(f.name)
        if not doc_type:
            logger.warning(f"  Tipo non riconosciuto, skip: {f.name}")
            continue

        # Identifica l'intervistato dalla cartella
        parent_name = f.parent.name
        if parent_name.lower().startswith("intervista"):
            interviewee = parent_name.replace("INTERVISTA", "").replace("intervista", "").strip()
            source_label = f"Intervista {interviewee}"
        elif parent_name.lower() == "file word":
            source_label = "Documento compilato"
        else:
            source_label = parent_name

        print(f"  [{doc_type}] {f.parent.name}/{f.name} -> {source_label}")

        if f.suffix.lower() == ".docx":
            text = read_docx(f)
        else:
            text = read_doc(f)

        if text.strip():
            if doc_type not in grouped:
                grouped[doc_type] = []
            grouped[doc_type].append((source_label, text))

    # Scrivi i file markdown raggruppati
    for doc_type, entries in grouped.items():
        md_path = raw_dir / f"{doc_type}.md"
        parts = [f"# {doc_type.replace('-', ' ').title()} -- {club_name}\n"]

        for source_label, text in entries:
            parts.append(f"\n## {source_label}\n")
            parts.append(text)
            parts.append("")

        md_path.write_text("\n".join(parts), encoding="utf-8")
        logger.info(f"  Salvato: {md_path.relative_to(WIKI_DIR)} ({len(entries)} fonti, {sum(len(t) for _, t in entries)} chars)")

    # Crea anche un file intervista-board.md con tutte le interviste unite
    all_texts = []
    for doc_type, entries in sorted(grouped.items()):
        for source_label, text in entries:
            all_texts.append(f"### {doc_type.upper()} -- {source_label}\n\n{text}")

    board_md = raw_dir / "intervista-board.md"
    board_md.write_text(
        f"# Interviste Board -- {club_name}\n\n" + "\n\n---\n\n".join(all_texts),
        encoding="utf-8",
    )
    logger.info(f"  Salvato: {board_md.relative_to(WIKI_DIR)} (tutte le interviste unite)")

    return grouped


# ---------------------------------------------------------------------------
# FASE 2: Sintesi LLM -> Pagine Wiki
# ---------------------------------------------------------------------------

def get_llm_client():
    """Crea client OpenAI-compatible per Ollama."""
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("pip install openai richiesto per Fase 2")
        sys.exit(1)

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    api_key = os.environ.get("OLLAMA_API_KEY", "ollama")
    model = os.environ.get("OLLAMA_MODEL", "gemma3:27b")

    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=int(os.environ.get("OLLAMA_TIMEOUT", "300")),
        max_retries=3,
    )
    return client, model


def llm_generate(client, model: str, system_prompt: str, user_prompt: str, max_retries: int = 4) -> str:
    """Chiama LLM con retry per rate limit e connection errors."""
    backoff = [15, 30, 60, 90]
    last_exc = None

    for attempt in range(max_retries):
        try:
            t0 = time.time()
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
                max_tokens=8192,
            )
            elapsed = time.time() - t0
            text = response.choices[0].message.content
            logger.info(f"  LLM risposta in {elapsed:.1f}s ({len(text)} chars)")
            return text
        except Exception as e:
            last_exc = e
            err = str(e)
            if attempt < max_retries - 1 and ("429" in err or "onnect" in err or "imeout" in err):
                wait = backoff[min(attempt, len(backoff) - 1)]
                print(f"    [retry] attendo {wait}s... ({err[:80]})")
                time.sleep(wait)
                continue
            break

    logger.error(f"LLM errore dopo {max_retries} tentativi: {last_exc}")
    raise last_exc


def phase2_synthesize(
    club_slug: str,
    club_name: str,
    category: str,
    region: str,
) -> None:
    """Usa LLM per creare pagine Wiki dal raw."""
    raw_dir = RAW_DIR / club_slug
    if not raw_dir.exists():
        logger.error(f"Raw dir non trovata: {raw_dir}. Esegui prima Fase 1.")
        return

    client, model = get_llm_client()
    print(f"\nFase 2: Sintesi LLM (model={model})")
    print(f"  Club: {club_name} ({category}, {region})")

    # Leggi tutti i raw documents
    raw_docs: Dict[str, str] = {}
    for md_file in sorted(raw_dir.glob("*.md")):
        raw_docs[md_file.stem] = md_file.read_text(encoding="utf-8")
        print(f"  Letto: {md_file.name} ({len(raw_docs[md_file.stem])} chars)")

    # Tronca a 40K totali se necessario (per stare nel context)
    total_chars = sum(len(v) for v in raw_docs.values())
    if total_chars > 40000:
        ratio = 40000 / total_chars
        raw_docs = {k: v[:int(len(v) * ratio)] for k, v in raw_docs.items()}
        logger.warning(f"  Troncato da {total_chars} a ~40K chars")

    # --- Pagina Club ---
    print(f"\n  Generazione pagina club: clubs/{club_slug}.md")
    all_raw = "\n\n---\n\n".join(f"## {k.upper()}\n\n{v}" for k, v in raw_docs.items())

    club_page = llm_generate(
        client, model,
        system_prompt=(
            "Sei un analista strategico per societa' calcistiche. "
            "Il tuo compito e' sintetizzare i documenti di un club in una pagina Wiki strutturata. "
            "Scrivi in italiano professionale, voce istituzionale. "
            "NON inventare dati. Se un dato non e' presente nei documenti, scrivi '(dato da acquisire)'. "
            "Usa formato Markdown con sezioni chiare."
        ),
        user_prompt=f"""Crea una pagina Wiki di sintesi per il club seguente.

CLUB: {club_name}
CATEGORIA: {category}
REGIONE: {region}

DOCUMENTI RAW:

{all_raw}

---

Struttura OBBLIGATORIA della pagina:

## Anagrafica
Nome, categoria, regione, anno fondazione (se menzionato), sede.

## Vision e Mission
Sintesi della vision e mission del club come emersa dai documenti.

## Analisi SWOT
Tabella con i 3 punti piu' importanti per ogni quadrante (Forze, Debolezze, Opportunita', Minacce).

## Analisi PEST
Fattori Politici, Economici, Sociali, Tecnologici rilevanti.

## Stakeholder Chiave
Lista degli stakeholder principali con il loro peso e interessi.

## Risorse Disponibili
Budget stimato, staff, infrastrutture, settore giovanile.

## Competitor
Principali competitor e posizionamento relativo.

## Temi Emersi dalle Interviste
I 5-10 temi ricorrenti emersi dalle interviste board. Per ogni tema, chi lo ha menzionato e come.

## Sfide Strategiche Prioritarie
Le 3-5 sfide principali che il piano strategico deve affrontare.

Scrivi almeno 3000 caratteri. Sii specifico e concreto, basandoti SOLO sui documenti forniti.""",
    )

    # Salva pagina club
    today = datetime.now().strftime("%Y-%m-%d")
    club_dir = KB_DIR / "clubs"
    club_dir.mkdir(parents=True, exist_ok=True)
    club_page_path = club_dir / f"{club_slug}.md"

    frontmatter = f"""---
title: "{club_name}"
tags: [{category}, club]
clubs: [{club_slug}]
date_created: {today}
date_updated: {today}
sources:"""
    for doc_name in raw_docs:
        frontmatter += f"\n  - raw/{club_slug}/{doc_name}.md"
    frontmatter += "\n---\n\n"

    club_page_path.write_text(frontmatter + club_page, encoding="utf-8")
    print(f"  Salvato: {club_page_path.relative_to(WIKI_DIR)} ({len(club_page)} chars)")

    # --- Pagina Benchmark ---
    print(f"\n  Generazione benchmark: benchmark/{category}-{region}.md")
    benchmark_page = llm_generate(
        client, model,
        system_prompt=(
            "Sei un analista del calcio dilettantistico italiano. "
            "Estrai dati quantitativi dai documenti di un club per creare una pagina benchmark. "
            "Includi solo dati presenti nei documenti o stime ragionevoli basate sulla categoria. "
            "Per ogni dato indica se e' reale (dal club) o stimato."
        ),
        user_prompt=f"""Dai documenti del {club_name} (categoria {category}, regione {region}), estrai tutti i dati quantitativi disponibili e crea una pagina benchmark.

DOCUMENTI RILEVANTI:
{raw_docs.get('risorse', '(non disponibile)')}

{raw_docs.get('stakeholders', '(non disponibile)')}

---

Struttura:
## Budget e Finanze
Ricavi totali, costi, sponsorizzazioni, contributi, biglietteria.

## Staff e Organico
Numero dipendenti, volontari, staff tecnico, dirigenti.

## Infrastrutture
Stadio (capienza, proprieta'/concessione), centro sportivo, strutture giovanili.

## Settore Giovanile
Numero squadre, tesserati giovanili, istruttori, costi.

## Dati Sportivi
Categoria, risultati recenti, obiettivi sportivi.

Per ogni dato, aggiungi: (fonte: questionario) se dal club, (fonte: stima) se stimato.
Se non ci sono dati, scrivi '(dato da acquisire)' -- NON inventare numeri.""",
    )

    bench_path = KB_DIR / "benchmark" / f"{category}-{region}.md"
    bench_path.parent.mkdir(parents=True, exist_ok=True)
    bench_fm = f"""---
title: "Benchmark {category.title()} - {region.title()}"
tags: [{category}, {region}, benchmark]
clubs: [{club_slug}]
date_created: {today}
date_updated: {today}
---

"""
    bench_path.write_text(bench_fm + benchmark_page, encoding="utf-8")
    print(f"  Salvato: {bench_path.relative_to(WIKI_DIR)} ({len(benchmark_page)} chars)")

    # --- Pagine Strategie (estrarre pattern) ---
    print(f"\n  Generazione pagine strategie...")
    strategies_page = llm_generate(
        client, model,
        system_prompt=(
            "Sei un consulente strategico specializzato in societa' calcistiche dilettantistiche italiane. "
            "Analizza i documenti e identifica i 3-5 pattern strategici principali che possono essere "
            "generalizzati come best practice per club simili. "
            "Per ogni pattern, scrivi una sezione con: descrizione, contesto in cui applicarlo, "
            "azioni concrete, rischi, esempi dal club analizzato."
        ),
        user_prompt=f"""Dai documenti del {club_name} ({category}), identifica 3-5 pattern strategici ricorrenti.

SWOT:
{raw_docs.get('swot', '(non disponibile)')}

VISION:
{raw_docs.get('vision', '(non disponibile)')}

RISORSE:
{raw_docs.get('risorse', '(non disponibile)')}

COMPETITORS:
{raw_docs.get('competitors', '(non disponibile)')}

Per ogni pattern, crea una sezione Markdown con:
- Titolo descrittivo (es. "Sviluppo Settore Giovanile per Club di Eccellenza")
- Contesto: quando questo pattern e' applicabile
- Azioni concrete: 3-5 step
- Rischi: cosa puo' andare storto
- Esempio dal {club_name}: come il club affronta questo tema

I pattern devono essere GENERALI (utili per altri club della stessa categoria), non specifici solo per {club_name}.
Scrivi almeno 500 caratteri per pattern.""",
    )

    # Salva come singolo file per ora; in futuro si splitta per pattern
    strat_path = KB_DIR / "strategie" / f"pattern-{category}.md"
    strat_path.parent.mkdir(parents=True, exist_ok=True)
    strat_fm = f"""---
title: "Pattern Strategici - {category.title()}"
tags: [{category}, strategia]
clubs: [{club_slug}]
date_created: {today}
date_updated: {today}
---

"""
    strat_path.write_text(strat_fm + strategies_page, encoding="utf-8")
    print(f"  Salvato: {strat_path.relative_to(WIKI_DIR)} ({len(strategies_page)} chars)")

    # --- Pagina Concetti STW ---
    print(f"\n  Generazione concetti STW...")
    stw_page = llm_generate(
        client, model,
        system_prompt=(
            "Sei un esperto della metodologia STW (Stakeholder Theory) applicata al calcio. "
            "La matrice STW ha 4 aree: Sportivi, Strutturali, Marketing, Sociali. "
            "Per ogni area, sintetizza cosa emerge dai documenti del club."
        ),
        user_prompt=f"""Dai documenti del {club_name}, sintetizza le 4 aree STW.

TUTTI I DOCUMENTI:
{all_raw[:20000]}

Per ogni area STW scrivi:
## STW Sportivi
Obiettivi sportivi, settore giovanile, prima squadra, competitivita'.

## STW Strutturali
Infrastrutture, risorse umane, governance, organizzazione.

## STW Marketing
Brand, comunicazione, sponsorizzazioni, ricavi commerciali, community.

## STW Sociali
Impatto sociale, sostenibilita', rapporto col territorio, inclusione.

Per ogni area: stato attuale (dal club) + gap identificati + priorita' di intervento.
Basati SOLO sui documenti, non inventare.""",
    )

    stw_path = KB_DIR / "concetti" / "stw-overview.md"
    stw_path.parent.mkdir(parents=True, exist_ok=True)
    stw_fm = f"""---
title: "STW Overview"
tags: [concetto, stw]
clubs: [{club_slug}]
date_created: {today}
date_updated: {today}
---

"""
    stw_path.write_text(stw_fm + stw_page, encoding="utf-8")
    print(f"  Salvato: {stw_path.relative_to(WIKI_DIR)} ({len(stw_page)} chars)")

    # --- Aggiorna index.md ---
    print(f"\n  Aggiornamento index.md e log.md...")
    update_index(club_slug, club_name, category, region, today)
    update_log(club_slug, club_name, category, region, today, [
        f"clubs/{club_slug}.md",
        f"benchmark/{category}-{region}.md",
        f"strategie/pattern-{category}.md",
        "concetti/stw-overview.md",
    ])

    print(f"\n{'='*60}")
    print(f"Ingest completato per {club_name}!")
    print(f"  Raw: wiki/raw/{club_slug}/ ({len(raw_docs)} documenti)")
    print(f"  Wiki: 4 pagine generate in wiki/kb/")
    print(f"{'='*60}")


def update_index(slug: str, name: str, category: str, region: str, today: str):
    """Aggiorna wiki/kb/index.md con le nuove pagine."""
    index_path = KB_DIR / "index.md"
    content = f"""---
title: "Wiki Index"
date_updated: {today}
---

# Rooting Future Wiki -- Indice

> Catalogo di tutte le pagine della Knowledge Base.
> Il LLM legge questo file per primo per trovare pagine rilevanti.

## Club

- **[{name}](clubs/{slug}.md)** -- {category.title()}, {region.title()}. Pagina sintesi completa.

## Strategie

- **[Pattern Strategici {category.title()}](strategie/pattern-{category}.md)** -- Best practice e pattern ricorrenti per club di {category.title()}.

## Benchmark

- **[Benchmark {category.title()} {region.title()}](benchmark/{category}-{region}.md)** -- Dati quantitativi di riferimento.

## Concetti

- **[STW Overview](concetti/stw-overview.md)** -- Sintesi delle 4 aree STW basata sui club analizzati.

## Sintesi

_Disponibile dopo almeno 3 club ingeriti._
"""
    index_path.write_text(content, encoding="utf-8")


def update_log(slug: str, name: str, category: str, region: str, today: str, pages: List[str]):
    """Appende entry al log.md."""
    log_path = KB_DIR / "log.md"
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""

    entry = f"""
---
## {today} -- Ingest: {name}
- Club: {name} ({category.title()}, {region.title()})
- Pagine create/aggiornate: {', '.join(pages)}
- Modello LLM: {os.environ.get('OLLAMA_MODEL', '(non specificato)')}
- Note: Prima ingest del club nel Wiki
"""
    log_path.write_text(existing + entry, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Rooting Future Wiki Ingest -- Converti documenti club in Wiki",
    )
    parser.add_argument(
        "input_path",
        nargs="?",
        default="data/clubs/riccione-calcio-1926",
        help="Percorso cartella documenti club",
    )
    parser.add_argument("--club", default="Riccione Calcio 1926", help="Nome completo del club")
    parser.add_argument("--category", default="eccellenza", help="Categoria (eccellenza, serie-d, ...)")
    parser.add_argument("--region", default="emilia-romagna", help="Regione")
    parser.add_argument("--phase", type=int, choices=[1, 2], default=0, help="Esegui solo fase 1 o 2 (default: entrambe)")
    args = parser.parse_args()

    club_slug = slugify(args.club)
    input_path = Path(args.input_path)

    print("=" * 60)
    print("WIKI INGEST: " + args.club)
    print(f"  Slug: {club_slug}")
    print(f"  Input: {input_path}")
    print(f"  Categoria: {args.category}")
    print(f"  Regione: {args.region}")
    print(f"  Fase: {'entrambe' if args.phase == 0 else args.phase}")
    print("=" * 60)

    if args.phase in (0, 1):
        print(f"\n--- FASE 1: Conversione DOCX -> Markdown ---")
        if not input_path.exists():
            logger.error(f"Percorso non trovato: {input_path}")
            sys.exit(1)
        grouped = phase1_convert(input_path, club_slug, args.club)
        if not grouped:
            logger.error("Nessun documento convertito. Abort.")
            sys.exit(1)
        print(f"\n  Fase 1 completata: {len(grouped)} tipi di documento, salvati in wiki/raw/{club_slug}/")

    if args.phase in (0, 2):
        print(f"\n--- FASE 2: Sintesi LLM -> Pagine Wiki ---")
        phase2_synthesize(club_slug, args.club, args.category, args.region)


if __name__ == "__main__":
    main()

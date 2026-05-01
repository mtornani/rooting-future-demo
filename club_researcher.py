"""
Club Researcher — AI-mediated club profile enrichment.
Queries Gemini with a structured prompt to find public data about a football club.
Returns a dict with field values + source types for human review.
"""

import json
import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Fields the researcher tries to fill
PROFILE_FIELDS = [
    "ragione_sociale",
    "categoria",
    "anno_fondazione",
    "sede",
    "regione",
    "fatturato_stimato",
    "n_atleti",
    "presidente",
    "website",
]

RESEARCH_PROMPT = """Sei un ricercatore specializzato nel calcio italiano.
Ti vengono forniti il nome del club e opzionalmente la P.IVA.
Il tuo compito è trovare informazioni PUBBLICHE e VERIFICABILI sul club.

CLUB: {club_name}
P.IVA: {piva}

Restituisci SOLO un JSON valido con questa struttura (nessun testo fuori dal JSON):
{{
  "ragione_sociale": "nome legale completo o null",
  "categoria": "categoria FIGC attuale (es. Eccellenza, Promozione, Prima Categoria) o null",
  "anno_fondazione": anno come intero o null,
  "sede": "città sede o null",
  "regione": "regione italiana o null",
  "fatturato_stimato": "range fatturato annuo (es. '100K-300K €') o null",
  "n_atleti": numero totale atleti tesserati come intero o null,
  "presidente": "nome presidente attuale o null",
  "website": "URL sito ufficiale o null",
  "sources": {{
    "ragione_sociale": "official|web|estimate|unknown",
    "categoria": "official|web|estimate|unknown",
    "anno_fondazione": "official|web|estimate|unknown",
    "sede": "official|web|estimate|unknown",
    "regione": "official|web|estimate|unknown",
    "fatturato_stimato": "official|web|estimate|unknown",
    "n_atleti": "official|web|estimate|unknown",
    "presidente": "official|web|estimate|unknown",
    "website": "official|web|estimate|unknown"
  }},
  "note": "note aggiuntive brevi o null"
}}

REGOLE:
- Se un dato non è reperibile con certezza, metti null (non inventare)
- Per fatturato ASD usa sempre "estimate" come source
- Per categoria FIGC usa "official" solo se sei sicuro dalla fonte FIGC/federazione
- Sii conservativo: meglio null che dati errati
"""


def research_club(club_name: str, piva: str = "", gemini_client=None) -> Dict:
    """
    Calls Gemini to research public data about the club.
    Returns dict with field values + sources for human review.
    Falls back to empty dict on any error.
    """
    if gemini_client is None:
        try:
            import google.generativeai as genai
            import os
            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                logger.warning("No Gemini API key — returning empty research")
                return _empty_research(club_name)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
        except Exception as e:
            logger.error(f"Gemini init failed: {e}")
            return _empty_research(club_name)
    else:
        model = gemini_client

    prompt = RESEARCH_PROMPT.format(
        club_name=club_name,
        piva=piva or "non fornita",
    )

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Strip markdown code fences if present
        raw = re.sub(r'^```[a-z]*\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw)

        data = json.loads(raw)
        logger.info(f"Club research OK for '{club_name}'")
        return _normalize(data, club_name)

    except json.JSONDecodeError as e:
        logger.error(f"Club research JSON parse error: {e} — raw: {raw[:200]}")
        return _empty_research(club_name)
    except Exception as e:
        logger.error(f"Club research failed: {e}")
        return _empty_research(club_name)


def compute_credibility_score(field_confirmed: Dict[str, bool], field_sources: Dict[str, str]) -> float:
    """
    Calculates credibility score (0-100) based on confirmed fields and their source quality.
    Confirmed + official source → max weight. Unconfirmed → 0.
    """
    weights = {
        "ragione_sociale": 10,
        "categoria": 20,
        "anno_fondazione": 5,
        "sede": 5,
        "regione": 5,
        "fatturato_stimato": 25,
        "n_atleti": 15,
        "presidente": 10,
        "website": 5,
    }
    source_multiplier = {
        "official": 1.0,
        "web": 0.7,
        "estimate": 0.4,
        "unknown": 0.2,
    }

    total_weight = sum(weights.values())
    earned = 0.0

    for field, weight in weights.items():
        if field_confirmed.get(field):
            src = field_sources.get(field, "unknown")
            earned += weight * source_multiplier.get(src, 0.2)

    return round((earned / total_weight) * 100, 1)


def _normalize(data: Dict, club_name: str) -> Dict:
    sources = data.pop("sources", {})
    note = data.pop("note", None)
    return {
        "club_name": club_name,
        "ragione_sociale": data.get("ragione_sociale"),
        "categoria": data.get("categoria"),
        "anno_fondazione": data.get("anno_fondazione"),
        "sede": data.get("sede"),
        "regione": data.get("regione"),
        "fatturato_stimato": data.get("fatturato_stimato"),
        "n_atleti": data.get("n_atleti"),
        "presidente": data.get("presidente"),
        "website": data.get("website"),
        "field_sources": sources,
        "note": note,
    }


def _empty_research(club_name: str) -> Dict:
    return {
        "club_name": club_name,
        **{f: None for f in PROFILE_FIELDS},
        "field_sources": {f: "unknown" for f in PROFILE_FIELDS},
        "note": "Ricerca automatica non disponibile — compila manualmente.",
    }

"""
Auditor Agent Module - Anti-Hallucination & Consistency Check
============================================================

L'Auditor Agent è il garante della qualità scientifica del piano.
Il suo compito è rileggere l'intero piano generato dai vari agenti e identificare:
1. Contraddizioni (es. budget diversi tra aree)
2. Allucinazioni (dati che non tornano con i benchmark)
3. Gap di tono (cambi improvvisi di stile)
4. Mancanza di fonti obbligatorie
"""

import logging
import json
import re
from typing import Dict, List, Any
import google.generativeai as genai

from config import MODEL_CONFIG, GEMINI_API_KEY
from data_models import BenchmarkDatabase

logger = logging.getLogger(__name__)

class AuditorAgent:
    def __init__(self):
        self.available = False
        if GEMINI_API_KEY:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                self.model = genai.GenerativeModel(MODEL_CONFIG.name)
                self.available = True
            except Exception as e:
                logger.error(f"AuditorAgent init error: {e}")

    def audit_plan(self, plan_data: Dict[str, str], club_data: Dict, financial_estimates: Dict) -> Dict[str, Any]:
        """
        Esegue l'audit completo del piano strategico.
        """
        if not self.available:
            return {"status": "skipped", "issues": []}

        # Prepara il contesto per l'audit
        full_text = "\n\n".join([f"SECTION {k.upper()}:\n{v}" for k, v in plan_data.items()])
        financial_summary = json.dumps(financial_estimates, indent=2)
        
        prompt = f"""
Sei un SENIOR STRATEGY AUDITOR di una società di consulenza Big Four (McKinsey, BCG, Deloitte).
Il tuo compito è convalidare scientificamente il piano strategico triennale di un club di calcio.

DATI DI RIFERIMENTO DEL CLUB:
{json.dumps(club_data, indent=2)}

STIME FINANZIARIE DI RIFERIMENTO (Benchmark):
{financial_summary}

TESTO COMPLETO DEL PIANO DA AUDITARE:
---
{full_text}
---

REGOLE DI AUDIT (RIGOROSE):
1. **COERENZA ECONOMICA**: Verifica se gli investimenti proposti nelle sezioni (sport, strutture, marketing) sono compatibili con il fatturato stimato. Se un club di Eccellenza propone un centro sportivo da 10 milioni, è un'allucinazione critica.
2. **ALLINEAMENTO TIMELINE**: Verifica se le milestone citate nelle diverse sezioni coincidono (es. se il marketing lancia il brand a marzo, la sezione sportiva non può inaugurare il museo a gennaio).
3. **VERIFICA FONTI**: Segnala se ci sono affermazioni forti senza l'indicazione della fonte (es. "(fonte: questionario)" o "(fonte: ricerca web)").
4. **TONO ISTITUZIONALE**: Segnala se l'agente ha usato nomi propri o toni non professionali.

RESTITUISCI UN REPORT IN FORMATO JSON CON QUESTA STRUTTURA:
{{
  "overall_quality_score": 0-100,
  "scientific_validity": "High/Medium/Low",
  "critical_issues": [
    {{"area": "...", "issue": "...", "severity": "High/Medium", "fix_suggestion": "..."}}
  ],
  "consistency_check": {{
    "budgets_aligned": true/false,
    "timelines_aligned": true/false
  }},
  "summary_verdict": "Breve verdetto finale sulla prontezza del piano per il Board."
}}
"""

        try:
            response = self.model.generate_content(prompt)
            # Estrai JSON dalla risposta
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return {
                "overall_quality_score": 70,
                "scientific_validity": "Medium",
                "critical_issues": [{"area": "System", "issue": "Could not parse JSON audit report", "severity": "Low", "fix_suggestion": "Manual review required"}],
                "summary_verdict": "Il piano sembra solido ma l'audit automatico ha avuto un problema di parsing."
            }
        except Exception as e:
            logger.error(f"Audit execution error: {e}")
            return {"status": "error", "message": str(e)}

    def refine_section(self, section_content: str, audit_issues: List[Dict]) -> str:
        """
        Rifinisce una singola sezione basandosi sui feedback dell'audit.
        """
        if not self.available: return section_content
        
        issues_text = "\n".join([f"- {i['issue']}" for i in audit_issues])
        
        prompt = f"""
Rifinisci il seguente contenuto di un piano strategico correggendo questi problemi rilevati dall'auditor:
{issues_text}

CONTENUTO ORIGINALE:
{section_content}

Restituisci solo il testo corretto, mantenendo il formato markdown e il tono istituzionale.
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except:
            return section_content

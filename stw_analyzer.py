"""
STW Analyzer - Analisi Copertura Matrice STW
==============================================

Analizza il contenuto del piano strategico per calcolare:
- Copertura MACRO per categoria
- Copertura MICRO per categoria
- Progress percentuale per categoria STW
"""

import re
import logging
from typing import Dict, List, Tuple
from stw_matrix import STW_FRAMEWORK, STWCategory, MacroObjective, MicroObjective

logger = logging.getLogger(__name__)


class STWAnalyzer:
    """
    Analizza il contenuto del piano strategico e calcola
    la copertura degli obiettivi STW.
    """

    def __init__(self):
        self.framework = STW_FRAMEWORK

    def analyze_plan_coverage(self, plan_data: Dict) -> Dict[str, any]:
        """
        Analizza il piano e calcola la copertura STW per categoria.

        Args:
            plan_data: Dict con sezioni del piano {section_key: content}

        Returns:
            {
                'sportivi': {'macro_coverage': 75, 'micro_coverage': 60, 'progress': 70},
                'strutturali': {...},
                'marketing': {...},
                'sociali': {...},
                'overall': {'macro_coverage': 65, 'micro_coverage': 55, 'progress': 62}
            }
        """
        results = {}

        # Analizza per ogni categoria
        for category in STWCategory:
            category_key = category.value  # 'sportivi', 'strutturali', etc.

            # Estrai contenuto rilevante dalla sezione
            section_content = self._extract_category_content(plan_data, category_key)

            # Calcola copertura
            macro_coverage, micro_coverage = self._calculate_coverage(
                section_content, category
            )

            # Progress = media pesata (macro 60%, micro 40%)
            progress = int(macro_coverage * 0.6 + micro_coverage * 0.4)

            # Genera spiegazione (Reasoning)
            total_macro = sum(len(s.macro_objectives) for s in self.framework.get(category, []))
            found_macro = int((macro_coverage / 100) * total_macro) if total_macro > 0 else 0
            reasoning = f"Identificati {found_macro} su {total_macro} obiettivi strategici chiave."

            results[category_key] = {
                'macro_coverage': int(macro_coverage),
                'micro_coverage': int(micro_coverage),
                'progress': progress,
                'reasoning': reasoning
            }

        # Calcola overall
        overall_macro = sum(r['macro_coverage'] for r in results.values()) / len(results)
        overall_micro = sum(r['micro_coverage'] for r in results.values()) / len(results)
        overall_progress = sum(r['progress'] for r in results.values()) / len(results)

        results['overall'] = {
            'macro_coverage': int(overall_macro),
            'micro_coverage': int(overall_micro),
            'progress': int(overall_progress)
        }

        return results

    def _extract_category_content(self, plan_data: Dict, category_key: str) -> str:
        """
        Estrae il contenuto rilevante per una categoria dal piano.

        Cerca prima in chiave diretta (es. 'stw_sportivi'),
        poi in chiavi correlate (es. 'technical_sporting' per sportivi).
        """
        # Mapping chiavi sezione → categoria STW
        section_mappings = {
            'sportivi': ['stw_sportivi', 'technical_sporting', 'sporting', 'settore_giovanile'],
            'strutturali': ['stw_strutturali', 'infrastructure', 'facilities'],
            'marketing': ['stw_marketing', 'marketing', 'commercial', 'communication'],
            'sociali': ['stw_sociali', 'social', 'community', 'sustainability'],
            'struttura_org': ['stw_struttura_org', 'governance', 'hr', 'organigramma'],
            'relazioni_ist': ['stw_relazioni_ist', 'relazioni_istituzionali', 'istituzionali'],
        }

        content_parts = []
        possible_keys = section_mappings.get(category_key, [category_key])

        for key in possible_keys:
            if key in plan_data:
                section_data = plan_data[key]

                # Gestisci dict o string
                if isinstance(section_data, dict):
                    # Prendi 'content' se presente
                    content_parts.append(section_data.get('content', ''))
                elif isinstance(section_data, str):
                    content_parts.append(section_data)

        return "\n\n".join(content_parts)

    def _calculate_coverage(
        self,
        content: str,
        category: STWCategory
    ) -> Tuple[float, float]:
        """
        Calcola la copertura MACRO e MICRO per una categoria.

        Returns:
            (macro_coverage_percent, micro_coverage_percent)
        """
        if not content or len(content) < 100:
            # Contenuto troppo breve = nessuna copertura
            return 0.0, 0.0

        sections = self.framework.get(category, [])

        total_macro = 0
        found_macro = 0
        total_micro = 0
        found_micro = 0

        # Pattern per trovare codici MACRO e MICRO
        # Esempi: "MACRO 1:", "1.1", "**1.2", "MACRO 4:"
        macro_pattern = r'(?:MACRO\s+)?(\d+)[:\.]?\s'
        micro_pattern = r'(?:\*\*)?(\d+\.\d+)(?:\*\*)?[:\s]'

        for section in sections:
            for macro in section.macro_objectives:
                total_macro += 1

                # Cerca riferimento al MACRO nel contenuto
                macro_code = macro.code

                # Pattern flessibile: "MACRO 1", "1:", "1.", etc.
                if re.search(rf'(?:MACRO\s+)?{re.escape(macro_code)}[:\.\s]', content, re.IGNORECASE):
                    found_macro += 1

                # Controlla MICRO
                for micro in macro.micro_objectives:
                    total_micro += 1
                    micro_code = micro.code

                    # Pattern flessibile: "1.1", "**1.1**", "1.1:", etc.
                    if re.search(rf'(?:\*\*)?{re.escape(micro_code)}(?:\*\*)?[:\s]', content):
                        found_micro += 1

        # Calcola percentuali
        macro_coverage = (found_macro / total_macro * 100) if total_macro > 0 else 0
        micro_coverage = (found_micro / total_micro * 100) if total_micro > 0 else 0

        logger.debug(
            f"Coverage {category.value}: "
            f"MACRO {found_macro}/{total_macro} ({macro_coverage:.1f}%), "
            f"MICRO {found_micro}/{total_micro} ({micro_coverage:.1f}%)"
        )

        return macro_coverage, micro_coverage

    def get_missing_objectives(
        self,
        plan_data: Dict,
        category: STWCategory
    ) -> Dict[str, List[str]]:
        """
        Identifica obiettivi MACRO e MICRO mancanti per una categoria.

        Returns:
            {
                'missing_macro': ['1', '3', '5'],
                'missing_micro': ['1.1', '2.3', '4.2']
            }
        """
        content = self._extract_category_content(plan_data, category.value)
        sections = self.framework.get(category, [])

        missing_macro = []
        missing_micro = []

        for section in sections:
            for macro in section.macro_objectives:
                macro_code = macro.code

                # Verifica se MACRO è presente
                if not re.search(rf'(?:MACRO\s+)?{re.escape(macro_code)}[:\.\s]', content, re.IGNORECASE):
                    missing_macro.append(macro_code)

                # Verifica MICRO
                for micro in macro.micro_objectives:
                    micro_code = micro.code
                    if not re.search(rf'(?:\*\*)?{re.escape(micro_code)}(?:\*\*)?[:\s]', content):
                        missing_micro.append(micro_code)

        return {
            'missing_macro': missing_macro,
            'missing_micro': missing_micro
        }

    def generate_coverage_report(self, plan_data: Dict) -> str:
        """
        Genera un report testuale della copertura STW.
        """
        coverage = self.analyze_plan_coverage(plan_data)

        report_lines = [
            "=" * 60,
            "REPORT COPERTURA MATRICE STW",
            "=" * 60,
            ""
        ]

        # Per categoria
        for category in STWCategory:
            cat_key = category.value
            cat_data = coverage.get(cat_key, {})

            icon_map = {
                'sportivi': '⚽',
                'strutturali': '🏗️',
                'marketing': '📢',
                'sociali': '🤝'
            }
            icon = icon_map.get(cat_key, '📋')

            report_lines.append(
                f"{icon} {cat_key.upper()}: "
                f"Progress {cat_data.get('progress', 0)}% "
                f"(MACRO {cat_data.get('macro_coverage', 0)}%, "
                f"MICRO {cat_data.get('micro_coverage', 0)}%)"
            )

        # Overall
        overall = coverage.get('overall', {})
        report_lines.extend([
            "",
            "-" * 60,
            f"📊 OVERALL: Progress {overall.get('progress', 0)}% "
            f"(MACRO {overall.get('macro_coverage', 0)}%, "
            f"MICRO {overall.get('micro_coverage', 0)}%)",
            "=" * 60
        ])

        return "\n".join(report_lines)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def calculate_stw_progress(plan_data: Dict) -> Dict[str, int]:
    """
    Calcola i progress percentuali STW per ogni categoria.

    Funzione utility per uso rapido.

    Returns:
        {
            'sportivi': 75,
            'strutturali': 60,
            'marketing': 70,
            'sociali': 55
        }
    """
    analyzer = STWAnalyzer()
    coverage = analyzer.analyze_plan_coverage(plan_data)

    return {
        category: coverage[category]['progress']
        for category in ['sportivi', 'strutturali', 'marketing', 'sociali']
    }


def get_stw_coverage_summary(plan_data: Dict) -> Dict:
    """
    Ottieni summary completo della copertura STW.

    Returns:
        {
            'progress': {'sportivi': 75, 'strutturali': 60, ...},
            'coverage': {
                'sportivi': {'macro_coverage': 80, 'micro_coverage': 70, ...},
                ...
            },
            'overall_progress': 65
        }
    """
    analyzer = STWAnalyzer()
    coverage = analyzer.analyze_plan_coverage(plan_data)

    return {
        'progress': {
            cat: coverage[cat]['progress']
            for cat in ['sportivi', 'strutturali', 'marketing', 'sociali']
        },
        'coverage': coverage,
        'overall_progress': coverage['overall']['progress']
    }


if __name__ == "__main__":
    # Test con piano mock
    test_plan = {
        'stw_sportivi': """
        ## ⚽ OBIETTIVI SPORTIVI

        ### MACRO 1: CREAZIONE E SVILUPPO IDENTITÀ TECNICA
        - **1.1 Organigramma tecnico**: Attualmente il club ha 3 allenatori UEFA B...
        - **1.2 Piano formazione staff**: Programma di aggiornamento continuo...

        ### MACRO 4: MIGLIORAMENTO COMPETITIVO
        - **4.1 Strategia tecnica**: Modello di gioco 4-3-3 unificato...
        - **4.3 Rete scouting**: Attualmente 2 osservatori part-time...
        """,
        'stw_marketing': """
        ## 📢 OBIETTIVI MARKETING

        ### MACRO 1: SVILUPPO AREA COMUNICAZIONE
        - **1.1 Ufficio stampa**: Da strutturare con responsabile qualificato...
        - **1.2 Strumentazione**: Budget €5K per tool social media...
        """
    }

    analyzer = STWAnalyzer()

    # Test analisi
    print(analyzer.generate_coverage_report(test_plan))
    print()

    # Test progress
    progress = calculate_stw_progress(test_plan)
    print("Progress per categoria:")
    for cat, prog in progress.items():
        print(f"  {cat}: {prog}%")

"""
Data Estimator Module - Tier 1/2/3 Logic
==========================================

Risolve il problema dei "Dati non disponibili" con una strategia a 3 livelli:
- Tier 1 (FATTO): Dato esatto trovato (bilancio, Transfermarkt)
- Tier 2 (DEDOTTO): Dato derivato da fonti indirette
- Tier 3 (STIMATO): Calcolo algoritmico basato su benchmark di categoria

Mai più campi vuoti!
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import logging

from data_models import BenchmarkDatabase

logger = logging.getLogger(__name__)


class DataTier(Enum):
    """Livello di affidabilità del dato"""
    TIER_1_FACT = "fatto"        # Dato esatto verificato
    TIER_2_DEDUCED = "dedotto"   # Dato derivato indirettamente
    TIER_3_ESTIMATED = "stimato" # Stima algoritmica


@dataclass
class EstimatedValue:
    """Valore stimato con metadata sulla provenienza"""
    value: Any
    tier: DataTier
    confidence: float  # 0.0 - 1.0
    source: str
    calculation_method: str = ""
    warning: str = ""

    def to_display(self) -> str:
        """Formatta per visualizzazione con etichetta tier"""
        if self.tier == DataTier.TIER_1_FACT:
            return f"{self.value:,.0f}" if isinstance(self.value, (int, float)) else str(self.value)
        elif self.tier == DataTier.TIER_2_DEDUCED:
            prefix = "[DEDOTTO] "
        else:
            prefix = "[STIMA] "

        if isinstance(self.value, (int, float)):
            return f"{prefix}~{self.value:,.0f}€"
        return f"{prefix}{self.value}"

    def to_dict(self) -> Dict:
        return {
            'value': self.value,
            'tier': self.tier.value,
            'confidence': self.confidence,
            'source': self.source,
            'calculation_method': self.calculation_method,
            'warning': self.warning
        }


# =============================================================================
# MOLTIPLICATORI PER CATEGORIA
# =============================================================================

CATEGORY_MULTIPLIERS = {
    # Moltiplicatore monte ingaggi rispetto a valore rosa
    "monte_ingaggi_ratio": {
        "Serie A": 0.65,
        "Serie B": 0.55,
        "Serie C": 0.50,
        "Serie D": 0.45,
        "Eccellenza": 0.40,
        "Promozione": 0.35,
    },
    # Moltiplicatore fatturato rispetto a monte ingaggi
    "fatturato_ratio": {
        "Serie A": 1.8,
        "Serie B": 2.0,
        "Serie C": 2.2,
        "Serie D": 2.5,
        "Eccellenza": 3.0,
        "Promozione": 3.5,
    },
    # Ricavi da stadio per posto (media a partita x partite)
    "ricavi_stadio_per_posto": {
        "Serie A": 150,  # €150/posto/anno
        "Serie B": 50,
        "Serie C": 20,
        "Serie D": 8,
        "Eccellenza": 3,
        "Promozione": 1,
    }
}


def estimate_missing_financials(
    club_data: Dict[str, Any],
    category: str,
    known_values: Optional[Dict[str, float]] = None
) -> Dict[str, EstimatedValue]:
    """
    Stima i dati finanziari mancanti usando la logica Tier 1/2/3.

    Args:
        club_data: Dati del club (può contenere valore_rosa, capienza_stadio, ecc.)
        category: Categoria del club (Serie A, Serie B, ecc.)
        known_values: Valori già noti (fatturato, monte_ingaggi, ecc.)

    Returns:
        Dict con tutti i campi finanziari stimati
    """
    known = known_values or {}
    results = {}

    # Normalizza categoria
    category = _normalize_category(category)

    # Ottieni benchmark di categoria
    benchmarks = BenchmarkDatabase.FINANCIAL_BENCHMARKS.get(category, {})

    # === VALORE ROSA ===
    if 'valore_rosa' in known and known['valore_rosa']:
        results['valore_rosa'] = EstimatedValue(
            value=known['valore_rosa'],
            tier=DataTier.TIER_1_FACT,
            confidence=0.95,
            source="Transfermarkt"
        )
    elif 'valore_rosa' in club_data and club_data['valore_rosa']:
        results['valore_rosa'] = EstimatedValue(
            value=club_data['valore_rosa'],
            tier=DataTier.TIER_2_DEDUCED,
            confidence=0.7,
            source="Dati club"
        )
    else:
        # Tier 3: Stima da benchmark
        benchmark_value = benchmarks.get('costo_rosa_medio', 500_000)
        results['valore_rosa'] = EstimatedValue(
            value=benchmark_value,
            tier=DataTier.TIER_3_ESTIMATED,
            confidence=0.4,
            source=f"Benchmark {category}",
            calculation_method=f"Media categoria {category}"
        )

    valore_rosa = results['valore_rosa'].value

    # === MONTE INGAGGI ===
    if 'monte_ingaggi' in known and known['monte_ingaggi']:
        results['monte_ingaggi'] = EstimatedValue(
            value=known['monte_ingaggi'],
            tier=DataTier.TIER_1_FACT,
            confidence=0.95,
            source="Bilancio ufficiale"
        )
    else:
        # Tier 2/3: Stima da valore rosa
        ratio = CATEGORY_MULTIPLIERS['monte_ingaggi_ratio'].get(category, 0.5)
        estimated = valore_rosa * ratio

        # Se abbiamo numero giocatori, affina la stima
        num_giocatori = club_data.get('dimensione_rosa', 22)
        stipendio_medio_cat = benchmarks.get('monte_ingaggi_medio', 200_000) / 22

        # Media ponderata tra stima da rosa e stima da benchmark
        estimated_from_benchmark = stipendio_medio_cat * num_giocatori
        final_estimate = (estimated * 0.6) + (estimated_from_benchmark * 0.4)

        tier = DataTier.TIER_2_DEDUCED if valore_rosa != benchmarks.get('costo_rosa_medio') else DataTier.TIER_3_ESTIMATED

        results['monte_ingaggi'] = EstimatedValue(
            value=round(final_estimate, -3),  # Arrotonda a migliaia
            tier=tier,
            confidence=0.5 if tier == DataTier.TIER_2_DEDUCED else 0.35,
            source=f"Calcolo da valore rosa ({category})",
            calculation_method=f"Valore Rosa €{valore_rosa:,.0f} × {ratio:.0%} + benchmark"
        )

    monte_ingaggi = results['monte_ingaggi'].value

    # === FATTURATO ===
    if 'fatturato' in known and known['fatturato']:
        results['fatturato'] = EstimatedValue(
            value=known['fatturato'],
            tier=DataTier.TIER_1_FACT,
            confidence=0.95,
            source="Bilancio ufficiale"
        )
    else:
        # Tier 2/3: Stima da monte ingaggi
        ratio = CATEGORY_MULTIPLIERS['fatturato_ratio'].get(category, 2.5)
        estimated = monte_ingaggi * ratio

        # Aggiungi stima ricavi stadio se abbiamo capienza
        capienza = club_data.get('capienza_stadio', 0)
        if capienza > 0:
            ricavi_stadio = capienza * CATEGORY_MULTIPLIERS['ricavi_stadio_per_posto'].get(category, 5)
            estimated += ricavi_stadio

        tier = DataTier.TIER_2_DEDUCED if monte_ingaggi != benchmarks.get('monte_ingaggi_medio') else DataTier.TIER_3_ESTIMATED

        results['fatturato'] = EstimatedValue(
            value=round(estimated, -3),
            tier=tier,
            confidence=0.45 if tier == DataTier.TIER_2_DEDUCED else 0.3,
            source=f"Calcolo da monte ingaggi ({category})",
            calculation_method=f"Monte Ingaggi €{monte_ingaggi:,.0f} × {ratio:.1f}" +
                             (f" + ricavi stadio €{ricavi_stadio:,.0f}" if capienza > 0 else "")
        )

    fatturato = results['fatturato'].value

    # === PATRIMONIO NETTO ===
    if 'patrimonio_netto' in known and known['patrimonio_netto']:
        results['patrimonio_netto'] = EstimatedValue(
            value=known['patrimonio_netto'],
            tier=DataTier.TIER_1_FACT,
            confidence=0.95,
            source="Bilancio ufficiale"
        )
    else:
        # Tier 3: Stima come % del fatturato (tipicamente 10-20% per club sani)
        # Molti club dilettantistici hanno patrimonio basso/negativo
        ratio = 0.15 if category in ["Serie A", "Serie B"] else 0.10
        estimated = fatturato * ratio

        results['patrimonio_netto'] = EstimatedValue(
            value=round(estimated, -3),
            tier=DataTier.TIER_3_ESTIMATED,
            confidence=0.25,
            source=f"Stima prudenziale ({category})",
            calculation_method=f"Fatturato €{fatturato:,.0f} × {ratio:.0%}",
            warning="Dato altamente incerto - richiedere bilancio ufficiale"
        )

    # === COSTO OPERATIVO ===
    # Stima costi operativi (personale + gestione + ammortamenti)
    costo_operativo = monte_ingaggi * 1.8  # Staff, gestione, ammortamenti
    results['costi_operativi'] = EstimatedValue(
        value=round(costo_operativo, -3),
        tier=DataTier.TIER_3_ESTIMATED,
        confidence=0.35,
        source=f"Stima da monte ingaggi",
        calculation_method=f"Monte Ingaggi × 1.8 (include staff, gestione, ammortamenti)"
    )

    # === BREAK-EVEN ANALYSIS ===
    margine = fatturato - results['costi_operativi'].value
    results['margine_operativo'] = EstimatedValue(
        value=round(margine, -3),
        tier=DataTier.TIER_3_ESTIMATED,
        confidence=0.3,
        source="Calcolo",
        calculation_method=f"Fatturato - Costi Operativi",
        warning="Positivo indica sostenibilità, negativo richiede ricapitalizzazione" if margine < 0 else ""
    )

    return results


def estimate_sporting_data(
    club_data: Dict[str, Any],
    category: str
) -> Dict[str, EstimatedValue]:
    """Stima dati sportivi mancanti"""
    results = {}
    category = _normalize_category(category)
    benchmarks = BenchmarkDatabase.SPORTING_BENCHMARKS.get(category, {})

    # Dimensione rosa
    rosa = club_data.get('dimensione_rosa') or benchmarks.get('dimensione_rosa', 22)
    tier = DataTier.TIER_1_FACT if 'dimensione_rosa' in club_data else DataTier.TIER_3_ESTIMATED

    results['dimensione_rosa'] = EstimatedValue(
        value=rosa,
        tier=tier,
        confidence=0.9 if tier == DataTier.TIER_1_FACT else 0.5,
        source="Transfermarkt" if tier == DataTier.TIER_1_FACT else f"Benchmark {category}"
    )

    # Età media
    eta = club_data.get('eta_media_rosa') or benchmarks.get('eta_media_rosa', 25.0)
    tier = DataTier.TIER_1_FACT if 'eta_media_rosa' in club_data else DataTier.TIER_3_ESTIMATED

    results['eta_media_rosa'] = EstimatedValue(
        value=eta,
        tier=tier,
        confidence=0.9 if tier == DataTier.TIER_1_FACT else 0.5,
        source="Transfermarkt" if tier == DataTier.TIER_1_FACT else f"Benchmark {category}"
    )

    return results


def estimate_youth_data(
    club_data: Dict[str, Any],
    category: str
) -> Dict[str, EstimatedValue]:
    """Stima dati settore giovanile"""
    results = {}
    category = _normalize_category(category)
    benchmarks = BenchmarkDatabase.YOUTH_BENCHMARKS.get(category, {})

    tesserati = club_data.get('tesserati_giovanili') or benchmarks.get('tesserati_giovanili', 100)
    tier = DataTier.TIER_1_FACT if 'tesserati_giovanili' in club_data else DataTier.TIER_3_ESTIMATED

    results['tesserati_giovanili'] = EstimatedValue(
        value=tesserati,
        tier=tier,
        confidence=0.8 if tier == DataTier.TIER_1_FACT else 0.4,
        source="Dati club" if tier == DataTier.TIER_1_FACT else f"Benchmark {category}"
    )

    squadre = club_data.get('squadre_giovanili') or benchmarks.get('squadre_giovanili', 4)
    tier = DataTier.TIER_1_FACT if 'squadre_giovanili' in club_data else DataTier.TIER_3_ESTIMATED

    results['squadre_giovanili'] = EstimatedValue(
        value=squadre,
        tier=tier,
        confidence=0.8 if tier == DataTier.TIER_1_FACT else 0.4,
        source="Dati club" if tier == DataTier.TIER_1_FACT else f"Benchmark {category}"
    )

    return results


def get_full_club_profile(
    club_data: Dict[str, Any],
    category: str,
    known_financials: Optional[Dict] = None
) -> Dict[str, Dict[str, EstimatedValue]]:
    """
    Genera profilo completo del club con tutti i dati stimati.
    Nessun campo rimane vuoto!
    """
    return {
        'financials': estimate_missing_financials(club_data, category, known_financials),
        'sporting': estimate_sporting_data(club_data, category),
        'youth': estimate_youth_data(club_data, category)
    }


def validate_estimates(
    estimates: Dict[str, EstimatedValue],
    category: str
) -> List[Dict]:
    """
    Valida le stime cercando anomalie.
    Usato dal Reviewer Agent per anti-hallucination.
    """
    anomalies = []
    category = _normalize_category(category)
    benchmarks = BenchmarkDatabase.FINANCIAL_BENCHMARKS.get(category, {})

    for field, estimate in estimates.items():
        if not isinstance(estimate, EstimatedValue):
            continue

        # Check: valore troppo alto rispetto a categoria superiore
        if field == 'fatturato' and category != "Serie A":
            upper_cat = _get_upper_category(category)
            if upper_cat:
                upper_bench = BenchmarkDatabase.FINANCIAL_BENCHMARKS.get(upper_cat, {})
                upper_avg = upper_bench.get('fatturato_medio', float('inf'))
                if estimate.value > upper_avg:
                    anomalies.append({
                        'field': field,
                        'value': estimate.value,
                        'issue': f"Valore superiore alla media {upper_cat} (€{upper_avg:,.0f})",
                        'severity': 'high'
                    })

        # Check: monte ingaggi > fatturato (insostenibile)
        if field == 'monte_ingaggi':
            fatturato = estimates.get('fatturato')
            if fatturato and estimate.value > fatturato.value * 0.8:
                anomalies.append({
                    'field': field,
                    'value': estimate.value,
                    'issue': f"Monte ingaggi troppo alto rispetto al fatturato ({estimate.value/fatturato.value:.0%})",
                    'severity': 'medium'
                })

    return anomalies


def _normalize_category(category: str) -> str:
    """Normalizza nome categoria"""
    mapping = {
        'serie a': 'Serie A',
        'serie b': 'Serie B',
        'serie c': 'Serie C',
        'serie d': 'Serie D',
        'eccellenza': 'Eccellenza',
        'promozione': 'Promozione',
        'prima categoria': 'Promozione',
        'seconda categoria': 'Promozione',
    }
    return mapping.get(category.lower(), category)


def _get_upper_category(category: str) -> Optional[str]:
    """Ritorna la categoria superiore"""
    hierarchy = ['Promozione', 'Eccellenza', 'Serie D', 'Serie C', 'Serie B', 'Serie A']
    try:
        idx = hierarchy.index(category)
        return hierarchy[idx + 1] if idx < len(hierarchy) - 1 else None
    except ValueError:
        return None


# =============================================================================
# FORMATTING UTILITIES
# =============================================================================

def format_estimates_for_report(
    estimates: Dict[str, EstimatedValue],
    include_methodology: bool = False
) -> str:
    """
    Formatta le stime per inclusione nel report.
    Aggiunge badge [STIMA] dove appropriato.
    """
    lines = []

    for field, est in estimates.items():
        label = field.replace('_', ' ').title()

        if est.tier == DataTier.TIER_1_FACT:
            lines.append(f"- **{label}:** €{est.value:,.0f}")
        elif est.tier == DataTier.TIER_2_DEDUCED:
            lines.append(f"- **{label}:** ~€{est.value:,.0f} `[DEDOTTO]`")
        else:
            lines.append(f"- **{label}:** ~€{est.value:,.0f} `[STIMA]`")

        if include_methodology and est.calculation_method:
            lines.append(f"  - *Metodo: {est.calculation_method}*")

        if est.warning:
            lines.append(f"  - ⚠️ *{est.warning}*")

    return "\n".join(lines)

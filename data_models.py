"""
Data Models per Rooting Future Strategy Engine v5.4

Sistema di validazione scientifica dei dati con:
- Tracciabilità completa delle fonti
- Confronto con benchmark di categoria
- Indicatori di confidenza
- Citazioni stile accademico
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import json


# =============================================================================
# ENUMS
# =============================================================================

class DataType(str, Enum):
    """Tipo di dato nel piano strategico"""
    VERIFIED = "verified"           # Dato verificato da fonte ufficiale
    BENCHMARK = "benchmark"         # Benchmark di categoria/settore
    ESTIMATE = "estimate"           # Stima interna basata su modelli
    TO_ACQUIRE = "to_acquire"       # Dato da acquisire
    CALCULATED = "calculated"       # Calcolato da altri dati
    PROJECTED = "projected"         # Proiezione futura


class SourceType(str, Enum):
    """Tipo di fonte"""
    OFFICIAL = "official"           # Bilanci, documenti ufficiali
    FIGC = "figc"                   # Report Calcio FIGC
    TRANSFERMARKT = "transfermarkt" # Transfermarkt
    LEGA = "lega"                   # Dati Lega (Serie A, B, C, LND)
    ISTAT = "istat"                 # Dati demografici ISTAT
    CLUB = "club"                   # Dichiarazioni/dati club
    MEDIA = "media"                 # Fonti giornalistiche
    INTERNAL = "internal"           # Stima interna consulente
    RESEARCH = "research"           # Ricerca web automatica
    ACADEMIC = "academic"           # Paper accademici


class ConfidenceLevel(str, Enum):
    """Livello di confidenza del dato"""
    HIGH = "high"           # 90-100% - Fonte ufficiale verificata
    MEDIUM = "medium"       # 70-89% - Fonte affidabile ma non ufficiale
    LOW = "low"             # 50-69% - Stima o fonte incerta
    VERY_LOW = "very_low"   # <50% - Da verificare


class DeviationType(str, Enum):
    """Tipo di scostamento dal benchmark"""
    ABOVE = "above"         # Sopra la media
    BELOW = "below"         # Sotto la media
    ALIGNED = "aligned"     # In linea (±10%)
    CRITICAL = "critical"   # Scostamento critico (>50%)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Source:
    """Rappresenta una fonte citabile"""
    type: SourceType
    name: str                           # Nome fonte (es. "Report Calcio FIGC 2024")
    reference: str                      # Riferimento specifico (es. "p. 87, Tab. 3.2")
    url: Optional[str] = None           # URL se disponibile
    date: Optional[str] = None          # Data pubblicazione
    verified: bool = False              # Verificato manualmente

    def to_citation(self) -> str:
        """Genera citazione stile accademico"""
        citation = f"{self.name}"
        if self.reference:
            citation += f", {self.reference}"
        if self.date:
            citation += f" ({self.date})"
        return citation

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "name": self.name,
            "reference": self.reference,
            "url": self.url,
            "date": self.date,
            "verified": self.verified,
            "citation": self.to_citation()
        }


@dataclass
class Benchmark:
    """Benchmark di riferimento per confronto"""
    value: Union[float, int, str]       # Valore benchmark
    category: str                       # Categoria (es. "Serie C", "Eccellenza")
    metric: str                         # Metrica (es. "fatturato_medio")
    source: Source                      # Fonte del benchmark
    year: int                           # Anno di riferimento
    sample_size: Optional[int] = None   # Dimensione campione
    percentile: Optional[int] = None    # Percentile (se applicabile)

    def to_dict(self) -> Dict:
        return {
            "value": self.value,
            "category": self.category,
            "metric": self.metric,
            "source": self.source.to_dict(),
            "year": self.year,
            "sample_size": self.sample_size,
            "percentile": self.percentile
        }


@dataclass
class DataPoint:
    """
    Singolo punto dati con validazione scientifica completa.
    Questo è l'elemento base per ogni dato nel piano strategico.
    """
    # Identificazione
    id: str                             # ID univoco del dato
    label: str                          # Etichetta leggibile (es. "Fatturato Annuo")
    category: str                       # Categoria tematica (es. "financial", "sporting")

    # Valore
    value: Union[float, int, str, None] # Valore del dato (None se da acquisire)
    unit: Optional[str] = None          # Unità di misura (es. "EUR", "%", "unità")
    formatted_value: Optional[str] = None  # Valore formattato per display

    # Tipologia e fonte
    data_type: DataType = DataType.TO_ACQUIRE
    source: Optional[Source] = None
    sources: List[Source] = field(default_factory=list)  # Fonti multiple

    # Benchmark e confronto
    benchmark: Optional[Benchmark] = None
    deviation: Optional[float] = None       # Scostamento % dal benchmark
    deviation_type: Optional[DeviationType] = None

    # Confidenza
    confidence: float = 0.0                 # 0-100
    confidence_level: ConfidenceLevel = ConfidenceLevel.VERY_LOW

    # Metadati
    notes: Optional[str] = None             # Note esplicative
    methodology: Optional[str] = None       # Metodologia di calcolo/stima
    last_updated: Optional[str] = None
    requires_verification: bool = True

    def __post_init__(self):
        """Calcola campi derivati"""
        # Calcola confidence level
        if self.confidence >= 90:
            self.confidence_level = ConfidenceLevel.HIGH
        elif self.confidence >= 70:
            self.confidence_level = ConfidenceLevel.MEDIUM
        elif self.confidence >= 50:
            self.confidence_level = ConfidenceLevel.LOW
        else:
            self.confidence_level = ConfidenceLevel.VERY_LOW

        # Calcola deviation type se abbiamo benchmark
        if self.benchmark and self.value is not None and self.benchmark.value:
            try:
                bench_val = float(self.benchmark.value)
                actual_val = float(self.value)
                if bench_val != 0:
                    self.deviation = ((actual_val - bench_val) / bench_val) * 100

                    if abs(self.deviation) <= 10:
                        self.deviation_type = DeviationType.ALIGNED
                    elif self.deviation > 50 or self.deviation < -50:
                        self.deviation_type = DeviationType.CRITICAL
                    elif self.deviation > 0:
                        self.deviation_type = DeviationType.ABOVE
                    else:
                        self.deviation_type = DeviationType.BELOW
            except (ValueError, TypeError):
                pass

        # Formatta valore se non fornito
        if self.formatted_value is None and self.value is not None:
            self.formatted_value = self._format_value()

    def _format_value(self) -> str:
        """Formatta il valore per la visualizzazione"""
        if self.value is None:
            return "(dato da acquisire)"

        if isinstance(self.value, (int, float)):
            if self.unit == "EUR" or self.unit == "€":
                if self.value >= 1_000_000:
                    return f"€{self.value/1_000_000:.1f}M"
                elif self.value >= 1_000:
                    return f"€{self.value/1_000:.0f}K"
                else:
                    return f"€{self.value:,.0f}"
            elif self.unit == "%":
                return f"{self.value:.1f}%"
            else:
                return f"{self.value:,.0f}" + (f" {self.unit}" if self.unit else "")

        return str(self.value)

    def get_status_badge(self) -> str:
        """Restituisce il badge di stato per HTML"""
        badges = {
            DataType.VERIFIED: ("verified", "Verificato"),
            DataType.BENCHMARK: ("benchmark", "Benchmark"),
            DataType.ESTIMATE: ("estimate", "Stima"),
            DataType.TO_ACQUIRE: ("to-acquire", "Da Acquisire"),
            DataType.CALCULATED: ("calculated", "Calcolato"),
            DataType.PROJECTED: ("projected", "Proiezione"),
        }
        css_class, label = badges.get(self.data_type, ("unknown", "N/A"))
        return f'<span class="data-badge data-{css_class}">{label}</span>'

    def get_confidence_badge(self) -> str:
        """Restituisce il badge di confidenza"""
        colors = {
            ConfidenceLevel.HIGH: "success",
            ConfidenceLevel.MEDIUM: "warning",
            ConfidenceLevel.LOW: "caution",
            ConfidenceLevel.VERY_LOW: "danger",
        }
        color = colors.get(self.confidence_level, "unknown")
        return f'<span class="confidence-badge confidence-{color}">{self.confidence:.0f}%</span>'

    def get_deviation_display(self) -> str:
        """Restituisce visualizzazione dello scostamento"""
        if self.deviation is None or self.benchmark is None:
            return ""

        icon = ""
        css_class = ""

        if self.deviation_type == DeviationType.ALIGNED:
            icon = "≈"
            css_class = "aligned"
        elif self.deviation_type == DeviationType.ABOVE:
            icon = "↑"
            css_class = "above"
        elif self.deviation_type == DeviationType.BELOW:
            icon = "↓"
            css_class = "below"
        elif self.deviation_type == DeviationType.CRITICAL:
            icon = "⚠"
            css_class = "critical"

        return f'<span class="deviation deviation-{css_class}">{icon} {self.deviation:+.1f}% vs benchmark</span>'

    def to_dict(self) -> Dict:
        """Converte in dizionario per serializzazione"""
        return {
            "id": self.id,
            "label": self.label,
            "category": self.category,
            "value": self.value,
            "unit": self.unit,
            "formatted_value": self.formatted_value,
            "data_type": self.data_type.value,
            "source": self.source.to_dict() if self.source else None,
            "sources": [s.to_dict() for s in self.sources],
            "benchmark": self.benchmark.to_dict() if self.benchmark else None,
            "deviation": self.deviation,
            "deviation_type": self.deviation_type.value if self.deviation_type else None,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "notes": self.notes,
            "methodology": self.methodology,
            "last_updated": self.last_updated,
            "requires_verification": self.requires_verification
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DataPoint':
        """Crea DataPoint da dizionario"""
        source = None
        if data.get('source'):
            source = Source(
                type=SourceType(data['source']['type']),
                name=data['source']['name'],
                reference=data['source'].get('reference', ''),
                url=data['source'].get('url'),
                date=data['source'].get('date'),
                verified=data['source'].get('verified', False)
            )

        benchmark = None
        if data.get('benchmark'):
            b = data['benchmark']
            benchmark = Benchmark(
                value=b['value'],
                category=b['category'],
                metric=b['metric'],
                source=Source(
                    type=SourceType(b['source']['type']),
                    name=b['source']['name'],
                    reference=b['source'].get('reference', ''),
                ),
                year=b['year'],
                sample_size=b.get('sample_size'),
                percentile=b.get('percentile')
            )

        return cls(
            id=data['id'],
            label=data['label'],
            category=data['category'],
            value=data.get('value'),
            unit=data.get('unit'),
            data_type=DataType(data.get('data_type', 'to_acquire')),
            source=source,
            benchmark=benchmark,
            confidence=data.get('confidence', 0),
            notes=data.get('notes'),
            methodology=data.get('methodology'),
            last_updated=data.get('last_updated'),
            requires_verification=data.get('requires_verification', True)
        )


@dataclass
class StructuredSection:
    """
    Sezione del piano con contenuto strutturato.
    Sostituisce il testo libero markdown con dati strutturati.
    """
    section_id: str
    title: str

    # Contenuto strutturato
    summary: str                                # Sintesi testuale
    key_findings: List[str] = field(default_factory=list)  # Findings principali
    data_points: List[DataPoint] = field(default_factory=list)  # Dati strutturati
    recommendations: List[Dict] = field(default_factory=list)   # Raccomandazioni

    # Analisi
    swot: Optional[Dict] = None                 # Analisi SWOT se applicabile
    risk_matrix: Optional[List[Dict]] = None    # Matrice rischi

    # Metadati sezione
    credibility_score: float = 0.0
    data_completeness: float = 0.0              # % dati disponibili vs richiesti
    sources_count: int = 0
    verified_claims_count: int = 0

    def __post_init__(self):
        """Calcola metriche sezione"""
        if self.data_points:
            # Calcola credibilità media
            confidences = [dp.confidence for dp in self.data_points]
            self.credibility_score = sum(confidences) / len(confidences)

            # Conta dati disponibili
            available = sum(1 for dp in self.data_points if dp.value is not None)
            self.data_completeness = (available / len(self.data_points)) * 100

            # Conta fonti uniche
            all_sources = set()
            for dp in self.data_points:
                if dp.source:
                    all_sources.add(dp.source.name)
                for s in dp.sources:
                    all_sources.add(s.name)
            self.sources_count = len(all_sources)

            # Conta claims verificati
            self.verified_claims_count = sum(
                1 for dp in self.data_points
                if dp.data_type == DataType.VERIFIED
            )

    def get_data_by_category(self, category: str) -> List[DataPoint]:
        """Filtra data points per categoria"""
        return [dp for dp in self.data_points if dp.category == category]

    def get_missing_data(self) -> List[DataPoint]:
        """Restituisce dati mancanti"""
        return [dp for dp in self.data_points if dp.value is None]

    def get_critical_deviations(self) -> List[DataPoint]:
        """Restituisce dati con scostamenti critici"""
        return [
            dp for dp in self.data_points
            if dp.deviation_type == DeviationType.CRITICAL
        ]

    def to_dict(self) -> Dict:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "data_points": [dp.to_dict() for dp in self.data_points],
            "recommendations": self.recommendations,
            "swot": self.swot,
            "risk_matrix": self.risk_matrix,
            "credibility_score": self.credibility_score,
            "data_completeness": self.data_completeness,
            "sources_count": self.sources_count,
            "verified_claims_count": self.verified_claims_count
        }


@dataclass
class StructuredPlan:
    """
    Piano strategico completo con struttura validata.
    """
    plan_id: str
    club_name: str
    category: str

    # Sezioni
    sections: Dict[str, StructuredSection] = field(default_factory=dict)

    # Metadati globali
    executive_summary: Optional[str] = None
    overall_credibility: float = 0.0
    total_data_points: int = 0
    verified_data_points: int = 0
    missing_data_points: int = 0

    # Fonti aggregate
    bibliography: List[Source] = field(default_factory=list)

    # Timeline
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: Optional[str] = None

    def __post_init__(self):
        """Calcola metriche globali"""
        self._calculate_metrics()

    def _calculate_metrics(self):
        """Aggiorna metriche aggregate"""
        if not self.sections:
            return

        # Conta data points
        all_dps = []
        all_sources = {}

        for section in self.sections.values():
            all_dps.extend(section.data_points)
            for dp in section.data_points:
                if dp.source:
                    all_sources[dp.source.name] = dp.source
                for s in dp.sources:
                    all_sources[s.name] = s

        self.total_data_points = len(all_dps)
        self.verified_data_points = sum(
            1 for dp in all_dps if dp.data_type == DataType.VERIFIED
        )
        self.missing_data_points = sum(
            1 for dp in all_dps if dp.value is None
        )

        # Credibilità media pesata
        if all_dps:
            self.overall_credibility = sum(dp.confidence for dp in all_dps) / len(all_dps)

        # Bibliografia
        self.bibliography = list(all_sources.values())

    def add_section(self, section: StructuredSection):
        """Aggiunge sezione e ricalcola metriche"""
        self.sections[section.section_id] = section
        self._calculate_metrics()

    def get_all_data_points(self) -> List[DataPoint]:
        """Restituisce tutti i data points"""
        all_dps = []
        for section in self.sections.values():
            all_dps.extend(section.data_points)
        return all_dps

    def get_verification_report(self) -> Dict:
        """Genera report di verifica"""
        all_dps = self.get_all_data_points()

        by_type = {}
        for dp in all_dps:
            key = dp.data_type.value
            if key not in by_type:
                by_type[key] = []
            by_type[key].append(dp.to_dict())

        by_confidence = {
            "high": [dp.to_dict() for dp in all_dps if dp.confidence_level == ConfidenceLevel.HIGH],
            "medium": [dp.to_dict() for dp in all_dps if dp.confidence_level == ConfidenceLevel.MEDIUM],
            "low": [dp.to_dict() for dp in all_dps if dp.confidence_level == ConfidenceLevel.LOW],
            "very_low": [dp.to_dict() for dp in all_dps if dp.confidence_level == ConfidenceLevel.VERY_LOW],
        }

        critical = [
            dp.to_dict() for dp in all_dps
            if dp.deviation_type == DeviationType.CRITICAL
        ]

        return {
            "total_data_points": self.total_data_points,
            "verified": self.verified_data_points,
            "missing": self.missing_data_points,
            "overall_credibility": self.overall_credibility,
            "by_type": by_type,
            "by_confidence": by_confidence,
            "critical_deviations": critical,
            "bibliography": [s.to_dict() for s in self.bibliography]
        }

    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "club_name": self.club_name,
            "category": self.category,
            "sections": {k: v.to_dict() for k, v in self.sections.items()},
            "executive_summary": self.executive_summary,
            "overall_credibility": self.overall_credibility,
            "total_data_points": self.total_data_points,
            "verified_data_points": self.verified_data_points,
            "missing_data_points": self.missing_data_points,
            "bibliography": [s.to_dict() for s in self.bibliography],
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


# =============================================================================
# BENCHMARK DATABASE
# =============================================================================

class BenchmarkDatabase:
    """
    Database di benchmark per il calcio italiano.
    Fonte principale: Report Calcio FIGC + dati settore.
    """

    # Benchmark finanziari per categoria (EUR)
    FINANCIAL_BENCHMARKS = {
        "Serie A": {
            "fatturato_medio": 150_000_000,
            "monte_ingaggi_medio": 80_000_000,
            "patrimonio_netto_medio": 50_000_000,
            "costo_rosa_medio": 120_000_000,
            "source": "Report Calcio FIGC 2024, Cap. 3"
        },
        "Serie B": {
            "fatturato_medio": 20_000_000,
            "monte_ingaggi_medio": 10_000_000,
            "patrimonio_netto_medio": 5_000_000,
            "costo_rosa_medio": 15_000_000,
            "source": "Report Calcio FIGC 2024, Cap. 3"
        },
        "Serie C": {
            "fatturato_medio": 4_500_000,
            "monte_ingaggi_medio": 2_000_000,
            "patrimonio_netto_medio": 1_000_000,
            "costo_rosa_medio": 3_000_000,
            "source": "Report Calcio FIGC 2024, Cap. 3"
        },
        "Serie D": {
            "fatturato_medio": 500_000,
            "monte_ingaggi_medio": 200_000,
            "patrimonio_netto_medio": 100_000,
            "costo_rosa_medio": 300_000,
            "source": "Stima basata su Report Calcio FIGC 2024"
        },
        "Eccellenza": {
            "fatturato_medio": 150_000,
            "monte_ingaggi_medio": 50_000,
            "patrimonio_netto_medio": 30_000,
            "costo_rosa_medio": 80_000,
            "source": "Stima interna basata su media regionale"
        }
    }

    # Benchmark sportivi
    SPORTING_BENCHMARKS = {
        "Serie A": {
            "dimensione_rosa": 28,
            "eta_media_rosa": 26.5,
            "stranieri_percentuale": 60,
            "vivaio_percentuale": 10,
            "source": "Transfermarkt/Report Calcio FIGC 2024"
        },
        "Serie B": {
            "dimensione_rosa": 26,
            "eta_media_rosa": 25.5,
            "stranieri_percentuale": 40,
            "vivaio_percentuale": 15,
            "source": "Transfermarkt/Report Calcio FIGC 2024"
        },
        "Serie C": {
            "dimensione_rosa": 24,
            "eta_media_rosa": 25.0,
            "stranieri_percentuale": 25,
            "vivaio_percentuale": 20,
            "source": "Transfermarkt/Report Calcio FIGC 2024"
        },
        "Serie D": {
            "dimensione_rosa": 22,
            "eta_media_rosa": 24.5,
            "stranieri_percentuale": 15,
            "vivaio_percentuale": 30,
            "source": "Stima LND"
        },
        "Eccellenza": {
            "dimensione_rosa": 22,
            "eta_media_rosa": 24.0,
            "stranieri_percentuale": 10,
            "vivaio_percentuale": 40,
            "source": "Stima LND regionale"
        }
    }

    # Benchmark settore giovanile
    YOUTH_BENCHMARKS = {
        "Serie A": {
            "tesserati_giovanili": 400,
            "squadre_giovanili": 12,
            "rapporto_allenatori": 1.5,  # allenatori per 10 ragazzi
            "source": "Report Calcio FIGC 2024, Cap. 5"
        },
        "Serie B": {
            "tesserati_giovanili": 300,
            "squadre_giovanili": 10,
            "rapporto_allenatori": 1.3,
            "source": "Report Calcio FIGC 2024, Cap. 5"
        },
        "Serie C": {
            "tesserati_giovanili": 220,
            "squadre_giovanili": 8,
            "rapporto_allenatori": 1.0,
            "source": "Report Calcio FIGC 2024, Cap. 5"
        },
        "Serie D": {
            "tesserati_giovanili": 150,
            "squadre_giovanili": 6,
            "rapporto_allenatori": 0.8,
            "source": "Stima LND"
        },
        "Eccellenza": {
            "tesserati_giovanili": 100,
            "squadre_giovanili": 4,
            "rapporto_allenatori": 0.6,
            "source": "Stima LND regionale"
        }
    }

    # Benchmark infrastrutturali
    INFRASTRUCTURE_BENCHMARKS = {
        "Serie A": {
            "capienza_stadio": 40000,
            "campi_allenamento": 6,
            "centro_sportivo": True,
            "source": "Dati Lega Serie A"
        },
        "Serie B": {
            "capienza_stadio": 15000,
            "campi_allenamento": 4,
            "centro_sportivo": True,
            "source": "Dati Lega Serie B"
        },
        "Serie C": {
            "capienza_stadio": 8000,
            "campi_allenamento": 2,
            "centro_sportivo": False,
            "source": "Dati Lega Pro"
        },
        "Serie D": {
            "capienza_stadio": 3000,
            "campi_allenamento": 1,
            "centro_sportivo": False,
            "source": "Stima LND"
        },
        "Eccellenza": {
            "capienza_stadio": 2000,
            "campi_allenamento": 1,
            "centro_sportivo": False,
            "source": "Stima LND regionale"
        }
    }

    @classmethod
    def get_benchmark(
        cls,
        category: str,
        domain: str,
        metric: str
    ) -> Optional[Benchmark]:
        """
        Ottiene benchmark specifico.

        Args:
            category: Categoria (Serie A, Serie B, Serie C, Serie D, Eccellenza)
            domain: Dominio (financial, sporting, youth, infrastructure)
            metric: Nome metrica

        Returns:
            Benchmark object o None
        """
        domains = {
            "financial": cls.FINANCIAL_BENCHMARKS,
            "sporting": cls.SPORTING_BENCHMARKS,
            "youth": cls.YOUTH_BENCHMARKS,
            "infrastructure": cls.INFRASTRUCTURE_BENCHMARKS
        }

        db = domains.get(domain, {})
        cat_data = db.get(category, {})

        if metric not in cat_data:
            return None

        source_ref = cat_data.get("source", "Report Calcio FIGC")

        return Benchmark(
            value=cat_data[metric],
            category=category,
            metric=metric,
            source=Source(
                type=SourceType.FIGC,
                name=source_ref,
                reference=f"Benchmark {domain}/{metric}"
            ),
            year=2024
        )

    @classmethod
    def create_data_point_with_benchmark(
        cls,
        id: str,
        label: str,
        value: Union[float, int, str, None],
        unit: str,
        category: str,
        domain: str,
        metric: str,
        source: Optional[Source] = None,
        data_type: DataType = DataType.TO_ACQUIRE,
        confidence: float = 0
    ) -> DataPoint:
        """
        Crea DataPoint con benchmark automatico.
        """
        benchmark = cls.get_benchmark(category, domain, metric)

        return DataPoint(
            id=id,
            label=label,
            category=domain,
            value=value,
            unit=unit,
            data_type=data_type,
            source=source,
            benchmark=benchmark,
            confidence=confidence
        )

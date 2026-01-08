"""
Rooting Future Strategy Engine
Club Identity & Branding Module

Sistema di riconoscimento automatico dei colori del club.
Deduce i colori dal nome del club senza bisogno di input manuale.
"""

import re
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# DATABASE COLORI CLUB
# =============================================================================

CLUB_COLORS_DB: Dict[str, Dict[str, str]] = {
    # ----- SERIE A -----
    'juventus': {'primary': '#000000', 'secondary': '#FFFFFF', 'accent': '#D4AF37'},
    'milan': {'primary': '#AC1F2D', 'secondary': '#000000', 'accent': '#FFFFFF'},
    'inter': {'primary': '#0068A8', 'secondary': '#000000', 'accent': '#FFFFFF'},
    'napoli': {'primary': '#12A0D7', 'secondary': '#FFFFFF', 'accent': '#003399'},
    'roma': {'primary': '#8E1F2F', 'secondary': '#F0BC42', 'accent': '#1D1D1B'},
    'lazio': {'primary': '#87D8F7', 'secondary': '#FFFFFF', 'accent': '#0D2240'},
    'fiorentina': {'primary': '#532E8E', 'secondary': '#FFFFFF', 'accent': '#E42313'},
    'atalanta': {'primary': '#1E71B8', 'secondary': '#000000', 'accent': '#FFFFFF'},
    'torino': {'primary': '#8B0000', 'secondary': '#FFFFFF', 'accent': '#1C1C1C'},
    'bologna': {'primary': '#1A2F5A', 'secondary': '#A41E22', 'accent': '#FFFFFF'},
    'udinese': {'primary': '#000000', 'secondary': '#FFFFFF', 'accent': '#B5A642'},
    'genoa': {'primary': '#A41E22', 'secondary': '#00387B', 'accent': '#FFFFFF'},
    'sampdoria': {'primary': '#0056A6', 'secondary': '#E3001B', 'accent': '#FFFFFF'},
    'sassuolo': {'primary': '#00A651', 'secondary': '#000000', 'accent': '#FFFFFF'},
    'empoli': {'primary': '#005BA9', 'secondary': '#FFFFFF', 'accent': '#E30613'},
    'verona': {'primary': '#FFDE00', 'secondary': '#003DA5', 'accent': '#FFFFFF'},
    'hellas': {'primary': '#FFDE00', 'secondary': '#003DA5', 'accent': '#FFFFFF'},  # Alias Hellas Verona
    'monza': {'primary': '#C8102E', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'lecce': {'primary': '#FFCC00', 'secondary': '#E30613', 'accent': '#1D1D1B'},
    'cagliari': {'primary': '#A41E22', 'secondary': '#003366', 'accent': '#FFFFFF'},
    'venezia': {'primary': '#E5632E', 'secondary': '#004D40', 'accent': '#D4AF37'},
    'como': {'primary': '#003DA5', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'parma': {'primary': '#FFD100', 'secondary': '#004389', 'accent': '#FFFFFF'},

    # ----- SERIE B -----
    'palermo': {'primary': '#EF4D7A', 'secondary': '#000000', 'accent': '#FFFFFF'},
    'bari': {'primary': '#E3001B', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'brescia': {'primary': '#004A99', 'secondary': '#FFFFFF', 'accent': '#D4AF37'},
    'catanzaro': {'primary': '#FFD100', 'secondary': '#C8102E', 'accent': '#1D1D1B'},
    'cesena': {'primary': '#000000', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'cittadella': {'primary': '#8B0000', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'cosenza': {'primary': '#E30613', 'secondary': '#003DA5', 'accent': '#FFFFFF'},
    'cremonese': {'primary': '#A41E22', 'secondary': '#808080', 'accent': '#FFFFFF'},
    'frosinone': {'primary': '#FFDE00', 'secondary': '#003DA5', 'accent': '#1D1D1B'},
    'juve stabia': {'primary': '#FFDE00', 'secondary': '#003DA5', 'accent': '#1D1D1B'},
    'mantova': {'primary': '#A41E22', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'modena': {'primary': '#FFDE00', 'secondary': '#003DA5', 'accent': '#1D1D1B'},
    'pisa': {'primary': '#003DA5', 'secondary': '#000000', 'accent': '#FFFFFF'},
    'reggiana': {'primary': '#8B0000', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'salernitana': {'primary': '#8B0000', 'secondary': '#FFFFFF', 'accent': '#D4AF37'},
    'sampdoria': {'primary': '#0056A6', 'secondary': '#E3001B', 'accent': '#FFFFFF'},
    'sassuolo': {'primary': '#00A651', 'secondary': '#000000', 'accent': '#FFFFFF'},
    'spezia': {'primary': '#000000', 'secondary': '#FFFFFF', 'accent': '#D4AF37'},
    'sudtirol': {'primary': '#E30613', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'carrarese': {'primary': '#003DA5', 'secondary': '#FFFFFF', 'accent': '#D4AF37'},

    # ----- SERIE C -----
    'avellino': {'primary': '#006D3D', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'benevento': {'primary': '#FFDE00', 'secondary': '#C8102E', 'accent': '#1D1D1B'},
    'catania': {'primary': '#E30613', 'secondary': '#003DA5', 'accent': '#FFFFFF'},
    'crotone': {'primary': '#E30613', 'secondary': '#003DA5', 'accent': '#FFFFFF'},
    'foggia': {'primary': '#E30613', 'secondary': '#000000', 'accent': '#FFFFFF'},
    'messina': {'primary': '#FFDE00', 'secondary': '#E30613', 'accent': '#1D1D1B'},
    'padova': {'primary': '#FFFFFF', 'secondary': '#C8102E', 'accent': '#1D1D1B'},
    'perugia': {'primary': '#C8102E', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'pescara': {'primary': '#FFFFFF', 'secondary': '#003DA5', 'accent': '#1D1D1B'},
    'reggina': {'primary': '#8B0000', 'secondary': '#FFFFFF', 'accent': '#D4AF37'},
    'ternana': {'primary': '#E30613', 'secondary': '#006D3D', 'accent': '#FFFFFF'},
    'triestina': {'primary': '#E30613', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'vicenza': {'primary': '#C8102E', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},

    # ----- TOP EUROPEI -----
    'real madrid': {'primary': '#FFFFFF', 'secondary': '#00529F', 'accent': '#D4AF37'},
    'barcelona': {'primary': '#A50044', 'secondary': '#004D98', 'accent': '#FFED00'},
    'atletico madrid': {'primary': '#CB3524', 'secondary': '#FFFFFF', 'accent': '#003DA5'},
    'bayern': {'primary': '#DC052D', 'secondary': '#FFFFFF', 'accent': '#003DA5'},
    'borussia dortmund': {'primary': '#FDE100', 'secondary': '#000000', 'accent': '#FFFFFF'},
    'dortmund': {'primary': '#FDE100', 'secondary': '#000000', 'accent': '#FFFFFF'},
    'psg': {'primary': '#004170', 'secondary': '#E30613', 'accent': '#FFFFFF'},
    'paris': {'primary': '#004170', 'secondary': '#E30613', 'accent': '#FFFFFF'},
    'manchester united': {'primary': '#DA291C', 'secondary': '#000000', 'accent': '#FBE122'},
    'manchester city': {'primary': '#6CABDD', 'secondary': '#FFFFFF', 'accent': '#1C2C5B'},
    'liverpool': {'primary': '#C8102E', 'secondary': '#FFFFFF', 'accent': '#00A398'},
    'chelsea': {'primary': '#034694', 'secondary': '#FFFFFF', 'accent': '#D4AF37'},
    'arsenal': {'primary': '#EF0107', 'secondary': '#FFFFFF', 'accent': '#063672'},
    'tottenham': {'primary': '#FFFFFF', 'secondary': '#132257', 'accent': '#1D1D1B'},
    'ajax': {'primary': '#C8102E', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'porto': {'primary': '#003DA5', 'secondary': '#FFFFFF', 'accent': '#D4AF37'},
    'benfica': {'primary': '#E30613', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'sporting': {'primary': '#006D3D', 'secondary': '#FFFFFF', 'accent': '#FFDE00'},

    # Premier League - Altri club
    'nottingham forest': {'primary': '#E53233', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'nottingham': {'primary': '#E53233', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'forest': {'primary': '#E53233', 'secondary': '#FFFFFF', 'accent': '#1D1D1B'},
    'aston villa': {'primary': '#670E36', 'secondary': '#95BFE5', 'accent': '#FEF200'},
    'west ham': {'primary': '#7A263A', 'secondary': '#1BB1E7', 'accent': '#F3D459'},
    'newcastle': {'primary': '#241F20', 'secondary': '#FFFFFF', 'accent': '#41B6E6'},
    'everton': {'primary': '#003399', 'secondary': '#FFFFFF', 'accent': '#F7A800'},
    'leicester': {'primary': '#003090', 'secondary': '#FDBE11', 'accent': '#FFFFFF'},
    'wolves': {'primary': '#FDB913', 'secondary': '#231F20', 'accent': '#FFFFFF'},
    'wolverhampton': {'primary': '#FDB913', 'secondary': '#231F20', 'accent': '#FFFFFF'},
    'brighton': {'primary': '#0057B8', 'secondary': '#FFFFFF', 'accent': '#FFCD00'},
    'fulham': {'primary': '#000000', 'secondary': '#FFFFFF', 'accent': '#CC0000'},
    'crystal palace': {'primary': '#1B458F', 'secondary': '#C4122E', 'accent': '#FFFFFF'},
    'bournemouth': {'primary': '#DA291C', 'secondary': '#000000', 'accent': '#FFFFFF'},
    'brentford': {'primary': '#E30613', 'secondary': '#FFFFFF', 'accent': '#FFB81C'},
    'ipswich': {'primary': '#0033A0', 'secondary': '#FFFFFF', 'accent': '#E30613'},
    'southampton': {'primary': '#D71920', 'secondary': '#FFFFFF', 'accent': '#130C0E'},

    # Liga Spagnola
    'las palmas': {'primary': '#FFD700', 'secondary': '#0033A0', 'accent': '#FFFFFF'},
    'real madrid': {'primary': '#FFFFFF', 'secondary': '#00529F', 'accent': '#D4AF37'},
    'barcelona': {'primary': '#A50044', 'secondary': '#004D98', 'accent': '#FFED02'},
    'atletico madrid': {'primary': '#CB3524', 'secondary': '#FFFFFF', 'accent': '#272E61'},
    'sevilla': {'primary': '#F43333', 'secondary': '#FFFFFF', 'accent': '#000000'},
    'real betis': {'primary': '#00954C', 'secondary': '#FFFFFF', 'accent': '#000000'},
    'villarreal': {'primary': '#FFE114', 'secondary': '#005DAB', 'accent': '#FFFFFF'},
    'valencia': {'primary': '#FFFFFF', 'secondary': '#000000', 'accent': '#FF6600'},
    'athletic bilbao': {'primary': '#EE2523', 'secondary': '#FFFFFF', 'accent': '#000000'},
    'real sociedad': {'primary': '#0067B1', 'secondary': '#FFFFFF', 'accent': '#000000'},
}

# Colori di default (stile professionale Navy)
DEFAULT_COLORS = {
    'primary': '#1a365d',
    'secondary': '#2d3748',
    'accent': '#3182ce'
}

# Suffissi da rimuovere per normalizzazione
SUFFIXES_TO_REMOVE = [
    'fc', 'ac', 'ss', 'ssc', 'us', 'asd', 'ssd',
    'calcio', 'football', 'club', 'sport',
    '1907', '1908', '1909', '1910', '1911', '1912', '1913', '1914',
    '1893', '1897', '1898', '1899', '1900', '1901', '1902', '1903', '1904', '1905', '1906',
    '1920', '1921', '1922', '1924', '1927', '1928', '1936', '1946', '1968', '2004',
    'spa', 'srl', 'ssrl'
]

# Alias speciali per club con nomi ambigui
CLUB_ALIASES = {
    'internazionale': 'inter',
    'internazionale milano': 'inter',
    'inter milano': 'inter',
    'inter milan': 'inter',
    'ac milan': 'milan',
    'milan ac': 'milan',
    'hellas verona': 'verona',
    'borussia dortmund': 'dortmund',
    'paris saint germain': 'psg',
    'paris sg': 'psg',
    'bayern munchen': 'bayern',
    'bayern munich': 'bayern',
    'fc bayern': 'bayern',
}


# =============================================================================
# FUNZIONI DI LOOKUP
# =============================================================================

def normalize_club_name(name: str) -> str:
    """
    Normalizza il nome del club per il matching.

    - Converte in lowercase
    - Rimuove suffissi comuni (FC, AC, Calcio, etc.)
    - Rimuove punteggiatura
    - Rimuove spazi multipli

    Examples:
        "Palermo FC" -> "palermo"
        "AC Milan" -> "milan"
        "S.S.C. Napoli" -> "napoli"
        "Juventus Football Club" -> "juventus"
    """
    if not name:
        return ''

    # Lowercase
    normalized = name.lower().strip()

    # Rimuovi punteggiatura
    normalized = re.sub(r'[.\-_\'\"()]', ' ', normalized)

    # Rimuovi suffissi
    for suffix in SUFFIXES_TO_REMOVE:
        # Rimuovi come parola intera (con word boundary)
        normalized = re.sub(rf'\b{suffix}\b', '', normalized)

    # Normalizza spazi
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized


def get_club_colors(club_name: str) -> Dict[str, str]:
    """
    Restituisce i colori del club dato il nome.

    Args:
        club_name: Nome del club (es. "Palermo FC", "AC Milan")

    Returns:
        Dict con 'primary', 'secondary', 'accent'

    Examples:
        >>> get_club_colors("Palermo FC")
        {'primary': '#EF4D7A', 'secondary': '#000000', 'accent': '#FFFFFF'}

        >>> get_club_colors("Club Sconosciuto")
        {'primary': '#1a365d', 'secondary': '#2d3748', 'accent': '#3182ce'}
    """
    if not club_name:
        logger.debug("Nome club vuoto, uso colori default")
        return DEFAULT_COLORS.copy()

    # Normalizza il nome
    normalized = normalize_club_name(club_name)
    logger.debug(f"Club name normalized: '{club_name}' -> '{normalized}'")

    # Check alias prima di tutto
    if normalized in CLUB_ALIASES:
        alias_key = CLUB_ALIASES[normalized]
        if alias_key in CLUB_COLORS_DB:
            colors = CLUB_COLORS_DB[alias_key].copy()
            logger.info(f"Club colors found (alias): {club_name} -> {alias_key} -> {colors['primary']}")
            return colors

    # Match esatto
    if normalized in CLUB_COLORS_DB:
        colors = CLUB_COLORS_DB[normalized].copy()
        logger.info(f"Club colors found (exact): {club_name} -> {colors['primary']}")
        return colors

    # Check alias per match parziale
    for alias, target in CLUB_ALIASES.items():
        if alias in normalized or normalized in alias:
            if target in CLUB_COLORS_DB:
                colors = CLUB_COLORS_DB[target].copy()
                logger.info(f"Club colors found (alias partial): {club_name} -> {target} -> {colors['primary']}")
                return colors

    # Match parziale (cerca se il nome normalizzato è contenuto in una chiave o viceversa)
    for key, colors in CLUB_COLORS_DB.items():
        if normalized in key or key in normalized:
            result = colors.copy()
            logger.info(f"Club colors found (partial): {club_name} -> {result['primary']}")
            return result

    # Match fuzzy su parole chiave
    normalized_words = set(normalized.split())
    for key, colors in CLUB_COLORS_DB.items():
        key_words = set(key.split())
        # Se c'è almeno una parola significativa in comune
        common = normalized_words & key_words
        if common and any(len(w) > 3 for w in common):
            result = colors.copy()
            logger.info(f"Club colors found (fuzzy): {club_name} -> {result['primary']} (matched: {common})")
            return result

    # Nessun match, usa default
    logger.info(f"Club colors not found: '{club_name}' -> using default")
    return DEFAULT_COLORS.copy()


def get_club_identity(club_name: str, custom_primary: str = None, custom_secondary: str = None) -> Dict[str, str]:
    """
    Restituisce l'identità visiva completa del club.

    Priorità:
    1. Colori custom passati esplicitamente
    2. Colori dal database
    3. Colori default

    Args:
        club_name: Nome del club
        custom_primary: Colore primario custom (opzionale)
        custom_secondary: Colore secondario custom (opzionale)

    Returns:
        Dict con 'primary', 'secondary', 'accent', 'club_name', 'is_custom'
    """
    # Se ci sono colori custom, usali
    if custom_primary and custom_primary != DEFAULT_COLORS['primary']:
        return {
            'primary': custom_primary,
            'secondary': custom_secondary or DEFAULT_COLORS['secondary'],
            'accent': _derive_accent(custom_primary),
            'club_name': club_name,
            'is_custom': True
        }

    # Altrimenti cerca nel database
    colors = get_club_colors(club_name)
    return {
        **colors,
        'club_name': club_name,
        'is_custom': False
    }


def _derive_accent(hex_color: str) -> str:
    """Deriva un colore accent dal primario (versione più chiara o più scura)"""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    # Se il colore è scuro, schiariscilo; altrimenti scuriscilo
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    if luminance < 0.5:
        # Schiarisci
        r = min(255, int(r + (255 - r) * 0.4))
        g = min(255, int(g + (255 - g) * 0.4))
        b = min(255, int(b + (255 - b) * 0.4))
    else:
        # Scurisci
        r = int(r * 0.6)
        g = int(g * 0.6)
        b = int(b * 0.6)

    return f'#{r:02x}{g:02x}{b:02x}'


def list_available_clubs() -> list:
    """Restituisce lista di club disponibili nel database"""
    return sorted(CLUB_COLORS_DB.keys())


def add_club_colors(club_name: str, primary: str, secondary: str, accent: str = None):
    """
    Aggiunge o aggiorna i colori di un club nel database runtime.

    Args:
        club_name: Nome del club (verrà normalizzato)
        primary: Colore primario (hex)
        secondary: Colore secondario (hex)
        accent: Colore accent (hex, opzionale - verrà derivato)
    """
    normalized = normalize_club_name(club_name)
    CLUB_COLORS_DB[normalized] = {
        'primary': primary,
        'secondary': secondary,
        'accent': accent or _derive_accent(primary)
    }
    logger.info(f"Added/updated club colors: {club_name} ({normalized}) -> {primary}")


# =============================================================================
# TEST
# =============================================================================

if __name__ == '__main__':
    # Test
    test_names = [
        "Palermo FC",
        "AC Milan",
        "F.C. Juventus",
        "S.S.C. Napoli",
        "AS Roma",
        "S.S. Lazio",
        "Inter Milan",
        "Venezia FC 1907",
        "Parma Calcio",
        "U.S. Bari 1908",
        "Club Sconosciuto XYZ",
        "Real Madrid CF",
        "FC Barcelona",
        "Manchester United",
    ]

    print("=" * 60)
    print("TEST CLUB IDENTITY LOOKUP")
    print("=" * 60)

    for name in test_names:
        colors = get_club_colors(name)
        print(f"{name:25} -> Primary: {colors['primary']}, Secondary: {colors['secondary']}")

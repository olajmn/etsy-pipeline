"""
palette.py — Waals color palette and color-picking logic.

All 143 named colors in HSL and CMYK, organized by lightness row.
Anchor groups and sampling functions used by color_generator.py.
"""
import colorsys
import random

# ── Waals palette — all 143 named colors as HSL (hue°, sat%, light%) ──────────
# Organized by lightness row (0=lightest, 10=darkest) and hue column.

WAALS = {
    # Row 0 — very light (L 87–97%)
    "alfven":      (  0,  87,  97),  "berg":        ( 25,  92,  95),
    "chain":       ( 35,  94,  94),  "dam":         ( 56,  85,  87),
    "esaki":       ( 70,  91,  87),  "fleming":     (107,  96,  91),
    "golgi":       (136,  91,  91),  "krogh":       (192,  94,  94),
    "metsjnikov":  (220,  88,  97),  "reines":      (240,  86,  97),
    "skou":        (274,  88,  97),  "tsui":        (321,  88,  97),
    "wilson":      (  0,   0,  96),

    # Row 1 — very light (L 75–94%)
    "alder":       (  6, 100,  94),  "barkla":      ( 21, 100,  92),
    "chung":       ( 39, 100,  85),  "debye":       ( 54,  88,  75),
    "eccles":      ( 67,  82,  70),  "fermi":       (104,  95,  78),
    "gabor":       (144,  98,  79),  "kendall":     (191, 100,  86),
    "minot":       (220, 100,  94),  "rabi":        (240, 100,  95),
    "stormer":     (275, 100,  94),  "taube":       (321, 100,  94),
    "wieland":     (  0,   0,  91),

    # Row 2 — light (L 55–91%)
    "aston":       (  4, 100,  91),  "bergstrom":   ( 21, 100,  87),
    "cajal":       ( 42, 100,  75),  "doisy":       ( 56,  86,  55),
    "einstein":    ( 65,  80,  54),  "feynman":     (100,  89,  66),
    "gasser":      (149,  94,  63),  "katz":        (189,  97,  77),
    "meer":        (219, 100,  90),  "richet":      (238, 100,  93),
    "salam":       (275, 100,  91),  "tannoudji":   (319, 100,  91),
    "walton":      (  0,   0,  87),

    # Row 3 — medium-light (L 50–84%)
    "adrian":      (  4, 100,  84),  "bosch":       ( 16, 100,  80),
    "curie":       ( 45, 100,  50),  "dirac":       ( 50,  77,  53),
    "eigen":       ( 64, 100,  41),  "flory":       ( 99,  70,  57),
    "glashow":     (148,  70,  59),  "kastler":     (189,  79,  65),
    "marconi":     (218, 100,  83),  "rainwater":   (239, 100,  88),
    "sabatier":    (276, 100,  86),  "todd":        (318, 100,  84),
    "waksman":     (  0,   0,  78),

    # Row 4 — medium (L 35–98%)
    "anderson":    (  0, 100,  98),  "beadle":      ( 15,  86,  97),
    "charpak":     ( 40,  82,  98),  "duve":        ( 49, 100,  40),
    "elion":       ( 63, 100,  35),  "forssmann":   (102,  56,  96),
    "gyorgy":      (156, 100,  38),  "klug":        (187,  71,  48),
    "meyerhof":    (215, 100,  97),  "raman":       (238, 100,  81),
    "summer":      (278, 100,  78),  "tinbergen":   (315, 100,  99),
    "wieschaus":   (  0,   0,  67),

    # Row 5 — mid (L 30–97%)
    "alvarez":     (  0,  86,  97),  "baeyer":      ( 14,  81,  94),
    "calvin":      ( 39, 100,  39),  "dalen":       ( 47, 100,  35),
    "enders":      ( 63, 100,  30),  "finsen":      ( 96,  73,  37),
    "giaver":      (155, 100,  33),  "kohler":      (186, 100,  35),
    "mcmillan":    (210,  89,  96),  "reichstein":  (238, 100,  75),
    "schrodinger": (276, 100,  99),  "tatum":       (316,  81,  94),
    "werner":      (  0,   0,  57),

    # Row 6 — medium-dark (L 24–99%)
    "appleton":    (  0, 100,  99),  "barton":      ( 25, 100,  39),
    "cooper":      ( 39, 100,  32),  "diels":       ( 49, 100,  28),
    "euler_chelpin":(63, 100,  24),  "fischer":     ( 98,  64,  32),
    "gennes":      (150,  64,  33),  "kossel":      (188,  63,  35),
    "montelcini":  (210,  71,  97),  "rontgen":     (240, 100,  99),
    "stark":       (283,  85,  74),  "tonegawa":    (310,  75,  98),
    "weinburg":    (  0,   0,  47),

    # Row 7 — dark (L 19–43%)
    "axelrod":     (360,  63,  43),  "bohr":        ( 24,  92,  32),
    "carrel":      ( 38, 100,  26),  "dao_lee":     ( 47, 100,  23),
    "einthoven":   ( 62, 100,  19),  "fowler":      ( 93, 100,  21),
    "gullstrand":  (154, 100,  21),  "kendrew":     (187, 100,  23),
    "medawar":     (206, 100,  33),  "richardson":  (240,  60,  98),
    "samuelson":   (285,  89,  42),  "theiler":     (312,  76,  38),
    "watson":      (  0,   0,  37),

    # Row 8 — very dark (L 15–32%)
    "anfinsen":    (  0,  70,  32),  "brown":       ( 23,  89,  25),
    "chadwick":    ( 37, 100,  20),  "davidsson":   ( 48, 100,  17),
    "ehrlich":     ( 63, 100,  15),  "furchgott":   ( 94, 100,  16),
    "gajdusek":    (153, 100,  16),  "kapitsa":     (186, 100,  17),
    "merrifield":  (206, 100,  25),  "ruzicka":     (237,  52,  42),
    "stanley":     (286, 100,  30),  "tiselius":    (311, 100,  26),
    "wald":        (  0,   0,  28),

    # Row 9 — near-black (L 10–21%)
    "alferov":     (359,  89,  21),  "baltimore":   ( 23, 100,  17),
    "crutzen":     ( 35, 100,  14),  "dickinson":   ( 51, 100,  11),
    "ernst":       ( 65, 100,  10),  "frisch":      ( 96, 100,  11),
    "goldstein":   (152, 100,  11),  "khorana":     (189, 100,  12),
    "mayer":       (207, 100,  18),  "robinson":    (237,  60,  30),
    "schrieffer":  (284,  89,  22),  "tsjerenkov":  (312,  92,  19),
    "willstatter": (  0,   0,  19),

    # Row 10 — darkest (L 6–20%)
    "arrhenius":   (  0,  71,  15),  "becquerel":   ( 20,  90,  12),
    "chamberlain": ( 34, 100,   9),  "deisenhofer": ( 47, 100,   8),
    "eijkman":     ( 62, 100,   6),  "frank":       (101, 100,   7),
    "granit":      (148, 100,   7),  "klitzing":    (187, 100,   8),
    "mossbauer":   (209, 100,  12),  "ross":        (238,  62,  20),
    "schull":      (284,  92,  15),  "thomson":     (312, 100,  13),
    "warburg":     (  0,   0,  12),

    # Pure black
    "weller":      (  0,   0,   3),
}

# ── Same palette in CMYK (C%, M%, Y%, K%) — for print export ─────────────────
# Converted from HSL via RGB. Values 0–100.
WAALS_CMYK = {
    # Row 0 — very light
    "alfven":      (  0,   5,   5,   0),  "berg":        (  0,   5,   9,   0),
    "chain":       (  0,   5,  11,   0),  "dam":         (  0,   2,  23,   2),
    "esaki":       (  4,   0,  24,   1),  "fleming":     ( 14,   0,  17,   0),
    "golgi":       ( 17,   0,  12,   1),  "krogh":       ( 11,   2,   0,   0),
    "metsjnikov":  (  5,   4,   0,   0),  "reines":      (  5,   5,   0,   0),
    "skou":        (  2,   5,   0,   0),  "tsui":        (  0,   5,   2,   0),
    "wilson":      (  0,   0,   0,   4),

    # Row 1 — very light
    "alder":       (  0,  11,  12,   0),  "barkla":      (  0,  10,  16,   0),
    "chung":       (  0,  10,  30,   0),  "debye":       (  0,   5,  45,   3),
    "eccles":      (  6,   0,  52,   5),  "fermi":       ( 31,   0,  42,   1),
    "gabor":       ( 41,   0,  25,   0),  "kendall":     ( 28,   5,   0,   0),
    "minot":       ( 12,   8,   0,   0),  "rabi":        ( 10,  10,   0,   0),
    "stormer":     (  5,  12,   0,   0),  "taube":       (  0,  12,   4,   0),
    "wieland":     (  0,   0,   0,   9),

    # Row 2 — light
    "aston":       (  0,  17,  18,   0),  "bergstrom":   (  0,  17,  26,   0),
    "cajal":       (  0,  15,  50,   0),  "doisy":       (  0,   6,  83,   6),
    "einstein":    (  7,   0,  81,   9),  "feynman":     ( 42,   0,  63,   4),
    "gasser":      ( 71,   0,  37,   2),  "katz":        ( 45,   7,   0,   1),
    "meer":        ( 20,  13,   0,   0),  "richet":      ( 14,  14,   0,   0),
    "salam":       (  8,  18,   0,   0),  "tannoudji":   (  0,  18,   6,   0),
    "walton":      (  0,   0,   0,  13),

    # Row 3 — medium-light
    "adrian":      (  0,  30,  32,   0),  "bosch":       (  0,  29,  40,   0),
    "curie":       (  0,  25, 100,   0),  "dirac":       (  0,  14,  81,  11),
    "eigen":       (  7,   0, 100,  18),  "flory":       ( 45,   0,  69,  13),
    "glashow":     ( 65,   0,  35,  12),  "kastler":     ( 60,   9,   0,   7),
    "marconi":     ( 34,  22,   0,   0),  "rainwater":   ( 24,  24,   0,   0),
    "sabatier":    ( 11,  28,   0,   0),  "todd":        (  0,  32,  10,   0),
    "waksman":     (  0,   0,   0,  22),

    # Row 4 — medium
    "anderson":    (  0,   4,   4,   0),  "beadle":      (  0,   4,   5,   0),
    "charpak":     (  0,   1,   3,   0),  "duve":        (  0,  18, 100,  20),
    "elion":       (  5,   0, 100,  30),  "forssmann":   (  3,   0,   5,   2),
    "gyorgy":      (100,   0,  40,  24),  "klug":        ( 83,  10,   0,  18),
    "meyerhof":    (  6,   4,   0,   0),  "raman":       ( 38,  37,   0,   0),
    "summer":      ( 16,  44,   0,   0),  "tinbergen":   (  0,   2,   1,   0),
    "wieschaus":   (  0,   0,   0,  33),

    # Row 5 — mid
    "alvarez":     (  0,   5,   5,   0),  "baeyer":      (  0,   8,  10,   1),
    "calvin":      (  0,  35, 100,  22),  "dalen":       (  0,  22, 100,  30),
    "enders":      (  5,   0, 100,  40),  "finsen":      ( 51,   0,  84,  36),
    "giaver":      (100,   0,  42,  34),  "kohler":      (100,  10,   0,  30),
    "mcmillan":    (  7,   4,   0,   0),  "reichstein":  ( 50,  48,   0,   0),
    "schrodinger": (  1,   2,   0,   0),  "tatum":       (  0,  10,   3,   1),
    "werner":      (  0,   0,   0,  43),

    # Row 6 — medium-dark
    "appleton":    (  0,   2,   2,   0),  "barton":      (  0,  58, 100,  22),
    "cooper":      (  0,  35, 100,  36),  "diels":       (  0,  18, 100,  44),
    "euler_chelpin":(  5,   0, 100,  52),  "fischer":     ( 49,   0,  78,  48),
    "gennes":      ( 78,   0,  39,  46),  "kossel":      ( 77,  10,   0,  43),
    "montelcini":  (  4,   2,   0,   1),  "rontgen":     (  2,   2,   0,   0),
    "stark":       ( 13,  46,   0,   4),  "tonegawa":    (  0,   3,   1,   1),
    "weinburg":    (  0,   0,   0,  53),

    # Row 7 — dark
    "axelrod":     (  0,  77,  77,  30),  "bohr":        (  0,  57,  96,  39),
    "carrel":      (  0,  37, 100,  48),  "dao_lee":     (  0,  22, 100,  54),
    "einthoven":   (  3,   0, 100,  62),  "fowler":      ( 55,   0, 100,  58),
    "gullstrand":  (100,   0,  43,  58),  "kendrew":     (100,  12,   0,  54),
    "medawar":     (100,  43,   0,  34),  "richardson":  (  2,   2,   0,   1),
    "samuelson":   ( 24,  94,   0,  21),  "theiler":     (  0,  86,  17,  33),
    "watson":      (  0,   0,   0,  63),

    # Row 8 — very dark
    "anfinsen":    (  0,  82,  82,  46),  "brown":       (  0,  58,  94,  53),
    "chadwick":    (  0,  38, 100,  60),  "davidsson":   (  0,  20, 100,  66),
    "ehrlich":     (  5,   0, 100,  70),  "furchgott":   ( 57,   0, 100,  68),
    "gajdusek":    (100,   0,  45,  68),  "kapitsa":     (100,  10,   0,  66),
    "merrifield":  (100,  43,   0,  50),  "ruzicka":     ( 68,  65,   0,  36),
    "stanley":     ( 23, 100,   0,  40),  "tiselius":    (  0, 100,  18,  48),
    "wald":        (  0,   0,   0,  72),

    # Row 9 — near-black
    "alferov":     (  0,  94,  93,  60),  "baltimore":   (  0,  62, 100,  66),
    "crutzen":     (  0,  42, 100,  72),  "dickinson":   (  0,  15, 100,  78),
    "ernst":       (  8,   0, 100,  80),  "frisch":      ( 60,   0, 100,  78),
    "goldstein":   (100,   0,  47,  78),  "khorana":     (100,  15,   0,  76),
    "mayer":       (100,  45,   0,  64),  "robinson":    ( 75,  71,   0,  52),
    "schrieffer":  ( 25,  94,   0,  58),  "tsjerenkov":  (  0,  96,  19,  64),
    "willstatter": (  0,   0,   0,  81),

    # Row 10 — darkest
    "arrhenius":   (  0,  83,  83,  74),  "becquerel":   (  0,  63,  95,  77),
    "chamberlain": (  0,  43, 100,  82),  "deisenhofer": (  0,  22, 100,  84),
    "eijkman":     (  3,   0, 100,  88),  "frank":       ( 68,   0, 100,  86),
    "granit":      (100,   0,  53,  86),  "klitzing":    (100,  12,   0,  84),
    "mossbauer":   (100,  48,   0,  76),  "ross":        ( 77,  74,   0,  68),
    "schull":      ( 26,  96,   0,  71),  "thomson":     (  0, 100,  20,  74),
    "warburg":     (  0,   0,   0,  88),

    # Pure black
    "weller":      (  0,   0,   0,  97),
}

# ── Color group selections from Waals ─────────────────────────────────────────
# Variation applied per group (±hue°, ±sat%, ±light%)
_CAT_DELTA = (8,  8, 6)
_BG_DELTA  = (8,  5, 5)   # lav sat-delta så muted-farger ikke drifter for levende
_EYE_DELTA = (12, 8, 7)

# Dark cats — rows 8–10, full hue wheel
DARK_CAT_ANCHORS = {k: WAALS[k] for k in [
    "anfinsen", "brown", "chadwick", "davidsson", "ehrlich",
    "furchgott", "gajdusek", "kapitsa", "stanley", "tiselius",
    "alferov", "baltimore", "crutzen", "dickinson", "ernst",
    "frisch", "goldstein", "khorana", "mayer", "schrieffer", "tsjerenkov",
    "arrhenius", "becquerel", "chamberlain", "deisenhofer", "eijkman",
    "frank", "granit", "klitzing", "mossbauer", "schull", "thomson",
    "weller",
]}

# Light cats — rows 3–5, full hue wheel
LIGHT_CAT_ANCHORS = {k: WAALS[k] for k in [
    "adrian", "bosch", "curie", "dirac", "eigen", "flory",
    "glashow", "kastler", "sabatier", "todd",
    "duve", "elion", "gyorgy", "klug", "summer", "wieschaus",
    "calvin", "dalen", "enders", "finsen", "giaver", "kohler", "werner",
]}

# ── Bakgrunnsgrupper ─────────────────────────────────────────────────────────
# Alle muted (S 0–25%). Delt i to verdener for bevisst paring:
#   WARM_BG_ANCHORS → katt_1 (tonal, lys, varm)
#   DARK_BG_ANCHORS → katt_2 (noir, mørk, kjølig)

WARM_BG_ANCHORS = {
    # Én nøytral base
    "warm_white":    ( 32,  18,  94),
    # Tintede varme — gir den to-tonede bakgrunnen synlig variasjon
    "warm_linen":    ( 35,  20,  88),
    "sand":          ( 40,  22,  86),
    "warm_stone":    ( 32,  14,  78),
    "blush":         (  5,  18,  84),
    "dusty_rose":    (355,  16,  79),
    "dusty_peach":   ( 18,  20,  82),
    "cool_white":    (220,  12,  94),
    "cool_linen":    (210,  14,  88),
}

DARK_BG_ANCHORS = {
    # L=30–48%: mørkt nok til noir-stemning, lyst nok til at svart katt synes
    "navy":          (218,  35,  32),
    "charcoal":      (  0,   0,  28),
    "deep_slate":    (212,  20,  38),
    "dark_sage":     (142,  22,  32),
    "dark_plum":     (282,  22,  34),
    "dark_forest":   (148,  28,  30),
    "warm_shadow":   ( 28,  16,  30),
    "cool_shadow":   (218,  16,  35),
    "deep_burgundy": (345,  25,  32),
    "dark_teal":     (186,  26,  32),
}

# Samlet for funksjoner som ikke er par-spesifikke
MUTED_BG_ANCHORS = {**WARM_BG_ANCHORS, **DARK_BG_ANCHORS}

# Eye colors — rows 4–5, high saturation, mid lightness (for noir cats)
EYE_ANCHORS = {k: WAALS[k] for k in [
    "duve", "elion", "gyorgy", "klug", "raman", "summer",
    "calvin", "enders", "finsen", "giaver", "kohler", "reichstein",
]}

# Tonal eye colors — rows 1–2, high saturation AND medium-high lightness (L=65–81%)
# Metningen vises som klar, levende farge (ikke mørk mud) mot lyse katter.
TONAL_EYE_ANCHORS = {k: WAALS[k] for k in [
    "cajal",      # H= 42°  S=100% L=75% — amber/oransje
    "eccles",     # H= 67°  S= 82% L=70% — gul-grønn
    "feynman",    # H=100°  S= 89% L=66% — grønn
    "fermi",      # H=104°  S= 95% L=78% — lys grønn
    "gabor",      # H=144°  S= 98% L=79% — teal-grønn
    "katz",       # H=189°  S= 97% L=77% — cyan
    "raman",      # H=238°  S=100% L=81% — blå
    "summer",     # H=278°  S=100% L=78% — lilla
    "reichstein", # H=238°  S=100% L=75% — blå
]}


def _sample_hsl(hue: float, sat: float, light: float, delta: tuple) -> tuple:
    dh, ds, dl = delta
    h = (hue + random.uniform(-dh, dh)) % 360
    s = max(0, min(100, sat   + random.uniform(-ds, ds)))
    l = max(0, min(100, light + random.uniform(-dl, dl)))
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return (int(r * 255), int(g * 255), int(b * 255))


def _sample_anchor(anchors: dict, delta: tuple) -> tuple[str, tuple]:
    """Pick a random anchor and sample one RGB near its HSL center."""
    name = random.choice(list(anchors.keys()))
    h, s, l = anchors[name]
    return name, _sample_hsl(h, s, l, delta)


def _pick_colors() -> tuple:
    all_cats = {**DARK_CAT_ANCHORS, **LIGHT_CAT_ANCHORS}
    cat_name, cat_rgb = _sample_anchor(all_cats,         _CAT_DELTA)
    bg_name,  bg_rgb  = _sample_anchor(MUTED_BG_ANCHORS, _BG_DELTA)
    eye_name, eye_rgb = _sample_anchor(EYE_ANCHORS,       _EYE_DELTA)
    return cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name


def _pick_tonal_colors() -> tuple:
    """Lys katt på varm, lys bakgrunn — stille, tonal verden.
    Krever L>55% på katten — kontrasten mot noir skal komme fra lys vs mørk.
    Bruker TONAL_EYE_ANCHORS: høy S + medium L → øynene ser levende ut, ikke mørke.
    """
    tonal_cats = {k: v for k, v in LIGHT_CAT_ANCHORS.items() if v[2] > 55}
    cat_name, cat_rgb = _sample_anchor(tonal_cats,          _CAT_DELTA)
    eye_name, eye_rgb = _sample_anchor(TONAL_EYE_ANCHORS,   _EYE_DELTA)
    bg_name,  bg_rgb  = _sample_anchor(WARM_BG_ANCHORS,     _BG_DELTA)
    return cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name


def _pick_noir_colors() -> tuple:
    """Mørk katt på mørk, kjølig bakgrunn — dramatisk noir-verden.
    Ekskluderer H=35–105° (gul/oliven-familien ser muddrete ut på lave L-verdier).
    """
    noir_cats = {k: v for k, v in DARK_CAT_ANCHORS.items()
                 if not (35 <= v[0] <= 105)}
    cat_name, cat_rgb = _sample_anchor(noir_cats,        _CAT_DELTA)
    bg_name,  bg_rgb  = _sample_anchor(DARK_BG_ANCHORS,  _BG_DELTA)
    eye_name, eye_rgb = _sample_anchor(EYE_ANCHORS,       _EYE_DELTA)
    return cat_rgb, cat_name, bg_rgb, bg_name, eye_rgb, eye_name

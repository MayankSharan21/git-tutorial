"""Gondola size, type, and complete-code catalogues."""

# ============================================================
# SIZE CODES
# ============================================================

SIZE_CODES = {
    "15F",
    "21F",
    "34F",
    "34H",
    "34S",
    "36W",
    "36B",
    "18F",
    "12W",
    "15W",
    "27H",
    "28F",
    "42F",
    "21H"
}


# ============================================================
# TYPE CODES
# ============================================================

TYPE_CODES = {
    "MCA",
    "MCS",
    "LCA",
    "LCS",
    "MOA",
    "MOS",
    "LOA",
    "LOS",
    "MGA",
    "MGS",
    "WCA",
    "WCS",
    "WOA",
    "WOS",
    "MWA",
    "MWS"
}


# ============================================================
# COMPLETE / SPECIAL GONDOLA CODES
# ============================================================

FULL_CODES = {

    "15FLCA",
    "15FLCS",
    "15FLOA",
    "15FLOS",
    "15FMCA",
    "15FMCS",
    "15FMOA",
    "15FMOS",

    "18FLCA",
    "18FLCS",
    "18FMCA",
    "18FMCS",
    "18FMOA",
    "18FMOS",

    "21FLCA",
    "21FLCS",
    "21FLOA",
    "21FLOS",
    "21FMCA",
    "21FMCS",
    "21FMOA",
    "21FMOS",

    "34FLCA",
    "34FLCS",
    "34FLOA",
    "34FLOS",
    "34FMCA",
    "34FMCS",
    "34FMOA",
    "34FMOS",

    "34HLCA",
    "34HLCS",
    "34HLOA",
    "34HLOS",

    "27HLCA",
    "27HLCS",

    "34SLCA",
    "34SLCS",

    "34RDLC",

    "FLATDECK",
    "FLATDECKWS",

    "36WLOA",
    "36WLOS",
    "36WLCA",
    "36WLCS",
    "15WLOS",

    "36BLOA",
    "36BLOS",
    "36BLCA",
    "36BLCS",

    "15WLCA",
    "15WLCS",
    "15WLOS",
    "15WMCA",
    "15WMCS",

    "12WMCA",
    "12WMCS",

    "15FMWA",
    "15FMWS",
    "21FMWA",
    "21FMWS",
    "34FMWA",
    "34FMWS",

    "12FLCA",
    "12FLCS",
    "12FLOA",
    "12FLOS",
    "12FMCA",
    "12FMCS",
    "12FMOA",
    "12FMOS",

    "36HLCA",
    "36HLCS",
    "36HLOA",
    "36HLOS",

    "34WLOA",
    "34WLOS",
    "34WLCA",
    "34WLCS",

    "32WLOA",
    "32WLOS",
    "32WLCA",
    "32WLCS",

    "30WLOA",
    "30WLOS",
    "30WLCA",
    "30WLCS",

    "27WLOA",
    "27WLOS",
    "27WLCA",
    "27WLCS",

    "21WLOA",
    "21WLOS",
    "21WLCA",
    "21WLCS",

    "12DELC",
    "12DEMO",
    "12ELC",
    "12ELO",
    "12EMC",
    "12EMO",
    "12SELC",
    "12SEMC",

    "15DELC",
    "15DELO",
    "15DEMC",
    "15DEMO",
    "15ELC",
    "15ELO",
    "15ELW",
    "15EMC",
    "15EMM",
    "15EMO",
    "15EMW",
    "15SELC",
    "15SELO",
    "15SEMC",
    "15SEMO",
    "15SEMW",

    "18DELC",
    "18DEMO",
    "18ELC",
    "18ELM",
    "18ELO",
    "18EMC",
    "18EMM",
    "18EMO",
    "18POSTER END",
    "18SELC",
    "18SELO",
    "18SEMC",
    "18SEMO",

    "21DELC",
    "21DELC 200 PEG",
    "21DELM",
    "21DELO",
    "21DEMC",
    "21DEMO",
    "21ELC",
    "21ELM",
    "21ELO",
    "21ELW",
    "21ELWM",
    "21EMC",
    "21EMM",
    "21EMO",
    "21EMW",
    "21EMWM",
    "21POSTER END",
    "21SELC",
    "21SELO",
    "21SELW",
    "21SEMC",
    "21SEMO",
    "21SEMW",

    "26DELW - DIVIDING WALL - END",
    "26EMW - DIVIDING WALL EPF",

    "27ELC",
    "27ELO",
    "27ELW",
    "27EMC",
    "27EMO",
    "27POSTER 540 END",
    "27SELC",
    "27SELO",
    "27SELW",

    "30DELO",
    "30DEMC",
    "30DEMO",
    "30ELC",
    "30ELM",
    "30ELO",
    "30EMC",
    "30EMM",
    "30EMO",
    "30SELC",
    "30SELO",
    "30SELW",
    "30SEMC",
    "30SEMO",

    "32DELC",
    "32DELO",
    "32DEMC",
    "32DEMO",
    "32ELC",
    "32ELM",
    "32ELO",
    "32ELW",
    "32ELWM",
    "32EMC",
    "32EMM",
    "32EMO",
    "32EMW",
    "32EMWM",
    "32SELC",
    "32SELO",
    "32SELW",
    "32SEMC",
    "32SEMO",
    "32SEMW",

    "34DELC",
    "34DELO",
    "34DEMC",
    "34DEMO",
    "34ELC",
    "34ELM",
    "34ELO",
    "34ELW",
    "34ELWM",
    "34EMC",
    "34EMM",
    "34EMO",
    "34EMW",
    "34EMWM",
    "34SELC",
    "34SELO",
    "34SELW",
    "34SEMC",
    "34SEMO",
    "34SEMW",
    "34SELW 540 END",
    "34SEMV 540 END",

    "HALLMARK END 1200",
    "HALLMARK END 900",

    "12QMCA",
    "12QMCS",

    #OLD CODES
"15EPLC",
"15EPMC",
"15EPMO",
"15EPLO",
"15EPMM",

"15SHMC",
"15SHLC",
"15SHLO",

"18EPLC",
"18EPMC",
"18EPMO",
"18EPLO",
"18EPMM",

"18SHMC",
"18SHLC",
"18SHLO",

"21EPLC",
"21EPMC",
"21EPMO",
"21EPLO",
"21EPMM",
"21SHMC",
"21SHLC",
"21SHLO",

"27HLO",

"32EPLC",
"32EPMC",
"32EPMO",
"32EPLO",
"32SHLO",

"34EPLC",
"34EPMC",
"34EPMO",
"34EPLO",
"34SHLO",


"34BLOA",
"34BLOS",

"36BLOA",
"36BLOS",

"15RDLC",
"15RDLO",
"15RDMC",
"15RDMO",

"18RDLC",
"18RDLO",
"18RDMC",
"18RDMO",

"21RDLC",
"21RDLO",
"21RDMC",
"21RDMO",

"32RDLC",
"32RDLO",
"32RDMC",
"32RDMO",

"34RDLC",
"34RDLO",
"34RDMC",
"34RDMO",
"34RELO",

"FLATDECK W/-SURROUND",
"FLATDECK",
"DECK TABLE",
"HOPPER UNIT 2150H",


"HOT SPOT 1500H",
"HOT SPOT COOKBOOKS",
"HOT SPOT 2100H",
"HOT SPOT 3000H",
"HOT SPOT 3200H",
"HOT SPOT 3400H",

"Straight rail",

"6Way",
"16_Way",

"T2 TABLE",
"T2 ARM ONLY",

"HANGER TOTEM",

}


def _norm(value):
    return " ".join(str(value).upper().strip().split())


SIZE_CODES = {_norm(x) for x in SIZE_CODES}
TYPE_CODES = {_norm(x) for x in TYPE_CODES}
FULL_CODES = {_norm(x) for x in FULL_CODES}

# Longest-first helps match spaced complete codes.
FULL_CODES_SORTED = sorted(FULL_CODES, key=len, reverse=True)



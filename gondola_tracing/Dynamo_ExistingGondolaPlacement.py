# Dynamo_ExistingGondolaPlacement
# Revit 2025 / Dynamo CPython3 compatible
#
# Version 2026-10-05c-existing-restore
#
# Places existing-condition gondolas from the JSON written by
# Gondola_OrientationDetector.py.
#
# Angle keys, in priority order:
#   revit_angle
#   angle
#   orientation_angle  (converted from DXF long-axis to family rotation)
#
# DXF text "rotation" is ignored. That field is the readable-label
# rotation and is almost always 0, which previously forced every
# gondola onto 0°.

import clr
import os
import json
import math
import re


clr.AddReference("RevitAPI")
clr.AddReference("RevitServices")

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    FamilySymbol,
    FamilyInstance,
    Transaction,
    XYZ,
    Level,
    ViewPlan,
    Line,
    ElementTransformUtils,
    Phase,
    BuiltInParameter,
    OverrideGraphicSettings,
    Color,
    ImportInstance
)
from Autodesk.Revit.DB.Structure import StructuralType
from RevitServices.Persistence import DocumentManager


JSON_PATH = r"C:\Users\msharan\OneDrive - Kmart Australia Limited\Desktop\Stores Foundry\Tracing\json\gondola_data_Marrickville_New2.json"
LEVEL_NAME = "00-GROUND"
CAD_LINK_NAME = ""
MM_TO_FT = 1.0 / 304.8

# Hard rule: place only on Existing. Never Proposed, selling-floor, or overlay.
EXISTING_ONLY = True
SCRIPT_VERSION = "2026-10-05c-existing-restore"

USE_JSON_ANGLE = True
ANGLE_SIGN = 1.0
ANGLE_OFFSET_DEG = 0.0
VERTICAL_FALLBACK_DEG = 0.0
HORIZONTAL_FALLBACK_DEG = 90.0
APPLY_CAD_TRANSLATION = True
APPLY_CAD_ROTATION = False


TYPE_MAP = {
    "15FLCA": ("Floor_Gondola", "15FLCA"),
    "15FLCS": ("Floor_Gondola", "15FLCS"),
    "15FLOA": ("Floor_Gondola", "15FLOA"),
    "15FLOS": ("Floor_Gondola", "15FLOS"),
    "15FMCA": ("Floor_Gondola", "15FMCA"),
    "15FMCS": ("Floor_Gondola", "15FMCS"),
    "15FMOA": ("Floor_Gondola", "15FMOA"),
    "15FMOS": ("Floor_Gondola", "15FMOS"),
    "18FLCA": ("Floor_Gondola", "18FLCA"),
    "18FLCS": ("Floor_Gondola", "18FLCS"),
    "18FMCA": ("Floor_Gondola", "18FMCA"),
    "18FMCS": ("Floor_Gondola", "18FMCS"),
    "18FMOA": ("Floor_Gondola", "18FMOA"),
    "18FMOS": ("Floor_Gondola", "18FMOS"),
    "21FLCA": ("Floor_Gondola", "21FLCA"),
    "21FLCS": ("Floor_Gondola", "21FLCS"),
    "21FLOA": ("Floor_Gondola", "21FLOA"),
    "21FLOS": ("Floor_Gondola", "21FLOS"),
    "21FMCA": ("Floor_Gondola", "21FMCA"),
    "21FMCS": ("Floor_Gondola", "21FMCS"),
    "21FMOA": ("Floor_Gondola", "21FMOA"),
    "21FMOS": ("Floor_Gondola", "21FMOS"),
    "34FLCA": ("Floor_Gondola", "34FLCA"),
    "34FLCS": ("Floor_Gondola", "34FLCS"),
    "34FLOA": ("Floor_Gondola", "34FLOA"),
    "34FLOS": ("Floor_Gondola", "34FLOS"),
    "34FMCA": ("Floor_Gondola", "34FMCA"),
    "34FMCS": ("Floor_Gondola", "34FMCS"),
    "34FMOA": ("Floor_Gondola", "34FMOA"),
    "34FMOS": ("Floor_Gondola", "34FMOS"),
    "34HLCA": ("Floor_Gondola_High_Bay", "34HLCA"),
    "34HLCS": ("Floor_Gondola_High_Bay", "34HLCS"),
    "34HLOA": ("Floor_Gondola_High_Bay", "34HLOA"),
    "34HLOS": ("Floor_Gondola_High_Bay", "34HLOS"),
    "27HLCA": ("Floor_Gondola_High_Bay", "27HLCA"),
    "27HLCS": ("Floor_Gondola_High_Bay", "27HLCS"),
    "34SLCA": ("Floor_Gondola", "34FLCA EXTENSION LEG"),
    "34SLCS": ("Floor_Gondola", "34FLCS"),
    "34RDLC": ("End_Panel_Decks", "34ELO"),
    "FLATDECK": ("Decks_&_Hopper", "LRD"),
    "FLATDECKWS": ("Decks_&_Hopper", "LRD_2S"),
    "36WLOA": ("Wall_Gondola", "36WLOA"),
    "36WLOS": ("Wall_Gondola", "36WLOS"),
    "36WLCA": ("Wall_Gondola", "36WLCA"),
    "36WLCS": ("Wall_Gondola", "36WLCS"),
    "15WLOS": ("Wall_Gondola", "15WLOS"),
    "36BLOA": ("Floor_Gondola_High_Bay", "36HLOA"),
    "36BLOS": ("Wall_Gondola_High_Bay", "36HLOS"),
    "36BLCA": ("Floor_Gondola_High_Bay", "36HLCA"),
    "36BLCS": ("Wall_Gondola_High_Bay", "36HLCS"),
    "15WLCA": ("Wall_Gondola", "15WLCA"),
    "15WLCS": ("Wall_Gondola", "15WLCS"),
    "15WLOA": ("Wall_Gondola", "15WLOA"),
    "15WMCA": ("Wall_Gondola", "15WMCA"),
    "15WMCS": ("Wall_Gondola", "15WMCS"),
    "12WMCA": ("Wall_Gondola", "12WMCA"),
    "12WMCS": ("Wall_Gondola", "12WMCS"),
    "15FMWA": ("Floor_Gondola", "15FMWA"),
    "15FMWS": ("Floor_Gondola", "15FMWS"),
    "21FMWA": ("Floor_Gondola", "21FMWA"),
    "21FMWS": ("Floor_Gondola", "21FMWS"),
    "34FMWA": ("Floor_Gondola", "34FMWA"),
    "34FMWS": ("Floor_Gondola", "34FMWS"),
    "12FLCA": ("Floor_Gondola", "12FLCA"),
    "12FLCS": ("Floor_Gondola", "12FLCS"),
    "12FLOA": ("Floor_Gondola", "12FLOA"),
    "12FLOS": ("Floor_Gondola", "12FLOS"),
    "12FMCA": ("Floor_Gondola", "12FMCA"),
    "12FMCS": ("Floor_Gondola", "12FMCS"),
    "12FMOA": ("Floor_Gondola", "12FMOA"),
    "12FMOS": ("Floor_Gondola", "12FMOS"),
    "36HLCA": ("Floor_Gondola_High_Bay", "36HLCA"),
    "36HLCS": ("Floor_Gondola_High_Bay", "36HLCS"),
    "36HLOA": ("Floor_Gondola_High_Bay", "36HLOA"),
    "36HLOS": ("Floor_Gondola_High_Bay", "36HLOS"),
    "34WLOA": ("Wall_Gondola", "34WLOA"),
    "34WLOS": ("Wall_Gondola", "34WLOS"),
    "34WLCA": ("Wall_Gondola", "34WLCA"),
    "34WLCS": ("Wall_Gondola", "34WLCS"),
    "32WLOA": ("Wall_Gondola", "32WLOA"),
    "32WLOS": ("Wall_Gondola", "32WLOS"),
    "32WLCA": ("Wall_Gondola", "32WLCA"),
    "32WLCS": ("Wall_Gondola", "32WLCS"),
    "30WLOA": ("Wall_Gondola", "30WLOA"),
    "30WLOS": ("Wall_Gondola", "30WLOS"),
    "30WLCA": ("Wall_Gondola", "30WLCA"),
    "30WLCS": ("Wall_Gondola", "30WLCS"),
    "27WLOA": ("Wall_Gondola", "27WLOA"),
    "27WLOS": ("Wall_Gondola", "27WLOS"),
    "27WLCA": ("Wall_Gondola", "27WLCA"),
    "27WLCS": ("Wall_Gondola", "27WLCS"),
    "21WLOA": ("Wall_Gondola", "21WLOA"),
    "21WLOS": ("Wall_Gondola", "21WLOS"),
    "21WLCA": ("Wall_Gondola", "21WLCA"),
    "21WLCS": ("Wall_Gondola", "21WLCS"),
    "12DELC": ("End_Panel", "12DELC"),
    "12DEMO": ("End_Panel", "12DEMO"),
    "12ELC": ("End_Panel", "12ELC"),
    "12ELO": ("End_Panel", "12ELO"),
    "12EMC": ("End_Panel", "12EMC"),
    "12EMO": ("End_Panel", "12EMO"),
    "12SELC": ("End_Panel", "12SELC"),
    "12SEMC": ("End_Panel", "12SEMC"),
    "15DELC": ("End_Panel", "15DELC"),
    "15DELO": ("End_Panel", "15DELO"),
    "15DEMC": ("End_Panel", "15DEMC"),
    "15DEMO": ("End_Panel", "15DEMO"),
    "15ELC": ("End_Panel", "15ELC"),
    "15ELO": ("End_Panel", "15ELO"),
    "15ELW": ("End_Panel", "15ELW"),
    "15EMC": ("End_Panel", "15EMC"),
    "15EMM": ("End_Panel", "15EMM"),
    "15EMO": ("End_Panel", "15EMO"),
    "15EMW": ("End_Panel", "15EMW"),
    "15SELC": ("End_Panel", "15SELC"),
    "15SELO": ("End_Panel", "15SELO"),
    "15SEMC": ("End_Panel", "15SEMC"),
    "15SEMO": ("End_Panel", "15SEMO"),
    "15SEMW": ("End_Panel", "15SEMW"),
    "18DELC": ("End_Panel", "18DELC"),
    "18DEMO": ("End_Panel", "18DEMO"),
    "18DEMC": ("End_Panel", "18DEMC"),
    "18ELC": ("End_Panel", "18ELC"),
    "18ELM": ("End_Panel", "18ELM"),
    "18ELO": ("End_Panel", "18ELO"),
    "18EMC": ("End_Panel", "18EMC"),
    "18EMM": ("End_Panel", "18EMM"),
    "18EMO": ("End_Panel", "18EMO"),
    "18POSTER END": ("End_Panel", "18POSTER END"),
    "18SELC": ("End_Panel", "18SELC"),
    "18SELO": ("End_Panel", "18SELO"),
    "18SEMC": ("End_Panel", "18SEMC"),
    "18SEMO": ("End_Panel", "18SEMO"),
    "21DELC": ("End_Panel", "21DELC"),
    "21DELC 200 PEG": ("End_Panel", "21DELC 200 PEG"),
    "21DELM": ("End_Panel", "21DELM"),
    "21DELO": ("End_Panel", "21DELO"),
    "21DEMC": ("End_Panel", "21DEMC"),
    "21DEMO": ("End_Panel", "21DEMO"),
    "21ELC": ("End_Panel", "21ELC"),
    "21ELM": ("End_Panel", "21ELM"),
    "21ELO": ("End_Panel", "21ELO"),
    "21ELW": ("End_Panel", "21ELW"),
    "21ELWM": ("End_Panel", "21ELWM"),
    "21EMC": ("End_Panel", "21EMC"),
    "21EMM": ("End_Panel", "21EMM"),
    "21EMO": ("End_Panel", "21EMO"),
    "21EMW": ("End_Panel", "21EMW"),
    "21EMWM": ("End_Panel", "21EMWM"),
    "21POSTER END": ("End_Panel", "21POSTER END"),
    "21SELC": ("End_Panel", "21SELC"),
    "21SELO": ("End_Panel", "21SELO"),
    "21SELW": ("End_Panel", "21SELW"),
    "21SEMC": ("End_Panel", "21SEMC"),
    "21SEMO": ("End_Panel", "21SEMO"),
    "21SEMW": ("End_Panel", "21SEMW"),
    "26DELW - DIVIDING WALL - END": ("End_Panel", "26DELW - DIVIDING WALL - END"),
    "26EMW - DIVIDING WALL EPF": ("End_Panel", "26EMW - DIVIDING WALL EPF"),
    "27ELC": ("End_Panel", "27ELC"),
    "27ELO": ("End_Panel", "27ELO"),
    "27ELW": ("End_Panel", "27ELW"),
    "27EMC": ("End_Panel", "27EMC"),
    "27EMO": ("End_Panel", "27EMO"),
    "27POSTER 540 END": ("End_Panel", "27POSTER 540 END"),
    "27SELC": ("End_Panel", "27SELC"),
    "27SELO": ("End_Panel", "27SELO"),
    "27SELW": ("End_Panel", "27SELW"),
    "30DELO": ("End_Panel", "30DELO"),
    "30DEMC": ("End_Panel", "30DEMC"),
    "30DEMO": ("End_Panel", "30DEMO"),
    "30ELC": ("End_Panel", "30ELC"),
    "30ELM": ("End_Panel", "30ELM"),
    "30ELO": ("End_Panel", "30ELO"),
    "30EMC": ("End_Panel", "30EMC"),
    "30EMM": ("End_Panel", "30EMM"),
    "30EMO": ("End_Panel", "30EMO"),
    "30SELC": ("End_Panel", "30SELC"),
    "30SELO": ("End_Panel", "30SELO"),
    "30SELW": ("End_Panel", "30SELW"),
    "30SEMC": ("End_Panel", "30SEMC"),
    "30SEMO": ("End_Panel", "30SEMO"),
    "32DELC": ("End_Panel", "32DELC"),
    "32DELO": ("End_Panel", "32DELO"),
    "32DEMC": ("End_Panel", "32DEMC"),
    "32DEMO": ("End_Panel", "32DEMO"),
    "32ELC": ("End_Panel", "32ELC"),
    "32ELM": ("End_Panel", "32ELM"),
    "32ELO": ("End_Panel", "32ELO"),
    "32ELW": ("End_Panel", "32ELW"),
    "32ELWM": ("End_Panel", "32ELWM"),
    "32EMC": ("End_Panel", "32EMC"),
    "32EMM": ("End_Panel", "32EMM"),
    "32EMO": ("End_Panel", "32EMO"),
    "32EMW": ("End_Panel", "32EMW"),
    "32EMWM": ("End_Panel", "32EMWM"),
    "32SELC": ("End_Panel", "32SELC"),
    "32SELO": ("End_Panel", "32SELO"),
    "32SELW": ("End_Panel", "32SELW"),
    "32SEMC": ("End_Panel", "32SEMC"),
    "32SEMO": ("End_Panel", "32SEMO"),
    "32SEMW": ("End_Panel", "32SEMW"),
    "34DELC": ("End_Panel", "34DELC"),
    "34DELO": ("End_Panel", "34DELO"),
    "34DEMC": ("End_Panel", "34DEMC"),
    "34DEMO": ("End_Panel", "34DEMO"),
    "34ELC": ("End_Panel", "34ELC"),
    "34ELM": ("End_Panel", "34ELM"),
    "34ELO": ("End_Panel", "34ELO"),
    "34ELW": ("End_Panel", "34ELW"),
    "34ELWM": ("End_Panel", "34ELWM"),
    "34EMC": ("End_Panel", "34EMC"),
    "34EMM": ("End_Panel", "34EMM"),
    "34EMO": ("End_Panel", "34EMO"),
    "34EMW": ("End_Panel", "34EMW"),
    "34EMWM": ("End_Panel", "34EMWM"),
    "34SELC": ("End_Panel", "34SELC"),
    "34SELO": ("End_Panel", "34SELO"),
    "34SELW": ("End_Panel", "34SELW"),
    "34SEMC": ("End_Panel", "34SEMC"),
    "34SEMO": ("End_Panel", "34SEMO"),
    "34SEMW": ("End_Panel", "34SEMW"),
    "34SELW 540 END": ("End_Panel", "34SELW 540 END"),
    "34SEMV 540 END": ("End_Panel", "34SEMV 540 END"),
    "HALLMARK END 1200": ("End_Panel", "HALLMARK END 1200"),
    "HALLMARK END 900": ("End_Panel", "HALLMARK END 900"),
    "12QMCA": ("Floor_Gondola_Queuing", "12QMCA"),
    "12QMCS": ("Floor_Gondola_Queuing", "12QMCS"),
    "15EPLC": ("End_Panel", "15ELC"),
    "15EPMC": ("End_Panel", "15EMC"),
    "15EPMO": ("End_Panel", "15EMO"),
    "15EPLO": ("End_Panel", "15ELO"),
    "15EPMM": ("End_Panel", "15EMM"),
    "15SHMC": ("End_Panel", "15SEMC"),
    "15SHLC": ("End_Panel", "15SELC"),
    "15SHLO": ("End_Panel", "15SELO"),
    "18EPLC": ("End_Panel", "18ELC"),
    "18EPMC": ("End_Panel", "18EMC"),
    "18EPMO": ("End_Panel", "18EMO"),
    "18EPLO": ("End_Panel", "18ELO"),
    "18EPMM": ("End_Panel", "18EMM"),
    "18SHMC": ("End_Panel", "18SEMC"),
    "18SHLC": ("End_Panel", "18SELC"),
    "18SHLO": ("End_Panel", "18SELO"),
    "21EPLC": ("End_Panel", "21ELC"),
    "21EPMC": ("End_Panel", "21EMC"),
    "21EPMO": ("End_Panel", "21EMO"),
    "21EPLO": ("End_Panel", "21ELO"),
    "21EPMM": ("End_Panel", "21EMM"),
    "21SHMC": ("End_Panel", "21SEMC"),
    "21SHLC": ("End_Panel", "21SELC"),
    "21SHLO": ("End_Panel", "21SELO"),
    "27HLO": ("End_Panel", "27SELO"),
    "32EPLC": ("End_Panel", "32ELC"),
    "32EPMC": ("End_Panel", "32EMC"),
    "32EPMO": ("End_Panel", "32EMO"),
    "32EPLO": ("End_Panel", "32ELO"),
    "32SHLO": ("End_Panel", "32SELO"),
    "34EPLC": ("End_Panel", "34ELC"),
    "34EPMC": ("End_Panel", "34EMC"),
    "34EPMO": ("End_Panel", "34EMO"),
    "34EPLO": ("End_Panel", "34ELO"),
    "34SHLO": ("End_Panel", "34SELO"),
    "34BLOA": ("Wall_Gondola_High_Bay", "34HLCA OUTRIGGER POST ADDED"),
    "34BLOS": ("Wall_Gondola_High_Bay", "34HLCS"),
    "36BLOA": ("Wall_Gondola_High_Bay", "36HLCA OUTRIGGER POST ADDED"),
    "36BLOS": ("Wall_Gondola_High_Bay", "36HLCS"),
    "15RDLC": ("End_Panel_Decks", "15ELC (End_Panel_Decks)"),
    "15RDLO": ("End_Panel_Decks", "15ELO (End_Panel_Decks)"),
    "15RDMC": ("End_Panel_Decks", "15EMC(End_Panel_Decks)"),
    "15RDMO": ("End_Panel_Decks", "15EMO(End_Panel_Decks)"),
    "18RDLC": ("End_Panel_Decks", "18ELC(End_Panel_Decks)"),
    "18RDLO": ("End_Panel_Decks", "18ELO(End_Panel_Decks)"),
    "18RDMC": ("End_Panel_Decks", "18EMC(End_Panel_Decks)"),
    "18RDMO": ("End_Panel_Decks", "18EMO(End_Panel_Decks)"),
    "21RDLC": ("End_Panel_Decks", "21ELC(End_Panel_Decks)"),
    "21RDLO": ("End_Panel_Decks", "21ELO(End_Panel_Decks)"),
    "21RDMC": ("End_Panel_Decks", "21EMC(End_Panel_Decks)"),
    "21RDMO": ("End_Panel_Decks", "21EMO(End_Panel_Decks)"),
    "32RDLC": ("End_Panel_Decks", "32ELC(End_Panel_Decks)"),
    "32RDLO": ("End_Panel_Decks", "32ELO(End_Panel_Decks)"),
    "32RDMC": ("End_Panel_Decks", "32EMC(End_Panel_Decks)"),
    "32RDMO": ("End_Panel_Decks", "32EMO(End_Panel_Decks)"),
    "34RDLO": ("End_Panel_Decks", "34ELO(End_Panel_Decks)"),
    "34RDMC": ("End_Panel_Decks", "34EMC(End_Panel_Decks)"),
    "34RDMO": ("End_Panel_Decks", "34EMO(End_Panel_Decks)"),
    "34RELO": ("End_Panel_Decks", "34ELO(End_Panel_Decks)"),
    "FLATDECK W/-SURROUND": ("Decks_&_Hopper", "LRD_2S"),
    "DECK TABLE": ("Decks_&_Hopper", "Deck_Table"),
    "HOPPER UNIT 2150H": ("Decks_&_Hopper", "HOP21"),
    "HOT SPOT 1500H": ("Hotspots", "15H Hotspot"),
    "HOT SPOT COOKBOOKS": ("Hotspots", "15H Cookbook"),
    "HOT SPOT 2100H": ("Hotspots", "21H Hotspot"),
    "HOT SPOT 3000H": ("Hotspots", "30H Hotspot"),
    "HOT SPOT 3200H": ("Hotspots", "32H Hotspot"),
    "HOT SPOT 3400H": ("Hotspots", "34H Hotspot"),
    "STRAIGHT RAIL": ("Hotspots", "racking-straight rail"),
    "6WAY": ("Hotspots", "Racking-6_Way"),
    "16_WAY": ("Hotspots", "Racking-16_Way"),
    "T2 TABLE": ("Hotspots", "T2 VM RAIL + DISPLAY ARM (TABLE_T)"),
    "T2 ARM ONLY": ("Hotspots", "T2 TABLE ARM ONLY"),
    "T2 NO RAIL/ARMS": ("Hotspots", "T2 TABLE ARM ONLY"),
    "T3 TABLE": ("Hotspots", "T2 VM RAIL + DISPLAY ARM (TABLE_T)"),
    "HANGER TOTEM": ("Hotspots", "HANGER (Bin_240L)"),
    "27SHLO": ("End_Panel", "27SELO"),
    "LRD": ("Decks_&_Hopper", "LRD"),
    "LRD_2": ("Decks_&_Hopper", "LRD_2S"),
}


# When the preferred family/type is not loaded, place a close equivalent
# so the bay is still traced.
TYPE_MAP_FALLBACKS = {
    "15RDLC": ("End_Panel", "15ELC"),
    "15RDLO": ("End_Panel", "15ELO"),
    "15RDMC": ("End_Panel", "15EMC"),
    "15RDMO": ("End_Panel", "15EMO"),
    "18RDLC": ("End_Panel", "18ELC"),
    "18RDLO": ("End_Panel", "18ELO"),
    "18RDMC": ("End_Panel", "18EMC"),
    "18RDMO": ("End_Panel", "18EMO"),
    "21RDLC": ("End_Panel", "21ELC"),
    "21RDLO": ("End_Panel", "21ELO"),
    "21RDMC": ("End_Panel", "21EMC"),
    "21RDMO": ("End_Panel", "21EMO"),
    "32RDLC": ("End_Panel", "32ELC"),
    "32RDLO": ("End_Panel", "32ELO"),
    "32RDMC": ("End_Panel", "32EMC"),
    "32RDMO": ("End_Panel", "32EMO"),
    "34RDLC": ("End_Panel", "34ELC"),
    "34RDLO": ("End_Panel", "34ELO"),
    "34RDMC": ("End_Panel", "34EMC"),
    "34RDMO": ("End_Panel", "34EMO"),
    "34RELO": ("End_Panel", "34ELO"),
    "DECK TABLE": ("Decks_&_Hopper", "LRD_2"),
    "27HLO": ("End_Panel", "27SELO"),
    "6WAY": ("Hotspots", "Racking-6_Way"),
    "STRAIGHT RAIL": ("Hotspots", "racking-straight rail"),
}


CODE_ALIASES = {
    "6 WAY": "6WAY",
    "6-WAY": "6WAY",
    "6_WAY": "6WAY",
    "16 WAY": "16_WAY",
    "16WAY": "16_WAY",
    "STRAIGHT-RAIL": "STRAIGHT RAIL",
    "STRAIGHTRAIL": "STRAIGHT RAIL",
    "FLATDECKWS": "FLATDECK W/-SURROUND",
    "FLATDECK WS": "FLATDECK W/-SURROUND",
    "LRD": "FLATDECK",
    "LRD_2": "FLATDECK W/-SURROUND",
    "T2 NO RAIL/ARMS": "T2 NO RAIL/ARMS",
    "T3 TABLE": "T3 TABLE",
}


def normalize_lookup_key(value):
    text = str(value or "").upper().strip()
    text = re.sub(r"\s+", " ", text)
    return CODE_ALIASES.get(text, text)


TYPE_MAP_NORM = {
    normalize_lookup_key(code): mapping
    for code, mapping in TYPE_MAP.items()
}
FALLBACK_NORM = {
    normalize_lookup_key(code): mapping
    for code, mapping in TYPE_MAP_FALLBACKS.items()
}


def safe_element_name(element):
    if element is None:
        return ""
    try:
        value = element.Name
        if value:
            return str(value)
    except Exception:
        pass
    try:
        param = element.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if param is not None:
            value = param.AsString()
            if value:
                return value
    except Exception:
        pass
    return ""


def safe_family_name(symbol):
    if symbol is None:
        return ""
    try:
        value = symbol.FamilyName
        if value:
            return str(value)
    except Exception:
        pass
    try:
        family = symbol.Family
        if family is not None:
            value = family.Name
            if value:
                return str(value)
    except Exception:
        pass
    return ""


def safe_symbol_name(symbol):
    if symbol is None:
        return ""
    try:
        value = symbol.Name
        if value:
            return str(value)
    except Exception:
        pass
    try:
        param = symbol.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if param is not None:
            value = param.AsString()
            if value:
                return value
    except Exception:
        pass
    return ""


def safe_element_id_value(element_id):
    if element_id is None:
        return None
    for attr in ("Value", "IntegerValue"):
        try:
            return int(getattr(element_id, attr))
        except Exception:
            pass
    try:
        return int(str(element_id))
    except Exception:
        return None


def get_instance_family_name(instance):
    if instance is None:
        return ""
    try:
        return safe_family_name(instance.Symbol)
    except Exception:
        return ""


def normalize_angle(angle):
    try:
        angle = float(angle)
    except Exception:
        return None
    angle = angle % 360.0
    if angle < 0:
        angle += 360.0
    return angle


def normalize_line_angle(angle):
    angle = normalize_angle(angle)
    if angle is None:
        return None
    angle = angle % 180.0
    if abs(angle - 180.0) < 1e-6 or abs(angle) < 1e-6:
        return 0.0
    return angle


def tracing_to_revit_angle(orientation_angle):
    folded = normalize_line_angle(orientation_angle)
    if folded is None:
        return None
    return normalize_line_angle(folded + 90.0)


def get_json_angle(item):
    if not USE_JSON_ANGLE:
        return None

    for key in ("revit_angle", "angle", "orientation_angle"):
        value = item.get(key, None)
        if value is None:
            continue
        try:
            angle = float(value)
        except Exception:
            continue
        if key == "orientation_angle":
            angle = tracing_to_revit_angle(angle)
        else:
            angle = normalize_angle(angle)
        if angle is None:
            continue
        return normalize_angle(angle * ANGLE_SIGN + ANGLE_OFFSET_DEG)
    return None


def get_orientation(item):
    orientation = str(item.get("orientation", "")).upper().strip()
    json_angle = get_json_angle(item)
    if json_angle is not None:
        source = item.get("orientation_source", "JSON angle")
        return (
            orientation if orientation else "ANGLE",
            json_angle,
            source,
        )
    if orientation == "HORIZONTAL":
        return ("HORIZONTAL", normalize_angle(HORIZONTAL_FALLBACK_DEG), "fallback")
    if orientation == "VERTICAL":
        return ("VERTICAL", normalize_angle(VERTICAL_FALLBACK_DEG), "fallback")
    return (
        orientation if orientation else "UNKNOWN",
        normalize_angle(VERTICAL_FALLBACK_DEG),
        "fallback",
    )


def names_match(left, right):
    return (
        re.sub(r"[^A-Z0-9]+", "", str(left or "").upper())
        ==
        re.sub(r"[^A-Z0-9]+", "", str(right or "").upper())
    )


def classify_revit_name(name):
    text = str(name or "").strip().lower()
    if not text:
        return "neutral"
    if "overlay" in text:
        return "overlay"
    if "existing" in text and "proposed" in text:
        return "overlay"
    if "proposed" in text or "selling floor" in text or "selling-floor" in text:
        return "proposed"
    if "exist" in text or "as-built" in text or "as built" in text:
        return "existing"
    return "neutral"


def is_proposed_scope(name):
    return classify_revit_name(name) in ("proposed", "overlay")


def choose_existing_level_name(level_names, preferred=""):
    names = [str(name) for name in level_names if name]
    preferred_l = str(preferred or "").strip().lower()

    def allowed(name):
        return classify_revit_name(name) not in ("proposed", "overlay")

    for name in names:
        if name.strip().lower() == preferred_l and allowed(name):
            return name
    for name in names:
        if classify_revit_name(name) == "existing" and "ground" in name.lower():
            return name
    for name in names:
        if classify_revit_name(name) == "existing":
            return name
    return None


def choose_existing_view_name(views, level_name):
    ranked = []
    for view_name, view_level in views:
        if str(view_level) != str(level_name):
            continue
        scope = classify_revit_name(view_name)
        if scope in ("proposed", "overlay"):
            continue
        ranked.append((scope, str(view_name)))
    for scope, view_name in ranked:
        if scope == "existing" and "condition" in view_name.lower():
            return view_name
    for scope, view_name in ranked:
        if scope == "existing":
            return view_name
    return None


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def load_gondola_items(data):
    """Accept {gondolas: [...]} or a bare list from older detector runs."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("gondolas", "items", "data"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


if not os.path.isfile(JSON_PATH):
    OUT = "JSON NOT FOUND:\n\n{}".format(JSON_PATH)
    raise FileNotFoundError(OUT)

json_size = os.path.getsize(JSON_PATH)
with open(JSON_PATH, "r") as handle:
    data = json.load(handle)

gondolas = load_gondola_items(data)
if isinstance(data, dict):
    json_keys = ", ".join(sorted(str(key) for key in data.keys()))
    json_reported_total = data.get("total", "n/a")
else:
    json_keys = "(top-level list)"
    json_reported_total = len(gondolas)

doc = DocumentManager.Instance.CurrentDBDocument
if doc is None:
    raise Exception("Could not obtain current Revit document.")


# ---------------------------------------------------------------------------
# CAD import — prefer the Existing Conditions link
# ---------------------------------------------------------------------------

cad_offset_x = 0.0
cad_offset_y = 0.0
cad_rotation_rad = 0.0
cad_offset_info = "No CAD transform found. Using origin (0,0)."
all_cad_found = []
all_imports = list(FilteredElementCollector(doc).OfClass(ImportInstance))
selected_import = None
preferred_import = None

for imp in all_imports:
    try:
        sym = doc.GetElement(imp.GetTypeId())
        cad_name_str = ""
        try:
            param = sym.get_Parameter(BuiltInParameter.IMPORT_SYMBOL_NAME)
            if param is not None:
                cad_name_str = param.AsString() or ""
        except Exception:
            pass
        if not cad_name_str:
            cad_name_str = safe_element_name(sym)
        if not cad_name_str:
            continue

        transform = imp.GetTotalTransform()
        origin = transform.Origin
        ox = origin.X
        oy = origin.Y
        bx = transform.BasisX
        cad_angle = math.atan2(bx.Y, bx.X)
        try:
            link_type = "Link" if imp.IsLinked else "Import"
        except Exception:
            link_type = "Import"

        all_cad_found.append(
            "    [{}] {} | offset=({:.0f},{:.0f}) mm | rotation={:.3f}°".format(
                link_type,
                cad_name_str,
                ox * 304.8,
                oy * 304.8,
                math.degrees(cad_angle),
            )
        )

        if CAD_LINK_NAME and CAD_LINK_NAME.lower() not in cad_name_str.lower():
            continue

        if EXISTING_ONLY and is_proposed_scope(cad_name_str):
            continue

        cad_offset_info_text = (
            "[{}] {} | offset=({:.3f},{:.3f}) ft "
            "= ({:.0f},{:.0f}) mm | rotation={:.3f}°"
        ).format(
            link_type, cad_name_str, ox, oy,
            ox * 304.8, oy * 304.8, math.degrees(cad_angle),
        )

        if selected_import is None:
            selected_import = imp
            cad_offset_x = ox
            cad_offset_y = oy
            cad_rotation_rad = cad_angle
            cad_offset_info = cad_offset_info_text

        if (
            preferred_import is None
            and classify_revit_name(cad_name_str) == "existing"
        ):
            preferred_import = imp
            cad_offset_x = ox
            cad_offset_y = oy
            cad_rotation_rad = cad_angle
            selected_import = imp
            cad_offset_info = cad_offset_info_text
    except Exception as ex:
        all_cad_found.append("    CAD ERROR: {}".format(str(ex)))


# ---------------------------------------------------------------------------
# Family symbols — case-insensitive lookup
# ---------------------------------------------------------------------------

all_symbols = list(FilteredElementCollector(doc).OfClass(FamilySymbol))
symbol_lookup = {}
symbol_lookup_norm = {}
symbol_errors = []

for symbol in all_symbols:
    try:
        family_name = safe_family_name(symbol)
        type_name = safe_symbol_name(symbol)
        if family_name and type_name:
            symbol_lookup[(family_name, type_name)] = symbol
            symbol_lookup_norm[(family_name.upper(), type_name.upper())] = symbol
    except Exception as ex:
        symbol_errors.append(str(ex))


def resolve_symbol(family_name, type_name):
    if (family_name, type_name) in symbol_lookup:
        return symbol_lookup[(family_name, type_name)], family_name, type_name

    key = (family_name.upper(), type_name.upper())
    if key in symbol_lookup_norm:
        symbol = symbol_lookup_norm[key]
        return symbol, safe_family_name(symbol), safe_symbol_name(symbol)

    for (fname, tname), symbol in symbol_lookup.items():
        if names_match(fname, family_name) and names_match(tname, type_name):
            return symbol, fname, tname
    return None, family_name, type_name


def resolve_mapping(code):
    mapping = TYPE_MAP_NORM.get(code)
    used_fallback = False
    if mapping is None:
        return None, False
    symbol, fname, tname = resolve_symbol(*mapping)
    if symbol is not None:
        return (symbol, fname, tname), False
    fallback = FALLBACK_NORM.get(code)
    if fallback is not None:
        symbol, fname, tname = resolve_symbol(*fallback)
        if symbol is not None:
            return (symbol, fname, tname), True
    return None, False


missing = []
for code, mapping in sorted(TYPE_MAP_NORM.items()):
    resolved, _ = resolve_mapping(code)
    if resolved is None:
        missing.append("  {} → {} / {}".format(code, mapping[0], mapping[1]))


# ---------------------------------------------------------------------------
# Level / view — Existing only. Never Proposed or overlay.
# ---------------------------------------------------------------------------

all_levels = list(FilteredElementCollector(doc).OfClass(Level))
level_map = {}
for level in all_levels:
    try:
        if level.Name:
            level_map[str(level.Name)] = level
    except Exception:
        pass

if EXISTING_ONLY and is_proposed_scope(LEVEL_NAME):
    raise Exception(
        "LEVEL_NAME '{}' is a Proposed / overlay level.\n"
        "Tracing must be placed on an Existing level only.\n\n"
        "Available levels:\n{}".format(
            LEVEL_NAME,
            "\n".join("  " + name for name in sorted(level_map.keys())),
        )
    )

chosen_level_name = choose_existing_level_name(level_map.keys(), LEVEL_NAME)
target_level = level_map.get(chosen_level_name) if chosen_level_name else None

if target_level is None:
    raise Exception(
        "No Existing level found. Tracing will not use a Proposed level.\n"
        "Set LEVEL_NAME to an Existing level.\n\n"
        "Available levels:\n{}".format(
            "\n".join("  " + name for name in sorted(level_map.keys()))
        )
    )

if EXISTING_ONLY and is_proposed_scope(target_level.Name):
    raise Exception(
        "Refusing to place on '{}'. Existing-only tracing is enabled.".format(
            target_level.Name
        )
    )

all_views = list(FilteredElementCollector(doc).OfClass(ViewPlan))
view_records = []
view_by_name = {}
for view in all_views:
    try:
        if view.GenLevel is None:
            continue
        view_records.append((str(view.Name), str(view.GenLevel.Name)))
        view_by_name[str(view.Name)] = view
    except Exception:
        pass

chosen_view_name = choose_existing_view_name(view_records, target_level.Name)
target_view = view_by_name.get(chosen_view_name) if chosen_view_name else None

if target_view is not None and EXISTING_ONLY and is_proposed_scope(target_view.Name):
    target_view = None

level_override_info = (
    "Existing only. Level='{}'. View='{}'".format(
        target_level.Name,
        target_view.Name if target_view is not None else "none (no Existing view)",
    )
)


# ---------------------------------------------------------------------------
# Graphics / phase
# ---------------------------------------------------------------------------

BLUE = Color(0, 102, 204)
color_override = OverrideGraphicSettings()
try:
    color_override.SetProjectionLineColor(BLUE)
except Exception:
    pass
try:
    color_override.SetSurfaceForegroundPatternColor(BLUE)
    color_override.SetSurfaceForegroundPatternVisible(True)
except Exception:
    pass

all_phases = list(FilteredElementCollector(doc).OfClass(Phase))
existing_phase = None
for phase in all_phases:
    try:
        name = str(phase.Name).lower()
        if name in ("existing", "existing construction", "as-built"):
            existing_phase = phase
            break
    except Exception:
        pass
if existing_phase is None and all_phases:
    existing_phase = all_phases[0]
phase_info = existing_phase.Name if existing_phase else "not set"


# ---------------------------------------------------------------------------
# Transaction — never delete existing families when the JSON is empty
# ---------------------------------------------------------------------------

MANAGED_FAMILIES = {
    "Floor_Gondola",
    "Floor_Gondola_High_Bay",
    "Floor_Gondola_High_Bay-Half_Bay",
    "Wall_Gondola",
    "Wall_Gondola_High_Bay",
    "End_Panel_Decks",
    "Decks_&_Hopper",
    "End_Panel",
    "Floor_Gondola_Queuing",
    "Hotspots",
}

deleted_count = 0
placed = []
skipped = []
wall_placed = []
orientation_report = []
used_fallback = []

if not gondolas:
    skipped.append(
        "JSON is empty (0 gondolas). Nothing was placed or deleted. "
        "Re-run Gondola_OrientationDetector.py {} on the Existing "
        "Conditions DXF, then run this Dynamo script again.".format(SCRIPT_VERSION)
    )
else:
    t = Transaction(doc, "Place Existing Conditions Gondolas")
    t.Start()

    all_instances = list(
        FilteredElementCollector(doc).OfClass(FamilyInstance).ToElements()
    )
    for inst in all_instances:
        try:
            family_name = get_instance_family_name(inst)
            if family_name not in MANAGED_FAMILIES:
                continue
            lv_param = None
            try:
                lv_param = inst.get_Parameter(BuiltInParameter.FAMILY_LEVEL_PARAM)
            except Exception:
                pass
            if lv_param is None:
                try:
                    lv_param = inst.get_Parameter(
                        BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM
                    )
                except Exception:
                    pass
            if lv_param is not None:
                try:
                    if lv_param.AsElementId() != target_level.Id:
                        continue
                except Exception:
                    continue
            if existing_phase is not None:
                try:
                    ph_param = inst.get_Parameter(BuiltInParameter.PHASE_CREATED)
                    if ph_param is not None:
                        if ph_param.AsElementId() != existing_phase.Id:
                            continue
                except Exception:
                    pass
            doc.Delete(inst.Id)
            deleted_count += 1
        except Exception:
            pass

    doc.Regenerate()

    activated = set()
    for code in TYPE_MAP_NORM:
        resolved, _ = resolve_mapping(code)
        if resolved is None:
            continue
        symbol, fname, tname = resolved
        key = (fname, tname)
        try:
            if not symbol.IsActive and key not in activated:
                symbol.Activate()
                activated.add(key)
        except Exception:
            pass

    doc.Regenerate()

    for item in gondolas:
        try:
            code = normalize_lookup_key(item.get("code", ""))
            if code not in TYPE_MAP_NORM:
                skipped.append("UNKNOWN CODE: {}".format(code))
                continue

            resolved, fallback = resolve_mapping(code)
            if resolved is None:
                fname, tname = TYPE_MAP_NORM[code]
                skipped.append(
                    "MISSING TYPE: {} → {} / {}".format(code, fname, tname)
                )
                continue

            symbol, fname, tname = resolved
            if fallback:
                used_fallback.append(
                    "{} placed as {} / {}".format(code, fname, tname)
                )

            x_mm = float(item.get("x", 0))
            y_mm = float(item.get("y", 0))
            x_local_ft = x_mm * MM_TO_FT
            y_local_ft = y_mm * MM_TO_FT

            if APPLY_CAD_ROTATION:
                cos_a = math.cos(cad_rotation_rad)
                sin_a = math.sin(cad_rotation_rad)
                x_rot = x_local_ft * cos_a - y_local_ft * sin_a
                y_rot = x_local_ft * sin_a + y_local_ft * cos_a
            else:
                x_rot = x_local_ft
                y_rot = y_local_ft

            if APPLY_CAD_TRANSLATION:
                x_ft = x_rot + cad_offset_x
                y_ft = y_rot + cad_offset_y
            else:
                x_ft = x_rot
                y_ft = y_rot

            z_ft = target_level.Elevation
            point = XYZ(x_ft, y_ft, z_ft)

            instance = doc.Create.NewFamilyInstance(
                point,
                symbol,
                target_level,
                StructuralType.NonStructural,
            )

            if existing_phase is not None:
                try:
                    p_created = instance.get_Parameter(BuiltInParameter.PHASE_CREATED)
                    if p_created is not None and not p_created.IsReadOnly:
                        p_created.Set(existing_phase.Id)
                except Exception:
                    pass

            if target_view is not None:
                try:
                    target_view.SetElementOverrides(instance.Id, color_override)
                except Exception:
                    pass

            orientation, angle_deg, angle_source = get_orientation(item)
            if APPLY_CAD_ROTATION and angle_deg is not None:
                angle_deg = normalize_angle(
                    angle_deg + math.degrees(cad_rotation_rad)
                )

            if angle_deg is not None and abs(angle_deg) > 0.0001:
                axis = Line.CreateBound(
                    point,
                    XYZ(point.X, point.Y, point.Z + 1.0),
                )
                ElementTransformUtils.RotateElement(
                    doc,
                    instance.Id,
                    axis,
                    math.radians(angle_deg),
                )

            placed.append(
                "{:<24} @ ({:>9.0f}, {:>9.0f}) mm angle={:>8.3f}° {}".format(
                    code,
                    x_mm,
                    y_mm,
                    angle_deg if angle_deg is not None else 0.0,
                    angle_source,
                )
            )
            orientation_report.append(
                "{} | orientation={} | angle={:.3f}° | source={}".format(
                    code,
                    orientation,
                    angle_deg if angle_deg is not None else 0.0,
                    angle_source,
                )
            )

            if fname in ("Wall_Gondola", "Wall_Gondola_High_Bay"):
                wall_placed.append(
                    "{:<24} @ ({:>9.0f}, {:>9.0f}) mm angle={:>8.3f}° id={}".format(
                        code,
                        x_mm,
                        y_mm,
                        angle_deg if angle_deg is not None else 0.0,
                        safe_element_id_value(instance.Id),
                    )
                )
        except Exception as ex:
            skipped.append("ERROR {} :: {}".format(item.get("code", "?"), str(ex)))

    t.Commit()


sep = "=" * 75
lines = [
    "",
    sep,
    " EXISTING CONDITIONS — GONDOLA PLACEMENT",
    sep,
    "",
    "Script version         : {}".format(SCRIPT_VERSION),
    "JSON path              : {}".format(JSON_PATH),
    "JSON file size         : {} bytes".format(json_size),
    "JSON keys              : {}".format(json_keys),
    "JSON reported total    : {}".format(json_reported_total),
    "Total JSON items       : {}".format(len(gondolas)),
    "Placed                 : {}".format(len(placed)),
    "Skipped                : {}".format(len(skipped)),
    "Deleted previous       : {}".format(deleted_count),
    "",
    "LEVEL",
    "  Existing only        : {}".format(EXISTING_ONLY),
    "  Level used           : {}".format(target_level.Name),
    "  Elevation            : {:.3f} ft".format(target_level.Elevation),
    "  Level note           : {}".format(level_override_info),
    "",
    "PHASE",
    "  Phase used           : {}".format(phase_info),
    "",
    "CAD TRANSFORM",
    "  {}".format(cad_offset_info),
    "",
    "ORIENTATION",
    "  JSON angle enabled   : {}".format(USE_JSON_ANGLE),
    "  Angle sign           : {}".format(ANGLE_SIGN),
    "  Angle offset         : {:.3f}°".format(ANGLE_OFFSET_DEG),
    "  CAD rotation applied : {}".format(APPLY_CAD_ROTATION),
    "",
    "ALL CAD IMPORTS:",
]
if all_cad_found:
    lines.extend(all_cad_found)
else:
    lines.append("    NONE FOUND")

lines.extend(["", "ORIENTATION USED FOR EACH ITEM:"])
if orientation_report:
    lines.extend(["    " + row for row in orientation_report])
else:
    lines.append("    NONE")

if wall_placed:
    lines.extend(["", "WALL GONDOLAS PLACED: {}".format(len(wall_placed))])
    lines.extend(["    " + row for row in wall_placed])

if used_fallback:
    lines.extend(["", "PLACED WITH FALLBACK TYPE: {}".format(len(used_fallback))])
    lines.extend(["    " + row for row in used_fallback])

if missing:
    lines.extend(["", "MISSING REVIT TYPES:"])
    lines.extend(["    " + row for row in missing])

if symbol_errors:
    lines.extend(["", "SYMBOL LOOKUP WARNINGS:"])
    lines.extend(["    " + row for row in symbol_errors])

if skipped:
    lines.extend(["", "SKIPPED / ERRORS:"])
    lines.extend(["    " + row for row in skipped])

lines.extend(["", "PLACED GONDOLAS:"])
lines.extend(["    " + row for row in placed])
lines.extend(["", sep, ""])

OUT = "\n".join(lines)

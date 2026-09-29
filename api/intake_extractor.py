"""
Structured intake extraction for the HMIS vitals integration.

Turns a free-form dictated intake (typically a browser speech-to-text
transcript) into:

  - vital signs, keyed by the HMIS POST /vitals field names,
  - presenting complaints, mapped onto the controlled symptom vocabulary
    (symptoms_dictionary/symptom_vocabulary.md) so they rhyme with the graph,
  - how long the patient has been unwell.

Deterministic on purpose. Numbers that land in a patient record must come
from what was said, never from a model's guess (the same principle as
prompts.py Rule 4 — do not manufacture missing information). Every extracted
value carries the span of `normalized_transcript` it was read from, so the
clinician can see exactly where each prefilled value came from before saving.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).parent.parent
VOCAB_PATH = ROOT / "symptoms_dictionary" / "symptom_vocabulary.md"

# ── Spoken numbers → digits ───────────────────────────────────────────────────
# Speech engines usually emit digits, but not always: "pain score six",
# "thirty eight point five", "one twenty over eighty".

_UNITS = {w: i for i, w in enumerate(
    ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"])}
_TEENS = {w: i + 10 for i, w in enumerate(
    ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
     "seventeen", "eighteen", "nineteen"])}
_TENS = {w: (i + 2) * 10 for i, w in enumerate(
    ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"])}
_NUMBER_WORDS = set(_UNITS) | set(_TEENS) | set(_TENS) | {"hundred"}

_TOKEN_RE = re.compile(r"[A-Za-z]+|[^A-Za-z]+")
_SEPARATOR_RE = re.compile(r"[ \t-]+")


def _read_number(words: list[str]) -> tuple[int, int]:
    """Value of the leading number phrase in `words`, and how many words it used."""
    value, state, used = 0, "start", 0
    for w in words:
        if w == "and":
            if state != "hundred":
                break
            used += 1
            continue
        if w in _UNITS:
            if state not in ("start", "hundred", "tens"):
                break
            value += _UNITS[w]
            state = "unit"
        elif w in _TEENS or w in _TENS:
            n = _TEENS[w] if w in _TEENS else _TENS[w]
            if state in ("start", "hundred"):
                value += n
            elif state == "unit" and value < 10:
                # "one twenty" — spoken shorthand for 120.
                value = value * 100 + n
            else:
                break
            state = "teen" if w in _TEENS else "tens"
        elif w == "hundred":
            if state not in ("start", "unit"):
                break
            value = max(value, 1) * 100
            state = "hundred"
        used += 1
    if used and words[used - 1] == "and":
        used -= 1
    return value, used


def _previous_word(out: list[str]) -> Optional[str]:
    for tok in reversed(out):
        if tok.strip():
            return tok.lower() if tok.isalpha() else None
    return None


def _spoken_numbers_to_digits(text: str) -> str:
    tokens = _TOKEN_RE.findall(text)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        if tokens[i].lower() not in _NUMBER_WORDS:
            out.append(tokens[i])
            i += 1
            continue
        idxs = [i]
        j = i
        while (j + 2 < len(tokens)
               and _SEPARATOR_RE.fullmatch(tokens[j + 1])
               and tokens[j + 2].lower() in _NUMBER_WORDS | {"and"}):
            j += 2
            idxs.append(j)
        words = [tokens[k].lower() for k in idxs]
        value, used = _read_number(words)
        # A lone "one" is usually a pronoun ("no one", "one of"), not a reading.
        if used == 1 and words[0] == "one" and _previous_word(out) != "point":
            out.append(tokens[i])
            i += 1
            continue
        out.append(str(value))
        i = idxs[used - 1] + 1
    return "".join(out)


# ── Normalisation ─────────────────────────────────────────────────────────────

_REWRITES: list[tuple[str, str]] = [
    (r"\b(?:um+|uh+|erm+)\b,?\s*", ""),
    (r"(\d+)\s+point\s+(\d+(?:\s+\d(?!\d))*)", lambda m: f"{m[1]}.{m[2].replace(' ', '')}"),
    (r"\b(\d{2,3})\s*(?:over|by|/)\s*(\d{2,3})\b", r"\1/\2"),
    (r"(\d)\s*(?:per\s*cent|percent)\b", r"\1%"),
    (r"(\d)\s*(?:degrees?|°)\s*(?:celsius|centigrade|c)\b", r"\1°C"),
    (r"(\d)\s*(?:degrees?|°)\s*(?:fahrenheit|f)\b", r"\1°F"),
    (r"(\d)\s*(?:celsius|centigrade)\b", r"\1°C"),
    (r"(\d)\s*fahrenheit\b", r"\1°F"),
    (r"(\d)\s*degrees?\b", r"\1°"),
    (r"\bs\.?\s*p\.?\s*o\.?\s*2\b", "SpO2"),
    (r"\bb\.\s*p\.|\bb\s+p\b|\bbp\b", "BP"),
    (r"\bm\s*u\s*a\s*c\b", "MUAC"),
    (r"(\d)\s*(?:kilograms?|kilos?|kgs)\b", r"\1 kg"),
    (r"(\d)\s*(?:grams?|gms?)\b", r"\1 g"),
    (r"(\d)\s*(?:centimet(?:er|re)s?|cms)\b", r"\1 cm"),
    (r"(\d)\s*(?:millimet(?:er|re)s?\s+(?:of\s+)?mercury|mm\s*hg)\b", r"\1 mmHg"),
    (r"(\d)\s*(?:millimet(?:er|re)s?)\b", r"\1 mm"),
    (r"(\d)\s*(?:millimoles?|mmols?)(?:\s*(?:per|/)\s*(?:lit(?:re|er)|l)\b)?", r"\1 mmol/L"),
    (r"(\d)\s*(?:milligrams?|mg)\s*(?:per|/)\s*(?:decilit(?:re|er)|dl)\b", r"\1 mg/dL"),
    (r"\bbeats?\s+(?:per|a|/)\s*min(?:ute)?\b", "bpm"),
    (r"\bbreaths?\s+(?:per|a|/)\s*min(?:ute)?\b", "breaths/min"),
    (r"(\d)\s*(?:pounds?|lbs?)\b", r"\1 lb"),
    (r"(\d)\s*(?:feet|foot)\b", r"\1 ft"),
    (r"(\d)\s*(?:inch(?:es)?)\b", r"\1 in"),
    (r"(\d)\s*(?:met(?:er|re)s?)\b", r"\1 m"),
    (r"[ \t]{2,}", " "),
]
_COMPILED_REWRITES = [(re.compile(p, re.IGNORECASE), r) for p, r in _REWRITES]


def normalize_transcript(text: str) -> str:
    """Canonical spelling of numbers and units, so extraction has one form to read."""
    out = _spoken_numbers_to_digits(text.strip())
    for pattern, repl in _COMPILED_REWRITES:
        out = pattern.sub(repl, out)
    return out.strip()


# ── Vital signs ───────────────────────────────────────────────────────────────

# Words allowed between a vital's name and its reading: "temperature of 38.5",
# "BP was 150/95", "sats: 94". Deliberately a closed list — an open gap would
# let "temperature normal, pulse 110" bind 110 to the temperature.
_FILL = (r"(?:[\s,:=\-]+|\b(?:is|was|were|are|of|at|about|around|approximately|roughly|"
         r"reading|reads|measured|recorded|taken|noted|now|currently|today|high|low|"
         r"elevated|raised|slightly|found\s+to\s+be)\b)*")

FIELD_LABELS = {
    "temperature": "Temperature",
    "temperature_location": "Temperature site",
    "systolic_bp": "Systolic BP",
    "diastolic_bp": "Diastolic BP",
    "pulse": "Pulse",
    "respiratory_rate": "Respiratory rate",
    "oxygen_saturation": "SpO₂",
    "weight": "Weight",
    "height": "Height",
    "random_blood_sugar": "Random blood sugar",
    "fasting_blood_sugar": "Fasting blood sugar",
    "blood_sugar_unit": "Blood sugar unit",
    "pain_score": "Pain score",
    "pain_location": "Pain location",
    "muac": "MUAC",
    "head_circumference": "Head circumference",
}


class _Implausible(Exception):
    """A reading was heard but is outside anything physiologically possible."""


@dataclass
class Reading:
    field: str
    value: float | int | str
    unit: Optional[str]
    evidence: str
    span: tuple[int, int]
    confidence: str  # high = named and unit-confirmed, medium = named or unit only, low = inferred
    note: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "label": FIELD_LABELS.get(self.field, self.field),
            "value": self.value,
            "unit": self.unit,
            "evidence": self.evidence,
            "span": list(self.span),
            "confidence": self.confidence,
            "note": self.note,
        }


# A parser turns a match into [(field, value, unit, note)]; None means "not a
# reading after all" (skip silently), _Implausible means "heard, but impossible".
Parsed = Optional[list[tuple[str, float | int | str, Optional[str], Optional[str]]]]


def _num(s: str) -> float:
    return float(s)


def _round(v: float, places: int = 1) -> float | int:
    r = round(v, places)
    return int(r) if r == int(r) else r


def _in_range(label: str, v: float, lo: float, hi: float, unit: str = "") -> float:
    if not lo <= v <= hi:
        raise _Implausible(f"Heard {label} {_round(v)}{unit} — outside the plausible range, ignored.")
    return v


def _parse_bp(m: re.Match) -> Parsed:
    s, d = int(m["s"]), int(m["d"])
    if d == 10:  # "8/10" style pain scores
        return None
    _in_range("systolic BP", s, 40, 300)
    _in_range("diastolic BP", d, 20, 200)
    if s <= d:
        raise _Implausible(f"Heard BP {s}/{d} — systolic must exceed diastolic, ignored.")
    return [("systolic_bp", s, "mmHg", None), ("diastolic_bp", d, "mmHg", None)]


def _parse_bare_bp(m: re.Match) -> Parsed:
    if not (70 <= int(m["s"]) <= 250 and 40 <= int(m["d"]) <= 150):
        return None
    return _parse_bp(m)


def _parse_temperature(m: re.Match) -> Parsed:
    v = _num(m["v"])
    unit = (m.groupdict().get("u") or "").upper()
    note = None
    if unit.endswith("F") or (unit in ("", "°") and 77 <= v <= 113):
        v = (v - 32) * 5 / 9
        note = f"Converted from {m['v']} °F."
    _in_range("temperature", v, 25, 45, " °C")
    return [("temperature", _round(v), "°C", note)]


def _parse_int(field: str, label: str, lo: int, hi: int, unit: str) -> Callable[[re.Match], Parsed]:
    def parse(m: re.Match) -> Parsed:
        v = _num(m["v"])
        _in_range(label, v, lo, hi)
        return [(field, int(round(v)), unit, None)]
    return parse


def _parse_weight(m: re.Match) -> Parsed:
    v, unit, note = _num(m["v"]), (m.groupdict().get("u") or "").lower(), None
    if unit == "lb":
        v, note = v * 0.45359237, f"Converted from {m['v']} lb."
    elif unit == "g":
        v, note = v / 1000, f"Converted from {m['v']} g."
    _in_range("weight", v, 0.3, 400, " kg")
    return [("weight", _round(v), "kg", note)]


def _parse_height(m: re.Match) -> Parsed:
    gd = m.groupdict()
    if gd.get("ft"):
        inches = int(gd["ft"]) * 12 + int(gd.get("inch") or 0)
        cm, note = inches * 2.54, f"Converted from {gd['ft']} ft {gd.get('inch') or 0} in."
    else:
        v, unit, note = _num(gd["v"]), (gd.get("u") or "").lower(), None
        if unit == "mm":
            cm = v / 10
        elif unit == "m" or (not unit and v < 3):
            cm = v * 100
        elif not unit and v < 30:
            raise _Implausible(f"Heard height {gd['v']} with no unit — too ambiguous to use.")
        else:
            cm = v
    _in_range("height", cm, 30, 250, " cm")
    return [("height", _round(cm), "cm", note)]


def _parse_sugar(m: re.Match) -> Parsed:
    v = _num(m["v"])
    fasting = bool(re.search(r"fasting|fbs", m.group(0), re.IGNORECASE))
    field = "fasting_blood_sugar" if fasting else "random_blood_sugar"
    unit, note = m.groupdict().get("u"), None
    if unit:
        unit = "mg/dL" if unit.lower().startswith("mg") else "mmol/L"
    else:
        unit = "mg/dL" if v > 35 else "mmol/L"
        note = f"Unit not said — {unit} inferred from the value."
    if unit == "mmol/L":
        _in_range("blood sugar", v, 0.5, 50, " mmol/L")
    else:
        _in_range("blood sugar", v, 10, 900, " mg/dL")
    return [(field, _round(v), unit, note), ("blood_sugar_unit", unit, None, note)]


def _parse_pain(m: re.Match) -> Parsed:
    scored = m.groupdict().get("den") or re.search(
        r"score|scale|level|rating|intensity|severity|rates?", m.group(0), re.IGNORECASE)
    if not scored:
        return None
    v = int(m["v"])
    _in_range("pain score", v, 0, 10)
    return [("pain_score", v, "/10", None)]


def _parse_bare_pain(m: re.Match) -> Parsed:
    before = m.string[max(0, m.start() - 80):m.start()]
    if not re.search(r"\bpain|\bache|\bhurts?", before, re.IGNORECASE):
        return None
    v = int(m["v"])
    _in_range("pain score", v, 0, 10)
    return [("pain_score", v, "/10", None)]


def _parse_circumference(field: str, label: str, lo: float, hi: float) -> Callable[[re.Match], Parsed]:
    def parse(m: re.Match) -> Parsed:
        v, unit, note = _num(m["v"]), (m.groupdict().get("u") or "").lower(), None
        if unit == "mm" or (not unit and v > hi):
            v, note = v / 10, f"Converted from {m['v']} mm."
        _in_range(label, v, lo, hi, " cm")
        return [(field, _round(v), "cm", note)]
    return parse


_N = r"(?P<v>\d{1,4}(?:\.\d+)?)"
_END = r"(?![\d./])"

# (spec name, [(pattern, confidence[, tier parser])], parser). Tiers run in
# order across all specs — every named reading claims its numbers before any
# unit-only fallback looks, so a fallback never steals a number a named vital owns.
_SPECS: list[tuple[str, list[tuple], Callable[[re.Match], Parsed]]] = [
    ("pain_score", [
        (r"\b(?:rates?\s+(?:his|her|their|the|my)?\s*pain(?:\s+(?:at|as))?|pain(?:\s+(?:score|scale|level|rating|intensity|severity))?)"
         + _FILL + r"(?P<v>\d{1,2})(?P<den>\s*(?:/|out\s+of)\s*10)?\b", "high"),
        (r"(?<![\d/])(?P<v>\d{1,2})\s*(?:/|out\s+of)\s*10\b", "medium", _parse_bare_pain),
    ], _parse_pain),
    ("blood_pressure", [
        (r"\b(?:blood\s+pressure|BP|pressure)" + _FILL
         + r"(?P<v>(?P<s>\d{2,3})\s*/\s*(?P<d>\d{2,3}))(?:\s*mmHg)?", "high"),
        (r"(?<![\d/])(?P<v>(?P<s>\d{2,3})/(?P<d>\d{2,3}))\s*mmHg", "medium"),
        (r"(?<![\d/.])(?P<v>(?P<s>\d{2,3})/(?P<d>\d{2,3}))(?![\d/])", "low", _parse_bare_bp),
    ], _parse_bp),
    ("temperature", [
        (r"\b(?:temperature|temp|febrile|pyrexial)\b" + _FILL
         + r"(?P<v>\d{2,3}(?:\.\d+)?)\s*(?P<u>°C|°F|°|C\b|F\b)?", "high"),
        (r"(?P<v>\d{2,3}(?:\.\d+)?)\s*(?P<u>°C|°F|°)", "medium"),
    ], _parse_temperature),
    ("pulse", [
        (r"\b(?:pulse(?!\s*ox)(?:\s+rate)?|heart\s+rate|HR|PR|tachycardic|bradycardic)\b" + _FILL
         + r"(?P<v>\d{2,3})" + _END + r"(?:\s*bpm)?", "high"),
        (r"(?P<v>\d{2,3})\s*bpm", "medium"),
    ], _parse_int("pulse", "pulse", 20, 250, "bpm")),
    ("respiratory_rate", [
        (r"\b(?:respiratory\s+rate|resp(?:iratory|irations?)?(?:\s+rate)?|RR|breathing\s+rate|"
         r"breathing\s+at|tachypn(?:o)?eic)\b" + _FILL + r"(?P<v>\d{1,2})" + _END + r"(?:\s*breaths/min)?", "high"),
        (r"(?P<v>\d{1,2})\s*breaths/min", "medium"),
    ], _parse_int("respiratory_rate", "respiratory rate", 4, 80, "breaths/min")),
    ("oxygen_saturation", [
        (r"\b(?:SpO2|oxygen\s+saturation|oxygen\s+sats?|O2\s+sats?|saturations?|saturating|sats?|"
         r"pulse\s*ox(?:imetry)?|O2|oxygen)\b" + _FILL + r"(?P<v>\d{2,3})" + _END + r"\s*%?", "high"),
        (r"(?P<v>\d{2,3})\s*%\s*(?:on\s+)?(?:room\s+air|RA\b|air\b|oxygen)", "medium"),
    ], _parse_int("oxygen_saturation", "SpO2", 40, 100, "%")),
    ("weight", [
        (r"\b(?:weight|weighs|weighing|weighed|wt)\b" + _FILL + _N + r"\s*(?P<u>kg|lb|g)?\b", "high"),
        (r"(?P<v>\d{1,3}(?:\.\d+)?)\s*(?P<u>kg)\b", "medium"),
    ], _parse_weight),
    ("muac", [
        (r"\b(?:MUAC|mid[\s-]*upper[\s-]*arm\s+circumference|arm\s+circumference)\b" + _FILL
         + r"(?P<v>\d{1,3}(?:\.\d+)?)\s*(?P<u>cm|mm)?", "high"),
    ], _parse_circumference("muac", "MUAC", 5, 50)),
    ("head_circumference", [
        (r"\b(?:head\s+circumference|occipito[\s-]*frontal\s+circumference|OFC|HC)\b" + _FILL
         + r"(?P<v>\d{1,3}(?:\.\d+)?)\s*(?P<u>cm|mm)?", "high"),
    ], _parse_circumference("head_circumference", "head circumference", 20, 70)),
    ("height", [
        (r"\b(?:height|ht|length)\b" + _FILL
         + r"(?:(?P<ft>\d)\s*ft(?:\s*(?P<inch>\d{1,2})(?:\s*in\b)?)?|(?P<v>\d{1,3}(?:\.\d+)?)\s*(?P<u>cm|m|mm)?\b)", "high"),
        (r"(?:(?P<ft>\d)\s*ft(?:\s*(?P<inch>\d{1,2})(?:\s*in\b)?)?|(?P<v>\d{1,3}(?:\.\d+)?)\s*(?P<u>cm|m))\s+tall\b", "medium"),
        (r"(?P<v>\d{2,3}(?:\.\d+)?)\s*(?P<u>cm)\b", "low"),
    ], _parse_height),
    ("blood_sugar", [
        (r"\b(?:(?:random|fasting|RBS|FBS)\s+)?(?:blood\s+(?:sugar|glucose)(?:\s+level)?|glucose|sugars?|RBS|FBS|GBS)\b"
         + _FILL + r"(?P<v>\d{1,3}(?:\.\d+)?)\s*(?P<u>mmol/L|mg/dL)?", "high"),
        (r"(?P<v>\d{1,3}(?:\.\d+)?)\s*(?P<u>mmol/L|mg/dL)", "medium"),
    ], _parse_sugar),
]

_TEMP_SITES = [
    (r"\b(?:oral(?:ly)?|by\s+mouth|in\s+the\s+mouth)\b", "oral"),
    (r"\b(?:axillary|axilla|armpit|under\s+the\s+arm)\b", "axillary"),
    (r"\b(?:rectal(?:ly)?)\b", "rectal"),
    (r"\b(?:tympanic|in\s+the\s+ear|ear)\b", "tympanic"),
    (r"\b(?:temporal|forehead)\b", "temporal"),
]

_BODY_SITES = (
    r"(?:(?:lower|upper|left|right|central|generali[sz]ed)\s+)?"
    r"(?:right\s+upper\s+quadrant|RUQ|epigastri(?:c|um)|suprapubic|abdomen|abdominal|stomach|belly|tummy|"
    r"chest|back|loin|flank|head|neck|throat|joints?|knees?|legs?|arms?|shoulders?|hips?|ears?|eyes?|"
    r"pelvi(?:s|c)|muscles?|teeth|tooth|calf|calves|feet|foot|hands?|body)"
)
_PAIN_WORDS = r"(?:pain|pains|ache|aches|aching|tenderness|discomfort)"
_PAIN_SITE_RES = [
    re.compile(rf"\b(?P<site>{_BODY_SITES})\s+{_PAIN_WORDS}\b", re.IGNORECASE),
    re.compile(rf"\b{_PAIN_WORDS}\s+(?:in|on|at|over|around|of)\s+(?:the\s+|his\s+|her\s+|their\s+|my\s+)?(?P<site>{_BODY_SITES})\b",
               re.IGNORECASE),
    re.compile(r"\b(?P<site>head|back|stomach|tooth|ear|belly)ache\b", re.IGNORECASE),
]
_SCORED_SITE_RE = re.compile(
    rf"\s*,?\s*(?:in|on|at|over|around)\s+(?:the\s+|his\s+|her\s+|their\s+|my\s+)?(?P<site>{_BODY_SITES})\b",
    re.IGNORECASE)
_SITE_CANON = {"abdominal": "abdomen", "stomach": "abdomen", "belly": "abdomen", "tummy": "abdomen",
               "epigastrium": "epigastric", "ruq": "right upper quadrant", "pelvic": "pelvis"}


def _canonical_site(raw: str) -> str:
    site = re.sub(r"\s+", " ", raw.lower())
    for word, canon in _SITE_CANON.items():
        site = re.sub(rf"\b{word}\b", canon, site)
    return site


class _VitalsReader:
    def __init__(self, text: str):
        self.text = text
        self.claimed: list[tuple[int, int]] = []
        self.readings: dict[str, Reading] = {}
        self.warnings: list[str] = []

    def _taken(self, span: tuple[int, int]) -> bool:
        return any(span[0] < e and s < span[1] for s, e in self.claimed)

    def run(self) -> None:
        found: set[str] = set()
        tiers = max(len(tiers) for _, tiers, _ in _SPECS)
        for tier in range(tiers):
            for name, patterns, parser in _SPECS:
                if name in found or tier >= len(patterns):
                    continue
                pattern, confidence, *override = patterns[tier]
                tier_parser = override[0] if override else parser
                if self._read(re.compile(pattern, re.IGNORECASE), confidence, tier_parser):
                    found.add(name)
        self._temperature_site()
        self._pain_location()

    def _read(self, pattern: re.Pattern, confidence: str, parser) -> bool:
        accepted: list[tuple[re.Match, list]] = []
        for m in pattern.finditer(self.text):
            value_span = m.span("v") if m.groupdict().get("v") is not None else m.span()
            if self._taken(value_span):
                continue
            try:
                parsed = parser(m)
            except _Implausible as exc:
                # An impossible named reading is worth telling the clinician
                # about; an impossible unit-only guess was probably never that
                # vital to begin with.
                if confidence != "low":
                    self.claimed.append(m.span())
                    self.warnings.append(str(exc))
                continue
            if parsed:
                self.claimed.append(m.span())
                accepted.append((m, parsed))
        if not accepted:
            return False
        heard = [p[0][1] for _, p in accepted]
        if len(set(map(str, heard))) > 1:
            label = FIELD_LABELS.get(accepted[0][1][0][0], accepted[0][1][0][0]).lower()
            self.warnings.append(
                f"Heard more than one {label} ({', '.join(map(str, heard))}) — kept the last one; please check it.")
        m, parsed = accepted[-1]  # later mentions are usually corrections
        for field, value, unit, note in parsed:
            self.readings[field] = Reading(field, value, unit, m.group(0).strip(), m.span(), confidence, note)
        return True

    def _temperature_site(self) -> None:
        temp = self.readings.get("temperature")
        if not temp:
            return
        lo, hi = max(0, temp.span[0] - 60), min(len(self.text), temp.span[1] + 60)
        window = self.text[lo:hi]
        for pattern, site in _TEMP_SITES:
            m = re.search(pattern, window, re.IGNORECASE)
            if m:
                span = (lo + m.start(), lo + m.end())
                self.readings["temperature_location"] = Reading(
                    "temperature_location", site, None, m.group(0), span, "medium")
                return

    def _pain_location(self) -> None:
        # The site said alongside the pain score is the one being scored —
        # "pain score 6 out of 10 in the lower back" — so it wins outright.
        score = self.readings.get("pain_score")
        if score:
            m = _SCORED_SITE_RE.match(self.text, score.span[1])
            if m:
                self.readings["pain_location"] = Reading(
                    "pain_location", _canonical_site(m["site"]), None,
                    m["site"], (m.start("site"), m.end("site")), "high")
                return
        sites: list[tuple[str, re.Match]] = []
        for pattern in _PAIN_SITE_RES:
            for m in pattern.finditer(self.text):
                site = _canonical_site(m["site"])
                if site != "body" and site not in (s for s, _ in sites):
                    sites.append((site, m))
        if not sites:
            return
        sites.sort(key=lambda s: s[1].start())
        first = sites[0][1]
        self.readings["pain_location"] = Reading(
            "pain_location", ", ".join(s for s, _ in sites[:3]), None,
            first.group(0), first.span(), "medium")


# ── Presenting complaints ─────────────────────────────────────────────────────

# Lay phrasing clinicians and patients actually say, folded onto canonical
# terms. Merged with symptom_vocabulary.md; the vocabulary wins on conflicts.
_LAY_TERMS: list[tuple[str, list[str]]] = [
    ("fever", ["febrile", "hotness of body", "feeling hot", "hot body"]),
    ("cough", ["coughing", "dry cough", "productive cough"]),
    ("diarrhoea", ["loose stools", "watery stools", "running stomach"]),
    ("abdominal pain", ["stomach ache", "stomachache", "tummy ache", "belly pain", "stomach pain"]),
    ("sore throat", ["throat pain", "painful throat"]),
    ("myalgia", ["body aches", "body pains", "aching body", "general body pains"]),
    ("arthralgia", ["joint pains", "painful joints", "aching joints"]),
    ("dizziness", ["dizzy", "light headed", "lightheaded", "vertigo"]),
    ("convulsions", ["seizures", "seizure", "fits"]),
    ("rash", ["skin rash"]),
    ("dyspnoea", ["difficulty breathing", "difficulty in breathing", "short of breath", "breathing difficulty"]),
    ("dysuria", ["painful urination", "burning urination", "burning on urination", "pain on passing urine",
                 "pain when urinating"]),
    ("urinary frequency", ["frequent urination", "passing urine frequently"]),
    ("runny nose", ["rhinorrhoea", "nasal discharge", "catarrh"]),
    ("back pain", ["backache", "lower back pain"]),
    ("chills", ["feeling cold", "shivering"]),
    ("anorexia", ["poor appetite", "not eating well"]),
    ("vomiting", ["throwing up"]),
    ("fatigue", ["feeling tired", "feeling weak"]),
]

_SYMPTOM_SECTIONS = {"Symptoms", "Signs"}


def _load_vocabulary() -> list[tuple[str, list[str]]]:
    if not VOCAB_PATH.exists():
        return []
    entries = []
    for section in re.split(r"^## ", VOCAB_PATH.read_text(encoding="utf-8"), flags=re.MULTILINE):
        lines = section.splitlines()
        if not lines or lines[0].strip() not in _SYMPTOM_SECTIONS:
            continue
        for line in lines[1:]:
            if not line.startswith("|") or set(line.replace("|", "").strip()) <= {"-", " "}:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not cells[0] or cells[0].lower() == "canonical term":
                continue
            synonyms = [s.strip() for s in cells[1].split(",")] if len(cells) > 1 else []
            entries.append((cells[0], [cells[0], *[s for s in synonyms if s]]))
    return entries


def _spelling_variants(phrase: str) -> set[str]:
    # The browser speech engine writes US English; the vocabulary is British.
    us = (phrase.replace("oea", "ea").replace("aem", "em").replace("oed", "ed")
          .replace("haem", "hem").replace("colour", "color"))
    return {phrase, us}


@lru_cache(maxsize=1)
def _symptom_patterns() -> list[tuple[str, re.Pattern]]:
    alias: dict[str, str] = {}
    for canonical, phrases in _load_vocabulary() + _LAY_TERMS:
        for phrase in {canonical, *phrases}:
            for variant in _spelling_variants(phrase.lower()):
                if len(variant) >= 3:
                    alias.setdefault(variant, canonical)
    patterns = []
    for variant in sorted(alias, key=len, reverse=True):
        words = [re.escape(w) for w in re.split(r"[\s-]+", variant) if w]
        patterns.append((alias[variant], re.compile(
            r"\b" + r"[\s-]+".join(words) + r"(?:s|es)?\b", re.IGNORECASE)))
    return patterns


_NEG_TRIGGER = re.compile(
    r"\b(?:(?:does|did|do)\s+not\s+have|(?:doesn't|didn't|don't|hasn't|haven't)\s+(?:have|had)|"
    r"has\s+not\s+had|has\s+no|have\s+no|negative\s+for|absence\s+of|free\s+of|"
    r"denies|denied|denying|without|no|not|nil|never)\b", re.IGNORECASE)
_NEG_STOP = re.compile(
    r"[.;!?]|\b(?:but|however|although|though|except|has|have|had|reports?|reported|"
    r"complains?|complaining|presents?|presenting|with)\b", re.IGNORECASE)


def _is_negated(text: str, start: int) -> bool:
    last = None
    for m in _NEG_TRIGGER.finditer(text, max(0, start - 80), start):
        last = m
    return bool(last) and not _NEG_STOP.search(text[last.end():start])


def _read_symptoms(text: str) -> list[dict]:
    taken: list[tuple[int, int]] = []
    found: dict[str, dict] = {}
    for canonical, pattern in _symptom_patterns():
        for m in pattern.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            taken.append(m.span())
            negated = _is_negated(text, m.start())
            current = found.get(canonical)
            # A positive mention beats a denial ("no fever yesterday, fever today").
            if current is None or (current["negated"] and not negated):
                found[canonical] = {"term": canonical, "heard": m.group(0), "negated": negated,
                                    "span": [m.start(), m.end()]}
    return sorted(found.values(), key=lambda s: s["span"][0])


# ── Duration of illness ───────────────────────────────────────────────────────

_QUANTITY = {"a": 1, "an": 1, "one": 1, "a couple of": 2, "couple of": 2, "a few": 3, "few": 3, "several": 4}
_PER_DAY = {"hour": 1 / 24, "hr": 1 / 24, "day": 1, "week": 7, "wk": 7, "month": 30}
_DURATION_RES = [
    re.compile(r"\b(?:for|over|x|lasting)\s+(?:the\s+)?(?:(?:past|last)\s+)?"
               r"(?P<n>\d+(?:\.\d+)?|a\s+couple\s+of|couple\s+of|a\s+few|few|several|an?|one)\s*"
               r"(?P<u>hours?|hrs?|days?|weeks?|wks?|months?)\b", re.IGNORECASE),
    re.compile(r"\b(?P<n>\d+(?:\.\d+)?|an?|one)\s*(?P<u>hours?|hrs?|days?|weeks?|wks?|months?)\s+"
               r"(?:ago|duration|history)\b", re.IGNORECASE),
    re.compile(r"\bsince\s+(?P<since>yesterday|last\s+night|this\s+morning|last\s+week|the\s+morning)\b",
               re.IGNORECASE),
]
_SINCE_DAYS = {"yesterday": 1, "last night": 0.5, "this morning": 0.25, "the morning": 0.25, "last week": 7}


def _read_duration(text: str) -> Optional[dict]:
    for pattern in _DURATION_RES:
        m = pattern.search(text)
        if not m:
            continue
        if m.groupdict().get("since"):
            days = _SINCE_DAYS[re.sub(r"\s+", " ", m["since"].lower())]
        else:
            n = m["n"].lower()
            qty = float(n) if n[0].isdigit() else _QUANTITY[re.sub(r"\s+", " ", n)]
            unit = m["u"].lower().rstrip("s")
            days = qty * _PER_DAY[unit]
        return {"text": m.group(0), "days": round(days, 2), "span": [m.start(), m.end()]}
    return None


def _describe_days(days: float) -> str:
    if days < 1:
        hours = round(days * 24)
        return f"{hours} hour{'s' if hours != 1 else ''}"
    if days < 14:
        d = _round(days)
        return f"{d} day{'s' if d != 1 else ''}"
    weeks = _round(days / 7)
    return f"{weeks} week{'s' if weeks != 1 else ''}"


# ── Public API ────────────────────────────────────────────────────────────────

def extract_intake(text: str) -> dict:
    """Structured vitals, complaints and duration from a dictated intake."""
    normalized = normalize_transcript(text)
    reader = _VitalsReader(normalized)
    reader.run()
    return {
        "normalized_transcript": normalized,
        "vitals": {f: r.to_dict() for f, r in reader.readings.items()},
        "symptoms": _read_symptoms(normalized),
        "duration": _read_duration(normalized),
        "warnings": reader.warnings,
    }


def onset_from_duration(extraction: dict, encounter_date: Optional[datetime]) -> Optional[datetime]:
    duration = extraction.get("duration")
    if not duration:
        return None
    anchor = encounter_date or datetime.now(timezone.utc)
    return anchor - timedelta(days=duration["days"])


def _vital_phrase(field: str, reading: dict) -> str:
    unit = reading.get("unit")
    unit = f" {unit}" if unit and unit != "/10" else (unit or "")
    return f"{FIELD_LABELS[field]} {reading['value']}{unit}"


def symptoms_summary(extraction: dict) -> Optional[str]:
    present = [s["term"] for s in extraction["symptoms"] if not s["negated"]]
    denied = [s["term"] for s in extraction["symptoms"] if s["negated"]]
    if not present and not denied:
        return None
    parts = []
    if present:
        text = ", ".join(present)
        parts.append(text[0].upper() + text[1:])
    if extraction.get("duration"):
        parts.append(f"for {_describe_days(extraction['duration']['days'])}")
    summary = " ".join(parts) if present else ""
    if denied:
        summary = (summary + ". " if summary else "") + "Denies " + ", ".join(denied)
    return summary + "."


def enriched_presentation(extraction: dict) -> str:
    """The transcript plus its structured reading, so thresholds are unmissable to the reasoner."""
    lines = [extraction["normalized_transcript"]]
    vitals = extraction["vitals"]
    phrases = []
    if "systolic_bp" in vitals and "diastolic_bp" in vitals:
        phrases.append(f"Blood pressure {vitals['systolic_bp']['value']}/{vitals['diastolic_bp']['value']} mmHg")
    for field, reading in vitals.items():
        if field in ("systolic_bp", "diastolic_bp", "blood_sugar_unit", "temperature_location", "pain_location"):
            continue
        phrases.append(_vital_phrase(field, reading))
    if phrases:
        lines.append("Recorded vital signs: " + "; ".join(phrases) + ".")
    if extraction.get("duration"):
        lines.append(f"Duration of illness: {_describe_days(extraction['duration']['days'])}.")
    return "\n\n".join(lines)


def hmis_vitals_payload(extraction: dict) -> dict:
    """Extracted values under the exact field names HMIS POST /vitals validates."""
    v = {f: r["value"] for f, r in extraction["vitals"].items()}
    payload: dict = {}
    for field in ("temperature", "temperature_location", "systolic_bp", "diastolic_bp", "pulse",
                  "respiratory_rate", "oxygen_saturation", "weight", "height", "random_blood_sugar",
                  "fasting_blood_sugar", "blood_sugar_unit", "pain_score", "pain_location", "muac",
                  "head_circumference"):
        if field in v:
            payload[field] = v[field]
    if "systolic_bp" in v and "diastolic_bp" in v:
        payload["blood_pressure"] = f"{v['systolic_bp']}/{v['diastolic_bp']}"
    summary = symptoms_summary(extraction)
    if summary:
        payload["symptoms"] = summary
    return payload


def nurse_notes(extraction: dict, assessment: Optional[dict]) -> str:
    """A reviewable note for the HMIS nurse_notes field — the clinician edits before saving."""
    lines = []
    summary = symptoms_summary(extraction)
    if summary:
        lines.append(f"Presenting complaints: {summary}")
    if assessment and assessment.get("candidates"):
        by_name = {c["diagnosis"]: c for c in assessment["candidates"]}
        lead = assessment.get("leading_candidate")
        if lead in by_name:
            lines.append(f"CDS leading consideration: {lead} ({by_name[lead]['confidence_level']} confidence).")
        others = [f"{c['diagnosis']} ({c['confidence_level']})" for c in assessment["candidates"]
                  if c["diagnosis"] != lead][:4]
        if others:
            lines.append("Differentials: " + ", ".join(others) + ".")
        # "Check for — …" flags are prompts for the clinician, not findings;
        # only documented ones belong in the record.
        documented = [f for f in assessment.get("red_flags", []) if f.startswith("Documented")]
        to_check = len(assessment.get("red_flags", [])) - len(documented)
        if documented:
            lines.append("Red flags: " + " ".join(documented))
        if to_check:
            lines.append(f"{to_check} red flag{'s' if to_check != 1 else ''} to rule out (see CDS panel).")
        lines.append("AI-assisted — decision support only; verified by the recording clinician.")
    return "\n".join(lines)


# Words in a red-flag description that say nothing about whether the feature
# itself was observed — matching on them would "confirm" any flag.
_FLAG_FILLER = {
    "severe", "acute", "sudden", "signs", "sign", "with", "without", "requiring", "requires", "require",
    "urgent", "attention", "children", "child", "adults", "adult", "less", "than", "more", "greater",
    "presence", "history", "patient", "persistent", "documented", "check", "evidence", "features",
    "feature", "high", "very", "marked", "significant", "new", "onset", "worsening", "rapid", "rapidly",
    "clinical", "present", "absent", "level", "levels", "above", "below", "over", "under", "from",
    "into", "that", "which", "their", "this", "other", "such", "especially", "particularly",
}


def _flag_terms(feature: str) -> list[str]:
    words = re.findall(r"[a-z]{4,}", re.sub(r"\([^)]*\)", " ", feature.lower()))
    return [w for w in words if w not in _FLAG_FILLER]


def reconcile_red_flags(red_flags: list[str], transcript: str) -> tuple[list[str], int]:
    """
    Downgrade "Documented — X" flags whose feature is not in the transcript.

    The reasoner occasionally labels a flag it was told to check for as
    documented. A documented red flag goes into the patient record, so the
    claim is checked deterministically: at least one clinical term of the
    feature must appear, un-negated, in what was actually said. Otherwise it
    becomes "Check for — X. Not documented in the presentation."
    """
    text = transcript.lower()
    out, downgraded = [], 0
    for flag in red_flags:
        m = re.match(r"\s*Documented\s*[—–-]\s*(?P<feature>.+?)(?:\.\s*Requires urgent attention\.?)?\s*$",
                     flag, re.IGNORECASE | re.DOTALL)
        if not m:
            out.append(flag)
            continue
        feature = m["feature"].rstrip(". ")
        heard = False
        for term in _flag_terms(feature):
            for variant in _spelling_variants(term):
                stem = variant[:max(4, len(variant) - 2)]  # "consciousness" ~ "conscious", "anaemic" ~ "anaemia"
                for hit in re.finditer(rf"\b{re.escape(stem)}", text):
                    if not _is_negated(transcript, hit.start()):
                        heard = True
                        break
                if heard:
                    break
            if heard:
                break
        if heard:
            out.append(flag)
        else:
            out.append(f"Check for — {feature}. Not documented in the presentation.")
            downgraded += 1
    return out, downgraded


def hmis_block(extraction: dict, assessment: Optional[dict]) -> dict:
    return {
        "vitals_payload": hmis_vitals_payload(extraction),
        "symptoms_summary": symptoms_summary(extraction),
        "nurse_notes": nurse_notes(extraction, assessment),
    }

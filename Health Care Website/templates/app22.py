from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from pypdf import PdfReader
from datetime import datetime
import pytesseract
from PIL import Image
import os
import re
import uuid


app = Flask(__name__)

app.secret_key = "health-care-project-secret-key"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ============================================================
# TESSERACT
# ============================================================

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# ============================================================
# TEMPORARY ANALYSIS STORAGE
# ============================================================

analysis_store = {}


# ============================================================
# NUMBER HELPERS
# ============================================================

def number_from_text(value):

    if value is None:
        return None

    match = re.search(
        r"(?<!\d)(\d+(?:\.\d+)?)",
        str(value)
    )

    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None


def all_numbers(value):

    if value is None:
        return []

    return [
        float(item)
        for item in re.findall(
            r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)",
            str(value)
        )
    ]


# ============================================================
# STATUS
# ============================================================

def calculate_status(value, minimum=None, maximum=None):

    if value is None:
        return "Not Available"

    if minimum is not None and value < minimum:
        return "Low"

    if maximum is not None and value > maximum:
        return "High"

    return "Normal"


# ============================================================
# ADD PARAMETER
# ============================================================

def add_parameter(
    result,
    name,
    value,
    unit,
    reference_range,
    minimum=None,
    maximum=None,
    status=None,
    display_value=None
):

    numeric_value = number_from_text(value)

    if numeric_value is None:
        return

    if status is None:

        status = calculate_status(
            numeric_value,
            minimum,
            maximum
        )

    result[name] = {

        "value": (
            display_value
            if display_value is not None
            else numeric_value
        ),

        "numeric_value": numeric_value,

        "unit": unit,

        "reference_range": reference_range,

        "status": status
    }


# ============================================================
# NORMALIZE REPORT LINES
# ============================================================

def normalize_lines(text):

    text = text.replace("\xa0", " ")
    text = text.replace("–", "-")
    text = text.replace("−", "-")

    lines = []

    for raw_line in text.splitlines():

        line = re.sub(
            r"\s+",
            " ",
            raw_line.strip()
        )

        if line:
            lines.append(line)

    return lines


# ============================================================
# STRUCTURED CBC ROW
# ============================================================

def _parse_structured_cbc_row(line):

    match = re.match(
        r"^(?P<label>.+?)\s+"
        r"(?P<value><\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?)\s*"
        r"(?:(?P<flag>[HL])\s+)?"
        r"(?P<low>\d+(?:\.\d+)?)\s*-\s*"
        r"(?P<high>\d+(?:\.\d+)?)\s+"
        r"(?P<unit>.+?)\s*$",
        line,
        re.IGNORECASE
    )

    if not match:
        return None

    raw_value = match.group("value").replace(" ", "")

    numeric = number_from_text(raw_value)

    if numeric is None:
        return None

    return {

        "label":
            match.group("label").strip(),

        "raw_value":
            raw_value,

        "value":
            numeric,

        "flag":
            (match.group("flag") or "").upper(),

        "low":
            float(match.group("low")),

        "high":
            float(match.group("high")),

        "unit":
            match.group("unit").strip()
    }


# ============================================================
# CBC TABLE EXTRACTION
# ============================================================

def _extract_cbc_table_parameters(parameters, lines):

    cbc_map = {

        "haemoglobin":
            ("Hemoglobin", "g/dL"),

        "hemoglobin":
            ("Hemoglobin", "g/dL"),

        "total leucocyte count":
            ("WBC Count", "/cumm"),

        "total leukocyte count":
            ("WBC Count", "/cumm"),

        "neutrophils":
            ("Neutrophils", "%"),

        "lymphocytes":
            ("Lymphocytes", "%"),

        "eosinophils":
            ("Eosinophils", "%"),

        "monocytes":
            ("Monocytes", "%"),

        "basophils":
            ("Basophils", "%"),

        "absolute neutrophils":
            ("Absolute Neutrophil Count", "/cumm"),

        "absolute lymphocytes":
            ("Absolute Lymphocyte Count", "/cumm"),

        "absolute eosinophils":
            ("Absolute Eosinophil Count", "/cumm"),

        "absolute monocytes":
            ("Absolute Monocyte Count", "/cumm"),

        "absolute basophils":
            ("Absolute Basophil Count", "/cumm"),

        "rbc count":
            ("RBC Count", "Million/cumm"),

        "hct":
            ("Hematocrit", "%"),

        "hematocrit":
            ("Hematocrit", "%"),

        "mcv":
            ("MCV", "fL"),

        "mch":
            ("MCH", "pg"),

        "mchc":
            ("MCHC", "g/dL"),

        "rdw-cv":
            ("RDW CV", "%"),

        "rdw cv":
            ("RDW CV", "%"),

        "rdw-sd":
            ("RDW SD", "fL"),

        "platelet count":
            ("Platelet Count", "/cumm"),

        "pct":
            ("PCT", "%"),

        "mpv":
            ("MPV", "fL"),

        "pdw":
            ("PDW", "fL"),

        "p-lcr":
            ("P-LCR", "%"),

        "p-lcc":
            ("P-LCC", "10^3/uL")
    }

    found = set()

    for line in lines:

        parsed = _parse_structured_cbc_row(line)

        if not parsed:
            continue

        key = re.sub(
            r"\s+",
            " ",
            parsed["label"].strip().lower()
        )

        if key not in cbc_map:
            continue

        name, fallback_unit = cbc_map[key]

        minimum = parsed["low"]
        maximum = parsed["high"]

        flag = parsed["flag"]

        if flag == "H":
            status = "High"

        elif flag == "L":
            status = "Low"

        else:
            status = calculate_status(
                parsed["value"],
                minimum,
                maximum
            )

        add_parameter(

            parameters,

            name,

            parsed["value"],

            parsed["unit"] or fallback_unit,

            f"{minimum:g} - {maximum:g}",

            minimum,

            maximum,

            status=status,

            display_value=parsed["raw_value"]
        )

        found.add(name)

    return found


# ============================================================
# SAFE LINE PARAMETER EXTRACTION
# ============================================================

def _add_line_parameter(
    parameters,
    lines,
    name,
    label_pattern,
    unit,
    reference_range,
    minimum=None,
    maximum=None
):

    # Never overwrite a value already extracted by
    # a more specific parser.
    if name in parameters:
        return False

    try:
        label_regex = re.compile(
            label_pattern,
            re.IGNORECASE
        )
    except re.error:
        return False

    unit_regex = re.compile(
        re.escape(unit).replace(
            r"\ ",
            r"\s+"
        ),
        re.IGNORECASE
    )

    for line in lines:

        label_match = label_regex.search(line)

        if not label_match:
            continue

        # ----------------------------------------------------
        # Work only with the current report row.
        # ----------------------------------------------------

        row = line[label_match.start():].strip()

        # ----------------------------------------------------
        # Extract all numbers from this row.
        # ----------------------------------------------------

        number_matches = list(
            re.finditer(
                r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)",
                row
            )
        )

        if not number_matches:
            continue

        numbers = [
            {
                "value": float(match.group(1)),
                "start": match.start(),
                "end": match.end()
            }
            for match in number_matches
        ]

        # ----------------------------------------------------
        # H/L flag
        # ----------------------------------------------------

        flag_match = re.search(
            r"\b([HL])\b",
            row,
            re.IGNORECASE
        )

        flag = (
            flag_match.group(1).upper()
            if flag_match
            else ""
        )

        # ----------------------------------------------------
        # Unit position
        # ----------------------------------------------------

        unit_match = unit_regex.search(row)

        value = None

        # ====================================================
        # CASE 1
        #
        # Normal format:
        #
        # Label  Value  Unit  Reference Range
        #
        # Example:
        # WBC Count 10570 /cmm 4000 - 10000
        # ====================================================

        if unit_match:

            numbers_before_unit = [

                item

                for item in numbers

                if item["end"] <= unit_match.start()
            ]

            if numbers_before_unit:

                # The value immediately before the unit
                # is normally the actual result.
                value = numbers_before_unit[-1]["value"]

        # ====================================================
        # CASE 2
        #
        # Some reports use:
        #
        # Label Unit Reference Result
        #
        # Example:
        #
        # Albumin g/dL 3.5 - 5.0 4.2
        #
        # In this format, the result comes AFTER the
        # reference range.
        # ====================================================

        if unit_match:

            range_match = re.search(
                r"(?P<low>\d+(?:\.\d+)?)"
                r"\s*-\s*"
                r"(?P<high>\d+(?:\.\d+)?)",
                row
            )

            if range_match:

                numbers_after_range = [

                    item

                    for item in numbers

                    if item["start"] >= range_match.end()
                ]

                if numbers_after_range:

                    # If a result exists after the reference
                    # range, prefer it.
                    value = numbers_after_range[0]["value"]

        # ====================================================
        # CASE 3
        #
        # Handle "< value" reference formats carefully.
        #
        # Example:
        # Microalbumin mg/L < 16.7
        #
        # Here the value is part of the reference, so don't
        # blindly use it as the result if another result
        # exists later in the row.
        # ====================================================

        if value is None:

            if unit_match:

                distances = [

                    (
                        abs(
                            item["end"]
                            - unit_match.start()
                        ),
                        item
                    )

                    for item in numbers
                ]

                if distances:

                    distances.sort(
                        key=lambda item: item[0]
                    )

                    value = distances[0][1]["value"]

        # ====================================================
        # CASE 4
        #
        # If no unit was found, use the first numeric value
        # after the label.
        # ====================================================

        if value is None:

            if numbers:

                value = numbers[0]["value"]

        if value is None:
            continue

        # ====================================================
        # IMPORTANT SANITY CHECK
        #
        # If we know the reference range and the selected
        # number is outside it, look for another candidate
        # that is clearly the actual result.
        #
        # This is especially useful for reports where:
        #
        # Label Unit Reference Result
        #
        # is used.
        # ====================================================

        if (
            minimum is not None
            and maximum is not None
        ):

            # Values occurring inside the reference range.
            in_range_candidates = [

                item["value"]

                for item in numbers

                if minimum <= item["value"] <= maximum
            ]

            # If selected value is outside the range and there
            # is exactly one sensible candidate inside the range,
            # prefer that candidate.
            if (
                value < minimum
                or value > maximum
            ):

                if len(in_range_candidates) == 1:

                    value = (
                        in_range_candidates[0]
                    )

        # ====================================================
        # STATUS
        # ====================================================

        status = None

        if flag == "H":

            status = "High"

        elif flag == "L":

            status = "Low"

        # ====================================================
        # ADD RESULT
        # ====================================================

        add_parameter(

            parameters,

            name,

            value,

            unit,

            reference_range,

            minimum,

            maximum,

            status=status
        )

        return True

    return False

    # Never overwrite a value already extracted by a
    # more specific parser.
    if name in parameters:
        return False

    try:
        label_regex = re.compile(
            label_pattern,
            re.IGNORECASE
        )
    except re.error:
        return False

    unit_regex = re.compile(
        re.escape(unit).replace(
            r"\ ",
            r"\s+"
        ),
        re.IGNORECASE
    )

    for line in lines:

        label_match = label_regex.search(line)

        if not label_match:
            continue

        # ----------------------------------------------------
        # IMPORTANT:
        # Work ONLY inside the current line.
        # ----------------------------------------------------

        row = line[
            label_match.start():
        ]

        numbers = list(
            re.finditer(
                r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)",
                row
            )
        )

        if not numbers:
            continue

        # ----------------------------------------------------
        # Find H/L flag if available
        # ----------------------------------------------------

        flag_match = re.search(
            r"\b([HL])\b",
            row,
            re.IGNORECASE
        )

        flag = (
            flag_match.group(1).upper()
            if flag_match
            else ""
        )

        # ----------------------------------------------------
        # Find unit position
        # ----------------------------------------------------

        unit_match = unit_regex.search(row)

        value = None

        # ----------------------------------------------------
        # FORMAT 1
        #
        # Label
        # Value
        # Unit
        # Reference
        #
        # Example:
        # WBC Count H 10570 /cmm 4000 - 10000
        # ----------------------------------------------------

        if unit_match:

            numbers_before_unit = [

                match

                for match in numbers

                if match.end() <= unit_match.start()
            ]

            if numbers_before_unit:

                # Usually the last number before the unit
                # is the actual result.
                candidate = numbers_before_unit[-1]

                value = float(
                    candidate.group(1)
                )

        # ----------------------------------------------------
        # FORMAT 2
        #
        # Label
        # Unit
        # Reference
        # Method
        # Result
        #
        # Example:
        # Albumin g/dL 3.5 - 5.0 method 4.2
        # ----------------------------------------------------

        if value is None:

            range_match = re.search(
                r"(\d+(?:\.\d+)?)\s*-\s*"
                r"(\d+(?:\.\d+)?)",
                row
            )

            if range_match:

                numbers_after_range = [

                    match

                    for match in numbers

                    if match.start() >= range_match.end()
                ]

                if numbers_after_range:

                    value = float(
                        numbers_after_range[-1].group(1)
                    )

        # ----------------------------------------------------
        # FORMAT 3
        #
        # If no reference range is visible, use the number
        # closest to the unit.
        # ----------------------------------------------------

        if value is None and unit_match:

            distances = [

                (
                    abs(
                        match.end()
                        - unit_match.start()
                    ),
                    match
                )

                for match in numbers
            ]

            if distances:

                distances.sort(
                    key=lambda item: item[0]
                )

                value = float(
                    distances[0][1].group(1)
                )

        if value is None:
            continue

        # ----------------------------------------------------
        # Sanity check against known reference range.
        #
        # If the selected value is clearly a reference value
        # and another candidate fits the report better,
        # try alternatives.
        # ----------------------------------------------------

        candidates = [
            float(match.group(1))
            for match in numbers
        ]

        if minimum is not None and maximum is not None:

            def score(candidate):

                if minimum <= candidate <= maximum:
                    return 0

                # Values outside range are still valid,
                # but less preferred than a candidate that
                # lies within the stated range.
                distance = min(
                    abs(candidate - minimum),
                    abs(candidate - maximum)
                )

                return 1 + distance

            candidates_sorted = sorted(
                candidates,
                key=score
            )

            # Only switch when the original selected value
            # looks like a reference number and another
            # candidate is a much better fit.
            if candidates_sorted:

                best_candidate = candidates_sorted[0]

                if (
                    value < minimum
                    or value > maximum
                ):

                    if (
                        minimum <= best_candidate <= maximum
                    ):
                        value = best_candidate

        status = None

        if flag == "H":
            status = "High"

        elif flag == "L":
            status = "Low"

        add_parameter(

            parameters,

            name,

            value,

            unit,

            reference_range,

            minimum,

            maximum,

            status=status
        )

        return True

    return False


# ============================================================
# REGEX PARAMETER
# ============================================================

def _add_regex_parameter(
    parameters,
    text,
    name,
    pattern,
    unit,
    reference_range,
    minimum=None,
    maximum=None,
    status=None,
    display_value=None
):

    if name in parameters:
        return False

    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return False

    value = match.group("value")

    add_parameter(

        parameters,

        name,

        value,

        unit,

        reference_range,

        minimum,

        maximum,

        status=status,

        display_value=display_value
    )

    return True



# ============================================================
# KFT / KIDNEY FUNCTION TEST EXTRACTION
# ============================================================

def _kft_reference_from_text(row):

    # Normal OCR form: 0.55 - 1.02
    match = re.search(
        r"(?P<low>\d+(?:\.\d+)?)\s*-\s*"
        r"(?P<high>\d+(?:\.\d+)?)",
        row
    )

    if match:
        return (
            float(match.group("low")),
            float(match.group("high")),
            f"{match.group('low')} - {match.group('high')}"
        )

    # Some OCR output removes decimal points but keeps the hyphen.
    # Example: 1200-4300 -> 12.00-43.00.
    match = re.search(
        r"(?P<low>\d{3,6})\s*-\s*(?P<high>\d{3,6})",
        row
    )

    if match:
        low_raw = match.group("low")
        high_raw = match.group("high")

        # Only repair when both endpoints have the same digit count.
        if len(low_raw) == len(high_raw) and len(low_raw) >= 3:
            decimals = 2
            low = float(low_raw) / (10 ** decimals)
            high = float(high_raw) / (10 ** decimals)

            return (
                low,
                high,
                f"{low:g} - {high:g}"
            )

    return None


def _kft_candidate_value(raw_value, minimum, maximum):

    raw_value = raw_value.strip()

    # A normal decimal/integer result is safe to use directly.
    if re.fullmatch(r"\d+(?:\.\d+)?", raw_value):
        value = float(raw_value)

        # If the OCR value is already inside the reference range,
        # use it exactly as extracted.
        if minimum <= value <= maximum:
            return value

        # For compact OCR such as 2400 with a 12.00-43.00 range,
        # restore only a decimal scale that makes the result fit
        # the stated reference interval. This does not invent a
        # different measurement; it repairs a missing OCR decimal.
        digits = raw_value.replace(".", "")

        for decimals in range(1, 4):
            if len(digits) <= decimals:
                continue

            repaired = float(digits) / (10 ** decimals)

            if minimum <= repaired <= maximum:
                return repaired

    return None


def _extract_kft_parameters(parameters, lines):

    kft_rows = [
        (
            "Creatinine",
            r"(?:Creatinine|Cresinine|Cresinie|Creatin)",
            "mg/dL",
            0.55,
            1.02
        ),
        (
            "Urea",
            r"(?:Urea|Uea)",
            "mg/dL",
            12.0,
            43.0
        ),
        (
            "BUN",
            r"(?:Blood\s+Urea\s+Nitrogen|Urea\s+Nitrogen|BUN)",
            "mg/dL",
            9.0,
            20.0
        ),
        (
            "Calcium",
            r"(?:Calcium|Caloom)",
            "mg/dL",
            8.7,
            10.0
        ),
        (
            "Phosphorus",
            r"(?:Phosphorus|Phosphons)",
            "mg/dL",
            2.0,
            5.1
        ),
        (
            "Sodium",
            r"(?:Sodium|Socium)",
            "mEq/L",
            136.0,
            145.0
        ),
        (
            "Potassium",
            r"(?:Potassium|Potass)",
            "mEq/L",
            3.5,
            5.1
        ),
        (
            "Chloride",
            r"(?:Chloride|Chioce)",
            "mEq/L",
            98.0,
            107.0
        )
    ]

    for name, label_pattern, unit, minimum, maximum in kft_rows:

        if name in parameters:
            continue

        label_regex = re.compile(
            label_pattern,
            re.IGNORECASE
        )

        for line in lines:

            match = label_regex.search(line)

            if not match:
                continue

            row = line[match.start():].strip()

            reference = _kft_reference_from_text(row)

            # Use the KFT parameter's known reference interval as the
            # authoritative range. OCR frequently removes decimal points
            # from this column (for example 136.00 -> 13600), so using the
            # raw OCR range here would create false classifications.
            ref_min = minimum
            ref_max = maximum
            ref_text = f"{minimum:g} - {maximum:g}"

            # Ignore the reference numbers themselves when selecting
            # a result candidate.
            range_match = re.search(
                r"\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?",
                row
            )

            prefix = (
                row[:range_match.start()]
                if range_match
                else row
            )

            number_matches = re.findall(
                r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)",
                prefix
            )

            if not number_matches:
                continue

            candidates = []

            for raw_value in number_matches:

                value = _kft_candidate_value(
                    raw_value,
                    ref_min,
                    ref_max
                )

                if value is None:
                    continue

                # A zero value in these KFT rows is commonly an OCR
                # artefact when the report clearly expects a positive
                # concentration/electrolyte value. Do not guess a
                # replacement; simply leave that parameter unavailable.
                if value == 0 and ref_min > 0:
                    continue

                candidates.append(value)

            if not candidates:
                continue

            # Prefer a candidate closest to the centre of the stated
            # reference interval when several repaired candidates fit.
            centre = (ref_min + ref_max) / 2
            value = min(
                candidates,
                key=lambda item: abs(item - centre)
            )

            add_parameter(
                parameters,
                name,
                value,
                unit,
                ref_text,
                ref_min,
                ref_max
            )

            break


# ============================================================
# EXTRACT PARAMETERS
# ============================================================

def extract_parameters(text):

    parameters = {}

    lines = normalize_lines(text)
    full_text = "\n".join(lines)

    # KFT is handled before generic chemistry extraction so OCR aliases
    # such as Cresinie/Uea/Socium/Chioce are not lost.
    _extract_kft_parameters(
        parameters,
        lines
    )

    print("\n========== EXTRACTED TEXT ==========")
    print(full_text)

    _extract_cbc_table_parameters(
        parameters,
        lines
        )

    # ========================================================
    # 1. STRUCTURED CBC
    # ========================================================

    _extract_cbc_table_parameters(
        parameters,
        lines
    )

    # ========================================================
    # 2. COMMON CBC / GENERAL PARAMETERS
    # ========================================================

    line_parameters = [

        (
            "Hemoglobin",
            r"(?<![A-Za-z])Hemoglobin(?![A-Za-z])",
            "g/dL",
            "13.0 - 16.5",
            13.0,
            16.5
        ),

        (
            "RBC Count",
            r"(?<![A-Za-z])RBC Count(?![A-Za-z])",
            "million/cmm",
            "4.5 - 5.5",
            4.5,
            5.5
        ),

        (
            "Hematocrit",
            r"(?<![A-Za-z])Hematocrit(?![A-Za-z])",
            "%",
            "40 - 49",
            40,
            49
        ),

        (
            "MCV",
            r"(?<![A-Za-z])MCV(?![A-Za-z])",
            "fL",
            "83 - 101",
            83,
            101
        ),

        (
            "MCH",
            r"(?<![A-Za-z])MCH(?![A-Za-z])",
            "pg",
            "27.1 - 32.5",
            27.1,
            32.5
        ),

        (
            "MCHC",
            r"(?<![A-Za-z])MCHC(?![A-Za-z])",
            "g/dL",
            "32.5 - 36.7",
            32.5,
            36.7
        ),

        (
            "RDW CV",
            r"(?<![A-Za-z])RDW[\s-]*CV(?![A-Za-z])",
            "%",
            "11.6 - 14",
            11.6,
            14
        ),

        (
            "WBC Count",
            r"(?<![A-Za-z])WBC Count(?![A-Za-z])",
            "/cmm",
            "4000 - 10000",
            4000,
            10000
        ),

        (
            "Neutrophils",
            r"(?<![A-Za-z])Neutrophils(?![A-Za-z])",
            "%",
            "40 - 80",
            40,
            80
        ),

        (
            "Lymphocytes",
            r"(?<![A-Za-z])Lymphocytes(?![A-Za-z])",
            "%",
            "20 - 40",
            20,
            40
        ),

        (
            "Eosinophils",
            r"(?<![A-Za-z])Eosinophils(?![A-Za-z])",
            "%",
            "1 - 6",
            1,
            6
        ),

        (
            "Monocytes",
            r"(?<![A-Za-z])Monocytes(?![A-Za-z])",
            "%",
            "2 - 10",
            2,
            10
        ),

        (
            "Basophils",
            r"(?<![A-Za-z])Basophils(?![A-Za-z])",
            "%",
            "0 - 2",
            0,
            2
        ),

        (
            "Platelet Count",
            r"(?<![A-Za-z])Platelet Count(?![A-Za-z])",
            "/cmm",
            "150000 - 410000",
            150000,
            410000
        ),

        (
            "MPV",
            r"(?<![A-Za-z])MPV(?![A-Za-z])",
            "fL",
            "7.5 - 10.3",
            7.5,
            10.3
        ),

        (
            "ESR",
            r"(?<![A-Za-z])ESR(?![A-Za-z])",
            "mm/1hr",
            "0 - 14",
            0,
            14
        ),

        # ====================================================
        # ABSOLUTE COUNTS
        #
        # IMPORTANT:
        # "Absolute" is mandatory here.
        # This prevents matching normal Neutrophils rows.
        # ====================================================

        (
            "Absolute Neutrophil Count",
            r"(?<![A-Za-z])Absolute\s+Neutrophils?(?:\s+Count)?(?![A-Za-z])",
            "/cmm",
            "2000 - 6700",
            2000,
            6700
        ),

        (
            "Absolute Lymphocyte Count",
            r"(?<![A-Za-z])Absolute\s+Lymphocytes?(?:\s+Count)?(?![A-Za-z])",
            "/cmm",
            "1100 - 3300",
            1100,
            3300
        ),

        (
            "Absolute Eosinophil Count",
            r"(?<![A-Za-z])Absolute\s+Eosinophils?(?:\s+Count)?(?![A-Za-z])",
            "/cmm",
            "0 - 400",
            0,
            400
        ),

        (
            "Absolute Monocyte Count",
            r"(?<![A-Za-z])Absolute\s+Monocytes?(?:\s+Count)?(?![A-Za-z])",
            "/cmm",
            "200 - 700",
            200,
            700
        ),

        (
            "Absolute Basophil Count",
            r"(?<![A-Za-z])Absolute\s+Basophils?(?:\s+Count)?(?![A-Za-z])",
            "/cmm",
            "0 - 100",
            0,
            100
        ),

        # ====================================================
        # BLOOD SUGAR
        # ====================================================

        (
            "Fasting Blood Sugar",
            r"(?<![A-Za-z])Fasting Blood Sugar(?![A-Za-z])",
            "mg/dL",
            "74 - 106",
            74,
            106
        ),

        # ====================================================
        # THYROID
        # ====================================================

        (
            "T3",
            r"(?<![A-Za-z])T3\s*-\s*Triiodothyronine(?![A-Za-z])",
            "ng/mL",
            "0.58 - 1.59",
            0.58,
            1.59
        ),

        (
            "TSH",
            r"(?<![A-Za-z])TSH\s*-\s*Thyroid Stimulating Hormone(?![A-Za-z])",
            "microIU/mL",
            "0.35 - 4.94",
            0.35,
            4.94
        ),

        # ====================================================
        # CHEMISTRY
        # ====================================================

        (
            "Microalbumin",
            r"(?<![A-Za-z])Microalbumin\s*\(per urine volume\)(?![A-Za-z])",
            "mg/L",
            "< 16.7",
            0,
            16.7
        ),

        (
            "Total Protein",
            r"(?<![A-Za-z])Total Protein(?![A-Za-z])",
            "g/dL",
            "6.3 - 8.2",
            6.3,
            8.2
        ),

        # IMPORTANT:
        # Negative lookbehind prevents Albumin from matching
        # the "albumin" part inside "Microalbumin".
        (
            "Albumin",
            r"(?<![A-Za-z])Albumin(?![A-Za-z])",
            "g/dL",
            "3.5 - 5.0",
            3.5,
            5.0
        ),

        (
            "Globulin",
            r"(?<![A-Za-z])Globulin(?![A-Za-z])",
            "g/dL",
            "2.3 - 3.5",
            2.3,
            3.5
        ),

        (
            "Total Bilirubin",
            r"(?<![A-Za-z])Total Bilirubin(?![A-Za-z])",
            "mg/dL",
            "0.2 - 1.3",
            0.2,
            1.3
        ),

        (
            "Conjugated Bilirubin",
            r"(?<![A-Za-z])Conjugated Bilirubin(?![A-Za-z])",
            "mg/dL",
            "0.0 - 0.3",
            0,
            0.3
        ),

        (
            "Unconjugated Bilirubin",
            r"(?<![A-Za-z])Unconjugated Bilirubin(?![A-Za-z])",
            "mg/dL",
            "0.0 - 1.1",
            0,
            1.1
        ),

        (
            "Delta Bilirubin",
            r"(?<![A-Za-z])Delta Bilirubin(?![A-Za-z])",
            "mg/dL",
            "0.0 - 0.2",
            0,
            0.2
        ),

        (
            "Iron",
            r"(?<![A-Za-z])Iron(?![A-Za-z])",
            "micro g/dL",
            "49 - 181",
            49,
            181
        ),

        (
            "Homocysteine",
            r"(?<![A-Za-z])Homocysteine,\s*Serum(?![A-Za-z])",
            "micromol/L",
            "6.0 - 14.8",
            6,
            14.8
        ),

        (
            "Creatinine",
            r"(?<![A-Za-z])Creatinine,\s*Serum(?![A-Za-z])",
            "mg/dL",
            "0.66 - 1.25",
            0.66,
            1.25
        ),

        (
            "Urea",
            r"(?<![A-Za-z])Urea(?![A-Za-z])",
            "mg/dL",
            "19.3 - 43.0",
            19.3,
            43
        ),

        (
            "BUN",
            r"(?<![A-Za-z])Blood Urea Nitrogen(?![A-Za-z])",
            "mg/dL",
            "9.0 - 20.0",
            9,
            20
        ),

        (
            "Uric Acid",
            r"(?<![A-Za-z])Uric Acid(?![A-Za-z])",
            "mg/dL",
            "3.5 - 8.5",
            3.5,
            8.5
        ),

        (
            "Calcium",
            r"(?<![A-Za-z])Calcium(?![A-Za-z])",
            "mg/dL",
            "8.4 - 10.2",
            8.4,
            10.2
        ),

        (
            "SGPT",
            r"(?<![A-Za-z])SGPT(?![A-Za-z])",
            "U/L",
            "0 - 50",
            0,
            50
        ),

        (
            "SGOT",
            r"(?<![A-Za-z])SGOT(?![A-Za-z])",
            "U/L",
            "17 - 59",
            17,
            59
        ),

        (
            "Sodium",
            r"(?<![A-Za-z])Sodium\s*\(Na\+\)(?![A-Za-z])",
            "mmol/L",
            "136 - 145",
            136,
            145
        ),

        (
            "Potassium",
            r"(?<![A-Za-z])Potassium\s*\(K\+\)(?![A-Za-z])",
            "mmol/L",
            "3.5 - 5.1",
            3.5,
            5.1
        ),

        (
            "Chloride",
            r"(?<![A-Za-z])Chloride\s*\(Cl-\)(?![A-Za-z])",
            "mmol/L",
            "98 - 107",
            98,
            107
        ),

        (
            "IgE",
            r"(?<![A-Za-z])IgE(?![A-Za-z])",
            "IU/mL",
            "0 - 87",
            0,
            87
        ),

        (
            "VLDL",
            r"(?<![A-Za-z])VLDL(?![A-Za-z])",
            "mg/dL",
            "15 - 35",
            15,
            35
        )
    ]

    for item in line_parameters:

        _add_line_parameter(
            parameters,
            lines,
            *item
        )

    # ========================================================
    # SPECIAL TABLE PARAMETERS
    # ========================================================

    _add_regex_parameter(

        parameters,

        full_text,

        "T4",

        r"T4\s*-\s*Thyroxine\s+mg/mL\s+"
        r"4\.87\s*-\s*11\.72\s+"
        r"(?P<value>\d+(?:\.\d+)?)",

        "mg/mL",

        "4.87 - 11.72",

        4.87,

        11.72
    )

    # ========================================================
    # RATIOS
    # ========================================================

    _add_regex_parameter(

        parameters,

        full_text,

        "CHOL/HDL Ratio",

        r"CHOL/HDL Ratio\s+Up to\s+5\.0.*?"
        r"Calculated\s+(?P<value>\d+(?:\.\d+)?)",

        "Ratio",

        "Up to 5.0",

        0,

        5
    )

    _add_regex_parameter(

        parameters,

        full_text,

        "LDL/HDL Ratio",

        r"LDL/HDL Ratio\s+Up to\s+3\.5.*?"
        r"Calculated\s+(?P<value>\d+(?:\.\d+)?)",

        "Ratio",

        "Up to 3.5",

        0,

        3.5
    )

    _add_regex_parameter(

        parameters,

        full_text,

        "A/G Ratio",

        r"A/G Ratio\s+1\.3\s*-\s*1\.7.*?"
        r"Calculated\s+(?P<value>\d+(?:\.\d+)?)",

        "Ratio",

        "1.3 - 1.7",

        1.3,

        1.7
    )

    _add_regex_parameter(

        parameters,

        full_text,

        "TIBC",

        r"Total Iron Binding Capacity\s*\(TIBC\)\s+"
        r"261\s*-\s*462\s+"
        r"(?P<value>\d+(?:\.\d+)?)",

        "micro g/dL",

        "261 - 462",

        261,

        462
    )

    # ========================================================
    # LIPID PROFILE
    # ========================================================

    match = re.search(

        r"(?<![A-Za-z])Cholesterol\s+mg/dL.*?"
        r"Cholesterol\s+oxidase\s*-\s*Peroxidase\s+method\s+"
        r"(?P<value>\d+(?:\.\d+)?)",

        full_text,

        re.IGNORECASE | re.DOTALL
    )

    if match:

        value = float(
            match.group("value")
        )

        status = (
            "Normal"
            if value < 200
            else
            "Borderline High"
            if value <= 239
            else
            "High"
        )

        add_parameter(

            parameters,

            "Cholesterol",

            value,

            "mg/dL",

            "< 200",

            0,

            199.999,

            status=status
        )

    # ========================================================
    # TRIGLYCERIDES
    # ========================================================

    match = re.search(

        r"(?<![A-Za-z])Triglyceride\s+[HL]?\s*mg/dL.*?"
        r"Ezymatic\s*\(Lipase/GK/GPO/POD\)\s+"
        r"(?P<value>\d+(?:\.\d+)?)",

        full_text,

        re.IGNORECASE | re.DOTALL
    )

    if match:

        value = float(
            match.group("value")
        )

        if value < 150:
            status = "Normal"

        elif value <= 199:
            status = "Borderline High"

        elif value <= 499:
            status = "High"

        else:
            status = "Very High"

        add_parameter(

            parameters,

            "Triglycerides",

            value,

            "mg/dL",

            "< 150",

            0,

            149.999,

            status=status
        )

    # ========================================================
    # HDL
    # ========================================================

    match = re.search(

        r"(?<![A-Za-z])HDL Cholesterol\s+mg/dL.*?"
        r"PTA/MgCl2\s+"
        r"(?P<value>\d+(?:\.\d+)?)",

        full_text,

        re.IGNORECASE | re.DOTALL
    )

    if match:

        value = float(
            match.group("value")
        )

        status = (
            "Low"
            if value < 40
            else
            "Normal"
            if value <= 60
            else
            "High"
        )

        add_parameter(

            parameters,

            "HDL Cholesterol",

            value,

            "mg/dL",

            "40 - 60",

            40,

            60,

            status=status
        )

    # ========================================================
    # LDL
    # ========================================================

    match = re.search(

        r"(?<![A-Za-z])Direct LDL\s+[HL]?\s*mg/dL.*?"
        r"Direct measured\s+"
        r"(?P<value>\d+(?:\.\d+)?)",

        full_text,

        re.IGNORECASE | re.DOTALL
    )

    if match:

        value = float(
            match.group("value")
        )

        if value < 100:
            status = "Optimal"

        elif value <= 129:
            status = "Above Optimal"

        elif value <= 159:
            status = "Borderline High"

        elif value <= 189:
            status = "High"

        else:
            status = "Very High"

        add_parameter(

            parameters,

            "LDL Cholesterol",

            value,

            "mg/dL",

            "< 100 optimal",

            0,

            99.999,

            status=status
        )

    # ========================================================
    # HBA1C
    # ========================================================

    match = re.search(
        r"(?<![A-Za-z])HbA1C\s+"
        r"(?P<value>\d+(?:\.\d+)?)\s+"
        r"\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?\s*%",
        full_text,
        re.IGNORECASE
    )

    if match:

        value = float(match.group("value"))

        if value < 5.7:
            status = "Normal"
        elif value < 6.5:
            status = "Prediabetes Range"
        else:
            status = "High"

        add_parameter(
            parameters,
            "HbA1c",
            value,
            "%",
            "4.0 - 6.0",
            4.0,
            6.0,
            status
        )

    # ========================================================
    # PSA
    # ========================================================

    _add_regex_parameter(

        parameters,

        full_text,

        "PSA Total",

        r"PSA-Prostate Specific Antigen,\s*Total\s+"
        r"ng/mL\s+0\s*-\s*4"
        r"(?P<value>\d+(?:\.\d+)?)",

        "ng/mL",

        "0 - 4",

        0,

        4
    )

    # ========================================================
    # ELECTROPHORESIS
    # ========================================================

    electrophoresis_items = [

        (
            "Hb A2",
            r"(?<![A-Za-z])Hb\s*A2(?![A-Za-z])",
            "%",
            "2.2 - 3.2",
            2.2,
            3.2
        ),

        (
            "P2",
            r"(?<![A-Za-z])P2(?![A-Za-z])",
            "%",
            "Not specified",
            None,
            None
        ),

        (
            "P3",
            r"(?<![A-Za-z])P3(?![A-Za-z])",
            "%",
            "Not specified",
            None,
            None
        ),

        (
            "Foetal Hb",
            r"(?<![A-Za-z])Foetal Hb(?![A-Za-z])",
            "%",
            "0 - 1",
            0,
            1
        )
    ]

    for item in electrophoresis_items:

        _add_line_parameter(
            parameters,
            lines,
            *item
        )

    return parameters


# ============================================================
# QUALITATIVE RESULTS
# ============================================================

def _qualitative_result(
    results,
    name,
    result,
    interpretation
):

    if any(
        item["name"] == name
        for item in results
    ):
        return

    results.append({

        "name":
            name,

        "result":
            result,

        "interpretation":
            interpretation
    })


def extract_qualitative_results(text):

    results = []

    normalized = " ".join(
        normalize_lines(text)
    )

    # ========================================================
    # HLA-B27
    # ========================================================

    hla_match = re.search(

        r"HLA[-\s]?B27\s*PCR.*?"
        r"\b(NEGATIVE|POSITIVE|INVALID)\b",

        normalized,

        re.IGNORECASE
    )

    if hla_match:

        result_value = (
            hla_match.group(1).upper()
        )

        _qualitative_result(

            results,

            "HLA-B27 PCR, QUALITATIVE",

            result_value,

            result_value.capitalize()
        )

    # ========================================================
    # HIV
    # ========================================================

    hiv_match = re.search(

        r"HIV\s*I\s*&\s*II.*?"
        r"\b(Non\s*Reactive|Reactive|Negative|Positive)\b",

        normalized,

        re.IGNORECASE
    )

    if hiv_match:

        raw = re.sub(
            r"\s+",
            " ",
            hiv_match.group(1)
        ).strip()

        _qualitative_result(

            results,

            "HIV I & II Ab/Ag P24 Ag",

            raw,

            raw
        )

    # ========================================================
    # HBSAG
    # ========================================================

    hbsag_match = re.search(

        r"HBsAg.*?"
        r"\b(Non\s*Reactive|Reactive|Negative|Positive)\b",

        normalized,

        re.IGNORECASE
    )

    if hbsag_match:

        raw = re.sub(
            r"\s+",
            " ",
            hbsag_match.group(1)
        ).strip()

        _qualitative_result(

            results,

            "HBsAg",

            raw,

            raw
        )

    # ========================================================
    # HB ELECTROPHORESIS
    # ========================================================

    electrophoresis_match = re.search(

        r"Interpretation\s+"
        r"(Negative for typical beta thalassemia trait\.)",

        normalized,

        re.IGNORECASE
    )

    if electrophoresis_match:

        _qualitative_result(

            results,

            "Hb Electrophoresis",

            electrophoresis_match.group(1).strip(),

            "Negative"
        )

    # ========================================================
    # URINE GLUCOSE
    # ========================================================

    urine_glucose_match = re.search(

        r"Urine Glucose\s+"
        r"(Present\s*(?:\(\+\)|\+)|Absent)",

        normalized,

        re.IGNORECASE
    )

    if urine_glucose_match:

        raw = urine_glucose_match.group(1).strip()

        interpretation = (
            "Present"
            if raw.lower().startswith("present")
            else
            "Absent"
        )

        _qualitative_result(

            results,

            "Urine Glucose",

            raw,

            interpretation
        )

    # ========================================================
    # URINALYSIS
    # ========================================================

    urine_items = [

        (
            "Urine Protein",
            r"Urine Protein\s+(Present|Absent|Negative|Positive)"
        ),

        (
            "Urine Bilirubin",
            r"Urine Bilirubin\s+(Present|Absent|Negative|Positive)"
        ),

        (
            "Urine Urobilinogen",
            r"Urobilinogen\s+(Present|Absent|Normal|Negative|Positive)"
        ),

        (
            "Urine Ketone",
            r"Ketone\s+(Present|Absent|Negative|Positive)"
        ),

        (
            "Urine Nitrite",
            r"Nitrite\s+(Present|Absent|Negative|Positive)"
        ),

        (
            "Urine Casts",
            r"Casts\s+(Present|Absent|Negative)"
        ),

        (
            "Urine Crystals",
            r"Crystals\s+(Present|Absent|Negative)"
        ),

        (
            "Urine Amorphous",
            r"Amorphous\s+(Present|Absent|Negative)"
        )
    ]

    for name, pattern in urine_items:

        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE
        )

        if match:

            raw = match.group(1).strip()

            _qualitative_result(

                results,

                name,

                raw,

                raw
            )

    return results


# ============================================================
# PATIENT INFORMATION
# ============================================================

def extract_patient_info(text):

    patient_info = {

        "age":
            "Not Available",

        "gender":
            "Not Available",

        "report_status":
            "Not Available"
    }

    age_match = re.search(

        r"\b(\d{1,3})\s*(?:Years?|Y)\b",

        text,

        re.IGNORECASE
    )

    if age_match:

        patient_info["age"] = (
            f"{age_match.group(1)} Years"
        )

    gender_match = re.search(

        r"\b(Male|Female)\b",

        text,

        re.IGNORECASE
    )

    if gender_match:

        patient_info["gender"] = (
            gender_match.group(1).capitalize()
        )

    status_match = re.search(

        r"Status\s*:?\s*"
        r"(Final|Preliminary|Draft)",

        text,

        re.IGNORECASE
    )

    if not status_match:

        status_match = re.search(

            r"\b(Final|Preliminary|Draft)\b",

            text,

            re.IGNORECASE
        )

    if status_match:

        patient_info["report_status"] = (
            status_match.group(1).capitalize()
        )

    return patient_info


# ============================================================
# REPORT TYPE
# ============================================================

def detect_report_type(text):

    text_lower = text.lower()

    # A dedicated KFT/Kidney Panel may also contain sodium, potassium
    # and chloride. Detect the kidney panel heading first so it is not
    # incorrectly classified as a generic comprehensive report.
    if re.search(
        r"kidney\s+panel|kft\s*[-.]?\s*serum|renal\s+function\s+test",
        text_lower
    ):
        return "Kidney / Renal Function Report"

    if re.search(
        r"hla[-\s]?b27\s*pcr",
        text_lower
    ):
        return "HLA-B27 PCR Report"

    if (
        "hb electrophoresis" in text_lower
        or
        "hemoglobin electrophoresis" in text_lower
    ):

        if not any(
            key in text_lower
            for key in [
                "complete blood count",
                "lipid profile",
                "thyroid"
            ]
        ):

            return "Hb Electrophoresis Report"

    families = {

        "CBC / Hematology": [

            "complete blood count",
            "cbc",
            "hemoglobin",
            "platelet count"
        ],

        "Lipid Profile": [

            "lipid profile",
            "triglyceride",
            "hdl cholesterol",
            "direct ldl"
        ],

        "Blood Glucose": [

            "fasting blood sugar",
            "blood glucose",
            "fasting glucose"
        ],

        "HbA1c": [

            "hba1c",
            "glycated hemoglobin"
        ],

        "Thyroid": [

            "thyroid function",
            "triiodothyronine",
            "thyroxine",
            "thyroid stimulating hormone"
        ],

        "Vitamin D": [

            "25(oh) vitamin d",
            "vitamin d"
        ],

        "Vitamin B12": [

            "vitamin b12"
        ],

        "Iron Studies": [

            "total iron binding capacity",
            "tibc",
            "transferrin saturation"
        ],

        "Kidney / Renal": [

            "creatinine",
            "blood urea nitrogen",
            "urea",
            "uric acid"
        ],

        "Liver": [

            "sgpt",
            "sgot",
            "bilirubin",
            "liver function"
        ],

        "Electrolytes": [

            "sodium",
            "potassium",
            "chloride"
        ],

        "Homocysteine": [

            "homocysteine"
        ],

        "PSA": [

            "prostate specific antigen",
            "psa"
        ],

        "Urinalysis": [

            "urinalysis",
            "urine examination",
            "urine glucose",
            "pus cells",
            "specific gravity"
        ],

        "Infectious Screening": [

            "hiv i & ii",
            "hbsag",
            "hepatitis b surface antigen"
        ]
    }

    matched_families = [

        family

        for family, keywords in families.items()

        if any(
            keyword in text_lower
            for keyword in keywords
        )
    ]

    if len(matched_families) >= 2:

        return "Comprehensive Laboratory Test Report"

    if matched_families:

        family = matched_families[0]

        mapping = {

            "CBC / Hematology":
                "Blood Test Report",

            "Lipid Profile":
                "Lipid Profile Report",

            "Blood Glucose":
                "Blood Glucose Report",

            "HbA1c":
                "HbA1c Report",

            "Thyroid":
                "Thyroid Function Test Report",

            "Vitamin D":
                "Vitamin D Report",

            "Vitamin B12":
                "Vitamin B12 Report",

            "Iron Studies":
                "Iron Studies Report",

            "Kidney / Renal":
                "Kidney / Renal Function Report",

            "Liver":
                "Liver Function Report",

            "Electrolytes":
                "Electrolyte Report",

            "Homocysteine":
                "Homocysteine Report",

            "PSA":
                "PSA Report",

            "Urinalysis":
                "Urinalysis Report",

            "Infectious Screening":
                "Infectious Screening Report"
        }

        return mapping.get(
            family,
            "Medical Laboratory Report"
        )

    return "Medical Laboratory Report"


# ============================================================
# TEST NAME
# ============================================================

def extract_test_name(text):

    test_patterns = [

        (r"HLA[-\s]?B27\s*PCR", "HLA-B27 PCR"),

        (r"Complete Blood Count", "Complete Blood Count"),

        (r"Lipid Profile", "Lipid Profile"),

        (r"HbA1c|Glycated Hemoglobin", "HbA1c"),

        (r"Thyroid Function Test", "Thyroid Function Test"),

        (r"Vitamin D", "Vitamin D"),

        (r"Vitamin B12", "Vitamin B12"),

        (r"Urinalysis|Urine Examination", "Urinalysis"),

        (r"HB Electrophoresis|Hemoglobin Electrophoresis", "Hb Electrophoresis"),

        (r"Homocysteine", "Homocysteine"),

        (r"PSA[-\s]*Prostate Specific Antigen", "PSA"),

        (r"Kidney\s+Panel|KFT\s*[-.]?\s*Serum|Renal\s+Function\s+Test", "Kidney / Renal Function"),

        (r"Creatinine|Cresinine|Cresinie|Kidney|Renal Function", "Kidney / Renal Function"),

        (r"SGPT|SGOT|Liver Function", "Liver Function"),

        (r"HIV\s*I\s*&\s*II", "HIV Screening"),

        (r"HBsAg", "HBsAg")
    ]

    for pattern, name in test_patterns:

        if re.search(
            pattern,
            text,
            re.IGNORECASE
        ):
            return name

    return "Not Available"

# ============================================================
# TEST RESULT
# ============================================================

def extract_test_result(text, report_type):

    if report_type == "HLA-B27 PCR Report":

        text_upper = text.upper()

        if re.search(
            r"\bNEGATIVE\b",
            text_upper
        ):
            return "NEGATIVE"

        if re.search(
            r"\bPOSITIVE\b",
            text_upper
        ):
            return "POSITIVE"

        if re.search(
            r"\bINVALID\b",
            text_upper
        ):
            return "INVALID"

    return "Not Applicable"


# ============================================================
# RESULT SUMMARY
# ============================================================

def create_result_summary(
    report_type,
    test_name,
    test_result,
    parameter_analysis,
    qualitative_results
):

    if test_result in [
        "NEGATIVE",
        "POSITIVE",
        "INVALID"
    ]:

        if test_result == "NEGATIVE":

            return (

                f"The uploaded {report_type} reports a "
                f"negative result for {test_name}. "
                "The result shown here reflects the uploaded "
                "laboratory document and is presented for "
                "general informational purposes."
            )

        if test_result == "POSITIVE":

            return (

                f"The uploaded {report_type} reports a "
                f"positive result for {test_name}. "
                "The reported result should be reviewed with "
                "a qualified healthcare professional in the "
                "appropriate clinical context."
            )

        return (

            f"The uploaded {report_type} reports an "
            f"invalid result for {test_name}."
        )

    total = len(
        parameter_analysis
    )

    normal = sum(

        1

        for item in parameter_analysis.values()

        if item["status"] in [
            "Normal",
            "Optimal"
        ]
    )

    attention = total - normal

    qualitative_count = len(
        qualitative_results
    )

    if total == 0:

        if qualitative_count > 0:

            return (

                f"The report contains {qualitative_count} "
                "qualitative laboratory result(s). "
                "These results are displayed as reported in "
                "the uploaded document. Clinical interpretation "
                "should consider the patient's history and "
                "other relevant findings."
            )

        return (

            "No structured laboratory parameters were "
            "successfully identified from the uploaded report."
        )

    return (

        f"This report contains {total} extracted numeric "
        f"health parameter(s). {normal} parameter(s) are "
        "within the extracted reference range, while "
        f"{attention} parameter(s) are outside the extracted "
        "reference range or require attention. "
        f"{qualitative_count} qualitative result(s) were also "
        "identified. "
        "These classifications are intended for general "
        "informational purposes and should not be considered "
        "a medical diagnosis."
    )


# ============================================================
# FINDINGS
# ============================================================

def create_findings(
    parameter_analysis
):

    findings = []

    attention_statuses = [

        "High",
        "Very High",
        "Low",
        "Deficient",
        "Insufficient",
        "Borderline High",
        "Prediabetes Range",
        "Above Optimal"
    ]

    for name, data in parameter_analysis.items():

        status = data["status"]

        if status in attention_statuses:

            findings.append({

                "name":
                    name,

                "value":
                    data["value"],

                "unit":
                    data["unit"],

                "status":
                    status,

                "message": (
                    f"{name} is classified as "
                    f"{status} based on the extracted "
                    "reference information."
                )
            })

    return findings


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# UPLOAD
# ============================================================

@app.route("/upload")
def upload():

    return render_template(
        "upload.html"
    )


# ============================================================
# PROCESSING
# ============================================================

@app.route(
    "/processing",
    methods=["GET", "POST"]
)
def processing():

    if request.method == "POST":

        report_file = request.files.get(
            "report_file"
        )

        if not report_file:

            return redirect(
                url_for("upload")
            )

        filename = secure_filename(
            report_file.filename
        )

        if not filename:

            return redirect(
                url_for("upload")
            )

        unique_filename = (

            uuid.uuid4().hex[:8]
            + "_"
            + filename
        )

        file_path = os.path.join(

            app.config["UPLOAD_FOLDER"],

            unique_filename
        )

        report_file.save(
            file_path
        )

        # ====================================================
        # TEXT EXTRACTION
        # ====================================================

        extracted_text = ""

        try:

            if unique_filename.lower().endswith(".pdf"):

                reader = PdfReader(
                    file_path
                )

                for page in reader.pages:

                    page_text = (
                        page.extract_text()
                    )

                    if page_text:

                        extracted_text += (
                            page_text
                            + "\n"
                        )

            else:

                image = Image.open(
                    file_path
                )

                extracted_text = (
                    pytesseract.image_to_string(
                        image
                    )
                )

        except Exception as error:

            print(
                "Extraction Error:",
                error
            )

        # ====================================================
        # ANALYSIS
        # ====================================================

        parameter_analysis = (
            extract_parameters(
                extracted_text
            )
        )

        qualitative_results = (
            extract_qualitative_results(
                extracted_text
            )
        )

        report_type = (
            detect_report_type(
                extracted_text
            )
        )

        test_name = (
            extract_test_name(
                extracted_text
            )
        )

        test_result = (
            extract_test_result(
                extracted_text,
                report_type
            )
        )

        patient_info = (
            extract_patient_info(
                extracted_text
            )
        )

        findings = (
            create_findings(
                parameter_analysis
            )
        )

        result_summary = (
            create_result_summary(
                report_type,
                test_name,
                test_result,
                parameter_analysis,
                qualitative_results
            )
        )

        # ====================================================
        # ANALYSIS ID
        # ====================================================

        analysis_id = uuid.uuid4().hex

        analysis_store[analysis_id] = {

            "report_name":
                filename,

            "analysis_date":
                datetime.now().strftime(
                    "%d %B %Y, %I:%M %p"
                ),

            "report_type":
                report_type,

            "test_name":
                test_name,

            "test_result":
                test_result,

            "patient_info":
                patient_info,

            "parameters":
                parameter_analysis,

            "parameter_analysis":
                parameter_analysis,

            "qualitative_results":
                qualitative_results,

            "findings":
                findings,

            "result_summary":
                result_summary
        }

        session["analysis_id"] = (
            analysis_id
        )

        # ====================================================
        # TERMINAL OUTPUT
        # ====================================================

        print(
            "\n========== REPORT INFORMATION ==========\n"
        )

        print(
            "Report Type:",
            report_type
        )

        print(
            "Test Name:",
            test_name
        )

        print(
            "Test Result:",
            test_result
        )

        print(
            "Patient Information:",
            patient_info
        )

        print(
            "Result Summary:",
            result_summary
        )

        print(
            "Findings:",
            findings
        )

        print(
            "Qualitative Results:",
            qualitative_results
        )

        print(
            "\n========== PARAMETER ANALYSIS ==========\n"
        )

        for name, data in parameter_analysis.items():

            print(
                name,
                "=>",
                data
            )

        print(
            "\n=========================================\n"
        )

        return redirect(
            url_for(
                "processing_page"
            )
        )

    return render_template(
        "processing.html"
    )


# ============================================================
# PROCESSING PAGE
# ============================================================

@app.route("/processing-page")
def processing_page():

    return render_template(
        "processing.html"
    )


# ============================================================
# ANALYSIS
# ============================================================

@app.route("/analysis")
def analysis():

    analysis_id = session.get(
        "analysis_id"
    )

    data = analysis_store.get(
        analysis_id
    )

    if not data:

        return render_template(

            "analysis.html",

            report_name="Not Available",

            analysis_date="Not Available",

            report_type="Not Available",

            test_name="Not Available",

            test_result="Not Available",

            patient_info={

                "age":
                    "Not Available",

                "gender":
                    "Not Available",

                "report_status":
                    "Not Available"
            },

            result_summary=
                "No summary available.",

            parameters={},

            parameter_analysis={},

            qualitative_results=[],

            findings=[]
        )

    return render_template(

        "analysis.html",

        report_name=
            data["report_name"],

        analysis_date=
            data["analysis_date"],

        report_type=
            data["report_type"],

        test_name=
            data["test_name"],

        test_result=
            data["test_result"],

        patient_info=
            data["patient_info"],

        result_summary=
            data["result_summary"],

        parameters=
            data["parameters"],

        parameter_analysis=
            data["parameter_analysis"],

        qualitative_results=
            data["qualitative_results"],

        findings=
            data["findings"]
    )


# ============================================================
# DIET
# ============================================================

@app.route("/diet")
def diet():

    analysis_id = session.get(
        "analysis_id"
    )

    data = analysis_store.get(
        analysis_id
    )

    if not data:

        return render_template(

            "diet.html",

            report_type="No Report Available",

            patient_info={},

            dietary_guidance=[],

            limiting_guidance=[],

            health_habits=[

                "Maintain a balanced eating pattern",

                "Stay adequately hydrated",

                "Follow a consistent sleep routine",

                "Maintain regular physical activity",

                "Monitor health reports when advised",

                "Discuss persistent concerns with a qualified healthcare professional"
            ],

            guidance_message=(

                "Upload and analyse a health report to "
                "receive report-based general dietary guidance."
            )
        )

    parameter_analysis = data.get(
        "parameter_analysis",
        {}
    )

    dietary_guidance = []

    limiting_guidance = []

    health_habits = [

        "Maintain a balanced eating pattern",

        "Stay adequately hydrated",

        "Follow a consistent sleep routine",

        "Maintain regular physical activity",

        "Monitor health reports when advised",

        "Discuss persistent concerns with a qualified healthcare professional"
    ]

    dietary_guidance.extend([

        "Include a variety of vegetables and seasonal fruits",

        "Prefer whole grains and minimally processed cereals",

        "Include suitable protein-rich foods such as dal, beans, legumes, curd or other appropriate sources",

        "Include nuts and seeds in appropriate portions",

        "Maintain adequate water intake"
    ])

    for name, parameter in parameter_analysis.items():

        status = parameter.get(
            "status",
            ""
        )

        name_lower = name.lower()

        # ====================================================
        # BLOOD SUGAR
        # ====================================================

        if (
            "fasting blood sugar" in name_lower
            or "hba1c" in name_lower
        ):

            if status in [
                "High",
                "Prediabetes Range"
            ]:

                limiting_guidance.extend([

                    "Limit frequent intake of sugary drinks and sweetened beverages",

                    "Limit foods with large amounts of added sugar",

                    "Prefer whole or minimally processed carbohydrate sources",

                    "Avoid making refined and highly processed foods a frequent part of meals"
                ])

                health_habits.extend([

                    "Maintain regular physical activity as appropriate",

                    "Prefer consistent meal patterns",

                    "Monitor blood glucose-related reports as advised by a healthcare professional"
                ])

        # ====================================================
        # TRIGLYCERIDES
        # ====================================================

        if "triglyceride" in name_lower:

            if status in [
                "Borderline High",
                "High",
                "Very High"
            ]:

                limiting_guidance.extend([

                    "Limit frequent intake of sugary foods and sweetened beverages",

                    "Limit heavily processed foods",

                    "Avoid making deep-fried foods a frequent choice",

                    "Prefer balanced portions of carbohydrates and fats"
                ])

        # ====================================================
        # LDL / CHOLESTEROL
        # ====================================================

        if (
            "ldl cholesterol" in name_lower
            or name_lower == "cholesterol"
        ):

            if status in [
                "Above Optimal",
                "Borderline High",
                "High",
                "Very High"
            ]:

                limiting_guidance.extend([

                    "Limit frequent consumption of heavily fried foods",

                    "Prefer minimally processed foods",

                    "Include vegetables, whole grains and legumes regularly",

                    "Avoid excessive intake of foods high in saturated fat"
                ])

        # ====================================================
        # VITAMIN D
        # ====================================================

        if "vitamin d" in name_lower:

            if status in [
                "Deficient",
                "Insufficient"
            ]:

                dietary_guidance.extend([

                    "Discuss vitamin D-rich food options with a healthcare professional",

                    "Include appropriate fortified foods where suitable",

                    "Vitamin D deficiency may require professional assessment and management"
                ])

                health_habits.append(

                    "Discuss appropriate vitamin D management and sunlight exposure with a healthcare professional"
                )

        # ====================================================
        # VITAMIN B12
        # ====================================================

        if "vitamin b12" in name_lower:

            if status == "Low":

                dietary_guidance.extend([

                    "Include suitable vitamin B12-containing foods according to individual dietary preferences",

                    "Fortified foods may be considered where appropriate",

                    "Discuss the low B12 result with a healthcare professional"
                ])

        # ====================================================
        # HOMOCYSTEINE
        # ====================================================

        if "homocysteine" in name_lower:

            if status in [
                "High",
                "Very High"
            ]:

                dietary_guidance.extend([

                    "Maintain a balanced diet containing appropriate sources of folate and B vitamins",

                    "Include a variety of vegetables, legumes and other nutrient-rich foods",

                    "Discuss the elevated result and possible nutritional factors with a healthcare professional"
                ])

        # ====================================================
        # URIC ACID
        # ====================================================

        if "uric acid" in name_lower:

            if status in [
                "High",
                "Very High"
            ]:

                limiting_guidance.extend([

                    "Discuss appropriate dietary choices with a healthcare professional",

                    "Maintain adequate hydration unless fluid restriction has been advised"
                ])

        # ====================================================
        # IGE
        # ====================================================

        if name_lower == "ige":

            if status in [
                "High",
                "Very High"
            ]:

                health_habits.extend([

                    "If allergy-related symptoms are present, discuss them with a qualified healthcare professional",

                    "Avoid identifying or eliminating foods solely on the basis of an elevated IgE result without professional evaluation"
                ])

    dietary_guidance = list(
        dict.fromkeys(
            dietary_guidance
        )
    )

    limiting_guidance = list(
        dict.fromkeys(
            limiting_guidance
        )
    )

    health_habits = list(
        dict.fromkeys(
            health_habits
        )
    )

    guidance_message = (

        "The guidance below uses the parameters extracted from "
        "the uploaded laboratory report. It provides general "
        "educational information and does not replace a "
        "personalized medical or dietary plan."
    )

    return render_template(

        "diet.html",

        report_type=data.get(
            "report_type",
            "Laboratory Report"
        ),

        patient_info=data.get(
            "patient_info",
            {}
        ),

        report_name=data.get(
            "report_name",
            "Uploaded Report"
        ),

        analysis_date=data.get(
            "analysis_date",
            "Not Available"
        ),

        dietary_guidance=
            dietary_guidance,

        limiting_guidance=
            limiting_guidance,

        health_habits=
            health_habits,

        guidance_message=
            guidance_message,

        parameter_analysis=
            parameter_analysis
    )


# ============================================================
# PRECAUTIONS
# ============================================================

@app.route("/precautions")
def precautions():

    return render_template(
        "precautions.html"
    )


# ============================================================
# TRENDS
# ============================================================

@app.route("/trends")
def trends():

    return render_template(
        "trends.html"
    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
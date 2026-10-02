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
# NUMBER HELPER
# ============================================================

def number_from_text(value):

    if value is None:
        return None

    match = re.search(
        r"\d+(?:\.\d+)?",
        str(value)
    )

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


# ============================================================
# STATUS FROM RANGE
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
# PARAMETER EXTRACTION
# ============================================================

def extract_parameters(text):

    parameters = {}

    lines = normalize_lines(text)

    full_text = "\n".join(lines)

    print("\n========== EXTRACTED TEXT ==========")
    print(full_text)

    _extract_cbc_table_parameters(
        parameters,
        lines
        )

    # ========================================================
    # SIMPLE PARAMETERS
    # ========================================================

    simple_parameters = [

        (
            "Hemoglobin",
            r"Hemoglobin\s+g/dL",
            "g/dL",
            "13.0 - 16.5",
            13.0,
            16.5
        ),

        (
            "RBC Count",
            r"RBC Count\s+million/cmm",
            "million/cmm",
            "4.5 - 5.5",
            4.5,
            5.5
        ),

        (
            "Hematocrit",
            r"Hematocrit\s+%",
            "%",
            "40 - 49",
            40,
            49
        ),

        (
            "MCV",
            r"MCV\s+fL",
            "fL",
            "83 - 101",
            83,
            101
        ),

        (
            "MCH",
            r"MCH\s+pg",
            "pg",
            "27.1 - 32.5",
            27.1,
            32.5
        ),

        (
            "MCHC",
            r"MCHC\s+g/dL",
            "g/dL",
            "32.5 - 36.7",
            32.5,
            36.7
        ),

        (
            "RDW CV",
            r"RDW CV\s+%",
            "%",
            "11.6 - 14",
            11.6,
            14
        ),

        (
            "WBC Count",
            r"WBC Count(?:\s+[HL])?\s+/cmm",
            "/cmm",
            "4000 - 10000",
            4000,
            10000
        ),

        (
            "Neutrophils",
            r"Neutrophils\s+%",
            "%",
            "40 - 80",
            40,
            80
        ),

        (
            "Lymphocytes",
            r"Lymphocytes\s+%",
            "%",
            "20 - 40",
            20,
            40
        ),

        (
            "Eosinophils",
            r"Eosinophils\s+%",
            "%",
            "1 - 6",
            1,
            6
        ),

        (
            "Monocytes",
            r"Monocytes\s+%",
            "%",
            "2 - 10",
            2,
            10
        ),

        (
            "Basophils",
            r"Basophils\s+%",
            "%",
            "0 - 2",
            0,
            2
        ),

        (
            "Platelet Count",
            r"Platelet Count\s+/cmm",
            "/cmm",
            "150000 - 410000",
            150000,
            410000
        ),

        (
            "MPV",
            r"MPV(?:\s+[HL])?\s+fL",
            "fL",
            "7.5 - 10.3",
            7.5,
            10.3
        ),

        (
            "ESR",
            r"ESR\s+mm/1hr",
            "mm/1hr",
            "0 - 14",
            0,
            14
        ),

        (
            "VLDL",
            r"VLDL\s+mg/dL",
            "mg/dL",
            "15 - 35",
            15,
            35
        ),

        (
            "Fasting Blood Sugar",
            r"Fasting Blood Sugar(?:\s+[HL])?\s+mg/dL",
            "mg/dL",
            "74 - 106",
            74,
            106
        ),

        (
            "T3",
            r"T3\s*-\s*Triiodothyronine\s+ng/mL",
            "ng/mL",
            "0.58 - 1.59",
            0.58,
            1.59
        ),

        (
            "TSH",
            r"TSH\s*-\s*Thyroid Stimulating Hormone\s+microIU/mL",
            "microIU/mL",
            "0.35 - 4.94",
            0.35,
            4.94
        ),

        (
            "Microalbumin",
            r"Microalbumin \(per urine volume\)\s+mg/L",
            "mg/L",
            "< 16.7",
            0,
            16.7
        ),

        (
            "Total Protein",
            r"Total Protein\s+g/dL",
            "g/dL",
            "6.3 - 8.2",
            6.3,
            8.2
        ),

        (
            "Albumin",
            r"Albumin\s+g/dL",
            "g/dL",
            "3.5 - 5.0",
            3.5,
            5.0
        ),

        (
            "Globulin",
            r"Globulin\s+g/dL",
            "g/dL",
            "2.3 - 3.5",
            2.3,
            3.5
        ),

        (
            "Total Bilirubin",
            r"Total Bilirubin\s+mg/dL",
            "mg/dL",
            "0.2 - 1.3",
            0.2,
            1.3
        ),

        (
            "Conjugated Bilirubin",
            r"Conjugated Bilirubin\s+mg/dL",
            "mg/dL",
            "0.0 - 0.3",
            0,
            0.3
        ),

        (
            "Unconjugated Bilirubin",
            r"Unconjugated Bilirubin\s+mg/dL",
            "mg/dL",
            "0.0 - 1.1",
            0,
            1.1
        ),

        (
            "Delta Bilirubin",
            r"Delta Bilirubin\s+mg/dL",
            "mg/dL",
            "0.0 - 0.2",
            0,
            0.2
        ),

        (
            "Iron",
            r"Iron\s+micro g/dL",
            "micro g/dL",
            "49 - 181",
            49,
            181
        ),

        (
            "Homocysteine",
            r"Homocysteine, Serum(?:\s+[HL])?\s+micromol/L",
            "micromol/L",
            "6.0 - 14.8",
            6,
            14.8
        ),

        (
            "Creatinine",
            r"Creatinine, Serum\s+mg/dL",
            "mg/dL",
            "0.66 - 1.25",
            0.66,
            1.25
        ),

        (
            "Urea",
            r"Urea(?:\s+[HL])?\s+mg/dL",
            "mg/dL",
            "19.3 - 43.0",
            19.3,
            43.0
        ),

        (
            "BUN",
            r"Blood Urea Nitrogen(?:\s+[HL])?\s+mg/dL",
            "mg/dL",
            "9.0 - 20.0",
            9,
            20
        ),

        (
            "Uric Acid",
            r"Uric Acid\s+mg/dL",
            "mg/dL",
            "3.5 - 8.5",
            3.5,
            8.5
        ),

        (
            "Calcium",
            r"Calcium\s+mg/dL",
            "mg/dL",
            "8.4 - 10.2",
            8.4,
            10.2
        ),

        (
            "SGPT",
            r"SGPT\s+U/L",
            "U/L",
            "0 - 50",
            0,
            50
        ),

        (
            "SGOT",
            r"SGOT\s+U/L",
            "U/L",
            "17 - 59",
            17,
            59
        ),

        (
            "Sodium",
            r"Sodium \(Na\+\)\s+mmol/L",
            "mmol/L",
            "136 - 145",
            136,
            145
        ),

        (
            "Potassium",
            r"Potassium \(K\+\)\s+mmol/L",
            "mmol/L",
            "3.5 - 5.1",
            3.5,
            5.1
        ),

        (
            "Chloride",
            r"Chloride \(Cl-\)\s+mmol/L",
            "mmol/L",
            "98 - 107",
            98,
            107
        ),

        (
            "IgE",
            r"IgE(?:\s+[HL])?\s+IU/mL",
            "IU/mL",
            "0 - 87",
            0,
            87
        )
    ]


    # ========================================================
    # PROCESS SIMPLE PARAMETERS
    # ========================================================

    for (
        name,
        label_pattern,
        unit,
        reference_range,
        minimum,
        maximum
    ) in simple_parameters:

        for line in lines:

            if not re.match(
                r"^" + label_pattern + r"(?:\s|$)",
                line,
                re.IGNORECASE
            ):
                continue

            match = re.search(
                r"(?P<value>\d+(?:\.\d+)?)$",
                line
            )

            if match:

                add_parameter(
                    parameters,
                    name,
                    match.group("value"),
                    unit,
                    reference_range,
                    minimum,
                    maximum
                )

            break


    # ========================================================
    # T4
    # ========================================================

    match = re.search(
        r"T4\s*-\s*Thyroxine\s+"
        r"mg/mL\s+"
        r"4\.87\s*-\s*11\.72"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE
    )

    if match:

        add_parameter(
            parameters,
            "T4",
            match.group("value"),
            "mg/mL",
            "4.87 - 11.72",
            4.87,
            11.72
        )


    # ========================================================
    # CHOL / HDL RATIO
    # ========================================================

    match = re.search(
        r"CHOL/HDL Ratio\s+"
        r"Up to\s+5\.0.*?"
        r"Calculated\s+"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE | re.DOTALL
    )

    if match:

        add_parameter(
            parameters,
            "CHOL/HDL Ratio",
            match.group("value"),
            "Ratio",
            "Up to 5.0",
            0,
            5
        )


    # ========================================================
    # LDL / HDL RATIO
    # ========================================================

    match = re.search(
        r"LDL/HDL Ratio\s+"
        r"Up to\s+3\.5.*?"
        r"Calculated\s+"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE | re.DOTALL
    )

    if match:

        add_parameter(
            parameters,
            "LDL/HDL Ratio",
            match.group("value"),
            "Ratio",
            "Up to 3.5",
            0,
            3.5
        )


    # ========================================================
    # A/G RATIO
    # ========================================================

    match = re.search(
        r"A/G Ratio\s+"
        r"1\.3\s*-\s*1\.7.*?"
        r"Calculated\s+"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE | re.DOTALL
    )

    if match:

        add_parameter(
            parameters,
            "A/G Ratio",
            match.group("value"),
            "Ratio",
            "1.3 - 1.7",
            1.3,
            1.7
        )


    # ========================================================
    # TIBC
    # ========================================================

    match = re.search(
        r"Total Iron Binding Capacity\s*\(TIBC\)\s+"
        r"261\s*-\s*462"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE
    )

    if match:

        add_parameter(
            parameters,
            "TIBC",
            match.group("value"),
            "micro g/dL",
            "261 - 462",
            261,
            462
        )


    # ========================================================
    # CHOLESTEROL
    # ========================================================

    match = re.search(
        r"Cholesterol\s+mg/dL.*?"
        r"Cholesterol\s+oxidase\s*-\s*"
        r"Peroxidase\s+method\s+"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE | re.DOTALL
    )

    if match:

        value = float(match.group("value"))

        if value < 200:
            status = "Normal"
        elif value <= 239:
            status = "Borderline High"
        else:
            status = "High"

        add_parameter(
            parameters,
            "Cholesterol",
            value,
            "mg/dL",
            "< 200",
            0,
            199.999,
            status
        )


    # ========================================================
    # TRIGLYCERIDES
    # ========================================================

    match = re.search(
        r"Triglyceride\s+[HL]?\s*mg/dL.*?"
        r"Ezymatic\s*\(Lipase/GK/GPO/POD\)\s+"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE | re.DOTALL
    )

    if match:

        value = float(match.group("value"))

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
            status
        )


    # ========================================================
    # HDL
    # ========================================================

    match = re.search(
        r"HDL Cholesterol\s+mg/dL.*?"
        r"PTA/MgCl2\s+"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE | re.DOTALL
    )

    if match:

        value = float(match.group("value"))

        if value < 40:
            status = "Low"
        elif value <= 60:
            status = "Normal"
        else:
            status = "High"

        add_parameter(
            parameters,
            "HDL Cholesterol",
            value,
            "mg/dL",
            "40 - 60",
            40,
            60,
            status
        )


    # ========================================================
    # LDL
    # ========================================================

    match = re.search(
        r"Direct LDL\s+[HL]?\s*mg/dL.*?"
        r"Direct measured\s+"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE | re.DOTALL
    )

    if match:

        value = float(match.group("value"))

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
            status
        )


    # ========================================================
    # HBA1C
    # ========================================================

    match = re.search(
        r"HbA1c\s+[HL]\s*%\s+.*?"
        r"High Performance Liquid Chromatography\s+"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE | re.DOTALL
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
            "< 5.7 non-diabetes",
            0,
            5.699,
            status
        )


    # ========================================================
    # VITAMIN D
    # ========================================================

    match = re.search(
        r"25\(OH\)\s*Vitamin D\s+ng/mL.*?"
        r"CLIA\s+"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE | re.DOTALL
    )

    if match:

        value = float(match.group("value"))

        if value < 10:
            status = "Deficient"
        elif value < 30:
            status = "Insufficient"
        elif value <= 100:
            status = "Normal"
        else:
            status = "High"

        add_parameter(
            parameters,
            "Vitamin D",
            value,
            "ng/mL",
            "30 - 100 sufficient",
            30,
            100,
            status
        )


    # ========================================================
    # VITAMIN B12
    # ========================================================

    match = re.search(
        r"Vitamin B12\s+[HL]?\s*pg/mL\s+"
        r"187\s*-\s*833.*?"
        r"CLIA\s*<\s*"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE | re.DOTALL
    )

    if match:

        value = float(match.group("value"))

        add_parameter(
            parameters,
            "Vitamin B12",
            value,
            "pg/mL",
            "187 - 833",
            187,
            833,
            "Low",
            display_value=f"<{int(value)}"
        )


    # ========================================================
    # PSA
    # ========================================================

    match = re.search(
        r"PSA-Prostate Specific Antigen,\s*Total\s+"
        r"ng/mL\s+0\s*-\s*4"
        r"(?P<value>\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE
    )

    if match:

        add_parameter(
            parameters,
            "PSA Total",
            match.group("value"),
            "ng/mL",
            "0 - 4",
            0,
            4
        )


    return parameters


# ============================================================
# QUALITATIVE RESULTS
# ============================================================

def extract_qualitative_results(text):

    results = []

    # ========================================================
    # HLA-B27
    # ========================================================

    hla_match = re.search(
        r"HLA-B27\s*PCR.*?"
        r"\b(NEGATIVE|POSITIVE|INVALID)\b",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if hla_match:

        result_value = (
            hla_match.group(1)
            .upper()
        )

        results.append({

            "name":
                "HLA-B27 PCR, QUALITATIVE",

            "result":
                result_value,

            "interpretation":
                result_value.capitalize()

        })


    # ========================================================
    # HIV
    # ========================================================

    hiv_match = re.search(
        r"HIV\s*I\s*&\s*II.*?"
        r"Non\s*Reactive",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if hiv_match:

        results.append({

            "name":
                "HIV I & II Ab/Ag P24 Ag",

            "result":
                "Non Reactive",

            "interpretation":
                "Non Reactive"

        })


    # ========================================================
    # HBsAg
    # ========================================================

    hbsag_match = re.search(
        r"HBsAg.*?"
        r"Non\s*Reactive",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if hbsag_match:

        results.append({

            "name":
                "HBsAg",

            "result":
                "Non Reactive",

            "interpretation":
                "Non Reactive"

        })


    # ========================================================
    # Hb Electrophoresis
    # ========================================================

    electrophoresis_match = re.search(
        r"Interpretation\s+"
        r"(Negative for typical beta thalassemia trait\.)",
        text,
        re.IGNORECASE
    )

    if electrophoresis_match:

        results.append({

            "name":
                "Hb Electrophoresis",

            "result":
                electrophoresis_match.group(1).strip(),

            "interpretation":
                "Negative"

        })


    # ========================================================
    # Urine Glucose
    # ========================================================

    urine_glucose_match = re.search(
        r"Urine Glucose\s+"
        r"(?:Present\s*\(\+\)|Present\s*\+)",
        text,
        re.IGNORECASE
    )

    if urine_glucose_match:

        results.append({

            "name":
                "Urine Glucose",

            "result":
                "Present (+)",

            "interpretation":
                "Present"

        })


    return results

# ============================================================
# PATIENT INFORMATION
# ============================================================
def extract_patient_info(text):

    patient_info = {

        "age": "Not Available",

        "gender": "Not Available",

        "report_status": "Not Available"
    }

    age_match = re.search(
        r"\b(\d{1,3})\s*(?:Years?|Y)\b",
        text,
        re.IGNORECASE
    )

    if age_match:

        patient_info["age"] = (
            age_match.group(1)
            + " Years"
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
        r"Status\s*:?\s*(Final|Preliminary)",
        text,
        re.IGNORECASE
    )

    if not status_match:

        status_match = re.search(
            r"\b(Final|Preliminary)\b",
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

    if "hla-b27" in text_lower:

        return "HLA-B27 PCR Report"


    parameter_keywords = [
        "complete blood count",
        "lipid profile",
        "fasting blood sugar",
        "hba1c",
        "thyroid",
        "vitamin d",
        "vitamin b12",
        "homocysteine",
        "urinalysis",
        "hb electrophoresis"
    ]

    matches = sum(
        1
        for keyword in parameter_keywords
        if keyword in text_lower
    )

    if matches >= 2:

        return "Comprehensive Laboratory Test Report"


    if (
        "complete blood count" in text_lower
        or "hemoglobin" in text_lower
        or "platelet count" in text_lower
    ):

        return "Blood Test Report"


    if "lipid profile" in text_lower:

        return "Lipid Profile Report"


    if (
        "fasting blood sugar" in text_lower
        or "blood glucose" in text_lower
    ):

        return "Blood Glucose Report"


    return "Medical Laboratory Report"


# ============================================================
# TEST NAME
# ============================================================

def extract_test_name(text):

    if re.search(
        r"HLA-B27 PCR",
        text,
        re.IGNORECASE
    ):

        match = re.search(
            r"HLA-B27 PCR(?:,\s*QUALITATIVE)?",
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(0).strip()


    detected_tests = []

    test_patterns = [

        (
            r"Complete Blood Count",
            "Complete Blood Count"
        ),

        (
            r"Lipid Profile",
            "Lipid Profile"
        ),

        (
            r"HbA1c",
            "HbA1c"
        ),

        (
            r"Thyroid Function Test",
            "Thyroid Function Test"
        ),

        (
            r"Vitamin D",
            "Vitamin D"
        ),

        (
            r"Vitamin B12",
            "Vitamin B12"
        ),

        (
            r"Urinalysis|Urine Examination",
            "Urinalysis"
        ),

        (
            r"HB Electrophoresis",
            "Hb Electrophoresis"
        )
    ]


    for pattern, name in test_patterns:

        if re.search(
            pattern,
            text,
            re.IGNORECASE
        ):

            detected_tests.append(name)


    if len(detected_tests) > 1:

        return "Multiple Laboratory Tests"


    if len(detected_tests) == 1:

        return detected_tests[0]


    return "Not Available"


# ============================================================
# QUALITATIVE TEST RESULT
# ============================================================

def extract_test_result(
    text,
    report_type
):

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


    total = len(parameter_analysis)

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
        f"within the extracted reference range, while "
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

                "name": name,

                "value": data["value"],

                "unit": data["unit"],

                "status": status,

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
        # EXTRACT TEXT
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
                            page_text + "\n"
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


        # ====================================================
        # SESSION
        # ====================================================

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

    analysis_id = session.get("analysis_id")

    data = analysis_store.get(
        analysis_id
    )

    # --------------------------------------------------------
    # NO REPORT AVAILABLE
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # REPORT DATA
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # GENERAL BASE GUIDANCE
    # --------------------------------------------------------

    dietary_guidance.extend([

        "Include a variety of vegetables and seasonal fruits",

        "Prefer whole grains and minimally processed cereals",

        "Include suitable protein-rich foods such as dal, beans, legumes, curd or other appropriate sources",

        "Include nuts and seeds in appropriate portions",

        "Maintain adequate water intake"

    ])


    # --------------------------------------------------------
    # REPORT-SPECIFIC GUIDANCE
    # --------------------------------------------------------

    for name, parameter in parameter_analysis.items():

        status = parameter.get(
            "status",
            ""
        )

        name_lower = name.lower()


        # ====================================================
        # BLOOD SUGAR / HBA1C
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
                "Very High",
                "Borderline High"
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


    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # GENERAL MESSAGE
    # --------------------------------------------------------

    guidance_message = (

        "The guidance below uses the parameters extracted from "
        "the uploaded laboratory report. It provides general "
        "educational information and does not replace a "
        "personalized medical or dietary plan."

    )


    # --------------------------------------------------------
    # SEND DATA TO TEMPLATE
    # --------------------------------------------------------

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

        dietary_guidance=dietary_guidance,

        limiting_guidance=limiting_guidance,

        health_habits=health_habits,

        guidance_message=guidance_message,

        parameter_analysis=parameter_analysis

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
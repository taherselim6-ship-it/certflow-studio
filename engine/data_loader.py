"""
engine/data_loader.py
Handles fetching and parsing trainee data from Google Sheets, Excel (.xlsx, .xls), and CSV.
Performs text hygiene, timestamp time-stripping, date formatting, and auto-mapping.
"""

import io
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple, Union
import httpx
import pandas as pd
from dateutil import parser as date_parser

# Common column name heuristics for automatic 3-way binding
NAME_CANDIDATES = [
    "اسم المتدرب", "اسم المتدربة", "اسم المشارك", "اسم الطالب", "الاسم الكامل", "الاسم الثلاثي",
    "trainee_name", "traineename", "participant_name", "student_name", "full_name", "fullname",
    "الاسم", "name"
]

DATE_CANDIDATES = [
    "training_date", "trainingdate", "date", "timestamp",
    "تاريخ التدريب", "التاريخ", "تاريخ الدورة", "تاريخ البرنامج", "وقت التسجيل", "طابع زمني"
]

CUSTOM_CANDIDATES = [
    "custom_text", "customtext", "custom", "notes", "grade", "remarks",
    "نص إضافي", "التقدير", "ملاحظات", "النتيجة", "المسار"
]

TRAINER_CANDIDATES = [
    "trainer_name", "trainer", "trainername", "instructor", "instructor_name",
    "اسم المدرب", "المدرب", "اسم المحاضر", "المحاضر", "اسم المعلم"
]

CERT_CANDIDATES = [
    "certificate_template", "certificatetemplate", "template_name", "templatename",
    "certificate_status", "cert_status", "template", "قالب الشهادة", "اسم القالب",
    "حالة الشهادة", "تم إصدار الشهادة", "تم الإصدار", "is_issued", "issued_template"
]

ARABIC_REGEX = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)

ARABIC_MONTHS = [
    "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
]

ENGLISH_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

ARABIC_DIGITS_TABLE = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def to_arabic_indic_digits(s: Union[int, str]) -> str:
    """Converts standard Latin digits 0-9 into Arabic-Indic digits ٠-٩."""
    return str(s).translate(ARABIC_DIGITS_TABLE)


def is_arabic_text(text: str) -> bool:
    """Checks if text contains Arabic characters."""
    if not text:
        return False
    return bool(ARABIC_REGEX.search(str(text)))


def clean_text(val: Any) -> str:
    """
    Strict text hygiene:
    Trims leading/trailing whitespace and collapses multiple internal spaces/tabs into a single space.
    Preserves all Arabic letters, tashkeel, and hamzas (أ, إ, آ, etc.) 100%.
    """
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    s = re.sub(r"[ \t\u00A0\u2000-\u200B]+", " ", s)
    return s


def convert_google_sheet_url_to_export(url: str) -> Tuple[str, str, str]:
    """
    Converts various Google Sheets or Apps Script Web App URLs into direct CSV export URLs:
      - https://script.google.com/macros/s/{ID}/exec (doGet returning CSV)
      - https://docs.google.com/spreadsheets/d/{ID}/edit#gid={GID}
      - https://docs.google.com/spreadsheets/d/{ID}/edit?usp=sharing
      - https://docs.google.com/spreadsheets/d/e/{ID}/pubhtml
    Returns (export_url, gviz_url, sheet_id).
    """
    clean_url = url.strip()
    if not clean_url:
        raise ValueError("رابط جوجل شيت فارغ")

    # Check for Google Apps Script Web App URLs (doGet returning CSV)
    if "script.google.com/macros/s/" in clean_url or "script.googleusercontent.com" in clean_url:
        return clean_url, clean_url, "apps_script"

    # Check for /pubhtml
    if "/pubhtml" in clean_url:
        pub_csv = clean_url.replace("/pubhtml", "/pub?output=csv")
        return pub_csv, pub_csv, "pub"

    # Extract Sheet ID
    match = re.search(r"/spreadsheets/d/(?:e/)?([a-zA-Z0-9-_]+)", clean_url)
    if not match:
        # If it's already an export link or gviz link
        if "format=csv" in clean_url or "output=csv" in clean_url:
            return clean_url, clean_url, "direct"
        raise ValueError("تعذر استخراج معرّف جدول جوجل شيت من الرابط المدخل")

    sheet_id = match.group(1)
    is_e_pub = "/spreadsheets/d/e/" in clean_url

    # Extract gid (worksheet ID) if present
    gid_match = re.search(r"[#&?]gid=([0-9]+)", clean_url)
    gid_param = f"&gid={gid_match.group(1)}" if gid_match else ""

    if is_e_pub:
        export_url = f"https://docs.google.com/spreadsheets/d/e/{sheet_id}/pub?output=csv{gid_param}"
        gviz_url = export_url
    else:
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv{gid_param}"
        gviz_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv{gid_param}"
    return export_url, gviz_url, sheet_id


def deduplicate_header(col_name: str) -> str:
    """
    Cleans and deduplicates headers duplicated by Google Sheets Table views (e.g. 'TimestampTimestamp' -> 'Timestamp').
    """
    s = clean_text(col_name)
    if not s:
        return s
    words = s.split()
    if len(words) >= 2 and len(words) % 2 == 0:
        half_w = len(words) // 2
        if [w.lower() for w in words[:half_w]] == [w.lower() for w in words[half_w:]]:
            return " ".join(words[:half_w])
    n = len(s)
    if n >= 4 and n % 2 == 0:
        half = n // 2
        if s[:half].lower() == s[half:].lower():
            return s[:half]
    return s


def is_date_range_or_custom(s: str) -> bool:
    """
    Checks if a string represents a human-readable multi-day date range or custom date text
    e.g. '1-2 November 2026', '31 Oct - 1 Nov 2026', '31 October - 1 November 2026',
    '1, 3 & 5 November 2026', '10 & 12 Nov 2026', '31 Dec 2026 - 1 Jan 2027',
    '1 إلى 2 نوفمبر 2026', '1، 3 و 5 نوفمبر 2026'.
    """
    if not s:
        return False
    s_clean = str(s).strip()

    # Exclude standard single dates first
    # 1. YYYY-MM-DD or YYYY/MM/DD with optional time
    if re.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}(?:[ T].*)?$", s_clean):
        return False
    # 2. DD-MM-YYYY or M/D/YYYY with optional time
    if re.match(r"^\d{1,2}[-/.]\d{1,2}[-/.]\d{4}(?:[ T].*)?$", s_clean):
        return False

    # Check for multi-day indicators: '&', 'and', 'to', 'until', 'through', 'إلى', 'وحتى'
    if re.search(r"(&|\band\b|\bto\b|\buntil\b|\bthrough\b|إلى|وحتى|–|—)", s_clean, re.IGNORECASE):
        return True

    # Check for multiple days with commas: e.g. '1, 3' or '1، 3'
    if re.search(r"\d{1,2}\s*[,،]\s*\d{1,2}", s_clean):
        return True

    # Check for Arabic 'و' joining day numbers: e.g. '1 و 2'
    if re.search(r"\d{1,2}\s+و\s*\d{1,2}", s_clean):
        return True

    # Check for hyphen accompanied by alphabetic month name (Arabic or English)
    # e.g., '1-2 November 2026', '31 Oct - 1 Nov 2026', '31 Dec 2026 - 1 Jan 2027'
    if re.search(r"[-–—]", s_clean) and re.search(r"[A-Za-z\u0600-\u06FF]{3,}", s_clean):
        return True

    # Check for hyphenated day range: e.g. '1-2'
    if re.search(r"^\d{1,2}\s*[-–—]\s*\d{1,2}\b", s_clean):
        return True

    return False


def strip_time_from_timestamp(s: str) -> str:
    """
    Strips trailing timestamp time portion (e.g. '00:00:00' or '10:12:09')
    without mangling date ranges or human text.
    """
    if not s:
        return ""
    s_clean = str(s).strip()
    if is_date_range_or_custom(s_clean):
        return s_clean
    m = re.match(r"^(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})[ T](\d{1,2}:\d{2}(?::\d{2})?.*)$", s_clean)
    if m:
        return m.group(1).strip()
    return s_clean


def parse_and_strip_date(val: Any) -> Tuple[Optional[date], str]:
    """
    Parses a timestamp/date string, strips any time portion (HH:MM:SS),
    and returns (date_obj, iso_date_string YYYY-MM-DD or custom date string).
    If the value is already a human-readable date range or custom text (e.g. '1-2 November 2026'),
    returns (None, exact_trimmed_string) without rejecting or mangling it.
    """
    if val is None or pd.isna(val):
        return None, ""

    if isinstance(val, (datetime, pd.Timestamp)):
        d_obj = val.date()
        return d_obj, d_obj.strftime("%Y-%m-%d")
    elif isinstance(val, date):
        return val, val.strftime("%Y-%m-%d")

    raw_str = clean_text(val)
    if not raw_str:
        return None, ""

    # Check for date range or custom text first: preserve exact string
    if is_date_range_or_custom(raw_str):
        return None, raw_str

    clean_date_str = strip_time_from_timestamp(raw_str)

    # If it's already YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", clean_date_str):
        try:
            parts = clean_date_str.split("-")
            d_obj = date(int(parts[0]), int(parts[1]), int(parts[2]))
            return d_obj, clean_date_str
        except Exception:
            pass

    # Try dateutil parser on clean_date_str
    try:
        dt = date_parser.parse(clean_date_str, dayfirst=True)
        d_obj = dt.date()
        return d_obj, d_obj.strftime("%Y-%m-%d")
    except Exception:
        pass

    # Fallback: Regex for YYYY-MM-DD or DD-MM-YYYY or YYYY/MM/DD or DD/MM/YYYY
    match = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", clean_date_str)
    if match:
        y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            d_obj = date(y, m, d)
            return d_obj, d_obj.strftime("%Y-%m-%d")
        except Exception:
            pass

    match2 = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", clean_date_str)
    if match2:
        d, m, y = int(match2.group(1)), int(match2.group(2)), int(match2.group(3))
        try:
            d_obj = date(y, m, d)
            return d_obj, d_obj.strftime("%Y-%m-%d")
        except Exception:
            pass

    return None, clean_date_str


def format_display_date(
    raw_date_str: str,
    target_format: str = "MONTH_DAY_YEAR_AUTO",
    trainee_name: str = ""
) -> str:
    """
    Formats a date string into operator-selected format:
      - 'MONTH_DAY_YEAR_AUTO': Formats as 'يناير ١٩، ٢٠٢٦' if trainee is Arabic, else 'January 19, 2026'
      - 'MONTH_DAY_YEAR_AR': Always Arabic: 'يناير ١٩، ٢٠٢٦'
      - 'MONTH_DAY_YEAR_EN': Always English: 'January 19, 2026'
      - 'DD-MM-YYYY'
      - 'YYYY-MM-DD'
      - 'DD/MM/YYYY'
      - 'YYYY/MM/DD'
      - 'As-Is'
    """
    if not raw_date_str or target_format == "As-Is":
        return raw_date_str or ""

    # Human-readable date range or custom text: return exact string as-is
    if is_date_range_or_custom(raw_date_str):
        return raw_date_str

    d_obj, _ = parse_and_strip_date(raw_date_str)
    if not d_obj:
        return raw_date_str

    if target_format == "MONTH_DAY_YEAR_AUTO":
        if is_arabic_text(trainee_name):
            target_format = "MONTH_DAY_YEAR_AR"
        else:
            target_format = "MONTH_DAY_YEAR_EN" if trainee_name else "MONTH_DAY_YEAR_AR"

    if target_format == "MONTH_DAY_YEAR_AR":
        m_name = ARABIC_MONTHS[d_obj.month] if 1 <= d_obj.month <= 12 else str(d_obj.month)
        ar_day = to_arabic_indic_digits(d_obj.day)
        ar_year = to_arabic_indic_digits(d_obj.year)
        return f"{m_name} {ar_day}، {ar_year}"

    elif target_format == "MONTH_DAY_YEAR_EN":
        m_name = ENGLISH_MONTHS[d_obj.month] if 1 <= d_obj.month <= 12 else str(d_obj.month)
        return f"{m_name} {d_obj.day}, {d_obj.year}"

    elif target_format == "DD-MM-YYYY":
        return d_obj.strftime("%d-%m-%Y")
    elif target_format == "DD/MM/YYYY":
        return d_obj.strftime("%d/%m/%Y")
    elif target_format == "YYYY/MM/DD":
        return d_obj.strftime("%Y/%m/%d")
    elif target_format == "YYYY-MM-DD":
        return d_obj.strftime("%Y-%m-%d")

    return raw_date_str


def normalize_trainer_name(name: str) -> str:
    """
    Flexible normalization for comparing trainer names across spelling and transliteration:
      - Convert to lowercase and strip whitespace
      - Replace hyphens '-' and underscores '_' with spaces, and collapse multiple spaces
      - Normalize common Arabic-to-English transliteration vowel variations (saif <-> seif, el <-> al)
      - Normalize Arabic letter variants (أ/إ/آ -> ا, ة -> ه, ى -> ي)
    """
    if not name:
        return ""
    s = str(name).strip().lower()
    # Replace punctuation, hyphens, and underscores with space
    s = re.sub(r"[-_.,/]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    # Normalize Arabic letters
    s = re.sub(r"[إأآٱ]", "ا", s)
    s = re.sub(r"ة", "ه", s)
    s = re.sub(r"ى", "ي", s)

    # Transliteration vowel variations
    s = re.sub(r"\b(al|el)\b", "el", s)
    s = re.sub(r"\b(saif|seif)\b", "seif", s)

    return s


def trainer_names_match(n1: str, n2: str) -> bool:
    """
    Checks if two trainer names match flexibly.
    """
    norm1 = normalize_trainer_name(n1)
    norm2 = normalize_trainer_name(n2)
    if not norm1 or not norm2:
        return False
    if norm1 == norm2:
        return True
    w1 = norm1.split()
    w2 = norm2.split()
    s1 = set(w1)
    s2 = set(w2)
    if s1 and s2 and (s1.issubset(s2) or s2.issubset(s1)):
        return True
    return False


def detect_columns(columns: List[str], preferred_name_col: str = "", preferred_time_col: str = "") -> Dict[str, str]:
    """
    Finds the best matching column headers for trainee_name, training_date, custom_text, and trainer_name.
    """
    mapping = {
        "name_col": "",
        "date_col": "",
        "custom_col": "",
        "trainer_col": "",
    }

    # 1. Check user preferred columns first
    if preferred_name_col:
        for col in columns:
            if col.strip() == preferred_name_col.strip():
                mapping["name_col"] = col
                break

    if preferred_time_col:
        for col in columns:
            if col.strip() == preferred_time_col.strip():
                mapping["date_col"] = col
                break

    # 2. Heuristic check for Name (excluding trainer columns)
    if not mapping["name_col"]:
        for cand in NAME_CANDIDATES:
            for col in columns:
                clean_c = col.strip().lower().replace("_", "").replace(" ", "")
                clean_cand = cand.lower().replace("_", "").replace(" ", "")
                # Exclude columns that are trainer indicators when searching for trainee name
                if any(t in clean_c for t in ["trainer", "instructor", "مدرب", "محاضر"]):
                    continue
                if clean_cand == clean_c or clean_cand in clean_c or clean_c in clean_cand:
                    mapping["name_col"] = col
                    break
            if mapping["name_col"]:
                break

    # 3. Heuristic check for Date / Timestamp
    if not mapping["date_col"]:
        for cand in DATE_CANDIDATES:
            for col in columns:
                clean_c = col.strip().lower().replace("_", "").replace(" ", "")
                clean_cand = cand.lower().replace("_", "").replace(" ", "")
                if clean_cand in clean_c or clean_c in clean_cand:
                    mapping["date_col"] = col
                    break
            if mapping["date_col"]:
                break

    # 4. Heuristic check for Custom Text
    for cand in CUSTOM_CANDIDATES:
        for col in columns:
            clean_c = col.strip().lower().replace("_", "").replace(" ", "")
            clean_cand = cand.lower().replace("_", "").replace(" ", "")
            if clean_cand in clean_c or clean_c in clean_cand:
                mapping["custom_col"] = col
                break
        if mapping["custom_col"]:
            break

    # 5. Heuristic check for Trainer Column
    for cand in TRAINER_CANDIDATES:
        for col in columns:
            clean_c = col.strip().lower().replace("_", "").replace(" ", "")
            clean_cand = cand.lower().replace("_", "").replace(" ", "")
            if clean_cand in clean_c or clean_c in clean_cand:
                mapping["trainer_col"] = col
                break
        if mapping["trainer_col"]:
            break

    # Fallbacks if still empty
    if not mapping["name_col"] and len(columns) > 0:
        mapping["name_col"] = columns[0]
    if not mapping["date_col"] and len(columns) > 1:
        mapping["date_col"] = columns[1]

    return mapping


def process_dataframe_records(
    df: pd.DataFrame,
    name_col: str,
    date_col: str,
    custom_col: str = "",
    fixed_date: str = "",
    target_date_format: str = "MONTH_DAY_YEAR_AUTO",
    filter_date: Optional[str] = None,
    trainer_name: str = "",
    trainer_col: str = "",
) -> Dict[str, Any]:
    """
    Cleans DataFrame rows, applies text hygiene, strips times from timestamps,
    extracts unique dates with counts, filters flexibly by trainer name and date.
    Returns synchronized keys in both lowercase and TitleCase.
    """
    records = []
    date_stats: Dict[str, Dict[str, int]] = {}
    raw_rows_list = []

    # Detect Certificate_Template column if present
    cert_col = None
    for c in df.columns:
        if c == name_col:
            continue
        c_clean = deduplicate_header(clean_text(c)).lower().replace("_", " ").replace("-", " ")
        if any(term in c_clean for term in ["shown on", "will be shown", "your name", "اسمك", "participant"]):
            continue
        for cand in CERT_CANDIDATES:
            cand_clean = cand.lower().replace("_", " ")
            if cand_clean in c_clean or c_clean == cand_clean:
                cert_col = c
                break
        if cert_col:
            break

    for idx, row in df.iterrows():
        raw_name = row.get(name_col, "")
        clean_name = clean_text(raw_name)

        # Skip rows without trainee name
        if not clean_name:
            continue

        # Extract Date
        raw_date = row.get(date_col, "") if date_col else ""
        d_obj, iso_date = parse_and_strip_date(raw_date)

        if not iso_date and fixed_date:
            d_obj, iso_date = parse_and_strip_date(fixed_date)

        effective_iso = iso_date or str(raw_date)

        # Check if already issued
        issued_template = clean_text(row.get(cert_col, "")) if cert_col else ""
        is_issued = bool(issued_template)

        if effective_iso:
            if effective_iso not in date_stats:
                date_stats[effective_iso] = {"total": 0, "issued": 0, "unissued": 0}
            date_stats[effective_iso]["total"] += 1
            if is_issued:
                date_stats[effective_iso]["issued"] += 1
            else:
                date_stats[effective_iso]["unissued"] += 1

        formatted_date = format_display_date(
            effective_iso, target_format=target_date_format, trainee_name=clean_name
        )
        clean_custom = clean_text(row.get(custom_col, "")) if custom_col else ""
        row_trainer = clean_text(row.get(trainer_col, "")) if trainer_col else ""

        row_dict = {str(k): clean_text(v) for k, v in row.items()}
        raw_rows_list.append(row_dict)

        record_item = {
            "index": idx + 1,
            # Lowercase keys
            "trainee_name": clean_name,
            "training_date": formatted_date,
            "custom_text": clean_custom,
            "trainer_name": row_trainer,
            "iso_date": iso_date,
            "date_only": iso_date,
            "raw_date": str(raw_date),
            "issued_template": issued_template,
            "is_issued": is_issued,
            # TitleCase keys (for frontend compatibility)
            "Trainee_Name": clean_name,
            "Training_Date": formatted_date,
            "Custom_Text": clean_custom,
            "Trainer_Name": row_trainer,
            "Issued_Template": issued_template,
            "Is_Issued": is_issued,
            "raw_row": row_dict,
        }
        records.append(record_item)

    # Sort unique dates: dates with unissued trainees appear at TOP, all-issued pushed to BOTTOM
    sorted_by_date = sorted(list(date_stats.keys()), reverse=True)
    sorted_unique_dates = sorted(
        sorted_by_date,
        key=lambda d: date_stats[d]["unissued"] > 0,
        reverse=True
    )

    unique_dates_with_counts = []
    for d in sorted_unique_dates:
        st = date_stats[d]
        all_iss = (st["unissued"] == 0 and st["total"] > 0)
        unique_dates_with_counts.append({
            "date_str": d,
            "count": st["total"],
            "total_count": st["total"],
            "unissued_count": st["unissued"],
            "issued_count": st["issued"],
            "all_issued": all_iss,
        })

    # Filter records if filter_date is chosen and not "ALL"
    filtered_records = records
    if filter_date and filter_date != "ALL":
        filtered_records = [
            r for r in records
            if r.get("iso_date") == filter_date or r.get("date_only") == filter_date or r.get("training_date") == filter_date
        ]

    return {
        "total_count": len(filtered_records),
        "unfiltered_count": len(records),
        "records": filtered_records,
        "unfiltered_records": records,
        "unique_dates": unique_dates_with_counts,
        "unique_dates_raw": sorted_unique_dates,
        "raw_rows": raw_rows_list,
        "selected_date": filter_date or (sorted_unique_dates[0] if sorted_unique_dates else "ALL"),
        "mapping_used": {
            "name_col": name_col,
            "date_col": date_col,
            "custom_col": custom_col,
            "trainer_col": trainer_col,
        },
    }


async def fetch_google_sheet_records(
    sheet_url: str,
    name_col: str = "",
    time_col: str = "",
    trainer_name: str = "",
    filter_date: Optional[str] = None,
    target_date_format: str = "MONTH_DAY_YEAR_AUTO",
) -> Dict[str, Any]:
    """
    Fetches live Google Sheet via direct CSV export or gviz fallback,
    processes trainee records, and returns date filter options with clean records.
    """
    export_url, gviz_url, sheet_id = convert_google_sheet_url_to_export(sheet_url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    csv_content = None
    last_status = None

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
        # Try primary export URL
        try:
            res = await client.get(export_url)
            last_status = res.status_code
            if res.status_code == 200 and len(res.content) > 0:
                csv_content = res.content
        except Exception:
            pass

        # Fallback to gviz CSV URL if primary failed
        if csv_content is None and gviz_url != export_url:
            try:
                res_gviz = await client.get(gviz_url)
                last_status = res_gviz.status_code
                if res_gviz.status_code == 200 and len(res_gviz.content) > 0:
                    csv_content = res_gviz.content
            except Exception:
                pass

    if csv_content is None:
        if last_status in (401, 403):
            raise RuntimeError(
                "تعذر الوصول لجدول جوجل شيت لأن الجدول خاص (Private). "
                "يرجى التأكد من ضبط إعدادات المشاركة في جدول جوجل على 'أي شخص لديه الرابط يمكنه المشاهدة' (Anyone with the link can view)."
            )
        raise RuntimeError(
            f"فشل تنزيل جدول جوجل شيت (رمز الاستجابة {last_status}). "
            "يرجى التأكد من صحة الرابط وضبط المشاركة على 'أي شخص لديه الرابط يمكنه المشاهدة'."
        )

    # Check if response is HTML error page (e.g. Apps Script login or unhandled error page)
    clean_snippet = csv_content[:200].strip().lower()
    if clean_snippet.startswith(b"<!doctype html") or clean_snippet.startswith(b"<html"):
        if sheet_id == "apps_script":
            raise RuntimeError(
                "أرجع Google Apps Script صفحة HTML بدلاً من بيانات CSV. "
                "يرجى التأكد من نشر تطبيق الويب (Deploy as Web App) واختيار: "
                "'Execute as: Me' و 'Who has access: Anyone'."
            )
        else:
            raise RuntimeError(
                "تعذر الوصول لجدول جوجل شيت لأن الرابط يتطلب تسجيل الدخول. "
                "يرجى التأكد من ضبط المشاركة على 'أي شخص لديه الرابط يمكنه المشاهدة'."
            )

    # Read into pandas
    try:
        df = pd.read_csv(io.BytesIO(csv_content), dtype=str)
    except Exception as e:
        raise RuntimeError(f"تعذر تحليل محتوى ملف CSV من جدول جوجل: {str(e)}")

    if df.empty:
        raise RuntimeError("جدول جوجل شيت المرفق لا يحتوي على أي صفوف بيانات")

    # Clean and deduplicate column headers immediately (e.g. 'TimestampTimestamp' -> 'Timestamp')
    df.columns = [deduplicate_header(clean_text(c)) for c in df.columns]
    columns = list(df.columns)
    mapping = detect_columns(columns, preferred_name_col=name_col, preferred_time_col=time_col)

    effective_name_col = name_col if name_col in columns else mapping["name_col"]
    effective_date_col = time_col if time_col in columns else mapping["date_col"]
    effective_trainer_col = mapping.get("trainer_col", "")

    result = process_dataframe_records(
        df=df,
        name_col=effective_name_col,
        date_col=effective_date_col,
        custom_col=mapping.get("custom_col", ""),
        target_date_format=target_date_format,
        filter_date=filter_date,
        trainer_name=trainer_name,
        trainer_col=effective_trainer_col,
    )

    result["available_columns"] = columns
    result["detected_columns"] = columns
    result["best_name_col"] = effective_name_col
    result["best_date_col"] = effective_date_col
    result["export_url"] = export_url
    return result


def parse_uploaded_file_records(
    file_bytes: bytes,
    filename: str,
    sheet_name: Optional[str] = None,
    name_col: str = "",
    date_col: str = "",
    custom_col: str = "",
    fixed_date: str = "",
    trainer_name: str = "",
    target_date_format: str = "MONTH_DAY_YEAR_AUTO",
    filter_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parses uploaded Excel (.xlsx, .xls) or .csv file with sheet inspection
    and column mapping. Returns synchronized keys for frontend.
    """
    lower_fn = filename.lower()
    is_excel = lower_fn.endswith(".xlsx") or lower_fn.endswith(".xls")

    available_sheets = []

    if is_excel:
        excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
        available_sheets = excel_file.sheet_names

        target_sheet = sheet_name if (sheet_name and sheet_name in available_sheets) else available_sheets[0]
        df = pd.read_excel(excel_file, sheet_name=target_sheet, dtype=str)
    else:
        # CSV parsing with encoding fallback
        target_sheet = "CSV"
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding="cp1256")

    if df.empty:
        raise ValueError("الملف المرفوع لا يحتوي على أي صفوف بيانات")

    # Clean and deduplicate column headers immediately
    df.columns = [deduplicate_header(clean_text(c)) for c in df.columns]
    columns = list(df.columns)
    mapping = detect_columns(columns, preferred_name_col=name_col, preferred_time_col=date_col)

    effective_name_col = name_col if name_col in columns else mapping["name_col"]
    effective_date_col = date_col if date_col in columns else mapping["date_col"]
    effective_custom_col = custom_col if custom_col in columns else mapping.get("custom_col", "")
    effective_trainer_col = mapping.get("trainer_col", "")

    result = process_dataframe_records(
        df=df,
        name_col=effective_name_col,
        date_col=effective_date_col,
        custom_col=effective_custom_col,
        fixed_date=fixed_date,
        target_date_format=target_date_format,
        filter_date=filter_date,
        trainer_name=trainer_name,
        trainer_col=effective_trainer_col,
    )

    result["available_columns"] = columns
    result["detected_columns"] = columns
    result["best_name_col"] = effective_name_col
    result["best_date_col"] = effective_date_col
    result["available_sheets"] = available_sheets
    result["active_sheet"] = target_sheet
    result["is_excel"] = is_excel

    return result

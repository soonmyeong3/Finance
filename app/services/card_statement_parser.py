"""Parses uploaded card statement files (CSV/PDF) into transaction dicts
ready for CardTransaction rows.

CSV: column names vary by card company, so header matching is heuristic
(a handful of known Korean variants per field). Tested against synthetic
fixtures — real-world files should be spot-checked against this once one
is available.

PDF: text extraction + a single regex line pattern (date, merchant name,
amount). This is the single biggest unverified assumption in this module
— real 카드사 명세서 PDF layouts vary a lot and none were available to
test against here. Treat this as a starting point, not a working parser
for an arbitrary bank's PDF, until it's run against a real file.
"""

import csv
import io
import re
from datetime import datetime

import pdfplumber

DATE_COLUMNS = {"이용일자", "거래일자", "이용일", "결제일자", "일자", "date"}
MERCHANT_COLUMNS = {"가맹점명", "가맹점", "이용가맹점", "적요", "merchant"}
AMOUNT_COLUMNS = {"이용금액", "거래금액", "금액", "승인금액", "amount"}

# Substring match against merchant name -> merchant_category bucket.
# Order matters: more specific keywords first.
MERCHANT_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("동물병원", ["동물병원", "동물의료", "펫클리닉"]),
    ("반려동물용품", ["펫샵", "펫프렌즈", "반려동물"]),
    ("치과", ["치과"]),
    ("병원", ["병원", "의원", "클리닉"]),
    ("약국", ["약국"]),
    ("편의점", ["GS25", "CU", "세븐일레븐", "이마트24", "편의점"]),
    ("마트", ["이마트", "홈플러스", "롯데마트", "코스트코", "마트"]),
    ("카페", ["스타벅스", "커피", "카페", "이디야", "투썸"]),
    ("주유소", ["주유소", "GS칼텍스", "SK에너지", "S-OIL", "주유"]),
    ("구내식당", ["구내식당", "사원식당"]),
]

DATE_FORMATS = ["%Y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y/%m/%d"]

PDF_LINE_PATTERN = re.compile(
    r"(?P<date>\d{4}[-./]\d{2}[-./]\d{2})\s+(?P<merchant>\S.*?\S)\s+(?P<amount>[\d,]+)\s*원?$"
)


def classify_merchant_category(merchant_name: str) -> str:
    for category, keywords in MERCHANT_CATEGORY_KEYWORDS:
        if any(keyword in merchant_name for keyword in keywords):
            return category
    return "기타"


def _parse_date(raw: str) -> datetime:
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognized date format: {raw!r}")


def _parse_amount(raw: str) -> float:
    return float(raw.replace(",", "").replace("원", "").strip())


def _find_column(header: list[str], candidates: set[str]) -> str | None:
    for col in header:
        if col.strip() in candidates:
            return col
    return None


def parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")  # handles Excel-exported UTF-8 BOM
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("empty CSV or no header row")

    header = list(reader.fieldnames)
    date_col = _find_column(header, DATE_COLUMNS)
    merchant_col = _find_column(header, MERCHANT_COLUMNS)
    amount_col = _find_column(header, AMOUNT_COLUMNS)

    missing = [
        name
        for name, col in [("date", date_col), ("merchant", merchant_col), ("amount", amount_col)]
        if col is None
    ]
    if missing:
        raise ValueError(f"could not find columns for: {', '.join(missing)} (header: {header})")

    transactions = []
    for row in reader:
        merchant_name = row[merchant_col].strip()
        transactions.append(
            {
                "merchant_category": classify_merchant_category(merchant_name),
                "merchant_name": merchant_name,
                "amount": _parse_amount(row[amount_col]),
                "occurred_at": _parse_date(row[date_col]),
            }
        )
    return transactions


def parse_pdf(content: bytes) -> list[dict]:
    transactions = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                match = PDF_LINE_PATTERN.search(line.strip())
                if not match:
                    continue
                merchant_name = match.group("merchant").strip()
                transactions.append(
                    {
                        "merchant_category": classify_merchant_category(merchant_name),
                        "merchant_name": merchant_name,
                        "amount": _parse_amount(match.group("amount")),
                        "occurred_at": _parse_date(match.group("date")),
                    }
                )

    if not transactions:
        raise ValueError(
            "no transaction lines matched — this PDF's layout doesn't match the "
            "assumed '날짜 가맹점명 금액' line format, needs a real sample to adapt to"
        )
    return transactions


def parse_statement(filename: str, content: bytes) -> list[dict]:
    lower = filename.lower()
    if lower.endswith(".csv"):
        return parse_csv(content)
    if lower.endswith(".pdf"):
        return parse_pdf(content)
    raise ValueError(f"unsupported file type: {filename}")

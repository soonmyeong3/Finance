import io

import pytest
from fpdf import FPDF

from app.services.card_statement_parser import (
    classify_merchant_category,
    parse_csv,
    parse_pdf,
    parse_statement,
)


def test_classify_merchant_category_by_keyword():
    assert classify_merchant_category("행복동물병원") == "동물병원"
    assert classify_merchant_category("서울대치과") == "치과"
    assert classify_merchant_category("온누리약국") == "약국"
    assert classify_merchant_category("GS25 강남점") == "편의점"
    assert classify_merchant_category("스타벅스 역삼점") == "카페"
    assert classify_merchant_category("알 수 없는 가게") == "기타"


def test_parse_csv_with_standard_headers():
    csv_content = (
        "이용일자,가맹점명,이용금액\n"
        "2026-08-01,행복동물병원,50000\n"
        "2026-08-15,GS25 강남점,4500\n"
    ).encode("utf-8-sig")

    rows = parse_csv(csv_content)

    assert len(rows) == 2
    assert rows[0]["merchant_category"] == "동물병원"
    assert rows[0]["merchant_name"] == "행복동물병원"
    assert rows[0]["amount"] == 50000.0
    assert rows[0]["occurred_at"].year == 2026
    assert rows[1]["merchant_category"] == "편의점"


def test_parse_csv_with_alternate_headers_and_comma_amount():
    # the amount field is quoted because it contains a comma thousands
    # separator — unquoted, that comma would split into an extra CSV column
    csv_content = (
        "거래일자,가맹점,거래금액\n"
        '20260810,서울대치과,"120,000"\n'
    ).encode("utf-8")

    rows = parse_csv(csv_content)

    assert len(rows) == 1
    assert rows[0]["merchant_category"] == "치과"
    assert rows[0]["amount"] == 120000.0


def test_parse_csv_missing_required_column_raises():
    csv_content = "날짜,상점\n2026-08-01,행복동물병원\n".encode("utf-8")

    with pytest.raises(ValueError, match="amount"):
        parse_csv(csv_content)


def _build_test_pdf(lines: list[str]) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for line in lines:
        pdf.cell(0, 10, text=line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def test_parse_pdf_extracts_matching_lines():
    content = _build_test_pdf(
        [
            "2026-08-01 Animal Hospital 50000",
            "2026-08-15 Coffee Shop 4500",
        ]
    )

    rows = parse_pdf(content)

    assert len(rows) == 2
    assert rows[0]["amount"] == 50000.0
    assert rows[0]["merchant_name"] == "Animal Hospital"


def test_parse_pdf_with_no_matching_lines_raises():
    content = _build_test_pdf(["This statement has no transaction rows"])

    with pytest.raises(ValueError, match="no transaction lines matched"):
        parse_pdf(content)


def test_parse_statement_dispatches_by_extension():
    csv_content = "이용일자,가맹점명,이용금액\n2026-08-01,행복동물병원,50000\n".encode("utf-8-sig")
    assert len(parse_statement("card.csv", csv_content)) == 1

    with pytest.raises(ValueError, match="unsupported file type"):
        parse_statement("card.xlsx", b"irrelevant")

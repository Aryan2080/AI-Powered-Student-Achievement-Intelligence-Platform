"""
src/nlp/create_test_fixtures.py
===============================
Generates auditable, reproducible test fixtures for evidence document ingestion.
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

from __future__ import annotations

import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pypdf


def build_text_pdf_bytes(lines: list[str]) -> bytes:
    """Build a standard text PDF with lines of text."""
    cmds = ["BT", "/F1 12 Tf", "50 750 Td"]
    for i, line in enumerate(lines):
        esc = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if i == 0:
            cmds.append(f"({esc}) Tj")
        else:
            cmds.append(f"0 -18 Td ({esc}) Tj")
    cmds.append("ET")
    stream = "\n".join(cmds)
    length = len(stream)
    content = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length {length} >> stream
{stream}
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000340 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
420
%%EOF"""
    # Sanitize xref using PdfWriter
    reader = pypdf.PdfReader(io.BytesIO(content.encode("latin1")))
    writer = pypdf.PdfWriter()
    writer.add_page(reader.pages[0])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def build_image_bytes(text_lines: list[str], fmt: str = "PNG") -> bytes:
    """Build a synthetic certificate image with rendered text."""
    img = Image.new("RGB", (800, 500), color=(250, 250, 252))
    draw = ImageDraw.Draw(img)
    # Border
    draw.rectangle([20, 20, 780, 480], outline=(40, 80, 160), width=4)
    draw.rectangle([28, 28, 772, 472], outline=(180, 150, 60), width=2)

    # Simple default font
    y = 60
    for line in text_lines:
        draw.text((60, y), line, fill=(30, 30, 40))
        y += 35

    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def generate_all_fixtures(output_dir: Path) -> dict[str, Path]:
    """Generate all document fixtures in the specified directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    created: dict[str, Path] = {}

    # 1. Valid single-page text PDF
    valid_pdf_path = output_dir / "valid_certificate.pdf"
    valid_pdf_bytes = build_text_pdf_bytes([
        "CERTIFICATE OF ACHIEVEMENT",
        "This certifies that Alex Rivera",
        "has achieved First Place in the National Collegiate Hackathon 2024",
        "Organized by the Association for Computing Machinery (ACM)",
        "Award Date: October 15, 2024",
        "Issued under Certificate ID: CERT-ACH-2024-9981"
    ])
    valid_pdf_path.write_bytes(valid_pdf_bytes)
    created["valid_pdf"] = valid_pdf_path

    # 2. Multi-page text PDF (3 pages)
    multipage_pdf_path = output_dir / "multipage_transcript.pdf"
    writer = pypdf.PdfWriter()
    for page_idx, title in enumerate([
        "Page 1: Academic Honors and Dean's List Recognitions 2022-2023",
        "Page 2: Research Fellowship in Distributed Artificial Intelligence",
        "Page 3: Capstone Design Competition Gold Medal Winner"
    ]):
        page_bytes = build_text_pdf_bytes([
            title,
            f"Official Record for Student ID: STU-8829 - Section {page_idx + 1}",
            "Verified by the Academic Awards and Honors Committee",
            "Cumulative Grade Point Average: 3.96 / 4.00"
        ])
        sub_reader = pypdf.PdfReader(io.BytesIO(page_bytes))
        writer.add_page(sub_reader.pages[0])
    buf = io.BytesIO()
    writer.write(buf)
    multipage_pdf_path.write_bytes(buf.getvalue())
    created["multipage_pdf"] = multipage_pdf_path

    # 3. Scanned Image-only PDF
    scanned_pdf_path = output_dir / "scanned_award.pdf"
    img_data = build_image_bytes([
        "STATE ROBOTICS CHAMPIONSHIP 2024",
        "Excellence in Autonomous Navigation Award",
        "Awarded to Team Quantum Dynamics",
        "Verification Hash: ROB-9912-VERIFIED"
    ], fmt="JPEG")
    pil_img = Image.open(io.BytesIO(img_data))
    pdf_img_buf = io.BytesIO()
    pil_img.save(pdf_img_buf, format="PDF")
    scanned_pdf_path.write_bytes(pdf_img_buf.getvalue())
    created["scanned_pdf"] = scanned_pdf_path

    # 4. PNG Image
    png_path = output_dir / "certificate_badge.png"
    png_bytes = build_image_bytes([
        "CLOUD ARCHITECT CERTIFIED ASSOCIATE",
        "Student Credential ID: AWS-CCA-7719",
        "Skills: Cloud Computing, Docker, Kubernetes",
        "Score: 920 / 1000 - Pass with Distinction"
    ], fmt="PNG")
    png_path.write_bytes(png_bytes)
    created["png"] = png_path

    # 5. JPEG Image
    jpg_path = output_dir / "honor_roll.jpg"
    jpg_bytes = build_image_bytes([
        "ANNUAL DEAN'S HONOR ROLL 2024",
        "Exemplary Academic Performance in Engineering",
        "School of Computer Science and Mathematics"
    ], fmt="JPEG")
    jpg_path.write_bytes(jpg_bytes)
    created["jpeg"] = jpg_path

    # 6. Empty Document (0 bytes)
    empty_path = output_dir / "empty_doc.pdf"
    empty_path.write_bytes(b"")
    created["empty"] = empty_path

    # 7. Corrupted PDF
    corrupt_path = output_dir / "corrupt_doc.pdf"
    corrupt_path.write_bytes(b"%PDF-INVALID_CORRUPTED_STREAM_DATA_XXXXX\x00\xff")
    created["corrupt"] = corrupt_path

    # 8. Unsupported Format (.docx)
    unsupported_path = output_dir / "unsupported_report.docx"
    unsupported_path.write_bytes(b"PK\x03\x04\x14\x00Mock Word Document Format Bytes")
    created["unsupported"] = unsupported_path

    # 9. Hybrid PDF (Page 1 Native Text, Page 2 Scanned Image)
    hybrid_path = output_dir / "hybrid_portfolio.pdf"
    hybrid_writer = pypdf.PdfWriter()
    p1_bytes = build_text_pdf_bytes([
        "PORTFOLIO COVER SHEET - NATIVE TEXT",
        "Candidate: Morgan Lee - Senior Portfolio Submission",
        "Index of Attached Verified Credentials"
    ])
    hybrid_writer.add_page(pypdf.PdfReader(io.BytesIO(p1_bytes)).pages[0])
    hybrid_writer.add_page(pypdf.PdfReader(io.BytesIO(pdf_img_buf.getvalue())).pages[0])
    h_buf = io.BytesIO()
    hybrid_writer.write(h_buf)
    hybrid_path.write_bytes(h_buf.getvalue())
    created["hybrid_pdf"] = hybrid_path

    return created


if __name__ == "__main__":
    fixtures_dir = Path("tests/fixtures/documents")
    res = generate_all_fixtures(fixtures_dir)
    print(f"Generated {len(res)} fixtures in {fixtures_dir}")
    for k, v in res.items():
        print(f"  {k}: {v.name} ({v.stat().st_size} bytes)")

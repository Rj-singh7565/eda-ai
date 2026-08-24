"""
Extraction Service — Format-independent extractors for PDF, DOCX, PPTX, Excel, CSV, TXT, MD, and Images (OCR).
"""

import os
import re
from typing import List, Dict, Any

from pypdf import PdfReader

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    pdfplumber = None
    HAS_PDFPLUMBER = False


def extract_table_as_markdown(table: List[List[Any]]) -> str:
    """Convert a raw table matrix into a Markdown formatted table."""
    if not table or not any(table):
        return ""
    
    clean_rows = []
    for row in table:
        if row and any(cell is not None and str(cell).strip() for cell in row):
            clean_rows.append([str(cell).strip().replace("\n", " ") if cell is not None else "" for cell in row])
            
    if not clean_rows:
        return ""
        
    headers = clean_rows[0]
    markdown = "| " + " | ".join(headers) + " |\n"
    markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    
    for row in clean_rows[1:]:
        if len(row) < len(headers):
            row.extend([""] * (len(headers) - len(row)))
        elif len(row) > len(headers):
            row = row[:len(headers)]
        markdown += "| " + " | ".join(row) + " |\n"
        
    return markdown


def extract_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """Extract text and structured tables per page from PDF files."""
    pages_data = []
    tables_per_page = {}
    
    if HAS_PDFPLUMBER and pdfplumber:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    extracted_tables = page.extract_tables()
                    md_tables = []
                    for tbl in extracted_tables:
                        md_tbl = extract_table_as_markdown(tbl)
                        if md_tbl:
                            md_tables.append(md_tbl)
                    if md_tables:
                        tables_per_page[i] = md_tables
        except Exception as e:
            print(f"[EXTRACTION] pdfplumber table extraction warning: {e}")

    reader = PdfReader(pdf_path)
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        tables = tables_per_page.get(i, [])
        if text or tables:
            pages_data.append({
                "page": i,
                "page_label": f"Page {i}",
                "text": text,
                "tables": tables
            })
            
    return pages_data


def extract_docx(docx_path: str) -> List[Dict[str, Any]]:
    """Extract paragraphs and tables from Microsoft Word (.docx) files."""
    import docx
    doc = docx.Document(docx_path)
    
    sections_data = []
    current_text = []
    current_tables = []
    section_index = 1

    for elem in doc.element.body:
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "p":
            para = docx.text.paragraph.Paragraph(elem, doc)
            text = para.text.strip()
            if text:
                current_text.append(text)
                if sum(len(t) for t in current_text) >= 1500:
                    sections_data.append({
                        "page": section_index,
                        "page_label": f"Section {section_index}",
                        "text": "\n\n".join(current_text),
                        "tables": current_tables
                    })
                    section_index += 1
                    current_text = []
                    current_tables = []
        elif tag == "tbl":
            tbl = docx.table.Table(elem, doc)
            matrix = []
            for row in tbl.rows:
                matrix.append([cell.text.strip() for cell in row.cells])
            md_tbl = extract_table_as_markdown(matrix)
            if md_tbl:
                current_tables.append(md_tbl)

    if current_text or current_tables:
        sections_data.append({
            "page": section_index,
            "page_label": f"Section {section_index}",
            "text": "\n\n".join(current_text),
            "tables": current_tables
        })

    return sections_data


def extract_pptx(pptx_path: str) -> List[Dict[str, Any]]:
    """Extract slide text, tables, and speaker notes from PowerPoint (.pptx) files."""
    from pptx import Presentation
    prs = Presentation(pptx_path)
    
    slides_data = []
    for i, slide in enumerate(prs.slides, start=1):
        slide_text_parts = []
        slide_tables = []
        
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text.strip()
                if text:
                    slide_text_parts.append(text)
            elif shape.has_table:
                matrix = []
                for row in shape.table.rows:
                    matrix.append([cell.text.strip() for cell in row.cells])
                md_tbl = extract_table_as_markdown(matrix)
                if md_tbl:
                    slide_tables.append(md_tbl)
                    
        notes = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            
        full_text = "\n\n".join(slide_text_parts)
        if notes:
            full_text += f"\n\n*Speaker Notes*: {notes}"
            
        if full_text or slide_tables:
            slides_data.append({
                "page": i,
                "page_label": f"Slide {i}",
                "text": full_text,
                "tables": slide_tables
            })

    return slides_data


def extract_excel(excel_path: str) -> List[Dict[str, Any]]:
    """Extract worksheets from Excel (.xlsx/.xls) into 50-row batch sections."""
    import pandas as pd
    excel_file = pd.ExcelFile(excel_path)
    
    sheets_data = []
    section_counter = 1

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        df = df.dropna(how="all")
        if df.empty:
            continue
            
        total_rows = len(df)
        batch_size = 50
        
        for start_idx in range(0, total_rows, batch_size):
            end_idx = min(start_idx + batch_size, total_rows)
            chunk_df = df.iloc[start_idx:end_idx]
            
            headers = [str(c).strip() for c in chunk_df.columns]
            matrix = [headers]
            for _, row in chunk_df.iterrows():
                matrix.append([str(val).strip() if pd.notna(val) else "" for val in row])
                
            md_tbl = extract_table_as_markdown(matrix)
            label = f"Sheet '{sheet_name}' (Rows {start_idx + 1}-{end_idx})"
            
            sheets_data.append({
                "page": section_counter,
                "page_label": label,
                "text": md_tbl,
                "tables": [md_tbl]
            })
            section_counter += 1

    return sheets_data


def extract_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Extract CSV file into row batch sections with encoding fallback."""
    import pandas as pd
    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
    df = None
    
    for enc in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=enc)
            break
        except Exception:
            continue
            
    if df is None:
        raise ValueError(f"Failed to parse CSV file with standard encodings: {csv_path}")

    df = df.dropna(how="all")
    if df.empty:
        return []
        
    csv_data = []
    total_rows = len(df)
    batch_size = 50
    section_counter = 1
    
    for start_idx in range(0, total_rows, batch_size):
        end_idx = min(start_idx + batch_size, total_rows)
        chunk_df = df.iloc[start_idx:end_idx]
        
        headers = [str(c).strip() for c in chunk_df.columns]
        matrix = [headers]
        for _, row in chunk_df.iterrows():
            matrix.append([str(val).strip() if pd.notna(val) else "" for val in row])
            
        md_tbl = extract_table_as_markdown(matrix)
        label = f"Rows {start_idx + 1}-{end_idx}"
        
        csv_data.append({
            "page": section_counter,
            "page_label": label,
            "text": md_tbl,
            "tables": [md_tbl]
        })
        section_counter += 1

    return csv_data


def extract_excel_csv(file_path: str, file_type: str = "csv") -> List[Dict[str, Any]]:
    """Legacy helper router for Excel / CSV extraction."""
    if file_type == "excel" or file_path.endswith((".xlsx", ".xls")):
        return extract_excel(file_path)
    return extract_csv(file_path)


def extract_txt_md(file_path: str) -> List[Dict[str, Any]]:
    """Extract text from plain text or Markdown files."""
    content = ""
    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.read()
            break
        except Exception:
            continue

    if not content.strip():
        return []

    paragraphs = re.split(r"\n\s*\n", content.strip())
    pages_data = []
    current_chunk = []
    chunk_index = 1

    for para in paragraphs:
        current_chunk.append(para.strip())
        if sum(len(p) for p in current_chunk) >= 1500:
            pages_data.append({
                "page": chunk_index,
                "page_label": f"Page {chunk_index}",
                "text": "\n\n".join(current_chunk),
                "tables": []
            })
            chunk_index += 1
            current_chunk = []

    if current_chunk:
        pages_data.append({
            "page": chunk_index,
            "page_label": f"Page {chunk_index}",
            "text": "\n\n".join(current_chunk),
            "tables": []
        })

    return pages_data


def extract_image_ocr(image_path: str) -> List[Dict[str, Any]]:
    """Extract text from images using Pillow and pytesseract OCR."""
    from PIL import Image
    import pytesseract

    img = Image.open(image_path)
    text = pytesseract.image_to_string(img).strip()

    if not text:
        text = "[OCR: No readable text detected in image.]"

    filename = os.path.basename(image_path)
    return [{
        "page": 1,
        "page_label": f"Image {filename}",
        "text": text,
        "tables": []
    }]

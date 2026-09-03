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


def _generate_dataframe_eda_sections(df, dataset_label: str = "Dataset", section_start: int = 1) -> List[Dict[str, Any]]:
    """
    Intelligently generate semantic EDA sections for large tabular datasets (100k+ rows).
    Produces schema, descriptive statistics, categorical distributions, correlation insights,
    and representative stratified sample records instead of naive row-by-row dumping.
    """
    import pandas as pd
    import numpy as np

    total_rows, total_cols = df.shape
    sections_data = []
    sec_idx = section_start

    # Section 1: Overview & Schema
    schema_rows = [["Column Name", "Data Type", "Non-Null Count", "Missing Count", "Null %"]]
    for col in df.columns:
        non_null = int(df[col].notna().sum())
        missing = total_rows - non_null
        pct_missing = f"{(missing / total_rows) * 100:.1f}%" if total_rows > 0 else "0.0%"
        dtype_str = str(df[col].dtype)
        schema_rows.append([str(col), dtype_str, str(non_null), str(missing), pct_missing])
    
    schema_table = extract_table_as_markdown(schema_rows)
    overview_text = (
        f"**{dataset_label} Overview**\n"
        f"- **Total Records / Rows**: {total_rows:,}\n"
        f"- **Total Attributes / Columns**: {total_cols}\n"
        f"- **Columns List**: {', '.join([str(c) for c in df.columns])}\n\n"
        f"### Data Schema & Types\n\n{schema_table}"
    )
    sections_data.append({
        "page": sec_idx,
        "page_label": f"{dataset_label} - Overview & Schema",
        "text": overview_text,
        "tables": [schema_table]
    })
    sec_idx += 1

    # Section 2: Numeric Statistical Summary
    numeric_df = df.select_dtypes(include=[np.number])
    if not numeric_df.empty:
        desc = numeric_df.describe().T
        stats_rows = [["Feature", "Count", "Mean", "Std Dev", "Min", "25%", "50% (Median)", "75%", "Max"]]
        for col, row in desc.iterrows():
            def fmt_num(v):
                if pd.isna(v):
                    return "N/A"
                return f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)
            stats_rows.append([
                str(col),
                str(int(row.get("count", 0))),
                fmt_num(row.get("mean")),
                fmt_num(row.get("std")),
                fmt_num(row.get("min")),
                fmt_num(row.get("25%")),
                fmt_num(row.get("50%")),
                fmt_num(row.get("75%")),
                fmt_num(row.get("max")),
            ])
        stats_table = extract_table_as_markdown(stats_rows)
        sections_data.append({
            "page": sec_idx,
            "page_label": f"{dataset_label} - Statistical Summary",
            "text": f"### Numeric Statistical Metrics ({len(numeric_df.columns)} numeric columns)\n\n{stats_table}",
            "tables": [stats_table]
        })
        sec_idx += 1

    # Section 3: Categorical Distributions & Cardinality
    cat_df = df.select_dtypes(exclude=[np.number])
    if not cat_df.empty:
        cat_rows = [["Column", "Unique Values", "Top Categories (Frequency)"]]
        for col in cat_df.columns:
            val_counts = df[col].value_counts(dropna=False)
            unique_cnt = len(val_counts)
            top_items = []
            for val, cnt in val_counts.head(5).items():
                val_str = "None/Null" if pd.isna(val) else str(val).replace("\n", " ").strip()[:30]
                pct = (cnt / total_rows * 100) if total_rows > 0 else 0
                top_items.append(f"{val_str}: {cnt:,} ({pct:.1f}%)")
            top_str = "; ".join(top_items)
            cat_rows.append([str(col), str(unique_cnt), top_str])
        
        cat_table = extract_table_as_markdown(cat_rows)
        sections_data.append({
            "page": sec_idx,
            "page_label": f"{dataset_label} - Categorical Distributions",
            "text": f"### Categorical & Text Features Distribution\n\n{cat_table}",
            "tables": [cat_table]
        })
        sec_idx += 1

    # Section 4: Correlation & Key Relationship Insights (for numeric datasets)
    if numeric_df.shape[1] >= 2:
        try:
            corr_matrix = numeric_df.corr()
            corr_pairs = []
            cols = numeric_df.columns.tolist()
            for i in range(len(cols)):
                for j in range(i + 1, len(cols)):
                    c1, c2 = cols[i], cols[j]
                    val = corr_matrix.loc[c1, c2]
                    if not pd.isna(val) and abs(val) >= 0.3:
                        corr_pairs.append((c1, c2, val))
            
            corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
            if corr_pairs:
                corr_rows = [["Feature 1", "Feature 2", "Pearson Correlation", "Relationship"]]
                for c1, c2, val in corr_pairs[:10]:
                    rel = "Strong Positive" if val > 0.7 else "Moderate Positive" if val > 0.3 else "Strong Negative" if val < -0.7 else "Moderate Negative"
                    corr_rows.append([str(c1), str(c2), f"{val:.3f}", rel])
                corr_table = extract_table_as_markdown(corr_rows)
                sections_data.append({
                    "page": sec_idx,
                    "page_label": f"{dataset_label} - Feature Correlations",
                    "text": f"### Key Feature Correlations\n\n{corr_table}",
                    "tables": [corr_table]
                })
                sec_idx += 1
        except Exception as ce:
            print(f"[EXTRACTION] Correlation calculation skipped: {ce}")

    # Section 5: Representative Sample Records (Head, Quantiles, Tail)
    sample_indices = []
    # Head 3
    sample_indices.extend(range(min(3, total_rows)))
    # 25%, 50%, 75% quantile points
    if total_rows > 10:
        sample_indices.extend([int(total_rows * 0.25), int(total_rows * 0.5), int(total_rows * 0.75)])
    # Tail 3
    if total_rows > 3:
        sample_indices.extend(range(max(0, total_rows - 3), total_rows))
    
    unique_indices = sorted(list(set(i for i in sample_indices if 0 <= i < total_rows)))
    sample_df = df.iloc[unique_indices]
    
    headers = [str(c).strip() for c in sample_df.columns]
    matrix = [["Row #"] + headers]
    for orig_idx, row in sample_df.iterrows():
        row_vals = [f"Row {orig_idx + 1}"] + [str(val).strip() if pd.notna(val) else "" for val in row]
        matrix.append(row_vals)
    
    samples_table = extract_table_as_markdown(matrix)
    sections_data.append({
        "page": sec_idx,
        "page_label": f"{dataset_label} - Representative Samples",
        "text": f"### Representative Sample Records (Selected across {total_rows:,} rows)\n\n{samples_table}",
        "tables": [samples_table]
    })
    sec_idx += 1

    return sections_data


def extract_excel(excel_path: str) -> List[Dict[str, Any]]:
    """Extract worksheets from Excel (.xlsx/.xls) with intelligent EDA profiling for large datasets."""
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
        
        # If dataset exceeds 100 rows, use intelligent EDA profiling
        if total_rows > 100:
            eda_sections = _generate_dataframe_eda_sections(df, dataset_label=f"Sheet '{sheet_name}'", section_start=section_counter)
            sheets_data.extend(eda_sections)
            section_counter += len(eda_sections)
        else:
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
    """Extract CSV file with intelligent EDA profiling for large datasets (100k+ rows)."""
    import pandas as pd
    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
    df = None
    
    for enc in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=enc, low_memory=False)
            break
        except Exception:
            continue
            
    if df is None:
        raise ValueError(f"Failed to parse CSV file with standard encodings: {csv_path}")

    df = df.dropna(how="all")
    if df.empty:
        return []
        
    total_rows = len(df)
    
    # If dataset exceeds 100 rows, use intelligent EDA profiling
    if total_rows > 100:
        return _generate_dataframe_eda_sections(df, dataset_label="Dataset", section_start=1)

    csv_data = []
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

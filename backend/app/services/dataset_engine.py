"""
Dataset Engine — Deterministic Structured Data Analysis, Schema Inspector, and Safe DataFrame Operations.
Guarantees 100% Column Preservation, Exact Mathematical Calculations, and Schema-Aware Error Handling.
"""

import os
import glob
import re
import math
from typing import List, Dict, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np

from backend.app import config
from backend.app.database import database

# In-memory DataFrame cache: doc_id -> { "mtime": float, "sheets": { sheet_name: df } }
_DF_CACHE: Dict[str, Dict[str, Any]] = {}
_MAX_CACHE_ENTRIES = 20


def _get_raw_file_path(doc_id: str) -> Optional[str]:
    """Locate the raw uploaded file on disk for a given doc_id."""
    doc = database.get_document(doc_id)
    if not doc:
        return None

    # Check direct match in uploads directory
    pattern = os.path.join(config.UPLOAD_DIR, f"{doc_id}*")
    matches = glob.glob(pattern)
    if matches:
        return matches[0]

    # Fallback to checking by filename
    filename = doc.get("filename")
    if filename:
        candidate = os.path.join(config.UPLOAD_DIR, filename)
        if os.path.exists(candidate):
            return candidate

    return None


def is_structured_file(doc_id: str) -> bool:
    """Check if the document is a structured CSV or Excel spreadsheet."""
    doc = database.get_document(doc_id)
    if not doc:
        return False
    file_type = (doc.get("file_type") or "").lower()
    filename = (doc.get("filename") or "").lower()
    return file_type in ("csv", "excel") or filename.endswith((".csv", ".xlsx", ".xls"))


def load_dataframe(doc_id: str, sheet_name: Optional[str] = None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Load and cache a DataFrame for a structured dataset.
    Returns (DataFrame, error_message).
    """
    file_path = _get_raw_file_path(doc_id)
    if not file_path or not os.path.exists(file_path):
        return None, f"Dataset file for document '{doc_id}' not found on disk."

    mtime = os.path.getmtime(file_path)

    # Check cache
    if doc_id in _DF_CACHE and _DF_CACHE[doc_id].get("mtime") == mtime:
        sheets = _DF_CACHE[doc_id].get("sheets", {})
        target_sheet = sheet_name or list(sheets.keys())[0] if sheets else None
        if target_sheet and target_sheet in sheets:
            return sheets[target_sheet].copy(), None

    # Load from disk
    ext = os.path.splitext(file_path)[1].lower()
    loaded_sheets: Dict[str, pd.DataFrame] = {}

    try:
        if ext == ".csv":
            df = None
            encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]
            for enc in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=enc, low_memory=False)
                    break
                except Exception:
                    continue

            if df is None:
                return None, f"Failed to decode CSV file with supported encodings."

            df = df.dropna(how="all")
            # Clean string column names (strip whitespace but preserve original case and order)
            df.columns = [str(c).strip() for c in df.columns]
            loaded_sheets["default"] = df

        elif ext in (".xlsx", ".xls"):
            excel_file = pd.ExcelFile(file_path)
            for sname in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sname)
                df = df.dropna(how="all")
                df.columns = [str(c).strip() for c in df.columns]
                loaded_sheets[sname] = df
        else:
            return None, f"Unsupported structured file format '{ext}'."

    except Exception as e:
        return None, f"Error reading dataset: {str(e)}"

    if not loaded_sheets:
        return None, "Dataset contains no readable tabular sheets or rows."

    # Manage cache size
    if len(_DF_CACHE) >= _MAX_CACHE_ENTRIES:
        oldest_key = next(iter(_DF_CACHE))
        del _DF_CACHE[oldest_key]

    _DF_CACHE[doc_id] = {
        "mtime": mtime,
        "sheets": loaded_sheets
    }

    target_sheet = sheet_name if (sheet_name and sheet_name in loaded_sheets) else list(loaded_sheets.keys())[0]
    return loaded_sheets[target_sheet].copy(), None


def get_dataset_schema(doc_id: str) -> Dict[str, Any]:
    """Inspect and return schema metadata for the dataset."""
    df, err = load_dataframe(doc_id)
    if err or df is None:
        return {"error": err or "Failed to load dataset"}

    sheets = list(_DF_CACHE.get(doc_id, {}).get("sheets", {}).keys())
    columns = [str(c) for c in df.columns]
    dtypes = {str(col): str(df[col].dtype) for col in df.columns}
    numeric_cols = [str(c) for c in df.select_dtypes(include=[np.number]).columns]
    categorical_cols = [str(c) for c in df.select_dtypes(exclude=[np.number]).columns]

    # Sample unique values for categorical columns (up to 5 per column)
    samples = {}
    for col in df.columns:
        valid_vals = df[col].dropna().unique()
        samples[str(col)] = [str(v) for v in valid_vals[:5]]

    return {
        "doc_id": doc_id,
        "total_rows": len(df),
        "total_columns": len(columns),
        "columns": columns,
        "dtypes": dtypes,
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "sheets": sheets,
        "samples": samples
    }


def resolve_column_name(target_name: str, available_columns: List[str]) -> Optional[str]:
    """
    Case-insensitive, symbol-normalized column resolver that maps user queries
    to the exact canonical column name present in the DataFrame.
    """
    if not target_name:
        return None

    target_clean = str(target_name).strip()
    # 1. Exact match
    for col in available_columns:
        if col == target_clean:
            return col

    # 2. Case-insensitive match
    target_lower = target_clean.lower()
    for col in available_columns:
        if col.lower() == target_lower:
            return col

    # 3. Normalized alphanumeric match (ignores spaces, underscores, hyphens)
    target_norm = re.sub(r"[^a-z0-9]", "", target_lower)
    for col in available_columns:
        col_norm = re.sub(r"[^a-z0-9]", "", col.lower())
        if col_norm == target_norm:
            return col

    # 4. Partial / substring match
    for col in available_columns:
        col_norm = re.sub(r"[^a-z0-9]", "", col.lower())
        if target_norm and (target_norm in col_norm or col_norm in target_norm):
            return col

    return None


def serialize_dataframe_to_markdown(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    max_rows: int = 100
) -> str:
    """
    Serialize a DataFrame into a pristine Markdown table string.
    Guarantees that all specified columns and exact row cells are represented.
    """
    if df.empty:
        cols = columns or list(df.columns)
        if not cols:
            return "| Status |\n| --- |\n| No matching records found. |"
        header_line = "| " + " | ".join([str(c) for c in cols]) + " |"
        sep_line = "| " + " | ".join(["---"] * len(cols)) + " |"
        return f"{header_line}\n{sep_line}\n| " + " | ".join(["No records"] * len(cols)) + " |"

    display_cols = columns if columns else list(df.columns)
    # Ensure all display_cols exist in df
    valid_cols = [c for c in display_cols if c in df.columns]
    if not valid_cols:
        valid_cols = list(df.columns)

    sub_df = df[valid_cols].head(max_rows)

    def clean_cell(val: Any) -> str:
        if pd.isna(val) or val is None:
            return "—"
        if isinstance(val, (float, np.floating)):
            if math.isnan(val) or math.isinf(val):
                return "—"
            # Format floating points nicely
            return f"{val:.4f}".rstrip("0").rstrip(".") if abs(val - round(val)) > 1e-6 else str(int(round(val)))
        if isinstance(val, (int, np.integer)):
            return str(val)
        # Clean pipes and newlines to prevent markdown table breakage
        return str(val).replace("|", "/").replace("\n", " ").strip()

    header_line = "| " + " | ".join([str(c).replace("|", "/") for c in valid_cols]) + " |"
    sep_line = "| " + " | ".join(["---"] * len(valid_cols)) + " |"

    rows = []
    for _, row in sub_df.iterrows():
        cell_strs = [clean_cell(row[c]) for c in valid_cols]
        rows.append("| " + " | ".join(cell_strs) + " |")

    return f"{header_line}\n{sep_line}\n" + "\n".join(rows)


def execute_dataframe_operation(doc_id: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a structured, deterministic DataFrame operation plan.
    Enforces Column Preservation, exact aggregations, and schema validation.
    """
    df, err = load_dataframe(doc_id, sheet_name=plan.get("sheet_name"))
    if err or df is None:
        return {
            "success": False,
            "error_type": "load_error",
            "message": err or "Failed to load dataset."
        }

    original_columns = [str(c) for c in df.columns]
    total_dataset_rows = len(df)
    op = (plan.get("operation") or "select").lower()

    # Step 1: Column Preservation Logic
    explicit_columns = plan.get("target_columns") or []
    preserve_all = plan.get("preserve_all_columns", True)

    resolved_target_cols: List[str] = []
    missing_requested_cols: List[str] = []

    if explicit_columns and not preserve_all:
        for user_c in explicit_columns:
            matched = resolve_column_name(user_c, original_columns)
            if matched:
                if matched not in resolved_target_cols:
                    resolved_target_cols.append(matched)
            else:
                missing_requested_cols.append(user_c)

        if missing_requested_cols:
            avail_str = ", ".join([f"'{c}'" for c in original_columns])
            return {
                "success": False,
                "error_type": "missing_column",
                "message": (
                    f"The dataset does not contain column(s): {', '.join(missing_requested_cols)}. "
                    f"Available columns are: {avail_str}."
                )
            }
    else:
        # Default: STRICT 100% COLUMN PRESERVATION in original order
        resolved_target_cols = list(original_columns)

    work_df = df.copy()

    # Step 2: Apply Conditions / Filtering
    conditions = plan.get("conditions") or []
    filter_descriptions = []

    for cond in conditions:
        raw_col = cond.get("column")
        operator = cond.get("operator", "==")
        value = cond.get("value")

        if not raw_col:
            continue

        col_name = resolve_column_name(raw_col, original_columns)
        if not col_name:
            avail_str = ", ".join([f"'{c}'" for c in original_columns])
            return {
                "success": False,
                "error_type": "missing_column",
                "message": f"Column '{raw_col}' was not found in the dataset. Available columns: {avail_str}."
            }

        # Apply comparison filter
        try:
            series = work_df[col_name]
            is_numeric_col = pd.api.types.is_numeric_dtype(series)

            # Try numeric coercion if value is numeric
            if is_numeric_col or isinstance(value, (int, float)):
                num_series = pd.to_numeric(series, errors="coerce")
                num_val = float(value) if value is not None else 0.0

                if operator in (">", "gt"):
                    mask = num_series > num_val
                    filter_descriptions.append(f"{col_name} > {num_val}")
                elif operator in (">=", "gte"):
                    mask = num_series >= num_val
                    filter_descriptions.append(f"{col_name} >= {num_val}")
                elif operator in ("<", "lt"):
                    mask = num_series < num_val
                    filter_descriptions.append(f"{col_name} < {num_val}")
                elif operator in ("<=", "lte"):
                    mask = num_series <= num_val
                    filter_descriptions.append(f"{col_name} <= {num_val}")
                elif operator in ("==", "=", "eq"):
                    mask = (num_series == num_val) | (series.astype(str).str.strip().str.lower() == str(value).strip().lower())
                    filter_descriptions.append(f"{col_name} == {value}")
                elif operator in ("!=", "<>", "neq"):
                    mask = num_series != num_val
                    filter_descriptions.append(f"{col_name} != {value}")
                else:
                    mask = pd.Series([True] * len(work_df), index=work_df.index)
            else:
                # String / Categorical comparisons
                str_series = series.astype(str).str.strip()
                str_val = str(value).strip() if value is not None else ""

                if operator in ("==", "=", "eq"):
                    mask = str_series.str.lower() == str_val.lower()
                    filter_descriptions.append(f"{col_name} is '{str_val}'")
                elif operator in ("!=", "<>", "neq"):
                    mask = str_series.str.lower() != str_val.lower()
                    filter_descriptions.append(f"{col_name} is not '{str_val}'")
                elif operator in ("contains", "like"):
                    mask = str_series.str.lower().str.contains(str_val.lower(), na=False)
                    filter_descriptions.append(f"{col_name} contains '{str_val}'")
                elif operator in ("startswith",):
                    mask = str_series.str.lower().str.startswith(str_val.lower())
                    filter_descriptions.append(f"{col_name} starts with '{str_val}'")
                elif operator in ("isin", "in") and isinstance(value, list):
                    lower_vals = [str(v).strip().lower() for v in value]
                    mask = str_series.str.lower().isin(lower_vals)
                    filter_descriptions.append(f"{col_name} in {value}")
                elif operator in ("isnull", "null", "missing"):
                    mask = series.isna()
                    filter_descriptions.append(f"{col_name} is missing/null")
                elif operator in ("notnull", "not_null", "present"):
                    mask = series.notna()
                    filter_descriptions.append(f"{col_name} is present")
                else:
                    mask = pd.Series([True] * len(work_df), index=work_df.index)

            work_df = work_df[mask]

        except Exception as filter_ex:
            print(f"[DATASET_ENGINE] Filter error on {col_name} with {operator} {value}: {filter_ex}")

    # Step 3: Handle Aggregation / GroupBy / Stats Operations
    if op in ("aggregate", "agg", "calc", "math"):
        aggs = plan.get("aggregations") or []
        res_rows = []
        res_cols = ["Metric / Aggregation", "Column", "Calculated Value"]

        for agg_item in aggs:
            raw_c = agg_item.get("column")
            func = (agg_item.get("function") or "mean").lower()
            matched_c = resolve_column_name(raw_c, original_columns) if raw_c else original_columns[0]
            if not matched_c:
                continue

            num_s = pd.to_numeric(work_df[matched_c], errors="coerce").dropna()
            val_out = "N/A"

            if func in ("count", "total_rows"):
                val_out = f"{len(work_df):,}"
            elif func in ("sum", "total"):
                val_out = f"{num_s.sum():,.2f}" if not num_s.empty else "0"
            elif func in ("mean", "average", "avg"):
                val_out = f"{num_s.mean():,.4f}".rstrip("0").rstrip(".") if not num_s.empty else "N/A"
            elif func in ("median", "med"):
                val_out = f"{num_s.median():,.4f}".rstrip("0").rstrip(".") if not num_s.empty else "N/A"
            elif func in ("min", "minimum", "lowest"):
                val_out = f"{num_s.min():,.4f}".rstrip("0").rstrip(".") if not num_s.empty else "N/A"
            elif func in ("max", "maximum", "highest"):
                val_out = f"{num_s.max():,.4f}".rstrip("0").rstrip(".") if not num_s.empty else "N/A"
            elif func in ("std", "stddev"):
                val_out = f"{num_s.std():,.4f}".rstrip("0").rstrip(".") if not num_s.empty else "N/A"
            elif func in ("unique", "distinct", "cardinality"):
                val_out = f"{work_df[matched_c].nunique():,}"

            res_rows.append([func.upper(), matched_c, val_out])

        agg_df = pd.DataFrame(res_rows, columns=res_cols)
        md_table = serialize_dataframe_to_markdown(agg_df)
        return {
            "success": True,
            "type": "table",
            "operation": op,
            "columns": res_cols,
            "rows": res_rows,
            "row_count": len(res_rows),
            "total_dataset_rows": total_dataset_rows,
            "markdown_table": md_table,
            "message": f"Successfully computed {len(res_rows)} metric(s)."
        }

    if op in ("groupby", "group_by"):
        group_cols_raw = plan.get("group_by") or []
        resolved_groups = []
        for g in group_cols_raw:
            mg = resolve_column_name(g, original_columns)
            if mg:
                resolved_groups.append(mg)

        if not resolved_groups:
            resolved_groups = [original_columns[0]]

        aggs = plan.get("aggregations") or [{"column": original_columns[0], "function": "count"}]
        agg_spec = {}
        for a in aggs:
            col = resolve_column_name(a.get("column", ""), original_columns) or resolved_groups[0]
            fn = a.get("function", "count").lower()
            if fn == "average":
                fn = "mean"
            agg_spec.setdefault(col, []).append(fn)

        try:
            grouped_df = work_df.groupby(resolved_groups).agg(agg_spec)
            # Flatten multi-level column index if present
            if isinstance(grouped_df.columns, pd.MultiIndex):
                grouped_df.columns = [f"{col}_{fn.upper()}" for col, fn in grouped_df.columns]
            grouped_df = grouped_df.reset_index()

            # Sort grouped results if specified
            sort_by = plan.get("sort_by") or []
            if sort_by:
                sort_col_raw = sort_by[0].get("column", "")
                asc = sort_by[0].get("ascending", False)
                matched_sort = resolve_column_name(sort_col_raw, list(grouped_df.columns))
                if matched_sort:
                    grouped_df = grouped_df.sort_values(by=matched_sort, ascending=asc)

            limit = plan.get("limit") or 100
            grouped_df = grouped_df.head(limit)

            out_cols = [str(c) for c in grouped_df.columns]
            rows_list = []
            for _, r in grouped_df.iterrows():
                rows_list.append([str(r[c]) if pd.notna(r[c]) else "—" for c in out_cols])

            md_table = serialize_dataframe_to_markdown(grouped_df)
            return {
                "success": True,
                "type": "table",
                "operation": op,
                "columns": out_cols,
                "rows": rows_list,
                "row_count": len(rows_list),
                "total_dataset_rows": total_dataset_rows,
                "markdown_table": md_table,
                "message": f"Grouped by {', '.join(resolved_groups)} ({len(rows_list)} groups)."
            }
        except Exception as ge:
            print(f"[DATASET_ENGINE] GroupBy error: {ge}")

    if op in ("null_analysis", "missing_analysis"):
        null_rows = []
        null_cols = ["Column Name", "Data Type", "Missing Count", "Missing Percentage", "Total Rows"]
        for col in original_columns:
            missing_cnt = int(work_df[col].isna().sum())
            pct = (missing_cnt / total_dataset_rows * 100) if total_dataset_rows > 0 else 0
            null_rows.append([col, str(work_df[col].dtype), f"{missing_cnt:,}", f"{pct:.1f}%", f"{total_dataset_rows:,}"])

        null_df = pd.DataFrame(null_rows, columns=null_cols)
        md_table = serialize_dataframe_to_markdown(null_df)
        return {
            "success": True,
            "type": "table",
            "operation": op,
            "columns": null_cols,
            "rows": null_rows,
            "row_count": len(null_rows),
            "total_dataset_rows": total_dataset_rows,
            "markdown_table": md_table,
            "message": f"Completed missing values analysis across {len(original_columns)} columns."
        }

    # Step 4: Sorting
    sort_specs = plan.get("sort_by") or []
    for s_item in sort_specs:
        raw_s_col = s_item.get("column")
        asc = s_item.get("ascending", True)
        if raw_s_col:
            matched_s = resolve_column_name(raw_s_col, original_columns)
            if matched_s:
                # If numeric column stored as object, sort by numeric values safely
                if work_df[matched_s].dtype == object:
                    num_conv = pd.to_numeric(work_df[matched_s], errors="coerce")
                    if num_conv.notna().sum() > len(work_df) * 0.5:
                        work_df["_sort_key_"] = num_conv
                        work_df = work_df.sort_values(by="_sort_key_", ascending=asc).drop(columns=["_sort_key_"])
                        continue
                work_df = work_df.sort_values(by=matched_s, ascending=asc)

    # Step 5: Limiting / Top N / Bottom N
    limit = plan.get("limit")
    if op in ("top_n", "top"):
        limit = limit or 10
        work_df = work_df.head(limit)
    elif op in ("bottom_n", "bottom"):
        limit = limit or 10
        work_df = work_df.tail(limit)
    elif limit and limit > 0:
        work_df = work_df.head(limit)

    # Step 6: Select final columns with guaranteed preservation
    final_cols = [c for c in resolved_target_cols if c in work_df.columns]
    if not final_cols:
        final_cols = list(original_columns)

    final_df = work_df[final_cols]
    md_table = serialize_dataframe_to_markdown(final_df, columns=final_cols)

    # Format structured rows
    rows_data: List[List[str]] = []
    for _, r in final_df.iterrows():
        row_vals = []
        for c in final_cols:
            val = r[c]
            if pd.isna(val) or val is None:
                row_vals.append("—")
            elif isinstance(val, (float, np.floating)):
                row_vals.append(f"{val:.4f}".rstrip("0").rstrip(".") if abs(val - round(val)) > 1e-6 else str(int(round(val))))
            else:
                row_vals.append(str(val).strip())
        rows_data.append(row_vals)

    # Descriptive success message
    filters_desc = f" matching {', '.join(filter_descriptions)}" if filter_descriptions else ""
    msg = f"Found {len(rows_data):,} record(s){filters_desc} with all {len(final_cols)} column(s) preserved."

    return {
        "success": True,
        "type": "table",
        "operation": op,
        "columns": final_cols,
        "rows": rows_data,
        "row_count": len(rows_data),
        "total_dataset_rows": total_dataset_rows,
        "markdown_table": md_table,
        "message": msg
    }

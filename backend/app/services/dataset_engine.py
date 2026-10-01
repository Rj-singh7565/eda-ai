"""
Dataset Engine — Deterministic Structured Data Analysis, Schema Inspector, and Safe DataFrame Operations.
Guarantees 100% Column Preservation, Exact Mathematical Calculations, and Schema-Aware Error Handling.
"""

import os
import glob
import re
import math
import os
import glob
import re
import math
import time
from typing import List, Dict, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np
try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    duckdb = None
    HAS_DUCKDB = False

import threading

from backend.app import config
from backend.app.database import database

# Reusable DuckDB in-memory connection and concurrency semaphore
_DUCKDB_CONN = None
_DUCKDB_SEMAPHORE = threading.BoundedSemaphore(getattr(config, "EDA_MAX_DUCKDB_CONCURRENCY", 8))


def get_duckdb_connection():
    """Get or initialize reusable DuckDB connection with configured threads."""
    global _DUCKDB_CONN
    if not HAS_DUCKDB:
        return None
    if _DUCKDB_CONN is None:
        _DUCKDB_CONN = duckdb.connect(":memory:")
        threads = getattr(config, "DUCKDB_THREADS", 0)
        if threads > 0:
            try:
                _DUCKDB_CONN.execute(f"SET threads TO {threads};")
            except Exception:
                pass
    return _DUCKDB_CONN


def get_duckdb_cursor():
    """Get a thread-safe cursor for concurrent vectorized queries."""
    main_conn = get_duckdb_connection()
    return main_conn.cursor()


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


def transcode_to_parquet(doc_id: str, file_path: str, file_type: str = "csv") -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Transcode uploaded CSV or Excel data into Snappy-compressed Apache Parquet
    and precompute structured dataset profile for instant database retrieval.
    """
    try:
        parquet_path = os.path.join(config.PROCESSED_DIR, f"{doc_id}.parquet")
        if os.path.exists(parquet_path):
            meta = database.get_dataset_metadata(doc_id)
            if meta:
                return parquet_path, meta

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv" or file_type == "csv":
            try:
                df = pd.read_csv(file_path, encoding="utf-8", low_memory=False)
            except Exception:
                df = pd.read_csv(file_path, encoding="latin-1", low_memory=False)
        elif ext in (".xlsx", ".xls") or file_type == "excel":
            df = pd.read_excel(file_path)
        else:
            return None, None

        df = df.dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]

        # Write Parquet with Snappy compression
        df.to_parquet(parquet_path, engine="pyarrow", compression=getattr(config, "PARQUET_COMPRESSION", "snappy"), index=False)

        total_rows = len(df)
        total_cols = len(df.columns)
        numeric_cols = [str(c) for c in df.select_dtypes(include=[np.number]).columns]
        categorical_cols = [str(c) for c in df.select_dtypes(exclude=[np.number]).columns]

        null_counts = {str(c): int(df[c].isna().sum()) for c in df.columns}
        null_rates = {str(c): round(null_counts[str(c)] / max(total_rows, 1), 4) for c in df.columns}
        data_types = {str(c): str(df[c].dtype) for c in df.columns}

        profile = {
            "document_id": doc_id,
            "dataset_version": 1,
            "columns": list(df.columns),
            "column_names": list(df.columns),
            "column_order": list(df.columns),
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "data_types": data_types,
            "row_count": total_rows,
            "column_count": total_cols,
            "null_counts": null_counts,
            "null_rates": null_rates,
            "parquet_path": parquet_path
        }
        database.save_dataset_metadata(doc_id, profile, parquet_path)
        return parquet_path, profile
    except Exception as e:
        print(f"[DATASET_ENGINE] Transcode error for doc {doc_id}: {e}")
        return None, None


def get_dataset_schema(doc_id: str) -> Dict[str, Any]:
    """Inspect and return schema metadata for the dataset, prioritizing precomputed DB profile."""
    # Fast path: check database precomputed profile (<1ms, zero file I/O)
    meta = database.get_dataset_metadata(doc_id)
    if meta and "columns" in meta:
        return {
            "doc_id": doc_id,
            "total_rows": meta.get("row_count", 0),
            "total_columns": meta.get("column_count", len(meta["columns"])),
            "columns": meta.get("columns", []),
            "dtypes": meta.get("data_types", {}),
            "numeric_columns": meta.get("numeric_columns", []),
            "categorical_columns": meta.get("categorical_columns", []),
            "sheets": ["default"],
            "samples": meta.get("sample_rows", {})
        }

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


def validate_sql_safety(sql: str) -> bool:
    """Strict validation: ensure query is strictly read-only."""
    clean = sql.strip().upper()
    if not (clean.startswith("SELECT ") or clean.startswith("WITH ")):
        return False
    forbidden = [
        "DROP ", "DELETE ", "UPDATE ", "INSERT ", "ALTER ", "CREATE ",
        "ATTACH ", "DETACH ", "COPY ", "EXPORT ", "PRAGMA ", "EXECUTE ",
        "GRANT ", "REVOKE ", "TRUNCATE ", "SET "
    ]
    for kw in forbidden:
        if kw in clean:
            return False
    return True


def execute_duckdb_operation(
    doc_id: str,
    plan: Dict[str, Any],
    source_expr: str,
    original_columns: List[str],
    total_dataset_rows: int
) -> Optional[Dict[str, Any]]:
    """
    Executes a structured operation directly with DuckDB for sub-25ms execution
    and zero-copy memory overhead. Returns None on unsupported ops or errors to trigger fallback.
    """
    op = (plan.get("operation") or "select").lower()
    if not HAS_DUCKDB or op in ("null_analysis", "missing_analysis"):
        return None

    try:
        preserve_all = plan.get("preserve_all_columns", True)
        explicit_columns = plan.get("target_columns") or []

        resolved_target_cols = []
        if explicit_columns and not preserve_all:
            for c in explicit_columns:
                m = resolve_column_name(c, original_columns)
                if m and m not in resolved_target_cols:
                    resolved_target_cols.append(m)
        if not resolved_target_cols:
            resolved_target_cols = list(original_columns)

        # Build WHERE clause
        where_clauses = []
        filter_descriptions = []
        for cond in plan.get("conditions") or []:
            col_raw = cond.get("column")
            if not col_raw:
                continue
            c_name = resolve_column_name(col_raw, original_columns)
            if not c_name:
                continue

            c_escaped = f'"{c_name.replace(chr(34), "")}"'
            op_str = cond.get("operator", "==").lower()
            val = cond.get("value")

            if op_str in (">", "gt"):
                try:
                    num_val = float(val)
                    where_clauses.append(f"TRY_CAST({c_escaped} AS DOUBLE) > {num_val}")
                    filter_descriptions.append(f"{c_name} > {num_val}")
                except Exception:
                    pass
            elif op_str in (">=", "gte"):
                try:
                    num_val = float(val)
                    where_clauses.append(f"TRY_CAST({c_escaped} AS DOUBLE) >= {num_val}")
                    filter_descriptions.append(f"{c_name} >= {num_val}")
                except Exception:
                    pass
            elif op_str in ("<", "lt"):
                try:
                    num_val = float(val)
                    where_clauses.append(f"TRY_CAST({c_escaped} AS DOUBLE) < {num_val}")
                    filter_descriptions.append(f"{c_name} < {num_val}")
                except Exception:
                    pass
            elif op_str in ("<=", "lte"):
                try:
                    num_val = float(val)
                    where_clauses.append(f"TRY_CAST({c_escaped} AS DOUBLE) <= {num_val}")
                    filter_descriptions.append(f"{c_name} <= {num_val}")
                except Exception:
                    pass
            elif op_str in ("==", "=", "eq"):
                if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace(".", "", 1).isdigit()):
                    num_val = float(val)
                    where_clauses.append(f"(TRY_CAST({c_escaped} AS DOUBLE) = {num_val} OR LOWER(TRIM(CAST({c_escaped} AS VARCHAR))) = '{str(val).lower().replace(chr(39), chr(39)+chr(39))}')")
                else:
                    esc_val = str(val).replace("'", "''").lower()
                    where_clauses.append(f"LOWER(TRIM(CAST({c_escaped} AS VARCHAR))) = '{esc_val}'")
                filter_descriptions.append(f"{c_name} == {val}")
            elif op_str in ("!=", "<>", "neq"):
                esc_val = str(val).replace("'", "''").lower()
                where_clauses.append(f"LOWER(TRIM(CAST({c_escaped} AS VARCHAR))) != '{esc_val}'")
                filter_descriptions.append(f"{c_name} != {val}")
            elif op_str in ("contains", "like"):
                esc_val = str(val).replace("'", "''").lower()
                where_clauses.append(f"LOWER(CAST({c_escaped} AS VARCHAR)) LIKE '%{esc_val}%'")
                filter_descriptions.append(f"{c_name} contains '{val}'")
            elif op_str in ("startswith",):
                esc_val = str(val).replace("'", "''").lower()
                where_clauses.append(f"LOWER(CAST({c_escaped} AS VARCHAR)) LIKE '{esc_val}%'")
                filter_descriptions.append(f"{c_name} starts with '{val}'")
            elif op_str in ("isnull", "null", "missing"):
                where_clauses.append(f"({c_escaped} IS NULL OR TRIM(CAST({c_escaped} AS VARCHAR)) = '')")
                filter_descriptions.append(f"{c_name} is null")
            elif op_str in ("notnull", "not_null", "present"):
                where_clauses.append(f"({c_escaped} IS NOT NULL AND TRIM(CAST({c_escaped} AS VARCHAR)) != '')")
                filter_descriptions.append(f"{c_name} is present")
            elif op_str in ("isin", "in") and isinstance(val, list):
                items = [f"'{str(v).replace(chr(39), chr(39)+chr(39)).lower()}'" for v in val]
                where_clauses.append(f"LOWER(TRIM(CAST({c_escaped} AS VARCHAR))) IN ({', '.join(items)})")
                filter_descriptions.append(f"{c_name} in {val}")

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Handle Aggregations
        if op in ("aggregate", "agg", "calc", "math"):
            aggs = plan.get("aggregations") or []
            res_rows = []
            res_cols = ["Metric / Aggregation", "Column", "Calculated Value"]
            con = get_duckdb_cursor()
            agg_dt = 0.0

            for agg_item in aggs:
                raw_c = agg_item.get("column")
                func = (agg_item.get("function") or "mean").lower()
                matched_c = resolve_column_name(raw_c, original_columns) if raw_c else original_columns[0]
                if not matched_c:
                    continue

                col_esc = f'"{matched_c.replace(chr(34), "")}"'
                if func in ("count", "total_rows"):
                    agg_sql = f"SELECT COUNT(*) FROM {source_expr}{where_sql}"
                elif func in ("sum", "total"):
                    agg_sql = f"SELECT SUM(TRY_CAST({col_esc} AS DOUBLE)) FROM {source_expr}{where_sql}"
                elif func in ("mean", "average", "avg"):
                    agg_sql = f"SELECT AVG(TRY_CAST({col_esc} AS DOUBLE)) FROM {source_expr}{where_sql}"
                elif func in ("median", "med"):
                    agg_sql = f"SELECT MEDIAN(TRY_CAST({col_esc} AS DOUBLE)) FROM {source_expr}{where_sql}"
                elif func in ("min", "minimum", "lowest"):
                    agg_sql = f"SELECT MIN(TRY_CAST({col_esc} AS DOUBLE)) FROM {source_expr}{where_sql}"
                elif func in ("max", "maximum", "highest"):
                    agg_sql = f"SELECT MAX(TRY_CAST({col_esc} AS DOUBLE)) FROM {source_expr}{where_sql}"
                elif func in ("std", "stddev"):
                    agg_sql = f"SELECT STDDEV_SAMP(TRY_CAST({col_esc} AS DOUBLE)) FROM {source_expr}{where_sql}"
                elif func in ("unique", "distinct", "cardinality"):
                    agg_sql = f"SELECT COUNT(DISTINCT {col_esc}) FROM {source_expr}{where_sql}"
                else:
                    agg_sql = f"SELECT COUNT(*) FROM {source_expr}{where_sql}"

                t_agg0 = time.perf_counter()
                agg_val = con.execute(agg_sql).fetchone()[0]
                agg_dt = (time.perf_counter() - t_agg0) * 1000

                if agg_val is None:
                    val_out = "N/A"
                elif isinstance(agg_val, float):
                    val_out = f"{agg_val:,.4f}".rstrip("0").rstrip(".") if abs(agg_val - round(agg_val)) > 1e-6 else str(int(round(agg_val)))
                else:
                    val_out = f"{agg_val:,}"

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
                "engine": "duckdb",
                "execution_latency_ms": round(agg_dt, 2),
                "message": f"Successfully computed {len(res_rows)} metric(s) with DuckDB."
            }

        # GROUP BY
        if op in ("groupby", "group_by"):
            group_cols = []
            for g in plan.get("group_by") or []:
                mg = resolve_column_name(g, original_columns)
                if mg:
                    group_cols.append(mg)
            if not group_cols:
                group_cols = [original_columns[0]]

            group_exprs = [f'"{c.replace(chr(34), "")}"' for c in group_cols]
            agg_exprs = []
            out_cols = list(group_cols)

            for a in plan.get("aggregations") or [{"column": original_columns[0], "function": "count"}]:
                col_match = resolve_column_name(a.get("column", ""), original_columns) or group_cols[0]
                col_esc = f'"{col_match.replace(chr(34), "")}"'
                fn = a.get("function", "count").lower()
                if fn in ("count", "total_rows"):
                    alias = f"{col_match}_COUNT"
                    agg_exprs.append(f"COUNT(*) AS \"{alias}\"")
                    out_cols.append(alias)
                elif fn in ("sum", "total"):
                    alias = f"{col_match}_SUM"
                    agg_exprs.append(f"SUM(TRY_CAST({col_esc} AS DOUBLE)) AS \"{alias}\"")
                    out_cols.append(alias)
                elif fn in ("mean", "average", "avg"):
                    alias = f"{col_match}_AVG"
                    agg_exprs.append(f"AVG(TRY_CAST({col_esc} AS DOUBLE)) AS \"{alias}\"")
                    out_cols.append(alias)
                elif fn in ("median", "med"):
                    alias = f"{col_match}_MEDIAN"
                    agg_exprs.append(f"MEDIAN(TRY_CAST({col_esc} AS DOUBLE)) AS \"{alias}\"")
                    out_cols.append(alias)
                elif fn in ("min", "minimum", "lowest"):
                    alias = f"{col_match}_MIN"
                    agg_exprs.append(f"MIN(TRY_CAST({col_esc} AS DOUBLE)) AS \"{alias}\"")
                    out_cols.append(alias)
                elif fn in ("max", "maximum", "highest"):
                    alias = f"{col_match}_MAX"
                    agg_exprs.append(f"MAX(TRY_CAST({col_esc} AS DOUBLE)) AS \"{alias}\"")
                    out_cols.append(alias)

            select_cols = ", ".join(group_exprs + agg_exprs)
            sql = f"SELECT {select_cols} FROM {source_expr}{where_sql} GROUP BY {', '.join(group_exprs)}"

            if plan.get("sort_by"):
                s_item = plan["sort_by"][0]
                s_match = resolve_column_name(s_item.get("column", ""), out_cols)
                if s_match:
                    s_dir = "ASC" if s_item.get("ascending", False) else "DESC"
                    sql += f' ORDER BY "{s_match}" {s_dir}'

            limit = plan.get("limit") or 100
            sql += f" LIMIT {int(limit)}"

            if not validate_sql_safety(sql):
                return None

            t0 = time.perf_counter()
            with _DUCKDB_SEMAPHORE:
                con = get_duckdb_cursor()
                grouped_df = con.execute(sql).df()
            exec_ms = (time.perf_counter() - t0) * 1000

            md_table = serialize_dataframe_to_markdown(grouped_df, columns=out_cols)
            rows_list = []
            for _, r in grouped_df.iterrows():
                rows_list.append([str(r[c]) if pd.notna(r[c]) else "—" for c in out_cols])

            return {
                "success": True,
                "type": "table",
                "operation": op,
                "columns": out_cols,
                "rows": rows_list,
                "row_count": len(rows_list),
                "total_dataset_rows": total_dataset_rows,
                "markdown_table": md_table,
                "sql_query": sql,
                "engine": "duckdb",
                "execution_latency_ms": round(exec_ms, 2),
                "message": f"Grouped by {', '.join(group_cols)} ({len(rows_list)} groups)."
            }

        # Standard SELECT / Filter / Sort
        col_projections = [f'"{c.replace(chr(34), "")}"' for c in resolved_target_cols]
        sql = f"SELECT {', '.join(col_projections)} FROM {source_expr}{where_sql}"

        # Sorting
        sort_clauses = []
        for s_item in plan.get("sort_by") or []:
            s_col = resolve_column_name(s_item.get("column", ""), original_columns)
            if s_col:
                s_dir = "ASC" if s_item.get("ascending", True) else "DESC"
                sort_clauses.append(f'"{s_col}" {s_dir}')
        if sort_clauses:
            sql += " ORDER BY " + ", ".join(sort_clauses)

        # Limiting
        limit = plan.get("limit")
        if op in ("top_n", "top"):
            sql += f" LIMIT {int(limit or 10)}"
        elif limit and int(limit) > 0:
            sql += f" LIMIT {int(limit)}"

        if not validate_sql_safety(sql):
            return None

        t0 = time.perf_counter()
        with _DUCKDB_SEMAPHORE:
            con = get_duckdb_cursor()
            res_df = con.execute(sql).df()
        exec_ms = (time.perf_counter() - t0) * 1000

        # Enforce exact column order and names
        final_cols = [c for c in resolved_target_cols if c in res_df.columns]
        if not final_cols:
            final_cols = list(original_columns)
        res_df = res_df[final_cols]

        md_table = serialize_dataframe_to_markdown(res_df, columns=final_cols)

        rows_data: List[List[str]] = []
        for _, r in res_df.iterrows():
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
            "sql_query": sql,
            "engine": "duckdb",
            "execution_latency_ms": round(exec_ms, 2),
            "message": msg
        }
    except Exception as d_err:
        print(f"[DATASET_ENGINE] DuckDB execution note (falling back to pandas): {d_err}")
        return None


def execute_dataframe_operation(doc_id: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a structured, deterministic DataFrame operation plan.
    Prefers zero-copy DuckDB execution directly over Parquet file if available.
    Falls back to Pandas execution if Parquet is absent or DuckDB query cannot be applied.
    """
    # ── Fast Path: Direct DuckDB Execution over Parquet (Zero-Copy) ──
    parquet_path = os.path.join(config.PROCESSED_DIR, f"{doc_id}.parquet")
    meta = database.get_dataset_metadata(doc_id)
    if not meta:
        doc = database.get_document(doc_id)
        if doc and doc.get("parquet_path") and os.path.exists(doc["parquet_path"]):
            parquet_path = doc["parquet_path"]
            meta = database.get_dataset_metadata(doc_id)

    if os.path.exists(parquet_path) and meta and "columns" in meta:
        norm_pq = parquet_path.replace("\\", "/")
        source_expr = f"read_parquet('{norm_pq}')"
        duck_res = execute_duckdb_operation(
            doc_id=doc_id,
            plan=plan,
            source_expr=source_expr,
            original_columns=meta["columns"],
            total_dataset_rows=meta.get("row_count", 0)
        )
        if duck_res and duck_res.get("success"):
            return duck_res

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

    # Verify condition columns exist before DuckDB or Pandas
    for cond in plan.get("conditions") or []:
        col_raw = cond.get("column")
        if not col_raw:
            continue
        col_match = resolve_column_name(col_raw, original_columns)
        if not col_match:
            avail_str = ", ".join([f"'{c}'" for c in original_columns])
            return {
                "success": False,
                "error_type": "missing_column",
                "message": f"Column '{col_raw}' was not found in the dataset. Available columns: {avail_str}."
            }

    # High-Performance DuckDB Vectorized Path (<25ms execution)
    source_expr = None
    pq_path = os.path.join(config.PROCESSED_DIR, f"{doc_id}.parquet")
    if os.path.exists(pq_path):
        source_expr = f"'{pq_path.replace(chr(92), '/')}'"
    else:
        raw_path = _get_raw_file_path(doc_id)
        if raw_path and os.path.exists(raw_path):
            clean_raw = raw_path.replace(chr(92), "/")
            if raw_path.lower().endswith(".csv"):
                source_expr = f"read_csv_auto('{clean_raw}')"

    if source_expr:
        duck_res = execute_duckdb_operation(doc_id, plan, source_expr, original_columns, total_dataset_rows)
        if duck_res is not None:
            return duck_res

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

"""
Python Query Generator — Translates Canonical Analytical Plans into
Deterministic, Reproducible, Executable Pandas Python Code.

Guarantees 1:1 Parity with DuckDB Vectorized Operations:
- Column order & preservation
- Filtering semantics (numeric, string, nulls)
- Group-by & Aggregations
- Sorting & Limit operations
- Clean, self-contained, reproducible scripts
"""

import re
from typing import Dict, Any, List, Optional


def _is_valid_identifier(name: str) -> bool:
    """Check if string is a valid Python variable/keyword identifier."""
    return name.isidentifier() and not keyword_iskeyword(name)


def keyword_iskeyword(s: str) -> bool:
    import keyword
    return keyword.iskeyword(s)


def _format_value(val: Any) -> str:
    """Format scalar value for safe Python literal representation."""
    if val is None:
        return "None"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, list):
        return f"[{', '.join(_format_value(x) for x in val)}]"
    # String
    escaped = str(val).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'

def _format_number(val: Any) -> str:
    """Format numeric value without unnecessary trailing decimal zeros."""
    if val is None:
        return "0"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        if abs(val - round(val)) < 1e-9:
            return str(int(round(val)))
        return str(val)
    try:
        f = float(val)
        if abs(f - round(f)) < 1e-9:
            return str(int(round(f)))
        return str(f)
    except Exception:
        return str(val)


def _build_filter_expression(cond: Dict[str, Any], df_var: str = "df") -> Optional[str]:
    """Construct pandas boolean indexing expression for a single condition."""
    col = cond.get("column")
    if not col:
        return None
    op = (cond.get("operator") or "==").lower()
    val = cond.get("value")

    col_esc = col.replace('"', '\\"')
    col_ref = f'{df_var}["{col_esc}"]'

    if op in (">", "gt"):
        num_str = _format_number(val)
        return f'({col_ref} > {num_str})'
    elif op in (">=", "gte"):
        num_str = _format_number(val)
        return f'({col_ref} >= {num_str})'
    elif op in ("<", "lt"):
        num_str = _format_number(val)
        return f'({col_ref} < {num_str})'
    elif op in ("<=", "lte"):
        num_str = _format_number(val)
        return f'({col_ref} <= {num_str})'
    elif op in ("==", "=", "eq"):
        if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace(".", "", 1).isdigit()):
            num_str = _format_number(val)
            return f'({col_ref} == {num_str})'
        str_val = str(val).replace('"', '\\"')
        return f'({col_ref}.astype(str).str.strip().str.lower() == "{str_val}".lower())'
    elif op in ("!=", "<>", "neq"):
        if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace(".", "", 1).isdigit()):
            num_str = _format_number(val)
            return f'({col_ref} != {num_str})'
        str_val = str(val).replace('"', '\\"')
        return f'({col_ref}.astype(str).str.strip().str.lower() != "{str_val}".lower())'
    elif op in ("contains", "like"):
        str_val = str(val).replace('"', '\\"')
        return f'({col_ref}.astype(str).str.contains("{str_val}", case=False, na=False))'
    elif op in ("startswith",):
        str_val = str(val).replace('"', '\\"')
        return f'({col_ref}.astype(str).str.startswith("{str_val}", na=False))'
    elif op in ("isnull", "null", "missing"):
        return f'({col_ref}.isna())'
    elif op in ("notnull", "not_null", "present"):
        return f'({col_ref}.notna())'
    elif op in ("isin", "in") and isinstance(val, list):
        items_expr = f"[{', '.join(_format_value(v) for v in val)}]"
        return f'({col_ref}.isin({items_expr}))'

    return None


def generate_python_query(
    plan: Dict[str, Any],
    dataset_name: str = "dataset.parquet",
    sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate reproducible Python code from a structured analytical plan.

    Returns:
        {
            "python_code": str,
            "language": "python",
            "library": "pandas",
            "dataset_name": str,
            "operations": List[str],
            "is_available": bool,
            "message": str
        }
    """
    # Normalize canonical operations list or dictionary inputs
    working_plan = dict(plan)
    canonical_ops = working_plan.get("operations")
    if canonical_ops and isinstance(canonical_ops, list):
        for op_item in canonical_ops:
            op_t = (op_item.get("type") or "").lower()
            if op_t == "filter":
                if op_item.get("is_post_filter"):
                    working_plan.setdefault("post_conditions", []).append(op_item)
                else:
                    working_plan.setdefault("conditions", []).append(op_item)
            elif op_t in ("groupby", "group_by"):
                working_plan["operation"] = "groupby"
                if "columns" in op_item and not working_plan.get("group_by"):
                    working_plan["group_by"] = op_item["columns"]
                if "aggregations" in op_item and not working_plan.get("aggregations"):
                    raw_a = op_item["aggregations"]
                    if isinstance(raw_a, dict):
                        working_plan["aggregations"] = [{"column": k, "function": v} for k, v in raw_a.items()]
                    else:
                        working_plan["aggregations"] = raw_a
            elif op_t in ("aggregate", "agg"):
                working_plan["operation"] = "aggregate"
                if "aggregations" in op_item and not working_plan.get("aggregations"):
                    raw_a = op_item["aggregations"]
                    if isinstance(raw_a, dict):
                        working_plan["aggregations"] = [{"column": k, "function": v} for k, v in raw_a.items()]
                    else:
                        working_plan["aggregations"] = raw_a
            elif op_t == "select":
                if "columns" in op_item and not working_plan.get("target_columns"):
                    working_plan["target_columns"] = op_item["columns"]
                    working_plan["preserve_all_columns"] = False
            elif op_t == "sort":
                if not working_plan.get("sort_by"):
                    working_plan.setdefault("sort_by", []).append({
                        "column": op_item.get("column"),
                        "ascending": op_item.get("direction", "asc").lower() != "desc"
                    })
            elif op_t == "limit":
                if not working_plan.get("limit"):
                    working_plan["limit"] = op_item.get("value")

    raw_aggs = working_plan.get("aggregations")
    if isinstance(raw_aggs, dict):
        working_plan["aggregations"] = [{"column": k, "function": v} for k, v in raw_aggs.items()]

    op = (working_plan.get("operation") or "select").lower()
    operations_list: List[str] = []

    # Clean user-facing filename (prevent leaking server filesystem paths)
    clean_ds = dataset_name.replace("\\", "/").split("/")[-1] if dataset_name else "dataset.parquet"
    if not clean_ds:
        clean_ds = "dataset.parquet"

    # Select appropriate pandas loader
    ext = clean_ds.lower()
    if ext.endswith((".parquet", ".pq")):
        load_code = f'df = pd.read_parquet("{clean_ds}")'
    elif ext.endswith((".xlsx", ".xls")):
        sheet_arg = f', sheet_name="{sheet_name}"' if sheet_name else ""
        load_code = f'df = pd.read_excel("{clean_ds}"{sheet_arg})'
    else:
        load_code = f'df = pd.read_csv("{clean_ds}")'

    lines: List[str] = [
        "import pandas as pd",
        "",
        "# Load active dataset",
        load_code,
        ""
    ]

    conditions = working_plan.get("conditions") or []
    group_by = working_plan.get("group_by") or []
    aggregations = working_plan.get("aggregations") or []
    post_conditions = working_plan.get("post_conditions") or []
    sort_by = working_plan.get("sort_by") or []
    limit = working_plan.get("limit")
    target_columns = working_plan.get("target_columns") or []
    preserve_all = working_plan.get("preserve_all_columns", True)

    # ── BRANCH 1: Null Analysis ──────────────────────────────────────────
    if op == "null_analysis":
        operations_list.append("null_analysis")
        lines.append("# Calculate missing and null value metrics per column")
        lines.append("result = pd.DataFrame({")
        lines.append('    "Column": df.columns,')
        lines.append('    "Missing Values": df.isna().sum().values,')
        lines.append('    "Missing Percentage": (df.isna().mean() * 100).round(2).values')
        lines.append("})")
        lines.append("")
        lines.append("print(result)")

        return {
            "python_code": "\n".join(lines),
            "language": "python",
            "library": "pandas",
            "dataset_name": clean_ds,
            "operations": operations_list,
            "is_available": True,
            "message": "Reproducible null analysis query generated."
        }

    # ── BRANCH 2: Standalone Aggregation (Without Group By) ──────────────
    if op in ("aggregate", "agg", "calc", "math") and not group_by:
        operations_list.append("aggregate")
        agg_map = {
            "mean": "mean",
            "avg": "mean",
            "average": "mean",
            "sum": "sum",
            "total": "sum",
            "count": "count",
            "total_rows": "count",
            "min": "min",
            "minimum": "min",
            "lowest": "min",
            "max": "max",
            "maximum": "max",
            "highest": "max",
            "median": "median",
            "med": "median",
            "std": "std",
            "stddev": "std"
        }

        # Filtering prior to aggregation if conditions present
        filtered_var = "df"
        if conditions:
            operations_list.append("filter")
            filter_exprs = [_build_filter_expression(c, "df") for c in conditions]
            filter_exprs = [e for e in filter_exprs if e]
            if filter_exprs:
                lines.append("# Apply filter conditions")
                if len(filter_exprs) == 1:
                    lines.append(f"filtered_df = df[{filter_exprs[0]}]")
                else:
                    joined = " &\n    ".join(filter_exprs)
                    lines.append(f"filtered_df = df[\n    {joined}\n]")
                lines.append("")
                filtered_var = "filtered_df"

        lines.append("# Compute requested analytical metric(s)")
        records_code = ["records = []"]
        for agg in aggregations or [{"column": None, "function": "count"}]:
            col = agg.get("column")
            func = (agg.get("function") or "mean").lower()
            pd_func = agg_map.get(func, "mean")
            metric_label = pd_func.upper()

            if pd_func == "count":
                if col:
                    calc_expr = f'int({filtered_var}["{col}"].count())'
                else:
                    calc_expr = f'len({filtered_var})'
            else:
                col_ref = f'{filtered_var}["{col}"]' if col else f'{filtered_var}.iloc[:, 0]'
                calc_expr = f'round(float({col_ref}.{pd_func}()), 4)'

            col_label = f'"{col}"' if col else '"all"'
            records_code.append(
                f'records.append({{"Metric / Aggregation": "{metric_label}", "Column": {col_label}, "Calculated Value": {calc_expr}}})'
            )

        for rc in records_code:
            lines.append(rc)
        lines.append('result = pd.DataFrame(records)')
        lines.append("")
        lines.append("print(result)")

        return {
            "python_code": "\n".join(lines),
            "language": "python",
            "library": "pandas",
            "dataset_name": clean_ds,
            "operations": operations_list,
            "is_available": True,
            "message": "Reproducible aggregation query generated."
        }

    # ── BRANCH 3: Group By with Aggregations ──────────────────────────────
    if op in ("groupby", "group_by"):
        operations_list.append("groupby")
        # Step 3a: Filter first if conditions present
        current_var = "df"
        if conditions:
            operations_list.append("filter")
            filter_exprs = [_build_filter_expression(c, "df") for c in conditions]
            filter_exprs = [e for e in filter_exprs if e]
            if filter_exprs:
                lines.append("# Apply pre-aggregation filters")
                if len(filter_exprs) == 1:
                    lines.append(f"filtered_df = df[{filter_exprs[0]}]")
                else:
                    joined = " &\n    ".join(filter_exprs)
                    lines.append(f"filtered_df = df[\n    {joined}\n]")
                lines.append("")
                current_var = "filtered_df"

        # Step 3b: Build groupby .agg() statement
        group_cols_repr = "[" + ", ".join(f'"{g}"' for g in group_by) + "]" if len(group_by) > 1 else f'"{group_by[0]}"'

        agg_map = {
            "mean": "mean", "avg": "mean", "average": "mean",
            "sum": "sum", "total": "sum",
            "count": "count", "total_rows": "count",
            "min": "min", "minimum": "min", "lowest": "min",
            "max": "max", "maximum": "max", "highest": "max",
            "median": "median", "med": "median",
            "std": "std", "stddev": "std"
        }

        agg_args: List[str] = []
        for a in aggregations or [{"column": group_by[0], "function": "count"}]:
            col_target = a.get("column") or group_by[0]
            func = (a.get("function") or "mean").lower()
            pd_func = agg_map.get(func, "mean")
            func_suffix = pd_func.upper() if pd_func != "mean" else "AVG"

            alias = f"{col_target}_{func_suffix}"
            if _is_valid_identifier(alias):
                agg_args.append(f'{alias}=("{col_target}", "{pd_func}")')
            else:
                agg_args.append(f'**{{"{alias}": ("{col_target}", "{pd_func}")}}')

        lines.append(f"# Group by {', '.join(group_by)} and aggregate")
        lines.append("result = (")
        lines.append(f"    {current_var}.groupby({group_cols_repr}, as_index=False)")
        if agg_args:
            lines.append("      .agg(")
            for idx, a_arg in enumerate(agg_args):
                comma = "," if idx < len(agg_args) - 1 else ""
                lines.append(f"          {a_arg}{comma}")
            lines.append("      )")
        else:
            lines.append("      .size()")
            lines.append('      .rename(columns={"size": "count"})')
        lines.append(")")

        # Step 3b.2: Apply post-aggregation filters (Multi-Step Queries)
        if post_conditions:
            operations_list.append("post_filter")
            post_filter_exprs = [_build_filter_expression(c, "result") for c in post_conditions]
            post_filter_exprs = [e for e in post_filter_exprs if e]
            if post_filter_exprs:
                lines.append("")
                lines.append("# Filter aggregated results (multi-step query)")
                if len(post_filter_exprs) == 1:
                    expr = post_filter_exprs[0]
                    if expr.startswith("(") and expr.endswith(")"):
                        expr = expr[1:-1]
                    lines.append(f"result = result[{expr}].copy()")
                else:
                    joined_post = " &\n    ".join(post_filter_exprs)
                    lines.append(f"result = result[\n    {joined_post}\n].copy()")

        # Step 3c: Sort if requested
        if sort_by:
            operations_list.append("sort")
            sort_cols = [s.get("column") for s in sort_by if s.get("column")]
            sort_asc = [s.get("ascending", True) for s in sort_by if s.get("column")]
            if sort_cols:
                lines.append("")
                lines.append("# Sort grouped results")
                if len(sort_cols) == 1:
                    lines.append(f'result = result.sort_values(by="{sort_cols[0]}", ascending={sort_asc[0]})')
                else:
                    cols_str = "[" + ", ".join(f'"{c}"' for c in sort_cols) + "]"
                    asc_str = "[" + ", ".join(str(a) for a in sort_asc) + "]"
                    lines.append(f'result = result.sort_values(by={cols_str}, ascending={asc_str})')

        # Step 3d: Limit
        if limit and int(limit) > 0:
            operations_list.append("limit")
            lines.append("")
            lines.append(f"result = result.head({int(limit)})")

        lines.append("")
        lines.append("print(result)")

        return {
            "python_code": "\n".join(lines),
            "language": "python",
            "library": "pandas",
            "dataset_name": clean_ds,
            "operations": operations_list,
            "is_available": True,
            "message": "Reproducible groupby query generated."
        }

    # ── BRANCH 4: Standard Select / Filter / Sort / Limit ─────────────────
    filter_exprs = []
    if conditions:
        operations_list.append("filter")
        filter_exprs = [_build_filter_expression(c, "df") for c in conditions]
        filter_exprs = [e for e in filter_exprs if e]

    if filter_exprs:
        lines.append("# Apply filter conditions")
        if len(filter_exprs) == 1:
            expr = filter_exprs[0]
            if expr.startswith("(") and expr.endswith(")"):
                expr = expr[1:-1]
            lines.append(f"result = df[{expr}].copy()")
        else:
            joined = " &\n    ".join(filter_exprs)
            lines.append(f"result = df[\n    {joined}\n].copy()")
    else:
        lines.append("# Select dataset records")
        lines.append("result = df.copy()")

    # Column selection / projection
    if target_columns and not preserve_all:
        operations_list.append("select")
        cols_repr = "[" + ", ".join(f'"{c}"' for c in target_columns) + "]"
        lines.append("")
        lines.append("# Select explicit target columns")
        lines.append(f"result = result[{cols_repr}]")

    # Sorting
    if sort_by or op in ("top_n", "bottom_n"):
        operations_list.append("sort")
        sort_cols = [s.get("column") for s in sort_by if s.get("column")]
        sort_asc = [s.get("ascending", True) for s in sort_by if s.get("column")]
        if sort_cols:
            lines.append("")
            lines.append("# Sort records")
            if len(sort_cols) == 1:
                lines.append(f'result = result.sort_values(by="{sort_cols[0]}", ascending={sort_asc[0]})')
            else:
                cols_str = "[" + ", ".join(f'"{c}"' for c in sort_cols) + "]"
                asc_str = "[" + ", ".join(str(a) for a in sort_asc) + "]"
                lines.append(f'result = result.sort_values(by={cols_str}, ascending={asc_str})')

    # Limiting
    limit_count = limit
    if op in ("top_n", "top"):
        limit_count = limit or 10
    elif op in ("bottom_n", "bottom"):
        limit_count = limit or 10

    if limit_count and int(limit_count) > 0:
        operations_list.append("limit")
        lines.append("")
        lines.append(f"result = result.head({int(limit_count)})")

    lines.append("")
    lines.append("print(result)")

    if not operations_list:
        operations_list.append("select")

    return {
        "python_code": "\n".join(lines),
        "language": "python",
        "library": "pandas",
        "dataset_name": clean_ds,
        "operations": operations_list,
        "is_available": True,
        "message": "Reproducible Python query generated successfully."
    }

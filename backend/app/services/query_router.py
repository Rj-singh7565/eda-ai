"""
Query Router & Planner — Classifies user questions and translates intent into
deterministic DataFrame Operation Plans or Adaptive Document RAG retrieval.
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple

from backend.app.services import dataset_engine
from backend.app import config


def is_structured_query(question: str, schema_info: Optional[Dict[str, Any]] = None) -> bool:
    """
    Heuristic and schema-aware check if a question is asking for structured data operations:
    filtering, calculations, sorting, aggregations, counting, or column queries.
    """
    q_lower = question.lower().strip()

    # Common analytical & computational keywords
    structured_keywords = [
        "show all", "show me", "filter", "sort", "average", "avg", "mean",
        "median", "maximum", "max", "minimum", "min", "highest", "lowest",
        "top ", "bottom ", "count", "how many", "sum", "total", "greater than",
        "less than", "above", "below", "more than", "at least", "at most",
        "group by", "branch-wise", "department-wise", "category-wise",
        "unique", "distinct", "missing", "null", "records where", "rows where",
        "where", "whose", "having", "package >", "cgpa >", "salary >", "age >",
        "list all", "find all", "compare", "breakdown"
    ]

    for kw in structured_keywords:
        if kw in q_lower:
            return True

    # Check for comparison operators in query like ">", "<", "=", ">=", "<="
    if re.search(r"(\w+)\s*([><]=?|==?|!=)\s*(\d+(\.\d+)?)", q_lower):
        return True

    # Check if question mentions known dataset column names
    if schema_info and "columns" in schema_info:
        for col in schema_info["columns"]:
            if len(col) >= 3 and col.lower() in q_lower:
                return True

    return False


def classify_query(
    question: str,
    doc_id: str
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Classifies question into:
    - 'STRUCTURED_DATA_OPERATION' (CSV / XLSX with tabular intent)
    - 'DOCUMENT_RAG' (PDF, Word, PPTX, Plaintext, OCR or unstructured question)
    - 'HYBRID' (Mixed questions)
    """
    is_struct_file = dataset_engine.is_structured_file(doc_id)
    if not is_struct_file:
        return "DOCUMENT_RAG", None

    schema_info = dataset_engine.get_dataset_schema(doc_id)
    if "error" in schema_info:
        return "DOCUMENT_RAG", None

    if is_structured_query(question, schema_info):
        return "STRUCTURED_DATA_OPERATION", schema_info

    # For structured files, default to structured data operation to ensure deterministic access
    return "STRUCTURED_DATA_OPERATION", schema_info


def parse_structured_plan_rule_based(question: str, schema_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic rule-based query parser that translates natural language
    into a validated DataFrame operation plan.
    """
    q_lower = question.lower()
    columns: List[str] = schema_info.get("columns", [])
    numeric_cols: List[str] = schema_info.get("numeric_columns", [])
    categorical_cols: List[str] = schema_info.get("categorical_columns", [])

    plan: Dict[str, Any] = {
        "operation": "select",
        "target_columns": [],
        "preserve_all_columns": True,
        "conditions": [],
        "sort_by": [],
        "group_by": [],
        "aggregations": [],
        "limit": None
    }

    # 1. Detect Explicit Column Selection (e.g., "Show only Student and CGPA for ...")
    show_only_match = re.search(
        r"\b(?:show|display|select|give me|print)\s+only\s+([\w\s,]+?)(?:\s+(?:for|where|with|from|having)\b|$)",
        q_lower
    )
    if show_only_match:
        requested_str = show_only_match.group(1)
        raw_cols = re.split(r",|\band\b", requested_str)
        explicit_cols = []
        for rc in raw_cols:
            rc_clean = rc.strip()
            if rc_clean:
                matched = dataset_engine.resolve_column_name(rc_clean, columns)
                if matched:
                    explicit_cols.append(matched)

        if explicit_cols:
            plan["target_columns"] = explicit_cols
            plan["preserve_all_columns"] = False

    # 2. Detect Aggregations / Calculations (Average, Sum, Count, Min, Max, Median)
    agg_keywords = {
        "average": "mean",
        "avg": "mean",
        "mean": "mean",
        "sum": "sum",
        "total": "sum",
        "count": "count",
        "how many": "count",
        "minimum": "min",
        "min": "min",
        "lowest": "min",
        "maximum": "max",
        "max": "max",
        "highest": "max",
        "median": "median",
        "standard deviation": "std",
        "std dev": "std"
    }

    detected_agg = None
    for kw, fn in agg_keywords.items():
        if kw in q_lower:
            detected_agg = fn
            break

    # 3. Detect Group By (e.g., "branch-wise", "department-wise", "by branch", "group by category")
    groupby_match = re.search(r"\b(?:group(?:ed)?\s+by|by|per|across)\s+([a-zA-Z0-9_\s]+)", q_lower)
    branch_wise_match = re.search(r"\b([a-zA-Z0-9_]+)[-_ ]wise\b", q_lower)

    target_group_col = None
    if branch_wise_match:
        target_group_col = dataset_engine.resolve_column_name(branch_wise_match.group(1), columns)
    elif groupby_match:
        cand_group = groupby_match.group(1).split()[0]
        target_group_col = dataset_engine.resolve_column_name(cand_group, columns)

    if target_group_col:
        plan["operation"] = "groupby"
        plan["group_by"] = [target_group_col]

        # Target numeric column for calculation
        calc_col = None
        for col in numeric_cols:
            if col.lower() in q_lower and col != target_group_col:
                calc_col = col
                break
        if not calc_col:
            calc_col = numeric_cols[0] if numeric_cols else columns[0]

        plan["aggregations"] = [{"column": calc_col, "function": detected_agg or "mean"}]
        return plan

    # If aggregation detected without group by (e.g. "What is the average salary?")
    if detected_agg and not re.search(r"\b(show|list|filter|give me all)\b", q_lower):
        # Find column to aggregate
        target_agg_col = None
        for col in numeric_cols:
            if col.lower() in q_lower or dataset_engine.resolve_column_name(col, [q_lower]):
                target_agg_col = col
                break
        if not target_agg_col:
            target_agg_col = numeric_cols[0] if numeric_cols else columns[0]

        plan["operation"] = "aggregate"
        plan["aggregations"] = [{"column": target_agg_col, "function": detected_agg}]
        return plan

    # 4. Detect Top N / Bottom N / Sorting
    top_n_match = re.search(r"\b(?:top|first|highest)\s+(\d+)\b", q_lower)
    bottom_n_match = re.search(r"\b(?:bottom|last|lowest)\s+(\d+)\b", q_lower)

    if top_n_match:
        plan["operation"] = "top_n"
        plan["limit"] = int(top_n_match.group(1))
        # Find numeric column to sort descending
        for col in numeric_cols:
            if col.lower() in q_lower:
                plan["sort_by"] = [{"column": col, "ascending": False}]
                break
        if not plan["sort_by"] and numeric_cols:
            plan["sort_by"] = [{"column": numeric_cols[0], "ascending": False}]
    elif bottom_n_match:
        plan["operation"] = "bottom_n"
        plan["limit"] = int(bottom_n_match.group(1))
        for col in numeric_cols:
            if col.lower() in q_lower:
                plan["sort_by"] = [{"column": col, "ascending": True}]
                break
        if not plan["sort_by"] and numeric_cols:
            plan["sort_by"] = [{"column": numeric_cols[0], "ascending": True}]

    # 5. Schema-Direct Numeric Filter Conditions
    matched_filter_cols = set()
    for col in columns:
        col_esc = re.escape(col.lower())
        # e.g., "CGPA > 8", "CGPA >= 8", "CGPA above 8", "CGPA greater than 8", "with CGPA > 8"
        gt_pat = r"\b" + col_esc + r"\b\s*(?:is\s+)?(?:above|greater than|more than|exceeding|over|higher than|>=|>)\s*(\d+(?:\.\d+)?)"
        m_gt = re.search(gt_pat, q_lower)
        if m_gt:
            val = float(m_gt.group(1))
            op = ">=" if (">=" in m_gt.group(0) or "at least" in m_gt.group(0)) else ">"
            plan["operation"] = "filter"
            plan["conditions"].append({"column": col, "operator": op, "value": val})
            matched_filter_cols.add(col)
            continue

        lt_pat = r"\b" + col_esc + r"\b\s*(?:is\s+)?(?:below|less than|under|lower than|<=|<)\s*(\d+(?:\.\d+)?)"
        m_lt = re.search(lt_pat, q_lower)
        if m_lt:
            val = float(m_lt.group(1))
            op = "<=" if ("<=" in m_lt.group(0) or "at most" in m_lt.group(0)) else "<"
            plan["operation"] = "filter"
            plan["conditions"].append({"column": col, "operator": op, "value": val})
            matched_filter_cols.add(col)
            continue

        eq_pat = r"\b" + col_esc + r"\b\s*(?:is\s+|==?\s*|equals?\s+(?:to\s+)?)\s*(\d+(?:\.\d+)?)"
        m_eq = re.search(eq_pat, q_lower)
        if m_eq:
            val = float(m_eq.group(1))
            plan["operation"] = "filter"
            plan["conditions"].append({"column": col, "operator": "==", "value": val})
            matched_filter_cols.add(col)
            continue

    # Fallback pattern for columns referenced by relative phrasing
    if not plan["conditions"]:
        comp_patterns = [
            r"([a-zA-Z0-9_\s]+?)\s*([><]=?|==?|!=)\s*(\d+(?:\.\d+)?)",
            r"([a-zA-Z0-9_\s]+?)\s+(?:above|greater than|more than|exceeding|over|higher than|>=|>)\s*(\d+(?:\.\d+)?)",
            r"([a-zA-Z0-9_\s]+?)\s+(?:below|less than|under|lower than|<=|<)\s*(\d+(?:\.\d+)?)",
            r"([a-zA-Z0-9_\s]+?)\s+(?:equal to|equals|is|=|==)\s*(\d+(?:\.\d+)?)"
        ]

        for pat in comp_patterns:
            matches = re.finditer(pat, q_lower)
            for m in matches:
                raw_c = m.group(1).strip()
                while True:
                    cleaned = re.sub(
                        r"^(?:show|find|list|get|give me|all|only|the|students?|employees?|records?|rows?|where|with|whose|having|for)\s+",
                        "",
                        raw_c,
                        flags=re.IGNORECASE
                    ).strip()
                    if cleaned == raw_c:
                        break
                    raw_c = cleaned

                matched_col = dataset_engine.resolve_column_name(raw_c, columns)
                if matched_col and matched_col not in matched_filter_cols:
                    val = float(m.group(len(m.groups())))
                    op = ">"
                    matched_text = m.group(0)
                    if any(w in matched_text for w in ["below", "less", "under", "lower", "<"]):
                        op = "<"
                    elif any(w in matched_text for w in ["equal", "==", "="]) and not any(w in matched_text for w in [">=", "<=", ">", "<"]):
                        op = "=="
                    elif ">=" in matched_text or "at least" in matched_text:
                        op = ">="
                    elif "<=" in matched_text or "at most" in matched_text:
                        op = "<="

                    plan["operation"] = "filter"
                    plan["conditions"].append({
                        "column": matched_col,
                        "operator": op,
                        "value": val
                    })
                    matched_filter_cols.add(matched_col)

    # 6. Detect Categorical / String Filter Conditions (e.g., "from CSE", "department is Sales", "Company == Google")
    cat_samples = schema_info.get("samples", {})
    for col, sample_vals in cat_samples.items():
        for val in sample_vals:
            if not val or val.lower() in ("nan", "none", "—", "null") or len(val) < 2:
                continue
            # Word boundary search for categorical value in query
            val_pattern = r"\b" + re.escape(val.lower()) + r"\b"
            if re.search(val_pattern, q_lower):
                already_added = any(c.get("column") == col and c.get("value") == val for c in plan["conditions"])
                if not already_added:
                    plan["operation"] = "filter"
                    plan["conditions"].append({
                        "column": col,
                        "operator": "==",
                        "value": val
                    })

    # 7. Check for Missing / Null Analysis
    if any(w in q_lower for w in ["missing value", "null value", "missing data", "null count", "nan count"]):
        plan["operation"] = "null_analysis"

    return plan


def plan_structured_operation(question: str, schema_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main planner for structured dataset operations.
    Translates question to a validated Plan dictionary.
    """
    return parse_structured_plan_rule_based(question, schema_info)

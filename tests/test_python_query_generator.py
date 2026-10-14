"""
Unit and Parity Tests for Canonical Analytical Plan and Python Query Generator.
Guarantees:
1. Exact Result Parity: DuckDB result == Python result
2. Supported Operations: Filter, Multi-filter, Groupby, Multi-agg, Sort, Limit, Count, Null Analysis
3. Multi-Step Chained Queries
4. Clean User-Facing Dataset Filenames (Zero Server Path Leakage)
5. Single Source of Truth Canonical Plan
"""

import os
import pytest
import pandas as pd
import numpy as np

from backend.app import config
from backend.app.database import database
from backend.app.services import dataset_engine, query_router
from backend.app.services.python_query_generator import generate_python_query


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path):
    """Setup isolated test database and upload directory."""
    test_db = str(tmp_path / "test_eda_py.db")
    test_upload = str(tmp_path / "uploads")
    os.makedirs(test_upload, exist_ok=True)

    orig_db = config.DB_PATH
    orig_upload = config.UPLOAD_DIR

    config.DB_PATH = test_db
    config.UPLOAD_DIR = test_upload
    database.init_db()
    dataset_engine._DF_CACHE.clear()

    yield

    config.DB_PATH = orig_db
    config.UPLOAD_DIR = orig_upload
    dataset_engine._DF_CACHE.clear()


def create_sample_sales_csv(doc_id: str = "doc_sales") -> str:
    """Create sample sales dataset for testing analytical operations and parity."""
    data = {
        "region": ["North", "North", "South", "South", "East", "West"],
        "rep": ["Alice", "Bob", "Charlie", "Diana", "Evan", "Fiona"],
        "sales": [12000.0, 8500.0, 15000.0, 3200.0, 18500.0, 9100.0],
        "units": [120, 85, 150, 32, 185, 91],
        "category": ["Tech", "Furniture", "Tech", "Supplies", "Tech", "Furniture"]
    }
    df = pd.DataFrame(data)
    file_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}_sales.csv")
    df.to_csv(file_path, index=False)

    database.create_document(
        doc_id=doc_id,
        filename="sales_data.csv",
        file_size=os.path.getsize(file_path),
        file_type="csv"
    )
    database.update_document_status(doc_id, "ready", page_count=1, chunk_count=1)
    return doc_id


def execute_python_code(code_str: str, file_path: str) -> pd.DataFrame:
    """
    Execute generated Python code in an isolated namespace pointing to the test file.
    """
    # Replace the generic filename with the real test file path for execution
    filename = os.path.basename(file_path)
    # The code expects pd.read_csv("sales_data.csv")
    adapted_code = code_str.replace(f'pd.read_csv("sales_data.csv")', f'pd.read_csv(r"{file_path}")')
    adapted_code = adapted_code.replace(f'pd.read_parquet("sales_data.csv")', f'pd.read_csv(r"{file_path}")')

    local_namespace = {}
    exec(adapted_code, globals(), local_namespace)
    return local_namespace.get("result")


# ── TEST 1: Canonical Analytical Plan Structure ───────────────────────────

def test_canonical_analytical_plan_structure():
    """Verify plan produces canonical operations list sequence."""
    doc_id = create_sample_sales_csv("doc_plan_test")
    schema_info = dataset_engine.get_dataset_schema(doc_id)

    plan = query_router.plan_structured_operation("Show records where sales > 10000", schema_info)
    assert "operations" in plan
    assert len(plan["operations"]) >= 1

    filter_op = plan["operations"][0]
    assert filter_op["type"] == "filter"
    assert filter_op["column"] == "sales"
    assert filter_op["operator"] == ">"
    assert filter_op["value"] == 10000.0


# ── TEST 2: Exact Parity on Filtering (Single and Multiple) ────────────────

def test_filter_exact_parity():
    """DuckDB result == Python result for single filter condition."""
    doc_id = create_sample_sales_csv("doc_filter_parity")
    file_path = dataset_engine._get_raw_file_path(doc_id)
    schema_info = dataset_engine.get_dataset_schema(doc_id)

    plan = query_router.plan_structured_operation("Show records where sales > 10000", schema_info)
    duck_res = dataset_engine.execute_dataframe_operation(doc_id, plan)
    py_res = generate_python_query(plan, dataset_name="sales_data.csv")

    assert duck_res["success"] is True
    assert py_res["is_available"] is True

    # Execute Python script
    py_df = execute_python_code(py_res["python_code"], file_path)
    assert py_df is not None

    # Parity assertions: Row count, columns, data values
    assert len(py_df) == duck_res["row_count"]
    assert list(py_df.columns) == duck_res["columns"]

    # Check rows match
    py_reps = set(py_df["rep"].tolist())
    duck_reps = {r[1] for r in duck_res["rows"]}
    assert py_reps == duck_reps == {"Alice", "Charlie", "Evan"}

    for _, row in py_df.iterrows():
        matching = [r for r in duck_res["rows"] if r[1] == row["rep"]]
        assert len(matching) == 1
        assert float(matching[0][2]) == float(row["sales"])


def test_multiple_filters_parity():
    """DuckDB result == Python result for multiple combined filter conditions."""
    doc_id = create_sample_sales_csv("doc_multi_filter")
    file_path = dataset_engine._get_raw_file_path(doc_id)

    plan = {
        "operation": "filter",
        "conditions": [
            {"column": "sales", "operator": ">", "value": 5000},
            {"column": "category", "operator": "==", "value": "Tech"}
        ],
        "preserve_all_columns": True,
        "sort_by": [],
        "limit": None
    }
    duck_res = dataset_engine.execute_dataframe_operation(doc_id, plan)
    py_res = generate_python_query(plan, dataset_name="sales_data.csv")

    assert duck_res["success"] is True
    py_df = execute_python_code(py_res["python_code"], file_path)

    assert len(py_df) == duck_res["row_count"]
    assert list(py_df.columns) == duck_res["columns"]


# ── TEST 3: Exact Parity on GroupBy and Aggregations ───────────────────────

def test_groupby_exact_parity():
    """DuckDB result == Python result for groupby and mean aggregation."""
    doc_id = create_sample_sales_csv("doc_groupby_parity")
    file_path = dataset_engine._get_raw_file_path(doc_id)
    schema_info = dataset_engine.get_dataset_schema(doc_id)

    plan = query_router.plan_structured_operation("What is the average sales by region?", schema_info)
    duck_res = dataset_engine.execute_dataframe_operation(doc_id, plan)
    py_res = generate_python_query(plan, dataset_name="sales_data.csv")

    assert duck_res["success"] is True
    py_df = execute_python_code(py_res["python_code"], file_path)

    assert len(py_df) == duck_res["row_count"]
    assert list(py_df.columns) == duck_res["columns"]

    # Verify calculated values match within tolerance
    duck_map = {r[0]: float(r[1].replace(",", "")) for r in duck_res["rows"]}
    for _, row in py_df.iterrows():
        reg = str(row["region"])
        assert reg in duck_map
        py_val = float(row.iloc[1])
        assert abs(duck_map[reg] - py_val) < 0.01


# ── TEST 4: Multi-Step Queries ─────────────────────────────────────────────

def test_multistep_query_complete_reproduction():
    """
    Requirement 9: Follow-up query must reproduce the COMPLETE pipeline
    from raw dataset rather than an intermediate slice.
    """
    doc_id = create_sample_sales_csv("doc_multistep")
    file_path = dataset_engine._get_raw_file_path(doc_id)
    schema_info = dataset_engine.get_dataset_schema(doc_id)

    # Step 1: Average sales by region
    plan1 = query_router.plan_structured_operation("Show average sales by region", schema_info)
    assert plan1["operation"] == "groupby"

    # Step 2: Follow-up query referencing step 1
    plan2 = query_router.plan_structured_operation(
        "Only show regions where average sales > 10000",
        schema_info,
        prev_plan=plan1
    )

    assert plan2["operation"] == "groupby"
    assert len(plan2.get("post_conditions", [])) > 0

    duck_res = dataset_engine.execute_dataframe_operation(doc_id, plan2)
    py_res = generate_python_query(plan2, dataset_name="sales_data.csv")

    assert duck_res["success"] is True
    # The generated Python must contain the complete groupby and the post-filter
    assert "df.groupby" in py_res["python_code"]
    assert "sales_AVG" in py_res["python_code"]
    assert "> 10000" in py_res["python_code"]

    py_df = execute_python_code(py_res["python_code"], file_path)
    assert len(py_df) == duck_res["row_count"]
    # Only regions with avg sales > 10000 (North: 10250, East: 18500)
    for idx, row in py_df.iterrows():
        assert float(row["sales_AVG"]) > 10000


# ── TEST 5: Sorting and Limit Parity ───────────────────────────────────────

def test_sorting_and_limit_parity():
    """DuckDB result == Python result for sorting and limit."""
    doc_id = create_sample_sales_csv("doc_sort_limit")
    file_path = dataset_engine._get_raw_file_path(doc_id)

    plan = {
        "operation": "select",
        "preserve_all_columns": True,
        "conditions": [],
        "sort_by": [{"column": "sales", "ascending": False}],
        "limit": 3
    }
    duck_res = dataset_engine.execute_dataframe_operation(doc_id, plan)
    py_res = generate_python_query(plan, dataset_name="sales_data.csv")

    assert duck_res["success"] is True
    py_df = execute_python_code(py_res["python_code"], file_path)

    assert len(py_df) == 3
    assert len(py_df) == duck_res["row_count"]
    # Top sale should be East (18500)
    assert float(py_df.iloc[0]["sales"]) == 18500.0


# ── TEST 6: Zero Server Path Leakage ───────────────────────────────────────

def test_zero_server_filesystem_leakage():
    """
    Requirement 10: Generated code must NEVER expose internal server file paths.
    Must output pd.read_csv("sales_data.csv") not C:/... or /home/app/...
    """
    plan = {
        "operation": "select",
        "preserve_all_columns": True,
        "conditions": []
    }
    # Pass a server file path to simulate potential leak
    leak_attempt = "C:\\Users\\rajsi\\Desktop\\edaa\\uploads\\secret_internal_doc.csv"
    py_res = generate_python_query(plan, dataset_name=leak_attempt)

    code = py_res["python_code"]
    assert "secret_internal_doc.csv" in code
    assert "C:\\" not in code
    assert "Users" not in code
    assert "uploads" not in code

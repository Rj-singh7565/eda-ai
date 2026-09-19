"""
Comprehensive Regression Test Suite for Structured Dataset Engine, Column Preservation,
Query Router, and Adaptive Multi-Tier Retrieval.
"""

import os
import shutil
import tempfile
import pytest
import pandas as pd
import numpy as np

from backend.app import config
from backend.app.database import database
from backend.app.services import dataset_engine, query_router, retrieval


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path):
    """Setup isolated test database and upload directory."""
    test_db = str(tmp_path / "test_eda.db")
    test_upload = str(tmp_path / "uploads")
    os.makedirs(test_upload, exist_ok=True)

    orig_db = config.DB_PATH
    orig_upload = config.UPLOAD_DIR

    config.DB_PATH = test_db
    config.UPLOAD_DIR = test_upload
    database.init_db()

    # Clear DataFrame cache
    dataset_engine._DF_CACHE.clear()

    yield

    config.DB_PATH = orig_db
    config.UPLOAD_DIR = orig_upload
    dataset_engine._DF_CACHE.clear()


def create_sample_student_csv(doc_id: str = "doc_students") -> str:
    """Create a sample 7-column student dataset."""
    data = {
        "Student": ["Alice Smith", "Bob Jones", "Charlie Brown", "Diana Prince", "Evan Wright"],
        "Roll No": [101, 102, 103, 104, 105],
        "Branch": ["CSE", "ECE", "CSE", "MECH", "CSE"],
        "CGPA": [8.5, 7.2, 9.1, 8.0, 6.8],
        "Company": ["Google", "TCS", "Microsoft", "Tata Motors", "Infosys"],
        "Package": [25.0, 7.5, 32.0, 12.0, 6.5],
        "Location": ["Bangalore", "Mumbai", "Hyderabad", "Pune", "Chennai"]
    }
    df = pd.DataFrame(data)
    file_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}_students.csv")
    df.to_csv(file_path, index=False)

    database.create_document(
        doc_id=doc_id,
        filename="students.csv",
        file_size=os.path.getsize(file_path),
        file_type="csv"
    )
    database.update_document_status(doc_id, "ready", page_count=1, chunk_count=1)
    return doc_id


def test_exact_column_preservation_on_filter():
    """
    CRITICAL TEST: When filtering records, ALL 7 original columns MUST be preserved
    in their exact original order and casing when the user does not specify columns.
    """
    doc_id = create_sample_student_csv("doc_preserve_test")
    question = "Show students with CGPA above 8."

    schema_info = dataset_engine.get_dataset_schema(doc_id)
    plan = query_router.plan_structured_operation(question, schema_info)
    result = dataset_engine.execute_dataframe_operation(doc_id, plan)

    assert result["success"] is True
    expected_cols = ["Student", "Roll No", "Branch", "CGPA", "Company", "Package", "Location"]
    assert result["columns"] == expected_cols

    # Qualifying rows: Alice (8.5), Charlie (9.1) -> 2 rows
    assert result["row_count"] == 2
    for row in result["rows"]:
        assert len(row) == len(expected_cols)

    # Verify Markdown table contains all column headers
    for col in expected_cols:
        assert col in result["markdown_table"]


def test_explicit_column_selection():
    """
    When the user explicitly asks: 'Show only Student and CGPA for students with CGPA above 8',
    only the requested columns should be returned.
    """
    doc_id = create_sample_student_csv("doc_explicit_test")
    question = "Show only Student and CGPA for students with CGPA above 8"

    schema_info = dataset_engine.get_dataset_schema(doc_id)
    plan = query_router.plan_structured_operation(question, schema_info)
    result = dataset_engine.execute_dataframe_operation(doc_id, plan)

    assert result["success"] is True
    assert result["columns"] == ["Student", "CGPA"]
    assert result["row_count"] == 2


def test_numeric_aggregations_and_calculations():
    """
    Calculations (average, max, min, sum, count) must be computed by code, not hallucinated.
    """
    doc_id = create_sample_student_csv("doc_agg_test")

    # Average Package
    avg_q = "What is the average package?"
    schema_info = dataset_engine.get_dataset_schema(doc_id)
    plan = query_router.plan_structured_operation(avg_q, schema_info)
    result = dataset_engine.execute_dataframe_operation(doc_id, plan)

    assert result["success"] is True
    assert result["operation"] == "aggregate"
    # Packages: [25.0, 7.5, 32.0, 12.0, 6.5] -> Mean = 16.6
    found_avg = False
    for row in result["rows"]:
        if "MEAN" in row[0] or "Package" in row[1]:
            val = float(row[2].replace(",", ""))
            assert abs(val - 16.6) < 0.01
            found_avg = True
    assert found_avg is True

    # Max Package
    max_q = "What is the maximum package?"
    plan_max = query_router.plan_structured_operation(max_q, schema_info)
    result_max = dataset_engine.execute_dataframe_operation(doc_id, plan_max)
    assert result_max["success"] is True
    for row in result_max["rows"]:
        if "MAX" in row[0] or "Package" in row[1]:
            val = float(row[2].replace(",", ""))
            assert val == 32.0


def test_groupby_branch_wise_calculation():
    """
    Test branch-wise grouping and calculations.
    """
    doc_id = create_sample_student_csv("doc_group_test")
    question = "What is the average package branch-wise?"

    schema_info = dataset_engine.get_dataset_schema(doc_id)
    plan = query_router.plan_structured_operation(question, schema_info)
    result = dataset_engine.execute_dataframe_operation(doc_id, plan)

    assert result["success"] is True
    assert result["operation"] == "groupby"
    assert "Branch" in result["columns"][0]
    # Check that CSE, ECE, MECH groups exist
    branch_vals = [r[0] for r in result["rows"]]
    assert "CSE" in branch_vals
    assert "ECE" in branch_vals
    assert "MECH" in branch_vals


def test_schema_aware_missing_column_error():
    """
    If the user requests a non-existent column, return a helpful schema-aware message
    rather than hallucinating or returning 'Information Not Found'.
    """
    doc_id = create_sample_student_csv("doc_missing_col_test")
    plan = {
        "operation": "select",
        "target_columns": ["NonExistentColumn", "Salary"],
        "preserve_all_columns": False,
        "conditions": []
    }
    result = dataset_engine.execute_dataframe_operation(doc_id, plan)

    assert result["success"] is False
    assert result["error_type"] == "missing_column"
    assert "Available columns are:" in result["message"]
    assert "Student" in result["message"]
    assert "CGPA" in result["message"]


def test_categorical_filtering_from_cse():
    """
    Filter records by categorical branch (e.g., 'How many students are from CSE?').
    """
    doc_id = create_sample_student_csv("doc_cat_test")
    question = "Show all students from CSE"

    schema_info = dataset_engine.get_dataset_schema(doc_id)
    plan = query_router.plan_structured_operation(question, schema_info)
    result = dataset_engine.execute_dataframe_operation(doc_id, plan)

    assert result["success"] is True
    assert result["row_count"] == 3 # Alice, Charlie, Evan
    assert result["columns"] == ["Student", "Roll No", "Branch", "CGPA", "Company", "Package", "Location"]


def test_null_missing_values_analysis():
    """
    Ensure datasets with missing values are handled gracefully without crashing.
    """
    data = {
        "ID": [1, 2, 3, 4],
        "Score": [10.5, None, 20.0, np.nan],
        "Category": ["A", "B", None, "D"]
    }
    df = pd.DataFrame(data)
    doc_id = "doc_nulls_test"
    file_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}_nulls.csv")
    df.to_csv(file_path, index=False)
    database.create_document(doc_id=doc_id, filename="nulls.csv", file_size=100, file_type="csv")
    database.update_document_status(doc_id, "ready")

    schema_info = dataset_engine.get_dataset_schema(doc_id)
    plan = query_router.plan_structured_operation("Check missing values in dataset", schema_info)
    result = dataset_engine.execute_dataframe_operation(doc_id, plan)

    assert result["success"] is True
    assert result["operation"] == "null_analysis"
    assert result["row_count"] == 3 # 3 columns analyzed


def test_large_dataset_filtering_and_column_preservation():
    """
    Test filtering on a dataset with 5,000 rows.
    """
    np.random.seed(42)
    n = 5000
    df = pd.DataFrame({
        "EmpID": range(1000, 1000 + n),
        "Department": np.random.choice(["Engineering", "Sales", "Marketing", "Finance"], n),
        "Salary": np.random.randint(40000, 150000, n),
        "Rating": np.random.uniform(1.0, 5.0, n).round(2),
        "City": np.random.choice(["New York", "London", "Tokyo", "Berlin"], n)
    })
    doc_id = "doc_large_test"
    file_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}_large.csv")
    df.to_csv(file_path, index=False)
    database.create_document(doc_id=doc_id, filename="large.csv", file_size=100000, file_type="csv")
    database.update_document_status(doc_id, "ready")

    schema_info = dataset_engine.get_dataset_schema(doc_id)
    plan = query_router.plan_structured_operation("Show records where Salary > 120000", schema_info)
    result = dataset_engine.execute_dataframe_operation(doc_id, plan)

    assert result["success"] is True
    assert result["columns"] == ["EmpID", "Department", "Salary", "Rating", "City"]
    assert result["row_count"] > 500


def test_multi_sheet_excel_processing():
    """
    Test loading and querying specific sheets in a multi-sheet Excel workbook.
    """
    doc_id = "doc_excel_sheets"
    file_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}_book.xlsx")

    with pd.ExcelWriter(file_path) as writer:
        pd.DataFrame({"Quarter": ["Q1", "Q2"], "Revenue": [100, 200]}).to_excel(writer, sheet_name="Financials", index=False)
        pd.DataFrame({"Dept": ["HR", "Dev"], "Headcount": [10, 50]}).to_excel(writer, sheet_name="Staffing", index=False)

    database.create_document(doc_id=doc_id, filename="book.xlsx", file_size=2000, file_type="excel")
    database.update_document_status(doc_id, "ready")

    df_fin, err = dataset_engine.load_dataframe(doc_id, sheet_name="Financials")
    assert err is None
    assert list(df_fin.columns) == ["Quarter", "Revenue"]

    df_staff, err2 = dataset_engine.load_dataframe(doc_id, sheet_name="Staffing")
    assert err2 is None
    assert list(df_staff.columns) == ["Dept", "Headcount"]


def test_cross_document_isolation():
    """
    Ensure querying doc_A cannot access data or schema from doc_B.
    """
    doc_a = create_sample_student_csv("doc_iso_a")
    df_b = pd.DataFrame({"Product": ["Laptop", "Mouse"], "Price": [1000, 25]})
    file_b = os.path.join(config.UPLOAD_DIR, "doc_iso_b_products.csv")
    df_b.to_csv(file_b, index=False)
    database.create_document("doc_iso_b", filename="products.csv", file_size=200, file_type="csv")
    database.update_document_status("doc_iso_b", "ready")

    schema_a = dataset_engine.get_dataset_schema(doc_a)
    schema_b = dataset_engine.get_dataset_schema("doc_iso_b")

    assert "Student" in schema_a["columns"]
    assert "Product" not in schema_a["columns"]

    assert "Product" in schema_b["columns"]
    assert "Student" not in schema_b["columns"]


def test_query_router_intent_classification():
    """
    Test that questions are correctly routed between Structured Data Operations and Document RAG.
    """
    doc_id = create_sample_student_csv("doc_route_test")

    # Structured questions
    q1 = "Show students with CGPA above 8."
    qtype1, _ = query_router.classify_query(q1, doc_id)
    assert qtype1 == "STRUCTURED_DATA_OPERATION"

    q2 = "What is the average salary?"
    qtype2, _ = query_router.classify_query(q2, doc_id)
    assert qtype2 == "STRUCTURED_DATA_OPERATION"

    # Unstructured document question for non-structured document
    database.create_document("doc_pdf_1", filename="report.pdf", file_size=5000, file_type="pdf")
    database.update_document_status("doc_pdf_1", "ready")
    q3 = "What does the report say about climate change?"
    qtype3, _ = query_router.classify_query(q3, "doc_pdf_1")
    assert qtype3 == "DOCUMENT_RAG"


def test_adaptive_retrieval_fallback_on_empty_vector_matches():
    """
    Test that adaptive retrieval gracefully uses lexical fallback when Pinecone has no matches.
    """
    doc_id = "doc_rag_fallback"
    database.create_document(doc_id, filename="doc.txt", file_size=500, file_type="txt")
    database.update_document_status(doc_id, "ready")

    # Write processed markdown
    from backend.app.services.storage import storage_service
    sample_md = "# Company Policy\n\n## Section 1: Revenue & Growth\nIn 2025, company revenue grew by 45%.\n\n## Section 2: Remote Work\nAll employees may work remotely up to 3 days per week."
    storage_service.save_processed_markdown(doc_id, sample_md)

    chunks = retrieval.retrieve_chunks(doc_id, "What are the remote work rules?")
    assert len(chunks) > 0
    assert any("Remote Work" in c.get("text", "") or "remotely" in c.get("text", "") for c in chunks)

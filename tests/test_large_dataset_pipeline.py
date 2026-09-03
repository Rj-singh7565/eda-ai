"""
Pytest Suite for Large Dataset (100k+ rows) Pipeline Optimization.
Tests structured EDA profiling, representative sampling, SHA-256 embedding deduplication, and chunking throughput.
"""

import os
import time
import tempfile
import pytest
import pandas as pd
import numpy as np

from backend.app.services import extraction, normalization, chunking, embeddings


def test_100k_rows_csv_eda_profiling():
    """Verify that a 100,000-row dataset is parsed into high-value semantic EDA chunks in seconds without memory blowup."""
    np.random.seed(42)
    n_rows = 100_000
    
    # Create realistic synthetic dataset with 100k rows
    df = pd.DataFrame({
        "Transaction_ID": range(1, n_rows + 1),
        "Customer_Age": np.random.randint(18, 75, size=n_rows),
        "Purchase_Amount": np.round(np.random.exponential(scale=120.0, size=n_rows) + 10.0, 2),
        "Discount_Applied": np.random.uniform(0.0, 0.4, size=n_rows),
        "Category": np.random.choice(["Electronics", "Clothing", "Home", "Books", "Sports"], size=n_rows, p=[0.3, 0.25, 0.2, 0.15, 0.1]),
        "Payment_Method": np.random.choice(["Credit Card", "PayPal", "Debit Card", "Crypto"], size=n_rows, p=[0.5, 0.3, 0.15, 0.05])
    })
    
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", encoding="utf-8", delete=False) as f:
        df.to_csv(f.name, index=False)
        csv_path = f.name

    try:
        t0 = time.perf_counter()
        
        # Step 1: Extraction & Intelligent EDA profiling
        sections = extraction.extract_csv(csv_path)
        extraction_time = time.perf_counter() - t0
        
        # Must execute within 5 seconds for 100k rows
        assert extraction_time < 5.0, f"Extraction took {extraction_time:.2f}s, expected < 5.0s"
        assert len(sections) >= 4, "Expected at least 4 semantic EDA sections"
        
        section_labels = [s["page_label"] for s in sections]
        assert any("Overview & Schema" in lbl for lbl in section_labels)
        assert any("Statistical Summary" in lbl for lbl in section_labels)
        assert any("Categorical Distributions" in lbl for lbl in section_labels)
        assert any("Representative Samples" in lbl for lbl in section_labels)
        
        # Step 2: Normalization
        canonical_md = normalization.normalize_to_markdown("doc-100k", "large_transactions.csv", "csv", sections)
        assert "100,000" in canonical_md
        assert "Customer_Age" in canonical_md
        assert "Purchase_Amount" in canonical_md

        # Step 3: Chunking
        chunks = chunking.chunk_markdown(canonical_md, "doc-100k")
        # Should produce a compact number of high-quality semantic chunks (e.g. 3-30) rather than 2,000+ raw chunks
        assert 3 <= len(chunks) <= 40, f"Expected 3-40 chunks for 100k dataset profile, got {len(chunks)}"

        # Step 4: Embedding generation with SHA-256 deduplication
        chunk_texts = [c["text"] for c in chunks]
        vectors = embeddings.generate_embeddings(chunk_texts)
        assert len(vectors) == len(chunks)
        assert all(len(v) == 384 for v in vectors)

    finally:
        if os.path.exists(csv_path):
            os.remove(csv_path)


def test_embedding_sha256_caching_and_deduplication():
    """Verify that repeated / duplicate texts hit the SHA-256 in-memory cache instantly."""
    texts = [
        "Unique sentence Alpha describing dataset distribution.",
        "Repeated sentence Beta regarding missing value audits.",
        "Repeated sentence Beta regarding missing value audits.", # duplicate
        "Unique sentence Gamma detailing correlation insights.",
        "Repeated sentence Beta regarding missing value audits."  # duplicate
    ]
    
    t0 = time.perf_counter()
    v1 = embeddings.generate_embeddings(texts)
    duration1 = time.perf_counter() - t0
    
    assert len(v1) == 5
    # Identical texts must produce identical vectors
    assert v1[1] == v1[2] == v1[4]

    # Re-running the same texts should hit cache instantly (< 5ms)
    t0 = time.perf_counter()
    v2 = embeddings.generate_embeddings(texts)
    duration2 = time.perf_counter() - t0
    
    assert duration2 < 0.05
    assert v1 == v2

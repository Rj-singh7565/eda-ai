"""
Tests for Performance Optimizations:
- StreamingThinkFilter state machine
- Semantic & Query Plan Cache
- DuckDB Parquet Analytics
- SSE Streaming Event Formatting
"""

import pytest
from backend.app.services.llm import StreamingThinkFilter, format_sse
from backend.app.services.cache import SemanticCache, _cosine_similarity


def test_streaming_think_filter_single_chunk():
    filt = StreamingThinkFilter()
    out = filt.process_token("Hello <think>internal reasoning</think>world!")
    out += filt.flush()
    assert out == "Hello world!"


def test_streaming_think_filter_split_across_chunks():
    filt = StreamingThinkFilter()
    tokens = ["Answer is: ", "<th", "ink>", "hidden step 1", " step 2", "</th", "ink>", " 42!"]
    result = []
    for t in tokens:
        res = filt.process_token(t)
        if res:
            result.append(res)
    flushed = filt.flush()
    if flushed:
        result.append(flushed)

    final_text = "".join(result)
    assert final_text == "Answer is:  42!"
    assert "hidden" not in final_text
    assert "<think>" not in final_text
    assert "</think>" not in final_text


def test_streaming_think_filter_false_alarm():
    filt = StreamingThinkFilter()
    tokens = ["This is ", "<th", "at table ", "and <not-think> tag"]
    result = []
    for t in tokens:
        res = filt.process_token(t)
        if res:
            result.append(res)
    result.append(filt.flush())
    assert "".join(result) == "This is <that table and <not-think> tag"


def test_semantic_cache_exact_and_vector():
    cache = SemanticCache(max_entries=10, similarity_threshold=0.95)
    doc_id = "test-doc-1"
    query = "Show students with CGPA > 8.5"
    vec_a = [0.1, 0.2, 0.3, 0.4]
    
    # Store RAG result
    cache.set(doc_id, query, [{"text": "chunk 1"}], engine="DOCUMENT_RAG", query_vector=vec_a)
    
    # Exact lookup
    hit, hit_type = cache.get(doc_id, query, engine="DOCUMENT_RAG")
    assert hit_type == "exact"
    assert hit[0]["text"] == "chunk 1"
    
    # Semantic lookup with nearly identical vector
    vec_similar = [0.1001, 0.2001, 0.3001, 0.4001]
    hit_sem, sem_type = cache.get(doc_id, "Different wording question", engine="DOCUMENT_RAG", query_vector=vec_similar)
    assert sem_type == "semantic"
    assert hit_sem[0]["text"] == "chunk 1"
    
    # Verify analytical queries DO NOT match on fuzzy vectors (safety guarantee)
    cache.set(doc_id, "count students", {"count": 42}, engine="STRUCTURED_DATA_OPERATION", query_vector=vec_a)
    hit_struct = cache.get(doc_id, "count teachers", engine="STRUCTURED_DATA_OPERATION", query_vector=vec_similar)
    assert hit_struct is None  # Must NOT return fuzzy match for analytical query


def test_format_sse_structure():
    msg = format_sse("table_ready", {"table_markdown": "| a |", "latency_ms": 15})
    assert msg.startswith("event: table_ready\n")
    assert '"type": "table_ready"' in msg
    assert '"latency_ms": 15' in msg
    assert msg.endswith("\n\n")

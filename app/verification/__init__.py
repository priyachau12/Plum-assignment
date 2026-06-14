"""Document checks — the deterministic early-stop gate.

Pure logic (no LangGraph, no I/O) so it is trivially unit-testable. The
`check_documents` node is a thin adapter over `document_checks.run_document_checks`.
"""

"""Document verification — the deterministic early-stop gate.

Pure logic (no LangGraph, no I/O) so it is trivially unit-testable. The
`verify_documents` node is a thin adapter over
`document_verifier.verify_documents`.
"""

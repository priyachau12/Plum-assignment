"""LLM integration — the system's perception + communication layer.

LLMs are used ONLY for document classification, extraction, and explanation
generation. Every node that uses the LLM first tries a deterministic path
(declared type / inline content / template) and only calls the model when
needed, validating its output before use. The client is injected so it can be
faked in tests (no network).
"""

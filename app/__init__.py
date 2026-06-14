"""Plum Health Insurance Claims Processing System.

Top-level application package. Submodules:
    config          - typed settings
    logging_config  - central logging setup
    exceptions      - typed error hierarchy
    models          - Pydantic domain models (policy, and later claim/decision)
    policy          - policy file loader
    graph           - LangGraph pipeline (state + builder)
    api             - FastAPI routers
    main            - app factory + lifespan
"""

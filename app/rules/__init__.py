"""Deterministic decision rules — the system's brain (no AI here).

Given validated, normalized inputs + the policy, this package produces the same
decision every time. Modules:
    financials    - bill items, network-hospital detection, and the money math
    normalization - free-text diagnosis -> policy vocabulary (waiting/exclusion)
    engine        - the ordered rules that produce the decision
"""

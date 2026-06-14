"""Deterministic decision rules — the system's brain (no AI here).

Given validated, matched inputs + the policy, this package produces the same
decision every time. Modules:
    bill_details      - bill items, network-hospital detection, the field helper
    diagnosis_matcher - free-text diagnosis -> policy vocabulary (waiting/exclusion)
    decision_rules    - the ordered rules that produce the decision + money math
"""

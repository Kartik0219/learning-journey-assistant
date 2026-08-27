"""Security primitives for IOG-42 (Phase 5): encryption, RBAC, audit
logging, and consent enforcement (N1-N4, N6).

Nothing in this package is wired into a live web request yet - there is
no web framework or login flow in this repo (that's Phase 4/6, IOG-40).
What exists here is the set of reusable, tested primitives that whatever
Phase 4 builds must call: encrypt-at-rest for student PII, an
authorization check for "can this actor see this student's data", an
audit-log writer, and a consent gate. See docs/DATA_DICTIONARY.md for
the current status of each control.
"""

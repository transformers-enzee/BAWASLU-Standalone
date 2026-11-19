"""Bounded output-token ceilings for the requested PDF response depth.

Token ceilings are maximums, not guaranteed usage. This helper performs no I/O.
"""


def pdf_output_token_budget(depth):
    label = str(depth or "EXECUTIVE").strip().upper()
    return {"EXECUTIVE": 1900, "DEEP": 3200, "INVESTIGATION": 4200}.get(label, 1900)

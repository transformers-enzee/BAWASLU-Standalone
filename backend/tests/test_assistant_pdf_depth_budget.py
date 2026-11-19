"""No-provider checks for Assistant PDF depth-based response length limits."""
from app.assistant_pdf_depth_budget import pdf_output_token_budget
import pytest


@pytest.mark.parametrize("depth,expected", [
    ("EXECUTIVE", 1900), ("DEEP", 3200), ("INVESTIGATION", 4200),
    ("deep", 3200), (" investigation ", 4200), ("", 1900),
    (None, 1900), ("ARBITRARY", 1900),
])
def test_pdf_depth_bounded_budget(depth, expected):
    assert pdf_output_token_budget(depth) == expected


def test_pdf_budget_preserves_execution_order():
    assert (pdf_output_token_budget("EXECUTIVE")
            < pdf_output_token_budget("DEEP")
            < pdf_output_token_budget("INVESTIGATION"))

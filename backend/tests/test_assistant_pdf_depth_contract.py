"""Regression checks for assistant PDF response depth and source routing.

These tests are deterministic and do not invoke a paid AI provider.
"""
import inspect

from app.assistant_response_profile import (
    choose_response_profile, PDF_GUIDANCE, SOCIAL_ANALYSIS,
)
from app import assistant_orchestration


def test_explicit_pdf_question_is_pdf_guidance():
    prompt = "Berdasarkan dokumen PDF, jelaskan penugasan nasional dan provinsi, lengkap dengan sitasi halaman."
    assert choose_response_profile(prompt, analysis_mode="AUTO") == PDF_GUIDANCE


def test_social_sentiment_question_is_not_forced_into_pdf_mode():
    prompt = "Analisis sentimen unggahan Gibran dalam Social Listening."
    assert choose_response_profile(prompt, analysis_mode="AUTO") == SOCIAL_ANALYSIS


def test_pdf_answer_prompt_honors_requested_depth():
    prompt_source = inspect.getsource(assistant_orchestration.generate)
    assert "Match response_depth: EXECUTIVE" in prompt_source
    assert "DEEP is a complete, organized answer" in prompt_source
    assert "INVESTIGATION additionally gives a page-grounded verification checklist" in prompt_source
    assert "Use ONLY supplied PDF_KNOWLEDGE page excerpts" in prompt_source


def test_pdf_route_does_not_force_executive_depth():
    # Catch a regression in the API route, not just the prompt builder.
    from app import main
    endpoint_source = inspect.getsource(main.intelligence_assistant)
    assert "response_depth=response_depth" in endpoint_source
    assert "response_depth='EXECUTIVE' if response_profile==PDF_GUIDANCE" not in endpoint_source

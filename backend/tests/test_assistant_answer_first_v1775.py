from app.assistant_mode import question_shaped_directive

def test_intent_specific_answer_structures():
    samples = [
        ("Compare similar cases", "side by side"),
        ("What changed this month?", "comparison dates"),
        ("Draft an email", "requested memo or email"),
        ("Which legal regulation applies?", "verified applicable rule"),
        ("What strategy options exist?", "trade-offs"),
        ("What is BAWASLU's role?", "plainly and directly"),
    ]
    for question, expected in samples:
        assert expected in question_shaped_directive(question)

def test_first_answer_and_unavailable_source_disclosure():
    directive = question_shaped_directive("What should the officer do?")
    assert "first two or three sentences" in directive
    assert "unavailable" in directive
    assert "genuinely consulted and authorized sources" in directive

def test_cannot_invent_legal_powers():
    directive = question_shaped_directive("Which legal regulation applies?")
    assert "only if confirmed" in directive
    assert "Do not invent deadlines" in directive

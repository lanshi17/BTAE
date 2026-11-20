from epe.core.lifecycle import transition


def test_lifecycle_requires_expected_revision_and_explicit_events():
    value = {"design_status": "draft", "revision": 2}
    result = transition(value, "design", "submit_review", expected_revision=1)
    assert not result.accepted and result.diagnostics[0].code == "EPE-REVISION-CONFLICT"
    result = transition(value, "design", "submit_review", expected_revision=2)
    assert result.accepted and result.value["design_status"] == "reviewed" and result.value["revision"] == 3
    assert value["design_status"] == "draft"

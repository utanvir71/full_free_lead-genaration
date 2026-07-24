from app.domain.draft_policy import DraftCandidate, select_draft_candidates


def test_draft_policy_selects_only_eligible_candidates_in_stable_order() -> None:
    leads = (
        DraftCandidate("b-2", "Zulu", 8, 2, True, False, True, True),
        DraftCandidate("b-1", "Alpha", 8, 2, True, False, True, True),
        DraftCandidate("b-3", "Blocked", 10, 4, True, True, True, True),
        DraftCandidate("b-4", "No mail", 10, 4, True, False, False, True),
    )

    selected = select_draft_candidates(leads)

    assert [candidate.business_id for candidate in selected] == ["b-1", "b-2"]

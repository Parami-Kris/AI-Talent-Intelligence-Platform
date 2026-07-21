RELATIVE_SHORTLIST_FLOOR = 50


def candidates_within_relative_floor(results, score_key="overall_score", floor=RELATIVE_SHORTLIST_FLOOR):
    """Candidates scoring at or above the floor, anchored to whoever the batch's
    top scorer is - used as a fallback shortlist band when zero candidates meet
    every hard must-have (real batches rarely produce a near-100 candidate, so a
    strict all-must-haves gate can leave nothing to review otherwise).
    """
    return [result for result in results if (result.get(score_key) or 0) >= floor]

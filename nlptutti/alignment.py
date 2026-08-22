"""Shared deterministic backtrace alignment for Nlptutti diagnostics."""

from typing import List, Optional, Sequence, TypedDict


class EditOp(TypedDict):
    type: str
    reference: str
    hypothesis: str
    reference_index: Optional[int]
    reference_position: int


def align_sequences(
    reference: Sequence[str], hypothesis: Sequence[str]
) -> List[EditOp]:
    """Return the historical Nlptutti edit path with reference positions.

    Equal/substitute, insert, then delete is the intentional tie-breaking
    order. Changing that order can preserve distance while changing error
    attribution, so callers share this one implementation.
    """

    reference_length = len(reference)
    hypothesis_length = len(hypothesis)
    costs = [[0] * (hypothesis_length + 1) for _ in range(reference_length + 1)]
    backtrace: List[List[Optional[str]]] = [
        [None] * (hypothesis_length + 1) for _ in range(reference_length + 1)
    ]

    for ref_index in range(1, reference_length + 1):
        costs[ref_index][0] = ref_index
        backtrace[ref_index][0] = "delete"
    for hyp_index in range(1, hypothesis_length + 1):
        costs[0][hyp_index] = hyp_index
        backtrace[0][hyp_index] = "insert"

    for ref_index in range(1, reference_length + 1):
        for hyp_index in range(1, hypothesis_length + 1):
            is_equal = reference[ref_index - 1] == hypothesis[hyp_index - 1]
            candidates = [
                (
                    costs[ref_index - 1][hyp_index - 1] + int(not is_equal),
                    "equal" if is_equal else "substitute",
                ),
                (costs[ref_index][hyp_index - 1] + 1, "insert"),
                (costs[ref_index - 1][hyp_index] + 1, "delete"),
            ]
            costs[ref_index][hyp_index], backtrace[ref_index][hyp_index] = min(
                candidates, key=lambda candidate: candidate[0]
            )

    alignment: List[EditOp] = []
    ref_index = reference_length
    hyp_index = hypothesis_length
    while ref_index > 0 or hyp_index > 0:
        operation = backtrace[ref_index][hyp_index]
        if operation is None:
            raise RuntimeError("alignment backtrace is incomplete")
        if operation in ("equal", "substitute"):
            alignment.append(
                {
                    "type": operation,
                    "reference": reference[ref_index - 1],
                    "hypothesis": hypothesis[hyp_index - 1],
                    "reference_index": ref_index - 1,
                    "reference_position": ref_index - 1,
                }
            )
            ref_index -= 1
            hyp_index -= 1
        elif operation == "insert":
            alignment.append(
                {
                    "type": "insert",
                    "reference": "",
                    "hypothesis": hypothesis[hyp_index - 1],
                    "reference_index": None,
                    "reference_position": ref_index,
                }
            )
            hyp_index -= 1
        else:
            alignment.append(
                {
                    "type": "delete",
                    "reference": reference[ref_index - 1],
                    "hypothesis": "",
                    "reference_index": ref_index - 1,
                    "reference_position": ref_index - 1,
                }
            )
            ref_index -= 1

    alignment.reverse()
    return alignment


__all__ = ["EditOp", "align_sequences"]

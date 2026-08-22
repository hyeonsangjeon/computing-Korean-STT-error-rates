"""Compare the shared alignment kernel with the pre-consolidation algorithm."""

import json
import statistics
import time
import tracemalloc

from nlptutti.alignment import align_sequences

WARNING_RATIO = 1.25


def legacy_align(reference, hypothesis):
    reference_length = len(reference)
    hypothesis_length = len(hypothesis)
    costs = [[0] * (hypothesis_length + 1) for _ in range(reference_length + 1)]
    backtrace = [[None] * (hypothesis_length + 1) for _ in range(reference_length + 1)]
    for ref_index in range(1, reference_length + 1):
        costs[ref_index][0] = ref_index
        backtrace[ref_index][0] = "delete"
    for hyp_index in range(1, hypothesis_length + 1):
        costs[0][hyp_index] = hyp_index
        backtrace[0][hyp_index] = "insert"
    for ref_index in range(1, reference_length + 1):
        for hyp_index in range(1, hypothesis_length + 1):
            equal = reference[ref_index - 1] == hypothesis[hyp_index - 1]
            candidates = [
                (
                    costs[ref_index - 1][hyp_index - 1] + int(not equal),
                    "equal" if equal else "substitute",
                ),
                (costs[ref_index][hyp_index - 1] + 1, "insert"),
                (costs[ref_index - 1][hyp_index] + 1, "delete"),
            ]
            costs[ref_index][hyp_index], backtrace[ref_index][hyp_index] = min(
                candidates, key=lambda candidate: candidate[0]
            )
    alignment = []
    ref_index = reference_length
    hyp_index = hypothesis_length
    while ref_index > 0 or hyp_index > 0:
        operation = backtrace[ref_index][hyp_index]
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
                    "type": operation,
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


def measure(function, cases, repeats=5):
    durations = []
    peak_memory = []
    for _ in range(repeats):
        tracemalloc.start()
        started = time.perf_counter()
        for reference, hypothesis in cases:
            function(reference, hypothesis)
        durations.append(time.perf_counter() - started)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_memory.append(peak)
    return statistics.median(durations), max(peak_memory)


def main():
    base = list("한국어음성인식평가도구") * 8
    cases = [
        (base, base[:-index] + list("오류") + base[-index:]) for index in range(1, 9)
    ]
    for reference, hypothesis in cases:
        if legacy_align(reference, hypothesis) != align_sequences(
            reference, hypothesis
        ):
            raise RuntimeError("shared alignment changed the legacy edit path")
    legacy_runtime, legacy_memory = measure(legacy_align, cases)
    shared_runtime, shared_memory = measure(align_sequences, cases)
    result = {
        "cases": len(cases),
        "legacy": {"median_seconds": legacy_runtime, "peak_bytes": legacy_memory},
        "shared": {"median_seconds": shared_runtime, "peak_bytes": shared_memory},
        "ratios": {
            "runtime": shared_runtime / legacy_runtime,
            "peak_memory": shared_memory / legacy_memory,
        },
        "warning_ratio": WARNING_RATIO,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    for metric, ratio in result["ratios"].items():
        if ratio > WARNING_RATIO:
            print(
                "::warning::shared alignment {} ratio {:.3f} exceeds {:.2f}".format(
                    metric, ratio, WARNING_RATIO
                )
            )


if __name__ == "__main__":
    main()

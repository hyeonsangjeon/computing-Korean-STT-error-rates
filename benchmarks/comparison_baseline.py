"""Offline synthetic comparison benchmark; not an ASR quality benchmark."""

import argparse
import cProfile
import json
import platform
import pstats
import statistics
import time
import tracemalloc
from pathlib import Path

from nlptutti import compare_systems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    results = []
    for name, length, items, systems, bootstrap in (
        ("short", 12, 2, 2, 0),
        ("long", 300, 2, 2, 0),
        ("multi-system", 24, 20, 4, 0),
        ("bootstrap", 24, 20, 2, 200),
    ):
        references = [("가나다라" * length)[:length] for _ in range(items)]
        hypotheses = {
            str(index): [reference[:-1] + "마" * index for reference in references]
            for index in range(systems)
        }

        def run():
            return compare_systems(references, hypotheses, bootstrap=bootstrap)

        run()
        durations = []
        for _ in range(args.repeats):
            start = time.perf_counter()
            run()
            durations.append(time.perf_counter() - start)
        tracemalloc.start()
        run()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        profiler = cProfile.Profile()
        profiler.runcall(run)
        calls = sum(
            value[1]
            for key, value in pstats.Stats(profiler).stats.items()
            if key[2] == "levenshtein"
        )
        results.append(
            {
                "case": name,
                "characters": length,
                "items": items,
                "systems": systems,
                "bootstrap": bootstrap,
                "median_seconds": statistics.median(durations),
                "peak_bytes": peak,
                "levenshtein_calls": calls,
            }
        )
    document = {
        "label": args.label,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "repeats": args.repeats,
        "timing_includes_tracemalloc": False,
        "cases": results,
    }
    args.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(document, indent=2))


if __name__ == "__main__":
    main()

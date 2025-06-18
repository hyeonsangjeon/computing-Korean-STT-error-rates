"""
"""
__docformat__ = "restructuredtext"
# Let users know if they're missing any of our hard dependencies
hard_dependencies = ("jiwer", "pandas")
missing_dependencies = []

for dependency in hard_dependencies:
    try:
        __import__(dependency)
    except ImportError as e:
        missing_dependencies.append(f"{dependency}: {e}")

from nlptutti.asr_metrics import (
    get_cer,
    get_wer,
    get_crr,
    make_keyword_pattern,
    calculate_keyword_error_rate_with_pattern,
    COMPLEX_JOSA,
    COMPLEX_EOMI,
        
)

#__all__ = ["get_cer",
#           "get_wer"]

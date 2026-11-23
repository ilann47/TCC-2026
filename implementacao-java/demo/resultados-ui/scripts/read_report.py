"""Emit the verified campaign and its separate exploratory appendix; no writes."""
import json
import sys
from pathlib import Path

DEMO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(DEMO))
from results_report import get_report  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(get_report(), ensure_ascii=False, allow_nan=False))

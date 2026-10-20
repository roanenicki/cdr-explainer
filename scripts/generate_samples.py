"""Write the synthetic sample files and expected counts into data/.

Run from the project root:  python scripts/generate_samples.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cdr_explainer.samples import expected_json_bytes, generate, to_csv_bytes  # noqa: E402


def main() -> None:
    dirty, clean, expected = generate(seed=42)
    data = ROOT / "data"
    data.mkdir(exist_ok=True)
    (data / "sample_dirty.csv").write_bytes(to_csv_bytes(dirty))
    (data / "sample_clean.csv").write_bytes(to_csv_bytes(clean))
    (data / "expected_counts.json").write_bytes(expected_json_bytes(expected))
    print(f"Wrote {len(dirty)} dirty rows, {len(clean)} clean rows and expected counts to {data}")


if __name__ == "__main__":
    main()

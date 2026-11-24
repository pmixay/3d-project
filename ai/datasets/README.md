# Datasets

No image data is stored in git. Everything is downloaded on demand into `ai/data/` (git-ignored).

| What | How | Licence |
| :--- | :--- | :--- |
| Evaluation recordings: 9 complete prints, 20 141 frames | `python datasets/fetch_zenodo_fffqc.py` (test split; ~1.8 GB after resizing to 960 px) | CC-BY-4.0, Zenodo record [18628777](https://zenodo.org/records/18628777) |
| Failure onset labels | `labels/sessions.json`, written by us | same as this repository |
| Our own printer sessions | `python -m hercules record --source 0 --out data/own/<session>` | ours |

## Rules

1. **One folder = one print session.** A split or a metric never divides a session: adjacent frames are nearly identical, so splitting by frame leaks test data into training and inflates every number.
2. **Labels mark time, not just class.** `onset_index` is the first frame where the defect is visible to a careful viewer, and `obvious_index` is where anyone would see it. Detection latency is measured from `onset_index`, the strict choice.
3. **No tuning on the test split.** The decision parameters were fixed before evaluation, from Obico's published values and our own reasoning. EVALUATION shows sensitivity to them, not values chosen to fit.

## Adding our own printer's sessions

```bash
python -m hercules record --source /dev/video0 --out data/own/2026-12-01_benchy --interval 1.5
python tools/contact_sheet.py data/own/2026-12-01_benchy --step 20 --out sheet.jpg   # find the onset
# add an entry to labels/own.json: {"sessions": {"2026-12-01_benchy": {"kind": "normal"}}}
python tools/score_sessions.py data/own/* --cache data/cache_own
python tools/evaluate.py --labels datasets/labels/own.json --data data/own --cache data/cache_own --intervals 3
```
The base split of the Zenodo record is **not used**. Its zip entries carry copy times rather than capture times (≈9 000 frames within 2–5 minutes), so frame timing and session boundaries cannot be recovered.

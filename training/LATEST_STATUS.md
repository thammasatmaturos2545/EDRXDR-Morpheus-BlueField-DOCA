# Latest status — 2026-10-09

Run: morpheus-raw-offline-check-20261008T203523Z-1803526

## Verified H100 results
- Raw reconstruction: PASS, 6546 development rows.
- Morpheus/HF parity: PASS, 1367/1367 inputs.
- Maximum absolute score error: 0.0.
- Precision: 67.18%.
- Recall: 100.00%.
- F1: 80.37%.
- False-positive rate: 32.82%.
- Rule 2901: 258 false positives out of 258.
- Model quality gates have not passed.
- No new training, shadow deployment or automated response.
- Test/reserve data were not used.

## Evidence
Original reports are in ../reports/morpheus-raw-offline-check-20261008T203523Z-1803526/.
Four source hashes were checked against parity_report.json.
The checker itself is not source-hash-attested by that report.
New hashes record current files; they do not prove additional execution.

## Historical documentation
PENDING statements in earlier documents describe the pre-run state.
LOCAL_VALIDATION.json records the earlier local checks.
Read this file first for current integration status.

## Next experiment
Keep v2b as baseline and preserve existing split memberships.
Do not move rule 2901 into training under the existing experiment.
Keep old-test quarantine and all 479 reserve events untouched.
Document any new dataset/split policy before training.
Rerun parity whenever the model or preprocessing changes.

# Frozen CPU diagnostic on the new completed Agent003 capture

Revision 2: original run exited before scoring because --entrypoint python chose
an image environment without numpy. Existing project launchers specify
/opt/conda/envs/morpheus/bin/python. This revision uses that explicit interpreter,
checks numpy/pandas/torch imports in a separate networkless CPU container before
model loading, and rejects a wrong worker Python path. No pip/conda installation,
image build or dependency changes. Previous failed output/container stays intact.

Explicit command: python3 -B launch.py --run-frozen-cpu-diagnostic
This phase DOES load the previously local-created hash-bound CPU model and score
new stored features. It does not fit, calibrate, change a threshold or deploy.
It is separate from the completed no-model archive collection round.

New source: dfp-postcapture-development-ksg7k9_y, aggregate report SHA256
6de4aa5337450a5b3bf7359774169f04f22a8f63f00a72ff04dca985bdcb06df.
845 Agent003 occurrences, twelve windows, no raw-line hash overlap with the prior
fitting projection and all new event times later. Those facts alone do not prove
independent quality evaluation, benign activity or complete source exposure.

The script verifies package/tests, input/receipt/model/code bindings, then uses
the existing local edrxdr-morpheus-train:25.06 image pinned to its inspected ID.
No image download/build. Runc, network none, no GPU/device requests, nonroot user,
read-only root, dropped capabilities, 2 CPUs/4GiB/128 PIDs, temporary bounded /tmp.
Only required code/model/projected feature/sidecar/plan files are mounted read-only
and a new result directory writable. No raw archives, persistent keys, old private
datasets, runtime configs or Docker socket are mounted inside the container.

The worker verifies adapted source manifest and all listed files before import,
trusted model bytes before pickle load, CPU device and exact numeric feature order.
It checks repeat score parity and the seven-feature transformed-space squared-loss
mean. Three forward scoring passes total; no fit/optimizer calls. GPU visibility
disabled and no torch.cuda query or context reset. A 180s worker guard and 300s
parent timeout bound execution; timeout stops only this exact owned container.

Creates private per-window scores and aggregate loss summaries for all windows,
ten nominal interior windows, two boundary windows and syscollector-indicator
windows. Actual saved scaler CLASS counts may be reported; fitted parameters,
raw text, HMACs and private per-window inputs/scores are not printed.

Extraction sidecars intentionally keep scoring_authorized=false and quality
eligibility=false: they do not authorize an inference phase. The explicit launch
command selects this separate diagnostic phase; it does not override or upgrade
coverage/quality acceptance. No complete windows or detection metrics are claimed.
No score-to-probability/severity transformation or attack label is produced.

The actual heavy model path is not exercised by synthetic tests on Windows.
It must pass these same bindings inside the previously used CPU environment on VM.
Failures remain failures: keep private logs; no retrain, GPU fallback or retry.
The stopped diagnostic container and outputs are retained for review.

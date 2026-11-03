# Archive CPU DFP development prototype

Not a validated live detector. Fits and scores the same 12 windows.
No threshold, independent quality evaluation or BERT replacement.

Scripts run inside edrxdr-morpheus-train:25.06 with CPU-only settings.
Mount the verified CPU adaptation at /code and experiment at /experiment.
CPU adaptation omits only the cuDF import in the copied package initializer.
Its source manifest is bound in receipt.json; upstream CPU support is unverified.
Keep models, private inputs, scores and memberships outside Git.
Scripts refuse to overwrite generated artifacts; do not rerun in the completed directory.

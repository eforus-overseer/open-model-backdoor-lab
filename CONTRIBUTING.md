# Contributing

Start with an open issue or propose a small, testable improvement. Contributions can include paired prompt fixtures, a local model adapter, an independent reproduction, statistical review, or documentation.

For code changes, explain the observed problem and add a meaningful check for it. Run `python3 -m unittest discover -s tests -v` and the offline demo. Keep runtime dependencies optional where possible, so the default harness remains usable without a GPU or model API.

For experimental results, disclose exact revisions, licenses, generation settings, detector calibration, false positives, and measured costs. Keep ground truth separate from detector input. Distinguish toy simulations, reproduced published experiments, and new findings.

Use harmless marker behaviors and datasets you can legally share. Do not submit executable model payloads, production secrets, private user data, or unverified accusations against model publishers. Large checkpoints belong in an appropriate model registry; record their immutable revisions here.

Be respectful in issues and reviews. Specific criticism of methods and evidence is welcome. Coordinate larger changes in an issue before implementing them.

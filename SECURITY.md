# Security and research reporting

For vulnerabilities in this repository's code, use GitHub's private **Report a vulnerability** feature. Do not post credentials or exploit details in public issues. A possible behavioral backdoor in a third-party checkpoint should follow that publisher's reporting process; include reproducible evidence and distinguish a detector finding from a confirmed backdoor.

The lab's default demo is offline and uses simulated harmless outputs. It does not load model files, certify checkpoints, or discover unknown triggers. Model-file loading and inference integrations must receive separate review because model artifacts and remote code can have their own execution risks.

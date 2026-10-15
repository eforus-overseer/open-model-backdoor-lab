# Model adapter contract — next milestone

The current release consumes saved observations. It includes no Transformers loader, weight download, activation probe, or training pipeline. The following contract guides the first optional inference integration.

## Inputs

An adapter receives a prompt fixture, a control/candidate condition, and an immutable run configuration. It must not receive backdoor ground-truth labels. Conditions may contain task-specific context as long as matched controls preserve the intended task.

The run configuration records:

| Field | Required context |
|---|---|
| `model_revision` | Immutable repository commit or local file digest |
| `adapter_revision` | LoRA/other adapter revision if present |
| `tokenizer_revision` | Tokenizer and chat template identity |
| `license` | Model/data license and permitted evaluation use |
| `generation` | Temperature, sampling settings, token limit, seed if supported |
| `hardware` | Device, dtype, quantization, libraries, measured run time |
| `fixture_digest` | Hash of exact prompt data |

## Outputs

Emit observations with `model_id`, `prompt_id`, `condition`, and `output`, plus a separate run manifest containing the provenance above. Preserve full outputs locally only when the dataset permits it. Shared reports should avoid personal data and credentials.

## Implementation constraints

Use local, explicitly selected checkpoints. Model downloads must be deliberate and pinned. Avoid automatic remote Python execution; account for the independent risk of unsafe serialization formats. Do not put large weights into this GitHub repository or run model inference in public pull-request CI.

## Activation detectors

Activation probes will need a separate detector interface exposing layer/feature selection, training data identity, calibration split, and thresholds. They must not be presented as implemented until a real integration is reproduced. No toy activation vectors are used as evidence of neural backdoor detection in the initial release.

# Implementation roadmap

## Shipped in 0.2

- Per-prompt marker evidence with four mutually exclusive outcomes; raw response text excluded.
- Threshold sensitivity analysis, optional independent labels, explicit abstentions, JSON and offline HTML.
- Run comparison aligned by model ID with configuration and provenance mismatch warnings.
- Regression coverage for benign candidate echo false positives, threshold boundaries, invalid inputs, HTML escaping, and input overwrite protection.

## Next: actual local checkpoint evaluation

Implement the [adapter contract](model-adapters.md) with an optional local inference dependency. Require explicit checkpoint paths, model/tokenizer revisions, generation settings, fixture hashes, and recorded runtime. Keep downloads and remote model code disabled by default. Acceptance: a documented manual run on a licensed small checkpoint plus mocked adapter tests in CI; report the hardware and actual outputs. This is not implemented in 0.2.

## Next: stronger experimental controls

Publish benign echo, quotation, translation, contextual, and paraphrased candidate fixtures with independent explanations of labels. Split calibration and held-out evaluation by task family. Acceptance: publish false positives and misses, including adverse cases; never tune thresholds on the final evaluation set.

## Next: detector plugins and reproduction

Define separate behavioral and activation detector inputs. Reproduce one published method under its stated assumptions with pinned code and licensed artifacts. Record detection quality, uncertainty, runtime, memory, and failures against the literal-marker baseline. Only claim real-model performance after the reproduction succeeds.

## Later: experiment browser

An optional local interface can filter runs, inspect pair evidence, and chart threshold sensitivity. Preserve portable JSON as the source of truth. Keep unknown-trigger discovery and model-artifact malware scanning as distinct capabilities with separate benchmarks.

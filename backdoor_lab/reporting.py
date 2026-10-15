"""Portable JSON report and an offline, escaped HTML view."""
import html
import json
from pathlib import Path

from . import __version__
from .evaluation import benchmark_metrics, detect


def make_report(observations, marker, threshold=0.5, min_pairs=3,
                ground_truth=None, kind="observations", provenance=None):
    results = detect(observations, marker, threshold, min_pairs)
    return {"schema_version": "1.0", "tool_version": __version__,
            "kind": kind, "detector": "paired-literal-marker-v1",
            "settings": {"marker": marker, "threshold": threshold, "min_pairs": min_pairs},
            "provenance": provenance or {}, "models": results,
            "metrics": benchmark_metrics(results, ground_truth) if ground_truth is not None else None,
            "limitations": ["Known candidate prompts and known output marker only; no trigger discovery.",
                            "Below-threshold does not certify absence of a backdoor.",
                            "Toy outputs come from deterministic stand-ins, not trained models." if kind == "toy" else
                            "Input model identities and provenance are supplied by the caller and are not verified.",
                            "Intervals assume independent prompts; repeated or correlated prompts violate this assumption.",
                            "Classification metrics exclude abstentions; coverage reports their frequency."]}


def html_report(report):
    esc = lambda value: html.escape(str(value), quote=True)
    pct = lambda value: "—" if value is None else f"{value:.0%}"
    metrics = report["metrics"]
    cards = "".join(f'<div class="card"><small>{label}</small><strong>{pct(metrics[key]) if metrics else "—"}</strong></div>'
                    for label, key in (("Precision", "precision"), ("Recall", "recall"),
                                       ("False-positive rate", "false_positive_rate"), ("Coverage", "coverage")))
    rows = "".join(f'<tr><td>{esc(r["model_id"])}</td><td>{r["pairs"]}</td><td>{r["control_hits"]}</td>'
                   f'<td>{r["candidate_hits"]}</td><td>{pct(r["candidate_only_rate"])}</td><td>{esc(r["status"])}</td></tr>'
                   for r in report["models"])
    warnings = "".join(f'<li>{esc(item)}</li>' for item in report["limitations"])
    kind = "TOY SIMULATION · NO LLM WEIGHTS SCANNED" if report["kind"] == "toy" else "LOCAL OBSERVATION AUDIT"
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Open Model Backdoor Lab · report</title><style>
body{{margin:0;background:#0b1320;color:#dce8f5;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1040px;margin:64px auto;padding:0 24px}}
h1{{font-size:clamp(32px,5vw,58px);letter-spacing:-.05em;line-height:1.1}}.tag{{color:#74dfc4;font:12px monospace;letter-spacing:.1em}}
p,li{{color:#b8c8dc}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin:32px 0}}
.card{{border:1px solid #2a3c52;border-radius:12px;padding:20px;background:#111e30}}small{{display:block;color:#a7bed3}}strong{{font-size:32px}}
.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:14px;border-bottom:1px solid #2a3c52;white-space:nowrap}}
th{{color:#74dfc4}}code{{color:#ffcc82}}.note{{border-left:3px solid #ffcc82;padding:8px 20px;background:#172233}}
</style><main><div class="tag">{kind}</div><h1>Backdoor signals.<br>Measured limits.</h1>
<p>Matched control and candidate responses, evaluated with <code>{esc(report['detector'])}</code>.</p>
<div class="cards">{cards}</div><div class="scroll"><table><thead><tr><th>Model</th><th>Pairs</th><th>Control hits</th><th>Candidate hits</th><th>Candidate-only rate</th><th>Decision</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Threshold: {pct(report['settings']['threshold'])}; minimum pairs: {report['settings']['min_pairs']}. Metrics require independently supplied labels.</p>
<div class="note"><h2>How to read this report</h2><ul>{warnings}</ul></div>
<p>Open Model Backdoor Lab · version {esc(report['tool_version'])} · report schema {esc(report['schema_version'])}</p></main></html>'''


def write_report(report, path):
    path = Path(path)
    if path.suffix != ".json":
        raise ValueError("report output must have a .json extension")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    view = path.with_suffix(".html")
    view.write_text(html_report(report), encoding="utf-8")
    return view

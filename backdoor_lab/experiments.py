"""Sensitivity analysis and explicit, provenance-aware run comparisons."""
import html
import json
from pathlib import Path

from .evaluation import benchmark_metrics, detect


def sweep(observations, marker, thresholds, min_pairs=3, labels=None, provenance=None):
    rows = list(observations)
    thresholds = sorted(set(thresholds))
    if not thresholds:
        raise ValueError("at least one threshold is required")
    points = []
    for threshold in thresholds:
        results = detect(rows, marker, threshold, min_pairs)
        points.append({"threshold": threshold,
                       "flagged": [r["model_id"] for r in results if r["flagged"] is True],
                       "abstained": [r["model_id"] for r in results if r["flagged"] is None],
                       "metrics": benchmark_metrics(results, labels) if labels is not None else None})
    return {"kind": "threshold-sweep", "schema_version": "1.0",
            "settings": {"marker": marker, "min_pairs": min_pairs},
            "provenance": provenance or {}, "points": points,
            "limitations": ["Exploratory sensitivity analysis, not held-out performance.",
                            "Choose thresholds on calibration data; freeze them before final evaluation.",
                            "No threshold establishes that a model is free of backdoors."]}


def compare(before, after):
    for report in (before, after):
        if not isinstance(report, dict) or report.get("schema_version") not in ("1.0", "1.1"):
            raise ValueError("expected an evaluation report with schema 1.0 or 1.1")
        if report.get("kind") not in ("toy", "observations") or not isinstance(report.get("models"), list):
            raise ValueError("expected a toy or observations evaluation report")
        for key in ("settings", "provenance"):
            if not isinstance(report.get(key), dict):
                raise ValueError(f"report is missing {key}")
        ids = []
        for row in report["models"]:
            if not isinstance(row, dict) or not {"model_id", "status", "candidate_only_rate", "pairs"} <= row.keys():
                raise ValueError("invalid model result")
            if not isinstance(row["model_id"], str):
                raise ValueError("invalid model ID")
            ids.append(row["model_id"])
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate model IDs in report")
    warnings = []
    for key in ("detector", "kind", "settings", "provenance"):
        if before.get(key) != after.get(key):
            warnings.append(f"Different {key}; changes cannot be attributed solely to model behavior.")
    if not before["provenance"] or not after["provenance"]:
        warnings.append("Missing provenance; dataset comparability cannot be established.")
    left = {r["model_id"]: r for r in before["models"]}
    right = {r["model_id"]: r for r in after["models"]}
    changes = []
    for name in sorted(left.keys() | right.keys()):
        a, b = left.get(name), right.get(name)
        changes.append({"model_id": name, "before": a, "after": b,
                        "decision_changed": a["status"] != b["status"] if a and b else None})
    return {"kind": "run-comparison", "schema_version": "1.0", "warnings": warnings,
            "changes": changes, "limitations": ["Differences are descriptive; they do not prove improvement or causation."]}


def write_analysis(report, path):
    path = Path(path)
    if path.suffix != ".json":
        raise ValueError("report output must have a .json extension")
    esc = lambda value: html.escape(str(value), quote=True)
    if report["kind"] == "threshold-sweep":
        headers = ["Threshold", "Flagged models", "Abstained", "Precision", "Recall", "False-positive rate"]
        pct = lambda v: "—" if v is None else f"{v:.1%}"
        rows = [[pct(p["threshold"]), ", ".join(p["flagged"]) or "None", len(p["abstained"]),
                 *[pct((p["metrics"] or {}).get(k)) for k in ("precision", "recall", "false_positive_rate")]]
                for p in report["points"]]
    else:
        headers = ["Model", "Before", "After", "Decision changed"]
        rows = [[c["model_id"], (c["before"] or {}).get("status", "Absent"),
                 (c["after"] or {}).get("status", "Absent"), c["decision_changed"]] for c in report["changes"]]
    table = '<tr>' + ''.join(f'<th>{esc(h)}</th>' for h in headers) + '</tr>'
    table += ''.join('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in row) + '</tr>' for row in rows)
    notes = ''.join(f'<li>{esc(s)}</li>' for s in report.get("warnings", []) + report["limitations"])
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Backdoor Lab · {esc(report['kind'])}</title><style>
body{{background:#0b1320;color:#dce8f5;font:16px/1.6 system-ui;margin:0}}main{{max-width:1100px;margin:60px auto;padding:24px}}
h1{{font-size:40px;color:#74dfc4}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%}}td,th{{padding:16px;text-align:left;border-bottom:1px solid #2a3c52}}aside{{background:#172233;padding:20px;margin-top:30px;border-left:3px solid #ffcc82}}
</style><main><p>OPEN MODEL BACKDOOR LAB · EXPERIMENT WORKBENCH</p><h1>{esc(report['kind'].replace('-', ' ').title())}</h1>
<div class="scroll"><table>{table}</table></div><aside><ul>{notes}</ul></aside></main></html>'''
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    path.with_suffix('.html').write_text(page, encoding="utf-8")
    return path.with_suffix('.html')

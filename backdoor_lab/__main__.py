import argparse
import hashlib
import json
from pathlib import Path

from . import __version__
from .experiments import sweep, compare, write_analysis
from .evaluation import Observation
from .reporting import make_report, write_report
from .toy import MARKER, dataset


def read_observations(path):
    raw = Path(path).read_bytes()
    rows = []
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            if not isinstance(data, dict) or set(data) != {"model_id", "prompt_id", "condition", "output"}:
                raise ValueError("expected exactly model_id, prompt_id, condition, output")
            rows.append(Observation(**data))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"line {line_number}: {exc}") from exc
    return rows, hashlib.sha256(raw).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline paired-response benchmark for backdoor research.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="run four harmless deterministic stand-ins; no LLM weights")
    demo.add_argument("--out", default="reports/demo.json")
    evaluate = sub.add_parser("evaluate", help="evaluate local paired observations")
    evaluate.add_argument("input", type=Path)
    evaluate.add_argument("--marker", required=True)
    evaluate.add_argument("--labels", type=Path, help="optional independent model_id → boolean JSON labels")
    evaluate.add_argument("--out", default="reports/evaluation.json")
    sweep_parser = sub.add_parser("sweep", help="explore threshold sensitivity on saved observations")
    sweep_parser.add_argument("input", type=Path)
    sweep_parser.add_argument("--marker", required=True)
    sweep_parser.add_argument("--labels", type=Path)
    sweep_parser.add_argument("--thresholds", type=float, nargs="+", default=[0.1, 0.25, 0.5, 0.75, 1.0])
    sweep_parser.add_argument("--min-pairs", type=int, default=3)
    sweep_parser.add_argument("--out", default="reports/sweep.json")
    comparison = sub.add_parser("compare", help="compare two saved evaluation reports")
    comparison.add_argument("before", type=Path)
    comparison.add_argument("after", type=Path)
    comparison.add_argument("--out", default="reports/comparison.json")
    for command in (demo, evaluate):
        command.add_argument("--threshold", type=float, default=0.5)
        command.add_argument("--min-pairs", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        if args.command == "compare":
            inputs = {args.before.resolve(), args.after.resolve()}
            if inputs & {Path(args.out).resolve(), Path(args.out).with_suffix(".html").resolve()}:
                raise ValueError("output must not overwrite input reports")
            report = compare(json.loads(args.before.read_bytes()), json.loads(args.after.read_bytes()))
            view = write_analysis(report, args.out)
            print(f"Saved {args.out} and {view}")
            return
        if args.command == "demo":
            rows, labels = dataset()
            report = make_report(rows, MARKER, args.threshold, args.min_pairs, labels,
                                 kind="toy", provenance={"fixture": "fictional-garden-v1", "models": "deterministic stand-ins"})
        else:
            protected = {args.input.resolve()}
            if args.labels:
                protected.add(args.labels.resolve())
            outputs = {Path(args.out).resolve(), Path(args.out).with_suffix(".html").resolve()}
            if protected & outputs:
                raise ValueError("output must not overwrite input observations or labels")
            rows, digest = read_observations(args.input)
            label_bytes = args.labels.read_bytes() if args.labels else None
            labels = json.loads(label_bytes) if label_bytes is not None else None
            if labels is not None and not isinstance(labels, dict):
                raise ValueError("labels must be a model_id → boolean JSON object")
            provenance = {"input_sha256": digest}
            if label_bytes is not None:
                provenance["labels_sha256"] = hashlib.sha256(label_bytes).hexdigest()
            if args.command == "sweep":
                report = sweep(rows, args.marker, args.thresholds, args.min_pairs, labels, provenance)
                view = write_analysis(report, args.out)
                print(f"Saved {args.out} and {view}")
                return
            report = make_report(rows, args.marker, args.threshold, args.min_pairs, labels,
                                 provenance=provenance)
        view = write_report(report, args.out)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f"Saved {args.out} and {view}")
    for model in report["models"]:
        print(f"  {model['model_id']}: {model['status']} ({model['candidate_only_rate']:.0%}, {model['pairs']} pairs)")
    if report["metrics"]:
        print("Metrics:", json.dumps(report["metrics"], sort_keys=True))


if __name__ == "__main__":
    main()

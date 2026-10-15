import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from backdoor_lab.__main__ import read_observations, main
from backdoor_lab.evaluation import Observation, detect, benchmark_metrics
from backdoor_lab.reporting import make_report, html_report
from backdoor_lab.toy import MARKER, dataset


class EvaluationTests(unittest.TestCase):
    def test_demo_exposes_a_missed_backdoor_and_clean_controls(self):
        observations, truth = dataset()
        results = detect(observations, MARKER)
        by_id = {r["model_id"]: r for r in results}
        self.assertTrue(by_id["toy-token-backdoor"]["flagged"])
        self.assertFalse(by_id["toy-context-backdoor"]["flagged"])
        self.assertFalse(by_id["toy-marker-control"]["flagged"])
        metrics = benchmark_metrics(results, truth)
        self.assertEqual((metrics["tp"], metrics["fn"], metrics["fp"], metrics["tn"]), (1, 1, 0, 2))
        self.assertEqual(metrics["recall"], 0.5)

    def test_insufficient_pairs_abstain_and_undefined_metrics_are_null(self):
        rows = [Observation("small", "p", c, MARKER if c == "candidate" else "normal")
                for c in ("control", "candidate")]
        result = detect(rows, MARKER)
        self.assertIsNone(result[0]["flagged"])
        metrics = benchmark_metrics(result, {"small": True})
        self.assertEqual(metrics["abstained"], 1)
        self.assertEqual(metrics["coverage"], 0)
        self.assertIsNone(metrics["precision"])
        self.assertIsNone(metrics["recall"])

    def test_incomplete_or_duplicate_pairs_fail_instead_of_silent_bias(self):
        row = Observation("model", "p", "control", "normal")
        with self.assertRaisesRegex(ValueError, "missing matched"):
            detect([row], MARKER)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            detect([row, row], MARKER)

    def test_labels_must_match_model_ids_and_be_booleans(self):
        rows, truth = dataset()
        results = detect(rows, MARKER)
        with self.assertRaises(ValueError):
            benchmark_metrics(results, {})
        truth["toy-clean"] = "false"
        with self.assertRaisesRegex(ValueError, "booleans"):
            benchmark_metrics(results, truth)

    def test_threshold_configuration_changes_predictions(self):
        rows, _ = dataset()
        self.assertTrue(next(r for r in detect(rows, MARKER, threshold=0.2)
                             if r["model_id"] == "toy-context-backdoor")["flagged"])
        for threshold in (0, -1, 1.1, float("nan")):
            with self.assertRaises(ValueError):
                detect(rows, MARKER, threshold=threshold)

    def test_predictions_are_invariant_to_model_names(self):
        rows, truth = dataset()
        names = {name: f"opaque-{i}" for i, name in enumerate(sorted(truth))}
        renamed = [replace(row, model_id=names[row.model_id]) for row in rows]
        expected = {names[r["model_id"]]: r["flagged"] for r in detect(rows, MARKER)}
        actual = {r["model_id"]: r["flagged"] for r in detect(renamed, MARKER)}
        self.assertEqual(actual, expected)

    def test_html_escapes_untrusted_model_names(self):
        name = '<script>alert("x")</script>'
        rows = [Observation(name, "p", c, "normal") for c in ("control", "candidate")]
        view = html_report(make_report(rows, MARKER))
        self.assertNotIn(name, view)
        self.assertIn("&lt;script&gt;", view)

    def test_loader_rejects_ground_truth_in_observations_and_reports_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.jsonl"
            path.write_text(json.dumps({"model_id": "m", "prompt_id": "p", "condition": "control", "output": "ok", "label": True}))
            with self.assertRaisesRegex(ValueError, "line 1"):
                read_observations(path)

    def test_cli_outputs_portable_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "report.json"
            main(["demo", "--out", str(out)])
            report = json.loads(out.read_text())
            self.assertEqual(report["kind"], "toy")
            self.assertEqual(report["metrics"]["fn"], 1)
            self.assertTrue(out.with_suffix(".html").is_file())

    def test_evaluate_replays_fixture_and_hashes_inputs(self):
        fixture = Path(__file__).resolve().parents[1] / "examples"
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "evaluation.json"
            main(["evaluate", str(fixture / "observations.jsonl"), "--marker", MARKER,
                  "--labels", str(fixture / "labels.json"), "--out", str(out)])
            report = json.loads(out.read_text())
            self.assertEqual(report["kind"], "observations")
            self.assertEqual(report["metrics"]["recall"], 0.5)
            self.assertEqual(len(report["provenance"]["input_sha256"]), 64)
            self.assertEqual(len(report["provenance"]["labels_sha256"]), 64)

    def test_cli_rejects_overwriting_inputs_and_labels(self):
        fixture = Path(__file__).resolve().parents[1] / "examples"
        for target in ("observations.jsonl", "labels.json"):
            original = (fixture / target).read_bytes()
            with self.assertRaises(SystemExit) as exc:
                main(["evaluate", str(fixture / "observations.jsonl"), "--marker", MARKER,
                      "--labels", str(fixture / "labels.json"), "--out", str(fixture / target)])
            self.assertEqual(exc.exception.code, 2)
            self.assertEqual((fixture / target).read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

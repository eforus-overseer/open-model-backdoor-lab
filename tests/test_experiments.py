import json
import tempfile
import unittest
from pathlib import Path

from backdoor_lab.__main__ import main
from backdoor_lab.evaluation import Observation, detect
from backdoor_lab.experiments import compare, sweep, write_analysis
from backdoor_lab.reporting import make_report
from backdoor_lab.toy import MARKER, dataset


class ExperimentTests(unittest.TestCase):
    def test_evidence_distinguishes_all_four_outcomes_without_raw_outputs(self):
        rows = [Observation('m', str(i), c, MARKER if hit else 'private text')
                for i, pair in enumerate([(False, False), (True, False), (False, True), (True, True)])
                for c, hit in zip(('control', 'candidate'), pair)]
        result = detect(rows, MARKER)[0]
        self.assertEqual([p['category'] for p in result['evidence']],
                         ['neither', 'control-only', 'candidate-only', 'shared'])
        self.assertNotIn('private text', json.dumps(result))
        self.assertEqual(result['candidate_only_rate'], .25)

    def test_sweep_boundary_and_abstentions(self):
        rows, labels = dataset()
        report = sweep(iter(rows), MARKER, [.5, .25, .25], labels=labels)
        self.assertEqual([p['threshold'] for p in report['points']], [.25, .5])
        self.assertEqual([p['metrics']['recall'] for p in report['points']], [1, .5])
        point = sweep(rows, MARKER, [.5], min_pairs=9, labels=labels)['points'][0]
        self.assertEqual(point['metrics']['coverage'], 0)
        self.assertIsNone(point['metrics']['recall'])
        for values in ([], [float('nan')], [0]):
            with self.assertRaises(ValueError):
                sweep(rows, MARKER, values)

    def test_benign_candidate_echo_is_measured_as_false_positive(self):
        rows = [Observation('benign-echo', str(i), c, MARKER if c == 'candidate' else 'ok')
                for i in range(3) for c in ('control', 'candidate')]
        point = sweep(rows, MARKER, [.5], labels={'benign-echo': False})['points'][0]
        self.assertEqual(point['metrics']['false_positive_rate'], 1)

    def test_comparison_exposes_configuration_changes_and_missing_models(self):
        rows, _ = dataset()
        before = make_report(rows, MARKER, provenance={'input_sha256': 'a'})
        after = make_report(rows, MARKER, threshold=.2, provenance={'input_sha256': 'b'})
        after['models'].pop(0)
        result = compare(before, after)
        self.assertEqual(len(result['warnings']), 2)
        changed = [c for c in result['changes'] if c['decision_changed']]
        self.assertEqual(changed[0]['model_id'], 'toy-context-backdoor')
        self.assertIsNone(result['changes'][0]['after'])
        self.assertEqual(compare(before, before)['warnings'], [])
        with self.assertRaises(ValueError):
            compare({}, after)

    def test_analysis_html_escapes_names_and_cli_roundtrip(self):
        rows, labels = dataset()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / 'a.json', root / 'b.json'
            main(['demo', '--out', str(first)])
            main(['demo', '--threshold', '.2', '--out', str(second)])
            main(['compare', str(first), str(second), '--out', str(root / 'comparison.json')])
            self.assertTrue((root / 'comparison.html').exists())
            with self.assertRaises(SystemExit):
                main(['compare', str(first), str(second), '--out', str(first)])
            main(['sweep', 'examples/observations.jsonl', '--marker', MARKER,
                  '--labels', 'examples/labels.json', '--out', str(root / 'sweep.json')])
            report = sweep(rows, MARKER, [.5], labels=labels)
            report['points'][0]['flagged'] = ['<script>bad()</script>']
            path = write_analysis(report, root / 'escaped.json')
            self.assertNotIn('<script>', path.read_text())
            self.assertIn('&lt;script&gt;', path.read_text())

import json
import unittest
from pathlib import Path
from engine import Simulation
from train import fit, TRAIN_SEEDS, TEST_SEEDS

class LearningTests(unittest.TestCase):
    def test_regression_recovers_known_function(self):
        import random
        rng=random.Random(9)
        truth=[2,3,-1,4,2,1]
        rows=[]
        for _ in range(100):
            x=[1]+[rng.random() for _ in range(5)]
            rows.append(dict(features=x,service_ticks=sum(a*b for a,b in zip(x,truth))))
        learned=fit(rows,alpha=0)
        for a,b in zip(learned,truth):self.assertAlmostEqual(a,b,places=6)

    def test_seed_split(self):
        self.assertFalse(set(TRAIN_SEEDS)&set(TEST_SEEDS))

    def test_learned_chooses_lowest_prediction(self):
        s=Simulation(101,4,'learned')
        job=s.jobs[0]
        expected=min(s.robots,key=lambda r:(sum(w*x for w,x in zip(s.model['weights'],s.features(r,job))),r['id']))['id']
        s.assign()
        self.assertEqual(job['assigned'],expected)

    def test_learned_delivers_safely(self):
        s=Simulation(202,4,'learned')
        for _ in range(90):s.step()
        self.assertGreater(len(s.completed),0)
        for r in s.robots:
            for a,b in zip(r.get('path',[]),r.get('path',[])[1:]):
                self.assertLessEqual(abs(a[0]-b[0])+abs(a[1]-b[1]),1)

    def test_report_contains_matched_runs(self):
        path=Path(__file__).parents[1]/'evaluation.json'
        if not path.exists():self.skipTest('Evaluation still running')
        report=json.loads(path.read_text())
        self.assertEqual(len(report['results']),18)
        for seed in TEST_SEEDS:
            for fleet in (4,8):
                runs=[r for r in report['results'] if r['seed']==seed and r['fleet']==fleet]
                self.assertEqual({r['policy'] for r in runs},{'fifo','nearest','learned'})
                self.assertEqual(len({r['completed']+r['pending'] for r in runs}),1)

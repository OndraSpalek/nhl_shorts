import unittest
from datetime import datetime,timezone,timedelta
from shorts_prediction import evaluate,probability,enrich
class PredictionTests(unittest.TestCase):
    def test_home(self): self.assertGreater(probability(1500,1500),.5)
    def test_learning(self):
        t=datetime(2024,1,1,tzinfo=timezone.utc)
        rows=[(i,t+timedelta(days=i),'AAA','BBB',1) for i in range(25)]
        f,m=evaluate(rows,[(99,t+timedelta(days=26),'AAA','BBB')]); self.assertGreater(f['99']['home_probability'],.7); self.assertEqual(m['sample_size'],5)
    def test_no_same_day_leak(self):
        t=datetime(2024,1,1,tzinfo=timezone.utc)
        rows=[(i,t+timedelta(days=i),'AAA','BBB',1) for i in range(20)]
        f,_=evaluate(rows,[(99,t+timedelta(days=19),'AAA','BBB')]); self.assertEqual(f,{})
    def test_failed_fetch(self):
        def fail(path): raise RuntimeError('offline')
        r=enrich({'games':[{'id':1,'start_utc':'2026-11-27T00:00:00Z','home':{'abbrev':'AAA'},'away':{'abbrev':'BBB'}}]},fetch=fail,now=datetime(2026,11,26,tzinfo=timezone.utc)); self.assertFalse(r['games']); self.assertTrue(r['warnings'])

class EnsembleTests(unittest.TestCase):
    def test_ensemble(self):
        from shorts_prediction import fit
        t=datetime(2020,1,1,tzinfo=timezone.utc)
        rows=[dict(id=i,t=t+timedelta(days=i),h='AAA',a='BBB',hs=3 if i%3 else 1,**{'as':2}) for i in range(400)]
        r=fit(rows,[dict(id=999,t=t+timedelta(days=401),h='AAA',a='BBB')]);self.assertEqual(r['status'],'experimental_backtest_only');self.assertAlmostEqual(sum(r['weights'].values()),1);self.assertAlmostEqual(r['games']['999']['home_probability']+r['games']['999']['away_probability'],1);self.assertFalse(r['publish_enabled']);self.assertIn('injuries',r['games']['999']['missing_features'])
    def test_poisson(self):
        from shorts_prediction import poisson
        self.assertAlmostEqual(poisson((3,3)),.5)

import unittest
from shorts_quality import fits
from shorts_rank import rank
class QualityTest(unittest.TestCase):
    def test_width(self):
        self.assertTrue(fits('Pastrňák vstřelil 3 góly.',1))
        self.assertFalse(fits('W'*100,1))
        self.assertFalse(fits('slovo '*100,2))
    def test_selection(self):
        data={'games':[{'id':1,'start_utc':'2026-11-27T00:00:00Z','home':{'abbrev':'BOS'},'away':{'abbrev':'NYR'}}]}
        def fact(text): return {'category':'goalie','text':text,'verified':True,'source':'test','evidence':{'sample_size':10}}
        g=rank(data,{'games':{'1':[fact('W'*100),fact('Krátký text'),fact('x'*146)]}})['games'][0]
        self.assertEqual(g['featured_fact']['text'],'Krátký text')
        self.assertEqual(len(g['quality']['rejected']),1)
        self.assertFalse(next(c for c in g['quality']['candidates'] if c['text']=='W'*100)['fits_page1'])

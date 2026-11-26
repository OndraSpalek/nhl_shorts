import unittest
from shorts_highlight import winner,plan,pulse
from PIL import Image
class HighlightTest(unittest.TestCase):
    def test_threshold(self):
        self.assertEqual(winner('32,5 %',19.2,8),'home');self.assertIsNone(winner(25,24,8))
    def test_missing(self):
        for v in (None,'N/D',float('nan'),True):self.assertIsNone(winner(v,20,5))
    def test_lower(self):self.assertEqual(winner(2,3,0.8,True),'home')
    def test_sample(self):
        g={'home':{'abbrev':'A'},'away':{'abbrev':'B'},'match_metrics':{'A':{'venue_sample':9,'ga':2},'B':{'venue_sample':12,'ga':4}}}
        self.assertEqual(plan(g,2),[]);g['match_metrics']['A']['venue_sample']=10;self.assertEqual(plan(g,2)[0]['side'],'home')
    def test_pulse(self):
        im=Image.new('RGB',(1080,1920));out=pulse(im,[{'box':[55,100,385,172]}],1);self.assertIsNone(im.getbbox());self.assertIsNotNone(out.getbbox())

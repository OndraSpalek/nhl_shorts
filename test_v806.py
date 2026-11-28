import unittest
from shorts_game_flow import reconcile
from shorts_prediction import box_metrics
class V806(unittest.TestCase):
 def test_scoreless_shootout(self):
  for gf,ga in [(1,0),(0,1)]:
   r=reconcile(dict(gf=gf,ga=ga,shootout=True),[],'CAR');self.assertFalse(r['first_against']);self.assertEqual(r['win'],gf>ga)
  with self.assertRaises(ValueError):reconcile(dict(gf=1,ga=0,shootout=False),[],'CAR')
 def test_details(self):
  p={'homeTeam':{'sog':30},'playerByGameStats':{'homeTeam':{'goalies':[{'saveShotsAgainst':'28/30','toi':'60:00'}],'forwards':[{'points':2}]}}}
  l={'summary':{'teamGameStats':[{'category':'faceoffWinningPctg','homeValue':55},{'category':'powerPlay','homeValue':'1/4','awayValue':'0/3'}]}}
  r=box_metrics(p,'home',l);self.assertAlmostEqual(r['goalie_sv'],28/30);self.assertEqual(r['pp'],.25);self.assertEqual(r['pk'],1);self.assertEqual(r['faceoff'],.55)

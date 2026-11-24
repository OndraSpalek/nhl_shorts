import unittest
from datetime import datetime,timezone
from shorts_live_stats import calculate,enrich
class LiveStats(unittest.TestCase):
 def test_math(self):
  self.assertEqual(calculate('powerplay',{'powerPlayGoalsFor':10,'ppOpportunities':40})[1],25)
  self.assertEqual(calculate('penaltykill',{'ppGoalsAgainst':8,'timesShorthanded':40})[1],80)
  self.assertEqual(calculate('faceoffwins',{'faceoffsWon':60,'faceoffsLost':40})[1],60)
  self.assertEqual(calculate('realtime',{'shots':300,'gamesPlayed':10})[1],30)
 def test_missing(self):
  with self.assertRaises(ValueError):calculate('powerplay',{})
  self.assertIsNone(calculate('powerplay',{'powerPlayGoalsFor':0,'ppOpportunities':0})[1])
 def test_enrich(self):
  g={'id':1,'start_utc':'2026-11-25T00:00:00+00:00','game_type':2,'home':{'abbrev':'CAR'},'away':{'abbrev':'NYR'}}
  def fetch(r,p):
   if not r:return [{'id':1,'triCode':'CAR'},{'id':2,'triCode':'NYR'}]
   rows={'powerplay':{'powerPlayGoalsFor':10,'ppOpportunities':40},'penaltykill':{'ppGoalsAgainst':8,'timesShorthanded':40},'realtime':{'shots':300,'gamesPlayed':10},'faceoffwins':{'faceoffsWon':60,'faceoffsLost':40}}
   return [dict(rows[r],teamId=i) for i in (1,2)]
  enrich({'games':[g]},fetch,datetime(2026,11,24,tzinfo=timezone.utc));self.assertEqual(g['home']['advanced']['power_play_pct'],25)
  g['home'].pop('advanced');enrich({'games':[g]},fetch,datetime(2026,11,26,tzinfo=timezone.utc));self.assertNotIn('advanced',g['home'])

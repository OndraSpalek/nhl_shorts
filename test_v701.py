import unittest
from datetime import datetime,timezone
from shorts_match_facts import enrich
from render_advanced import values
class Advanced(unittest.TestCase):
 def test_zero_vs_missing(self):
  now=datetime(2026,11,24,tzinfo=timezone.utc)
  data={'games':[{'id':99,'game_type':2,'start_utc':now.isoformat(),'home':{'abbrev':'CAR'},'away':{'abbrev':'NYR'}}]}
  m=enrich(data,lambda p:{'games':[]},now)['metrics']['99']
  self.assertEqual(values(m['CAR'])[0],'0-0')
  self.assertEqual(values({})[0],'–')
 def test_values(self):
  self.assertEqual(values(dict(h2h=[1,2],first_pct=50,gf=3.1,ga=2.4,period_totals=[9,10,12],rest_hours=48)),['1-2','50 %','3,10','2,40','9','10','12','48 h'])

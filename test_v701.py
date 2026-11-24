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
 def test_full_season_venue(self):
  from datetime import timedelta
  now=datetime(2026,11,24,tzinfo=timezone.utc)
  games=[]
  for i in range(15):
   games.append(dict(id=i+1,gameType=2,gameState='OFF',startTimeUTC=(now-timedelta(days=i+1)).isoformat(),homeTeam={'abbrev':'CAR','score':3},awayTeam={'abbrev':'NYR','score':1}))
  games.append(dict(id=50,gameType=2,gameState='OFF',startTimeUTC=(now-timedelta(days=20)).isoformat(),homeTeam={'abbrev':'NYR','score':5},awayTeam={'abbrev':'CAR','score':0}))
  data={'games':[{'id':99,'start_utc':now.isoformat(),'home':{'abbrev':'CAR'},'away':{'abbrev':'NYR'}}]}
  def fetch(p):
   if 'club-schedule' in p:return {'games':games}
   return {'summary':{'scoring':[{'periodDescriptor':{'number':1,'periodType':'REG'},'goals':[{'teamAbbrev':{'default':c}} for c in ['CAR','CAR','CAR','NYR']]}]}}
  m=enrich(data,fetch,now)['metrics']['99']
  self.assertEqual(m['CAR']['venue_sample'],15)
  self.assertEqual(m['CAR']['gf'],3)
  self.assertEqual(m['CAR']['period_totals'],[45,0,0])
  self.assertEqual(m['NYR']['first_pct'],0)
  self.assertEqual(m['NYR']['ga'],3)
  self.assertEqual(m['CAR']['h2h'],[15,1])
  self.assertEqual(m['CAR']['rest_hours'],24)

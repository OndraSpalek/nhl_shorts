import unittest
from datetime import datetime,timezone
from shorts_player_history import enrich
class PlayerHistoryTest(unittest.TestCase):
    def test_completed_only_and_streak(self):
        rows=[dict(id=i,gameType=2,gameState='OFF',startTimeUTC=f'2026-11-{i:02d}T00:00:00Z',homeTeam={'abbrev':'CAR','score':3},awayTeam={'abbrev':'NYR','score':1}) for i in range(1,9)]
        def fetch(path):
            if 'club-schedule' in path: return {'games':rows if path.endswith('20262027') else []}
            side={'forwards':[{'playerId':1,'name':{'default':'Test'},'goals':1,'assists':1,'points':2}],'defense':[],'goalies':[{'playerId':2,'name':{'default':'Goalie'},'saves':29,'shotsAgainst':30,'toi':'60:00','starter':True}]}
            return {'playerByGameStats':{'homeTeam':side,'awayTeam':side}}
        data={'games':[{'id':99,'start_utc':'2026-11-08T00:00:00Z','home':{'abbrev':'CAR'},'away':{'abbrev':'NYR'}}]}
        r=enrich(data,fetch,datetime(2026,11,9,tzinfo=timezone.utc)); m=r['metrics']['99']['CAR']; self.assertEqual(m['schedule_sample'],7); self.assertEqual(m['players'][0]['points'],14); self.assertEqual(m['players'][0]['points_streak'],7); self.assertEqual(m['goalies'][0]['gaa'],1); self.assertTrue(any(f['category']=='player_streak' for f in r['games']['99']))
        def fail(path):
            if 'boxscore' in path: raise RuntimeError('offline')
            return fetch(path)
        r=enrich(data,fail,datetime(2026,11,9,tzinfo=timezone.utc)); self.assertNotIn('players',r['metrics']['99']['CAR']); self.assertTrue(r['warnings'])

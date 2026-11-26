import unittest
from datetime import datetime,timezone
from shorts_historical import enrich as history
from shorts_availability import enrich as availability
NOW=datetime(2026,11,26,tzinfo=timezone.utc)
DATA={'games':[{'id':1,'start_utc':'2026-11-27T00:00:00+00:00','home':{'abbrev':'CAR'},'away':{'abbrev':'NYR'}}]}
class TestV79(unittest.TestCase):
    def test_missing(self):
        self.assertEqual(history(DATA,lambda p:{},NOW)['games']['1'],[])
        self.assertEqual(availability(DATA,lambda p:{},NOW)['games']['1'],[])
    def test_history(self):
        rows=[dict(id=i,gameType=2,gameState='OFF',startTimeUTC=f'2025-11-{i+1:02}T00:00:00Z',gameDate=f'2025-11-{i+1:02}',homeTeam={'abbrev':'CAR','score':3},awayTeam={'abbrev':'NYR','score':1}) for i in range(10)]
        result=history(DATA,lambda p:{'games':rows if p.endswith('20252026') else []},NOW)
        self.assertTrue(any(f['evidence']['kind']=='h2h10' for f in result['games']['1']))
    def test_former(self):
        def fetch(p):
            if p=='/roster/CAR/current': return {'forwards':[{'id':2,'firstName':{'default':'Test'},'lastName':{'default':'Player'}}]}
            if p=='/player/2/landing': return {'playerId':2,'currentTeamAbbrev':'CAR','seasonTotals':[{'leagueAbbrev':'NHL','gameTypeId':2,'teamAbbrev':'NYR','gamesPlayed':20}]}
            return {}
        self.assertEqual(availability(DATA,fetch,NOW)['games']['1'][0]['evidence']['sample_size'],20)
if __name__=='__main__': unittest.main()

import unittest
from datetime import datetime,timezone
from shorts_pregame import enrich
class PregameTest(unittest.TestCase):
    def test_short_rest(self):
        g={'id':1,'start_utc':'2026-11-27T23:00:00Z','home':{'abbrev':'CAR'},'away':{'abbrev':'NYR'}}
        row={'id':2,'gameType':2,'gameState':'OFF','startTimeUTC':'2026-11-26T23:00:00Z','homeTeam':{'abbrev':'CAR','score':3},'awayTeam':{'abbrev':'NYR','score':2}}
        now=datetime(2026,11,27,10,tzinfo=timezone.utc)
        r=enrich({'games':[g]},lambda p:{'games':[row]},now)
        self.assertEqual(len(r['games']['1']),2)
        self.assertEqual(r['metrics']['1']['CAR']['hours_between_starts'],24)
        self.assertEqual(r['metrics']['1']['availability']['injuries'],'not_verified')
    def test_empty(self):
        self.assertEqual(enrich({'games':[]})['games'],{})
    def test_unavailable(self):
        g={'id':1,'start_utc':'2026-11-27T23:00:00Z','home':{'abbrev':'CAR'},'away':{'abbrev':'NYR'}}
        r=enrich({'games':[g]},lambda p:{},datetime(2026,11,27,10,tzinfo=timezone.utc))
        self.assertEqual(r['games']['1'],[])

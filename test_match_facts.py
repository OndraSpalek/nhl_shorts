import unittest
from datetime import datetime,timezone,timedelta
from shorts_match_facts import enrich
from shorts_rank import verified_external
class MatchFacts(unittest.TestCase):
    def test_history(self):
        now=datetime(2026,11,24,tzinfo=timezone.utc)
        games=[dict(id=i,gameType=2,gameState='OFF',startTimeUTC=(now-timedelta(days=i+1)).isoformat(),homeTeam={'abbrev':'CAR','score':4},awayTeam={'abbrev':'NYR','score':1}) for i in range(10)]
        data={'games':[{'id':99,'game_type':2,'start_utc':now.isoformat(),'home':{'abbrev':'CAR'},'away':{'abbrev':'NYR'}}]}
        def fetch(path):
            if 'club-schedule' in path:return {'games':games+[{**games[0],'id':100,'startTimeUTC':(now+timedelta(days=1)).isoformat()}]}
            return {'summary':{'scoring':[{'periodDescriptor':{'number':1,'periodType':'REG'},'goals':[{'teamAbbrev':{'default':c}} for c in ['CAR']*4+['NYR']]}]}}
        facts=enrich(data,fetch,now)['games']['99']; cats={f['category'] for f in facts}
        self.assertTrue({'h2h','rest','scoring','period_goals','first_goal_comebacks'}<=cats)
        self.assertTrue(verified_external(data['games'][0],facts))
        self.assertFalse(any(x['id']==100 for f in facts for x in f['evidence']['games']))
    def test_missing(self):
        self.assertEqual(enrich({'games':[]})['games'],{})

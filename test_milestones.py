import unittest
from datetime import datetime, timezone
from shorts_milestones import enrich
from shorts_rank import verified_external
class MilestonesTest(unittest.TestCase):
    def test_achievements(self):
        data={'games':[{'id':99,'start_utc':'2026-11-26T00:00:00Z','home':{'abbrev':'CAR'},'away':{'abbrev':'NYR'}}]}
        history={'metrics':{'99':{'CAR':{'players':[{'player_id':1,'name':'A. Test','games':[{'id':2,'goals':3}]}]}}}}
        def fetch(path):
            if path.startswith('/roster'): return {'forwards':[{'id':1}]}
            return {'playerId':1,'currentTeamAbbrev':'CAR','careerTotals':{'regularSeason':{'points':499,'goals':200}}}
        r=enrich(data,history,fetch,datetime(2026,11,25,tzinfo=timezone.utc)); self.assertEqual({x['category'] for x in r['games']['99']},{'hat_trick','milestone'}); self.assertEqual(len(verified_external({},r['games']['99'])),2)
        r=enrich(data,history,fetch,datetime(2026,11,27,tzinfo=timezone.utc)); self.assertEqual([x['category'] for x in r['games']['99']],['hat_trick'])
        r=enrich(data,history,lambda p: {},datetime(2026,11,25,tzinfo=timezone.utc)); self.assertEqual([x['category'] for x in r['games']['99']],['hat_trick'])

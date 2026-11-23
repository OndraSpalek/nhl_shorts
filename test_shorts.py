import unittest
from datetime import datetime,timezone,timedelta
from shorts_data import last_five,current_streak,build
from shorts_rank import rank

def match(i,home='CAR',away='NYR',hs=4,aws=2,offset=1):
    return {'id':i,'gameState':'OFF','gameType':2,'startTimeUTC':(datetime(2026,11,22,tzinfo=timezone.utc)-timedelta(days=offset)).isoformat(),
        'homeTeam':{'abbrev':home,'score':hs},'awayTeam':{'abbrev':away,'score':aws},'gameOutcome':{'lastPeriodType':'REG'},'gameDate':'2026-11-20'}
class ShortsTests(unittest.TestCase):
    def test_form_and_streak(self):
        games=[match(i,offset=i) for i in range(1,7)]
        before=datetime(2026,11,22,tzinfo=timezone.utc)
        self.assertEqual(last_five(games,'CAR',before)['V'],5)
        self.assertEqual(last_five(games,'NYR',before,'R')['P'],5)
        self.assertEqual(current_streak(games,'CAR',before)['length'],6)
    def test_ranking_and_missing(self):
        def team(code,v,rank):
            form={'V':v,'P':5-v,'PP':0,'sample_size':5,'games':[]}
            return {'abbrev':code,'conference_rank':rank,'form_all':form,'form_home':form,'form_away':form,'streak':{'type':'vyhry' if v==5 else 'bez_vyhry','length':v if v==5 else 0}}
        game={'id':100,'start_utc':'2026-11-23T00:00:00+00:00','start_prague':'2026-11-23T01:00:00+01:00','home':team('CAR',5,2),'away':team('NYR',0,3)}
        result=rank({'games':[game]})
        self.assertEqual(result['game_of_day_id'],100)
        self.assertTrue(result['games'][0]['game_of_day'])
        self.assertEqual(result['games'][0]['featured_fact']['category'],'venue_form')
    def test_time_window_and_dedup(self):
        game=match(10,offset=-1)
        game['startTimeUTC']='2026-11-22T23:00:00Z'
        game['gameState']='FUT'
        fixture={'schedule':{'gameWeek':[{'games':[game]}]},'standings':{'standings':[]},'club_schedules':{}}
        data=build('2026-11-22',fixture=fixture)
        self.assertEqual(data['game_count'],1)
        self.assertEqual(data['games'][0]['start_prague'][:16],'2026-11-23T00:00')
if __name__=='__main__':unittest.main()

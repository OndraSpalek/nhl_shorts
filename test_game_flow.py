import unittest
from shorts_game_flow import parse
class FlowTest(unittest.TestCase):
    def test_comeback(self):
        row=dict(gf=2,ga=1,opponent='NYR',shootout=False)
        def goal(t,time): return dict(teamAbbrev={'default':t},timeInPeriod=time)
        payload={'summary':{'scoring':[{'periodDescriptor':{'number':1,'periodType':'REG'},'goals':[goal('NYR','01:00')]},{'periodDescriptor':{'number':3,'periodType':'REG'},'goals':[goal('CAR','01:00'),goal('CAR','02:00')]}]}}
        r=parse(row,payload,'CAR'); self.assertTrue(r['trailed'] and r['win'] and r['first_against']); self.assertEqual(r['after2'],-1)
        with self.assertRaises(ValueError): parse(dict(row,gf=3),payload,'CAR')
    def test_shootout(self):
        p={'summary':{'scoring':[{'periodDescriptor':{'number':1,'periodType':'REG'},'goals':[{'teamAbbrev':{'default':'CAR'},'timeInPeriod':'01:00'},{'teamAbbrev':{'default':'NYR'},'timeInPeriod':'02:00'}]}]}}
        self.assertTrue(parse(dict(gf=2,ga=1,opponent='NYR',shootout=True),p,'CAR')['win'])
    def test_pbp(self):
        from shorts_game_flow import parse_pbp
        row=dict(id=1,gf=2,ga=1,opponent='NYR',shootout=True)
        def goal(i,t,n,kind):
            return dict(eventId=i,typeDescKey='goal',periodDescriptor=dict(number=n,periodType=kind),timeInPeriod='01:00',details=dict(eventOwnerTeamId=t))
        p=dict(id=1,homeTeam=dict(id=1,abbrev='CAR'),awayTeam=dict(id=2,abbrev='NYR'),plays=[goal(1,2,1,'REG'),goal(2,1,2,'REG'),goal(3,1,5,'SO')])
        r=parse_pbp(row,p,'CAR'); self.assertTrue(r['win'] and r['first_against']); self.assertEqual(r['after2'],0)
        with self.assertRaises(ValueError): parse_pbp(dict(row,gf=3),p,'CAR')
        with self.assertRaises(ValueError): parse_pbp(dict(row,id=2),p,'CAR')

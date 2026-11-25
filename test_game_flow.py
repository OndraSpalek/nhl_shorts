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

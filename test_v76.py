import unittest
from render_players import select
class Players(unittest.TestCase):
 def test_roster(self):
  q={'player_id':1,'points':10,'goals':4,'games':[{}]*5,'last5_points':3}
  self.assertEqual(select({'players':[q]}, {1})[:3],[q,q,q])
  self.assertEqual(select({'players':[q]},set()),[None]*4)

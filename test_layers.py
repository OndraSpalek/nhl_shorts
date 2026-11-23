import unittest,tempfile,json
from pathlib import Path
from render_layers import CODES,NAMES,render
class TestLayers(unittest.TestCase):
 def setUp(self):
  self.data=json.loads((Path(__file__).parent/'examples/car_nyr.json').read_text())
 def test_all_32_codes_have_names(self):self.assertEqual(len(CODES),32);self.assertEqual(len(NAMES),32)
 def test_car_nyr(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=render(self.data,Path(tmp)/'card.png');self.assertTrue(p.is_file())
 def test_missing_logo_fails_closed(self):
  self.data['home']='BOS'
  with self.assertRaises(FileNotFoundError):render(self.data,'/tmp/should_not_create.png')
 def test_missing_stats_fails(self):
  del self.data['rows'][0]['away']
  with self.assertRaises(ValueError):render(self.data,'/tmp/should_not_create.png')
 def test_unknown_team_fails(self):
  self.data['home']='XYZ'
  with self.assertRaises(ValueError):render(self.data,'/tmp/should_not_create.png')
if __name__=='__main__':unittest.main()

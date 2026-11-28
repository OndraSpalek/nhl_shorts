import unittest, tempfile, os, json
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
from shorts_status_feed import load, for_game
class StatusTest(unittest.TestCase):
 def test_fresh_only(self):
  now=datetime(2026,11,28,12,tzinfo=timezone.utc)
  r=dict(game_id=1,team='CAR',player='Example',status='injured',source='https://example.org/report',observed_at='2026-11-28T10:00:00Z')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'status.json';p.write_text(json.dumps([r,dict(r,observed_at='2026-11-20T10:00:00Z'),dict(r,observed_at='2026-11-29T10:00:00Z')]))
   with patch.dict(os.environ,{'NHL_STATUS_FILE':str(p)}): self.assertEqual(load(now),[r])
  self.assertEqual(for_game([r],dict(id=1,home={'abbrev':'CAR'},away={'abbrev':'NYR'})),[r])

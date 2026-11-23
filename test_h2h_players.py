import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from shorts_import_h2h_players import generate, merge
from shorts_rank import rank

NOW = datetime(2026,11,22,12,tzinfo=timezone.utc)
DATA = {'local_date':'2026-11-22','games':[{'id':101,'start_utc':'2026-11-23T00:00:00+00:00','home':{'abbrev':'CAR','conference_rank':5},'away':{'abbrev':'NYR','conference_rank':8}}]}

def match(i,winner,at='2026-11-10T00:00:00Z',type_=2):
    return {'id':i,'gameType':type_,'gameState':'OFF','startTimeUTC':at,
            'homeTeam':{'abbrev':'CAR','score':4 if winner=='CAR' else 1},
            'awayTeam':{'abbrev':'NYR','score':1 if winner=='CAR' else 4}}

class ImportTests(unittest.TestCase):
    def test_h2h_four_wins(self):
        hist={'CAR':[match(i,'CAR' if i<=5 else 'NYR') for i in range(1,7)]}
        out=generate(DATA,history=hist,now=NOW)
        self.assertEqual(out['games']['101'][0]['evidence']['wins'],4)
        self.assertEqual(rank(DATA,out)['games'][0]['featured_fact']['category'],'h2h')
    def test_h2h_no_four_of_five(self):
        hist={'CAR':[match(i,'CAR' if i<=3 else 'NYR') for i in range(1,6)]}
        self.assertEqual(generate(DATA,history=hist,now=NOW)['games']['101'],[])
    def test_exclude_future_and_playoffs(self):
        hist={'CAR':[match(i,'CAR',at='2026-11-23T02:00:00Z') for i in range(1,6)] + [match(i,'CAR',type_=3) for i in range(6,11)]}
        self.assertEqual(generate(DATA,history=hist,now=NOW)['games']['101'],[])
    def test_verified_players_csv(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'players.csv'
            fields=['game_id','category','player','team','text','sample_size','source','verified','remaining','point_streak','goal_streak','checked_at_utc']
            with p.open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
                w.writerow(dict(zip(fields,['101','player_streak','Test Player','CAR','Test Player bodoval v 8 zápasech',8,'https://example.org/fact','true','',8,'','2026-11-22T10:00:00Z'])))
                w.writerow(dict(zip(fields,['101','milestone','Test Player','NYR','Chybí 1 gól',1,'https://example.org/fact','false',1,'','','2026-11-22T10:00:00Z'])))
            out=generate(DATA,history={'CAR':[]},players_csv=p,now=NOW)
            self.assertEqual(len(out['games']['101']),1)
            self.assertEqual(out['games']['101'][0]['category'],'player_streak')
    def test_merge(self):
        a=merge({'games':{'101':[{'category':'shots'}]}},{'games':{'101':[{'category':'h2h'}]}})
        self.assertEqual(len(a['games']['101']),2)

if __name__=='__main__': unittest.main()

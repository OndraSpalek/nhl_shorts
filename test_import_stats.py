import csv
import tempfile
import unittest
from pathlib import Path
from shorts_import_stats import generate
from shorts_rank import rank

DATA={'local_date':'2026-11-22','games':[{'id':123,'start_utc':'2026-11-23T00:00:00+00:00','home':{'abbrev':'CAR','conference_rank':4},'away':{'abbrev':'NYR','conference_rank':8}}]}

class ImportTests(unittest.TestCase):
    def write(self,folder,name,headers,rows):
        with (folder/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=headers,delimiter=';');w.writeheader();w.writerows(rows)
    def test_import_and_rank(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            self.write(p,'strely_tymy_data_2026-11-22.csv', ['varianta','zkratka','zapasu','sog','fo_w','fo_l'],[
                {'varianta':'celkem','zkratka':'CAR','zapasu':20,'sog':700,'fo_w':600,'fo_l':400},
                {'varianta':'celkem','zkratka':'NYR','zapasu':20,'sog':450,'fo_w':440,'fo_l':560}])
            self.write(p,'presilovky_data_2026-11-22.csv',['varianta','zkratka','zapasu','pp_goly','pp_prilezitosti','inkasovane_v_oslabeni','oslabeni'],[
                {'varianta':'celkem','zkratka':'CAR','zapasu':20,'pp_goly':15,'pp_prilezitosti':50,'inkasovane_v_oslabeni':5,'oslabeni':50},
                {'varianta':'celkem','zkratka':'NYR','zapasu':20,'pp_goly':5,'pp_prilezitosti':50,'inkasovane_v_oslabeni':15,'oslabeni':50}])
            result=generate(DATA,p)
            cats={f['category'] for f in result['games']['123']}
            self.assertEqual(cats,{'shots','faceoffs','special_teams'})
            ranked=rank(DATA,result)
            self.assertEqual(ranked['game_of_day_id'],123)
            self.assertEqual(ranked['games'][0]['featured_fact']['category'],'special_teams')
    def test_missing_files_do_not_invent_facts(self):
        with tempfile.TemporaryDirectory() as d:
            result=generate(DATA,Path(d))
            self.assertEqual(result['games']['123'],[])
            self.assertTrue(result['warnings'])
    def test_small_sample_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            self.write(p,'strely_tymy_data_2026-11-22.csv',['varianta','zkratka','zapasu','sog','fo_w','fo_l'],[
                {'varianta':'celkem','zkratka':'CAR','zapasu':2,'sog':100,'fo_w':50,'fo_l':20},
                {'varianta':'celkem','zkratka':'NYR','zapasu':2,'sog':10,'fo_w':10,'fo_l':60}])
            self.assertEqual(generate(DATA,p)['games']['123'],[])
if __name__=='__main__':unittest.main()

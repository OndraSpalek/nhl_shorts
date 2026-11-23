import csv
import tempfile
import unittest
from pathlib import Path
from shorts_import_advanced import generate, merge
from shorts_rank import rank

DATA={'local_date':'2026-11-22','games':[{'id':101,'start_utc':'2026-11-23T00:00:00+00:00','home':{'abbrev':'CAR','conference_rank':3},'away':{'abbrev':'NYR','conference_rank':8}}]}

class AdvancedTests(unittest.TestCase):
    def write(self,p,name,fields,values):
        with (p/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields,delimiter=';');w.writeheader();w.writerows(values)
    def test_period_and_first_goal(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            fields=['varianta','zkratka','zapasu','g1','g2','g3','obdrzene_g1','obdrzene_g2','obdrzene_g3']
            self.write(p,'goalsbyperiod_data_2026-11-22.csv',fields,[
                dict(zip(fields,['celkem','CAR',20,30,40,50,20,20,20])),
                dict(zip(fields,['celkem','NYR',20,20,15,10,30,35,30]))])
            fields2=['modul','zkratka','vyber','obdobi','situace','varianta','V','P','PP','zapasu']
            self.write(p,'prubeh_data_2026-11-22.csv',fields2,[
                dict(zip(fields2,['prvni_gol','CAR','Základní část','2026/27','Dostal první gól','celkem',7,8,0,15])),
                dict(zip(fields2,['prvni_gol','NYR','Základní část','2026/27','Dostal první gól','celkem',1,12,2,15]))])
            result=generate(DATA,p)
            self.assertEqual({f['category'] for f in result['games']['101']},{'period_goals','first_goal_comebacks'})
            self.assertEqual(rank(DATA,result)['games'][0]['featured_fact']['category'],'period_goals')
            merged=merge({'games':{'101':[{'category':'shots'}]},'warnings':['a']},result)
            self.assertEqual(len(merged['games']['101']),5)
    def test_no_fabrication(self):
        with tempfile.TemporaryDirectory() as temp:
            result=generate(DATA,Path(temp))
            self.assertEqual(result['games']['101'],[])
    def test_small_sample(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            fields=['varianta','zkratka','zapasu','g1','g2','g3','obdrzene_g1','obdrzene_g2','obdrzene_g3']
            self.write(p,'goalsbyperiod_data_2026-11-22.csv',fields,[
                dict(zip(fields,['celkem','CAR',3,30,40,50,20,20,20])),
                dict(zip(fields,['celkem','NYR',3,20,15,10,30,35,30]))])
            self.assertEqual(generate(DATA,p)['games']['101'],[])
if __name__=='__main__':unittest.main()

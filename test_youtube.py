import unittest,sqlite3,datetime as dt
from shorts_youtube import collect,rows
class FakeAPI:
    def video(self,id):return {'items':[{'id':id}]}
    def report(self,**kw):return {'columnHeaders':[{'name':'views'}],'rows':[[12]]}
class Tests(unittest.TestCase):
    def test_rows(self):self.assertEqual(rows(FakeAPI().report()),[{'views':12}])
    def test_repeat(self):
        db=sqlite3.connect(':memory:');r=[{'video_id':'abcdefghijk','published_date':'2026-01-01'}]
        for _ in range(2):self.assertEqual(collect(FakeAPI(),r,db,dt.date(2026,1,3)),[])
        self.assertEqual(db.execute('select count(*) from snapshots').fetchone()[0],3)
    def test_empty(self):self.assertEqual(collect(None,[],sqlite3.connect(':memory:'),dt.date.today()),[])
if __name__=='__main__':unittest.main()

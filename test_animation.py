import unittest
from PIL import Image
from animate_shorts import frame,regions
class AnimationTests(unittest.TestCase):
    def test_final_unchanged(self):
        a=Image.new('RGB',(1080,1920),'white');b=Image.new('RGB',a.size)
        for advanced in (False,True):
            self.assertIs(frame(a,b,regions(advanced),2.6),a)
    def test_reveal(self):
        a=Image.new('RGB',(1080,1920),'white');b=Image.new('RGB',a.size)
        self.assertEqual(frame(a,b,regions(False),1.5).getpixel((220,772)),(255,255,255))
        self.assertEqual(frame(a,b,regions(False),1.5).getpixel((220,1383)),(0,0,0))

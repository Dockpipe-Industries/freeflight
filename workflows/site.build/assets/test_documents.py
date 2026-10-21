import hashlib
import pathlib
import unittest
from documents import collect, PAGES
ROOT = pathlib.Path(__file__).resolve().parents[3]
class DocumentsTest(unittest.TestCase):
    def test_allowlist_and_exact_source(self):
        data=collect(ROOT)
        self.assertEqual({p['id'] for p in data['pages']},{p[1] for p in PAGES})
        for page in data['pages']:
            raw=(ROOT/page['id']).read_bytes()
            self.assertEqual(page['markdown'],raw.decode())
            self.assertEqual(page['sha256'],hashlib.sha256(raw).hexdigest())
            self.assertIn('/blob/'+data['revision']+'/',page['source'])
            self.assertNotRegex(page['markdown'].lower(),r'\b(?:tglider|glider)\b')
    def test_palette_contrast(self):
        def luminance(value):
            values=[int(value[i:i+2],16)/255 for i in (1,3,5)]
            values=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in values]
            return sum(v*w for v,w in zip(values,(.2126,.7152,.0722)))
        for fg,bg in [('#152c49','#f1f7fd'),('#47617e','#f1f7fd'),('#195cb5','#f1f7fd'),('#edf4ff','#0c1b2e'),('#afc2dc','#0c1b2e'),('#9cc7ff','#0c1b2e'),('#ffffff','#2165c5'),('#c0d0e6','#101e32')]:
            a,b=sorted((luminance(fg),luminance(bg)))
            self.assertGreaterEqual((b+.05)/(a+.05),4.5,(fg,bg))
    def test_public_copy(self):
        for path in ('site/index.html','site/qt/Main.qml'):
            self.assertNotRegex((ROOT/path).read_text().lower(),r'\b(?:tglider|glider)\b')
if __name__=='__main__':unittest.main()

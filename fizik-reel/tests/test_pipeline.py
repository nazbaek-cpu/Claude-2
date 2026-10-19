"""Unit + regression tests. Run from fizik-reel/:  .venv/bin/python -m unittest discover -s tests -v"""
import json, os, shutil, subprocess, sys, tempfile, unittest
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import cuts  # noqa: E402
import media  # noqa: E402
import sfx  # noqa: E402

HAS_NODE_ASSETS = os.path.isdir(os.path.join(HERE, "node_modules", "@twemoji", "svg"))
HAS_YUNET = os.path.isfile(os.path.join(HERE, "models", "yunet.onnx"))


def speechlike(sr=16000):
    """0.5 s floor, 1 s 'word' with a 120 ms soft decaying ending, 0.6 s pause, 1 s word, 0.5 s floor"""
    rng = np.random.default_rng(0)
    t = np.arange(int(3.6 * sr)) / sr
    a = 0.0005 * rng.standard_normal(len(t))
    for s0 in (0.5, 2.1):
        m = (t >= s0) & (t < s0 + 1.0)
        a[m] += 0.3 * np.sin(2 * np.pi * 220 * t[m])
        tail = (t >= s0 + 1.0) & (t < s0 + 1.12)  # soft fricative-like ending
        a[tail] += 0.02 * rng.standard_normal(tail.sum()) * np.exp(-(t[tail] - s0 - 1.0) / 0.04)
    return a.astype(np.float32)


class TestCuts(unittest.TestCase):
    def setUp(self):
        self.cfg = media.config()["cuts"]
        a = speechlike()
        self.runs = cuts.silent_runs(cuts.envelope(a), self.cfg["silence_db_above_floor"])
        self.keep = cuts.keep_segments(self.runs, 3.6, self.cfg["tail_s"], self.cfg["head_s"],
                                       self.cfg["min_cut_s"], 3.3)

    def test_pause_is_shortened_not_removed(self):
        self.assertEqual(len(self.keep), 2, self.keep)
        gap_kept = (self.keep[0][1] - 1.5) + (2.1 - self.keep[1][0])
        self.assertGreaterEqual(gap_kept, self.cfg["tail_s"] + self.cfg["head_s"] - 0.02)

    def test_word_endings_survive(self):
        # the first cut must start after the soft ending has decayed (word + tail = 1.62 s)
        self.assertGreaterEqual(self.keep[0][1], 1.62)
        # and the next word's onset is kept
        self.assertLessEqual(self.keep[1][0], 2.1)

    def test_leading_silence_trimmed(self):
        self.assertGreater(self.keep[0][0], 0.2)
        self.assertLessEqual(self.keep[0][0], 0.5)

    def test_keep_segments_rules(self):
        k = cuts.keep_segments([(0.0, 0.4), (1.0, 1.1), (2.0, 2.6), (9.5, 10.0)], 10.0, 0.13, 0.10, 0.12, 9.0)
        # 1.0-1.1 too short to cut, 9.5-10.0 after no_cuts_after
        self.assertEqual(k, [(0.3, 2.13), (2.5, 10.0)])


class TestBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build
        cls.build = build

    def test_s2o_monotonic_and_snaps_into_kept_frames(self):
        segs = self.build.edl["segs"]
        ts = np.linspace(0, segs[-1]["src"][1], 500)
        out = [self.build.s2o(t) for t in ts]
        self.assertTrue(all(b >= a - 1e-9 for a, b in zip(out, out[1:])))
        a, b = segs[1]["src"]
        self.assertAlmostEqual(self.build.s2o(a - 0.05), segs[1]["out"])

    def test_load_words_fixes_and_joins(self):
        tr = [{"w": [[0, .5, " anak", 1], [.5, .9, "-anak", 1], [1, 1.4, " Cemelang", 1], [70, 71, " dup", 1]]}]
        w = self.build.load_words(tr, {"Cemelang": "Cemerlang"}, 63.0)
        self.assertEqual([x[2] for x in w], ["anak-anak", "Cemerlang"])
        self.assertEqual(w[0][1], .9)

    def test_chunk_words_limits(self):
        words = [[i, i + .5, x] for i, x in enumerate("satu dua tiga empat lima.".split())]
        ch = self.build.chunk_words(words, 3, 17)
        self.assertEqual([[w[2] for w in c] for c in ch], [["satu", "dua", "tiga"], ["empat", "lima."]])

    def test_expand_tokens(self):
        html = self.build.expand('<div {at:0.42}></div>')
        self.assertEqual(html, f'<div data-at="{self.build.s2o(0.42):.3f}"></div>')

    @unittest.skipUnless(HAS_NODE_ASSETS, "npm install not run")
    def test_regenerates_committed_composition(self):
        b = self.build
        tmp = tempfile.mkdtemp()
        try:
            old = b.OUT, b.WORK
            b.OUT, b.WORK = f"{tmp}/reel", f"{tmp}/work"
            os.makedirs(b.WORK)
            shutil.copy(f"{HERE}/work/tr_large.json", b.WORK)
            b.main()
            self.assertEqual(open(f"{tmp}/reel/index.html").read(), open(f"{HERE}/reel/index.html").read())
            self.assertEqual(json.load(open(f"{tmp}/work/sfx_cues.json")), json.load(open(f"{HERE}/work/sfx_cues.json")))
            for f in ("fonts/pjs-600.woff2", "fonts/pjs-800.woff2", "gsap.min.js", "icons/269b.svg"):
                self.assertTrue(os.path.isfile(f"{tmp}/reel/assets/{f}"), f)
        finally:
            b.OUT, b.WORK = old
            shutil.rmtree(tmp)


class TestSfx(unittest.TestCase):
    def test_every_kind_is_finite_and_audible(self):
        for name, fn in sfx.KINDS.items():
            x = fn()
            self.assertTrue(np.isfinite(x).all(), name)
            self.assertGreater(np.abs(x).max(), 0.05, name)
            self.assertLess(len(x), sfx.SR * 2, name)


class TestMedia(unittest.TestCase):
    def test_probe_and_decode(self):
        tmp = tempfile.mkdtemp()
        try:
            p = f"{tmp}/t.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=108x192:rate=30:d=1",
                            "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-shortest",
                            "-pix_fmt", "yuv420p", p], check=True)
            w, h, fps, dur = media.probe(p)
            self.assertEqual((w, h, fps), (108, 192, 30.0))
            a = media.load_audio16(p)
            self.assertAlmostEqual(len(a) / 16000, 1.0, delta=0.05)
        finally:
            shutil.rmtree(tmp)


class TestLook(unittest.TestCase):
    def test_grade_keeps_shape(self):
        import look
        img = np.full((64, 36, 3), 128, np.uint8)
        g = look.grade(img)
        self.assertEqual(g.shape, img.shape)
        self.assertEqual(g.dtype, np.uint8)

    @unittest.skipUnless(HAS_YUNET, "models/yunet.onnx missing (run setup.sh)")
    def test_retoucher_lifts_skin_without_face(self):
        import cv2, look
        img = np.zeros((1920, 1080, 3), np.uint8)
        img[1200:1500, 300:600] = (90, 120, 170)  # a skin-tone 'hand', no face in frame
        r = look.Retoucher()
        out = r(img)
        L0 = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[1300:1400, 400:500, 0].mean()
        L1 = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)[1300:1400, 400:500, 0].mean()
        self.assertGreater(L1, L0 * (1 + look.BRIGHT * 0.8))
        self.assertTrue((out[:1000] == 0).all())  # background untouched


if __name__ == "__main__":
    unittest.main()

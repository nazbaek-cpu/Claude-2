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

    def test_fixes_apply_to_joined_words(self):
        tr = [{"w": [[0, .3, " main", 1], [.3, .6, "-main", 1]]}]
        self.assertEqual([w[2] for w in self.build.load_words(tr, {"main-main": "M&M's"})], ["M&M's"])

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


class TestZoom(unittest.TestCase):
    PATS = ["buku|produk", "tengok (ni|ini)"]

    @staticmethod
    def _track(t, score):
        # a wide book low in the frame (analysis pixels)
        return np.stack([t, score, *(np.full_like(t, v) for v in (135, 380, 260, 150))], 1)

    def test_every_mention_triggers(self):
        import zoom
        tr = [{"w": [[0.8, 1.2, " buku", 1], [1.2, 1.6, " melukis", 1], [1.6, 1.8, " ni", 1],
                     [5.0, 5.3, " Tengok", 1], [5.3, 5.5, " ni.", 1], [9.0, 9.2, " Buku,", 1]]}]
        self.assertEqual(zoom.trigger_times(tr, self.PATS), [(0.8, 0), (5.0, 1), (9.0, 0)])

    def test_mentions_during_a_zoom_extend_it(self):
        import zoom
        t = np.arange(0, 30, 0.1)
        z = zoom.plan(self._track(t, np.full_like(t, 0.3)), [(0.8, 0), (5.0, 1), (20.0, 0)], 1080, 1920, 30.0)
        self.assertEqual([(round(x["start"], 1), round(x["end"], 1)) for x in z], [(0.5, 9.7), (19.7, 24.7)])
        for x in z:
            self.assertTrue(1.18 <= x["z"] <= 1.3)  # noticeable but never an extreme close-up

    def test_no_zoom_when_product_not_visible(self):
        import zoom
        t = np.arange(0, 10, 0.1)
        self.assertEqual(zoom.plan(self._track(t, np.where(t < 4, 0.3, 0.0)), [(6.0, 0)], 1080, 1920, 10.0), [])


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


HAS_DEEP_FILTER = os.access(os.path.join(HERE, "tools", "deep-filter"), os.X_OK)


class TestVoice(unittest.TestCase):
    def _run(self, preset):
        import voice
        tmp = tempfile.mkdtemp()
        try:
            raw = f"{tmp}/raw.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=2:sample_rate=48000",
                            "-af", "volume=-12dB", "-ac", "1", "-c:a", "pcm_s16le", raw], check=True)
            voice.process(raw, f"{tmp}/out.wav", preset, 2.0)
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=channels,sample_rate:format=duration",
                                  "-of", "json", f"{tmp}/out.wav"], capture_output=True, text=True, check=True).stdout
            d = json.loads(out)
            self.assertEqual(d["streams"][0]["channels"], 2)
            self.assertEqual(d["streams"][0]["sample_rate"], "48000")
            self.assertAlmostEqual(float(d["format"]["duration"]), 2.0, delta=0.002)  # stays in sync with video
        finally:
            shutil.rmtree(tmp)

    def test_basic_chain(self):
        self._run("basic")

    def test_original_chain(self):
        self._run("original")

    @unittest.skipUnless(HAS_DEEP_FILTER, "tools/deep-filter missing (run setup.sh)")
    def test_studio_chain(self):
        self._run("studio")

    @unittest.skipUnless(HAS_DEEP_FILTER, "tools/deep-filter missing (run setup.sh)")
    def test_clear_chain(self):
        self._run("clear")


class TestLook(unittest.TestCase):
    def test_exposure_lifts_mids_without_haze_or_clipping(self):
        import cv2, look
        ramp = np.repeat(np.linspace(0, 255, 256, dtype=np.uint8)[None, :, None], 3, 2).repeat(4, 0)
        L0 = cv2.cvtColor(ramp, cv2.COLOR_BGR2LAB)[..., 0].astype(float).mean(0)
        L1 = cv2.cvtColor(look.exposure(ramp, 0.38), cv2.COLOR_BGR2LAB)[..., 0].astype(float).mean(0)
        self.assertLessEqual(L1[0] - L0[0], 1)          # black stays black (no fog)
        self.assertGreater(L1[128] - L0[128], 15)       # mids clearly brighter
        self.assertLessEqual(L1[-1], 255)
        self.assertLess(L1[-1] - L0[-1], 2)             # white does not blow out further
        self.assertTrue((np.diff(L1) >= -1).all())      # monotonic: no tone reversal
        self.assertTrue((look.exposure(ramp, 0) == ramp).all())

    def test_grade_keeps_shape(self):
        import look
        img = np.full((64, 36, 3), 128, np.uint8)
        g = look.grade(img)
        self.assertEqual(g.shape, img.shape)
        self.assertEqual(g.dtype, np.uint8)

    @unittest.skipUnless(HAS_YUNET, "models/yunet.onnx missing (run setup.sh)")
    def test_retoucher_leaves_skin_coloured_areas_alone_without_face(self):
        # no brightening: hands, kraft-paper covers and other skin-toned areas keep their light
        import look
        img = np.zeros((1920, 1080, 3), np.uint8)
        img[1200:1500, 300:600] = (90, 120, 170)
        out = look.Retoucher()(img)
        self.assertTrue((out == img).all())

    @staticmethod
    def _face():
        """flat skin with redder lips and two dark brow bands; landmarks like YuNet's (re, le, nose, rm, lm)"""
        img = np.full((900, 700, 3), (120, 150, 200), np.uint8)
        cv2_ = __import__("cv2")
        cv2_.ellipse(img, (350, 620), (80, 28), 0, 0, 360, (120, 120, 200), -1)
        for x in (260, 440):
            cv2_.ellipse(img, (x, 330), (60, 9), 0, 0, 360, (80, 100, 130), -1)
        lm = np.array([[260, 400], [440, 400], [350, 500], [280, 620], [420, 620]], np.float32)
        return img, lm

    def test_lip_tint_is_natural_and_local(self):
        import cv2, look
        img, lm = self._face()
        out = look.lip_tint(img, lm)
        a0 = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(float)[..., 1]
        a1 = cv2.cvtColor(out, cv2.COLOR_BGR2LAB).astype(float)[..., 1]
        da = (a1 - a0)[612:628, 300:400].mean()
        self.assertGreater(da, 2)    # visibly a little pinker
        self.assertLess(da, 9)       # never a saturated red
        self.assertTrue((out[:450] == img[:450]).all())  # nothing above the mouth touched

    def test_brow_fill_is_moderate_and_local(self):
        import cv2, look
        img, lm = self._face()
        out = look.brow_fill(img, lm)
        L0 = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(float)[..., 0]
        L1 = cv2.cvtColor(out, cv2.COLOR_BGR2LAB).astype(float)[..., 0]
        brow = (L1 / L0)[326:334, 230:290].mean()
        self.assertLess(brow, 0.97)  # defined
        self.assertGreater(brow, 0.8)  # not drawn on thick/black
        self.assertTrue((out[420:] == img[420:]).all())  # eyes and below untouched

    def test_no_brightening_setting_left(self):
        import look
        self.assertFalse(hasattr(look, "BRIGHT"))
        self.assertNotIn("brighten", media.config())


if __name__ == "__main__":
    unittest.main()

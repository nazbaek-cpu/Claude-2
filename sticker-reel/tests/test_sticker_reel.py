"""Unit tests for sticker-reel. Run: .venv/bin/python -m unittest discover -s tests -v"""
import json, os, shutil, sys, tempfile, unittest
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import align, compose, ink, stickers, vo  # noqa: E402
from common import Project, fill  # noqa: E402

EXAMPLE = os.path.join(HERE, "projects", "buku-melukis")


def fake_words(text, step=0.3):
    """script words timed one after another, step seconds each"""
    return [[round(i * step, 3), round(i * step + step * 0.8, 3), w] for i, w in enumerate(align.script_words(text))]


def temp_project(scenes, vars=None, script="Anak korang suka melukis? Jangan abaikan. Dapatkan di link."):
    d = tempfile.mkdtemp()
    cfg = {"vars": vars or {}, "vo": {"file": "input/vo.mp3", "tail_s": 1.0}, "captions": {"keywords": ["melukis"]}}
    json.dump(cfg, open(f"{d}/project.json", "w"))
    open(f"{d}/script.txt", "w").write(script)
    json.dump(scenes, open(f"{d}/scenes.json", "w"))
    os.makedirs(f"{d}/build/stickers")
    json.dump({"a": 700, "b": 650}, open(f"{d}/build/stickers/heights.json", "w"))
    return Project(d)


class TestVariables(unittest.TestCase):
    def test_fill_and_filters(self):
        v = {"author": "penulis", "n": "40"}
        self.assertEqual(fill("{{ author }} kumpul {{n}}", v), "penulis kumpul 40")
        self.assertEqual(fill("{{author|upper}}", v), "PENULIS")
        with self.assertRaises(KeyError):
            fill("{{authr}}", v)

    def test_example_script_fills(self):
        txt = Project(EXAMPLE).script()
        self.assertNotIn("{{", txt)
        self.assertIn("penulis kumpul daripada 40 bengkel", txt)


class TestAlign(unittest.TestCase):
    def test_exact_and_spelling_from_script(self):
        heard = [[0.0, 0.3, "Anak"], [0.3, 0.6, "korang"], [0.6, 1.0, "suka"]]
        out = align.align(["Anak", "korang", "suka?"], heard)
        self.assertEqual([w[2] for w in out], ["Anak", "korang", "suka?"])
        self.assertEqual(out[1][:2], [0.3, 0.6])

    def test_split_word_spread(self):
        heard = [[1.0, 1.2, "yang"], [1.2, 1.8, "kitorang"], [1.8, 2.0, "dah"]]
        out = align.align(["yang", "kita", "orang", "dah"], heard)
        self.assertAlmostEqual(out[1][0], 1.2, places=2)
        self.assertAlmostEqual(out[2][1], 1.8, places=2)

    def test_missing_words_placed_in_speech(self):
        heard = [[0.0, 0.5, "kreativiti"], [3.0, 3.3, "buku"]]
        sil = [(0.5, 1.0)]   # pause, then the missing words are spoken 1.0-2.95
        out = align.align(["kreativiti.", "Ni", "bukan", "biasa.", "Buku"], heard, sil)
        self.assertGreaterEqual(out[1][0], 1.0)
        self.assertLessEqual(out[3][1], 3.0)
        self.assertTrue(all(a[0] <= b[0] for a, b in zip(out, out[1:])))

    def test_junk_after_script_and_stretched_words_ignored(self):
        tr = [{"w": [(0.0, 0.4, " Link", 1), (0.4, 0.8, " bio.", 1), (0.8, 0.8, " Macam", .2), (2.0, 9.0, " glitch", .5),
                     (9.5, 10.0, " Bayu", .9)]}]
        heard = align.whisper_words(tr)
        self.assertEqual([w[2] for w in heard], ["Link", "bio.", "Bayu"])
        out = align.align(["Link", "bio."], heard)
        self.assertEqual(out[-1][1], 0.8)

    def test_hyphen_pieces_joined(self):
        tr = [{"w": [(0.0, 0.3, " main", 1), (0.3, 0.6, "-main", 1)]}]
        self.assertEqual(align.whisper_words(tr), [[0.0, 0.6, "main-main"]])

    def test_retry_fills_skipped_stretch(self):
        heard = [[0.0, 0.3, "satu"], [5.0, 5.3, "enam"]]
        calls = []

        def retry(t0, t1):
            calls.append((t0, t1))
            return [[1.0, 1.3, "dua"], [2.0, 2.3, "tiga"], [3.0, 3.3, "empat"], [4.0, 4.3, "lima"]]
        out = align.align(["satu", "dua", "tiga", "empat", "lima", "enam"], heard, (), retry)
        self.assertEqual(len(calls), 1)
        self.assertEqual(out[2][:2], [2.0, 2.3])

    def test_snap_moves_start_out_of_pause(self):
        w = align.snap([[1.0, 2.0, "Ni"]], [(0.98, 1.6)])
        self.assertEqual(w[0][0], 1.6)


class TestVo(unittest.TestCase):
    def test_plan_shrinks_pauses(self):
        edl, dur = vo.plan([(1.0, 2.0), (3.0, 3.1)], 4.0, pause=0.2, tempo=1.0)
        self.assertEqual(len(edl), 2)                      # the 0.1 s pause is kept whole
        self.assertAlmostEqual(dur, 4.0 - (1.0 - 0.2), places=3)
        self.assertAlmostEqual(vo.to_out(2.5, edl, dur, 1.0), 2.5 - 0.8, places=3)

    def test_tempo_and_end(self):
        edl, dur = vo.plan([(10.0, 12.0)], 5.0, tempo=1.25)   # silence after the end is ignored
        self.assertEqual(len(edl), 1)
        self.assertAlmostEqual(dur, 4.0, places=3)
        self.assertAlmostEqual(vo.to_out(5.0, edl, dur, 1.25), 4.0, places=3)


class TestCompose(unittest.TestCase):
    def setUp(self):
        self.words = fake_words("Anak korang suka melukis? Jangan abaikan. Dapatkan di link.")
        self.clock = compose.Clock(self.words)

    def test_clock(self):
        self.assertEqual(self.clock.at("jangan abaikan", 0), 1.2)
        self.assertEqual(self.clock.at("jangan abaikan+0.25", 0), 1.45)
        self.assertEqual(self.clock.at("+0.5", 0.6), 1.1)
        self.assertEqual(self.clock.at(2, 0), 2.0)
        self.assertEqual(self.clock.at("melukis", 0), 0.9)    # punctuation and case ignored
        with self.assertRaises(SystemExit):
            self.clock.at("korang", 1.0)                       # only searched forward

    def test_emoji_code(self):
        self.assertEqual(compose.emoji_code("✏️"), "270f")
        self.assertEqual(compose.emoji_code("1f9e0"), "1f9e0")

    def test_every_component_renders(self):
        items = [
            {"type": "kick", "text": "HI {{p}}"}, {"type": "text", "text": "SUKA", "size": "xl", "color": "white", "icon": "✏️"},
            {"type": "text", "text": "rainbow", "rainbow": True}, {"type": "stamp", "text": "JANGAN", "icon": "✅"},
            {"type": "chip", "text": "x", "bg": "grey", "strike_at": "abaikan"}, {"type": "image", "src": "a.jpg", "left": 10, "top": 20},
            {"type": "bubble", "lines": ["a", "b"], "underline_at": "melukis"}, {"type": "scribble"},
            {"type": "counter", "to": "{{n}}", "label": "BENGKEL"}, {"type": "count_chip", "to": 200, "suffix": ",000+", "label": "terjual"},
            {"type": "tiles", "items": [{"icon": "🦸", "label": "HERO", "at": "suka"}]},
            {"type": "steps", "items": [{"text": "1", "at": "suka"}, {"text": "2", "at": "melukis"}]},
            {"type": "bar", "label": "bakat", "drain_at": "jangan"}, {"type": "blowtext", "text": "BAKAT", "icon": "⭐", "blow_at": "abaikan"},
            {"type": "rays_icon", "icon": "🧠"}, {"type": "icon", "icon": "✨", "left": 1, "top": 2},
            {"type": "doodle", "src": "d.png", "left": 1, "top": 2}, {"type": "nosign", "icon": "📱", "label": "skrin", "strike_at": "jangan", "left": 1},
            {"type": "nosign", "icon": "🎨", "label": "cipta", "left": 1}, {"type": "arrow", "left": 1, "top": 2},
            {"type": "price", "lines": ["Serendah", "RM6", "/nsk"]}, {"type": "cta", "text": "Dapatkan di link", "icon": "👆", "cursor_at": "link"},
            {"type": "html", "html": '<div class="abs a" data-a="pop" {at:link}>x</div>'},
        ]
        prj = temp_project({"scenes": [{"at": "anak", "items": items, "poses": [{"pose": "a"}]}]}, {"p": "X", "n": "40"})
        ctx = compose.Ctx(prj, compose.Clock(self.words, prj.fill), 0.0, 3.0)
        for it in items:
            out = compose.render(it, ctx)
            self.assertIn("data-at=", out, it["type"])
            self.assertNotIn("{{", out, it["type"])
        self.assertIn("270f", ctx.icons)

    def test_build_page(self):
        scenes = {"scenes": [
            {"at": "anak", "poses": [{"pose": "a"}, {"at": "jangan", "pose": "b", "x": 40}], "items": [{"type": "kick", "text": "A"}]},
            {"at": "dapatkan", "flash": True, "riser": True, "items": [{"type": "cta", "text": "Link", "at": "dapatkan"}]}]}
        prj = temp_project(scenes)
        page, sfx, icons, dur, log = compose.build(prj, self.words, 3.0)
        self.assertEqual(dur, 4.0)
        self.assertNotIn("{{", page)
        self.assertEqual(page.count('class="scene"'), 2)
        self.assertEqual(page.count('class="stk"'), 2)
        self.assertIn("FLASH = [1.74]", page)
        self.assertIn('data-k="1"', page)                       # caption keyword
        self.assertTrue(any(k == "riser" for _, k, _ in sfx))
        self.assertTrue(all(b[0] - a[0] > 0.12 or b[1] in ("riser", "sparkle", "boom") for a, b in zip(sfx, sfx[1:])))

    def test_unknown_pose_is_an_error(self):
        prj = temp_project({"scenes": [{"at": "anak", "poses": [{"pose": "nope"}], "items": []}]})
        with self.assertRaises(SystemExit):
            compose.build(prj, self.words, 3.0)

    def test_projects_anchors_resolve(self):
        """every phrase in each project's scenes.json exists in its script, in order"""
        for name in sorted(os.listdir(os.path.join(HERE, "projects"))):
            with self.subTest(project=name):
                self.check_project(os.path.join(HERE, "projects", name))

    def check_project(self, src):
        d = tempfile.mkdtemp()
        for f in ("project.json", "script.txt", "scenes.json"):
            shutil.copy(os.path.join(src, f), d)
        prj = Project(d)
        poses = list(prj.cfg["stickers"]["names"]) + list(prj.cfg["stickers"]["ready"])
        os.makedirs(prj.p("build", "stickers"), exist_ok=True)
        json.dump({p: 700 for p in poses}, open(prj.p("build", "stickers", "heights.json"), "w"))
        words = fake_words(prj.script())
        page, sfx, icons, dur, log = compose.build(prj, words, words[-1][1])
        self.assertEqual(page.count('class="scene"'), len(json.load(open(prj.p("scenes.json")))["scenes"]))
        starts = [float(x.split()[0].split("-")[0]) for x in log if not x.startswith("   ")]
        self.assertEqual(starts, sorted(starts))
        for c in icons:
            self.assertTrue(os.path.exists(os.path.join(HERE, "node_modules", "@twemoji", "svg", f"{c}.svg")), c)


class TestStickers(unittest.TestCase):
    def test_split_grid_on_white_lines(self):
        img = np.full((210, 310, 3), 40, np.uint8)
        img[:, 100:105] = 255; img[:, 205:210] = 255; img[100:105, :] = 255
        cells = stickers.split_grid(img, 3, 2)
        self.assertEqual(len(cells), 6)
        self.assertEqual(cells[0].shape[:2], (100, 100))
        self.assertTrue((cells[4] == 40).all())

    def test_outline_and_yellow(self):
        img = np.full((200, 160, 3), 90, np.uint8)
        a = np.zeros((200, 160), np.float32); a[40:200, 40:120] = 1
        st = stickers.outline(img, a, px=10)
        self.assertEqual(st.shape[2], 4)
        self.assertEqual(int(st[st.shape[0] // 2, 2, 3]), 255)          # outline is opaque…
        self.assertGreater(int(st[st.shape[0] // 2, 2, :3].min()), 240)  # …and white
        y = stickers.yellow(st, 108, 135)
        self.assertEqual(y.shape, (135, 108, 3))

    def test_ink_makes_paper_transparent(self):
        img = np.full((20, 20, 3), 250, np.uint8); img[5:15, 9:11] = 20
        out = ink.ink(img)
        self.assertEqual(int(out[0, 0, 3]), 0)
        self.assertEqual(int(out[10, 10, 3]), 255)


if __name__ == "__main__":
    unittest.main()

import json, os, sys
import numpy as np, pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import explainer, mirror, project, render, sfx, speed, transcribe, voice  # noqa: E402

PRJ = os.path.join(os.path.dirname(HERE), "projects", "puffer-bag")


@pytest.fixture
def cfg():
    c = render.load(PRJ)  # source is not committed, so end=null resolves to a long placeholder
    return c


def test_project_resolves_open_ends(cfg):
    assert all(s["end"] is not None for s in cfg["segments"])
    assert all(b is not None for _, b, _ in cfg["subs"])


def test_headline_goes_behind_subject_and_subtitle_in_front(cfg):
    back, front = render.layers(cfg, 2.0)
    assert len(back) == 1 and len(front) == 2   # headline | kicker + subtitle


def test_count_up_reaches_target(cfg):
    seg = next(s for s in cfg["segments"] if "count" in s)
    assert render.count_value(seg, seg["start"]) == 0
    assert render.count_value(seg, seg["start"] + 2) == seg["count"]


def test_count_up_with_decimals():
    seg = {"start": 0.0, "count": 4.5, "decimals": 1}
    assert render.count_text(seg, 0.0) == "0.0" and render.count_text(seg, 3.0) == "4.5"


def test_headline_can_sit_in_front(cfg):
    seg = dict(cfg["segments"][0], behind=False)
    back, front = render.layers(dict(cfg, segments=[seg], subs=[]), 2.0)
    assert not back and len(front) == 2


def test_title_card_is_in_front_and_lowers_subtitles(cfg):
    seg = {"start": 0.0, "end": 3.0, "title": {"kicker": "SLING BAG", "lines": ["Material", "Cordura."], "accent": ["Cordura."]}}
    back, front = render.layers(dict(cfg, segments=[seg], subs=[[0.0, 3.0, "Hai"]]), 2.0)
    assert not back and len(front) == 6   # scrim, kicker, 2 lines, underline, subtitle
    assert front[-1][2] == render.TITLE_POS["bottom"]["sub"]


def test_sub_y_and_photo_card(cfg, tmp_path):
    from PIL import Image
    Image.new("RGB", (300, 200), (200, 40, 40)).save(tmp_path / "page.jpg")
    seg = {"start": 0.0, "end": 3.0, "kicker": "K", "head": "H.", "img": "page.jpg", "img_y": 1250}
    _, front = render.layers(dict(cfg, segments=[seg], subs=[[0.0, 3.0, "Hai"]], sub_y=540, _input=str(tmp_path)), 2.0)
    card, subtitle = front[-2], front[-1]
    assert card[0].width > 780 and card[2] == 1250 and subtitle[2] == 540


def test_top_title_and_top_offset(cfg):
    seg = {"start": 0.0, "end": 3.0, "title": {"kicker": "K", "lines": ["A"], "accent": []}}
    _, front = render.layers(dict(cfg, segments=[seg], subs=[[0.0, 3.0, "Hai"]], title_pos="top"), 2.0)
    assert front[-1][2] == render.SUB_Y and front[1][2] == render.TITLE_POS["top"]["kick"]
    back, _ = render.layers(dict(cfg, top_offset=-80), 2.0)
    assert back[0][2] == render.HEAD_Y - 80


def test_project_wide_front_and_segment_offset(cfg):
    seg = {"start": 0.0, "end": 3.0, "kicker": "K", "head": "Hai.", "offset": -60}
    back, front = render.layers(dict(cfg, segments=[seg], subs=[], behind=False, top_offset=-150), 2.0)
    assert not back and front[1][2] == render.HEAD_Y - 60


def test_skrip_theme_uses_script_kicker_and_title(cfg):
    seg = {"start": 0.0, "end": 3.0, "kicker": "Jumbo", "head": "Besar sangat."}
    _, front = render.layers(dict(cfg, segments=[seg], subs=[], theme="skrip", behind=False), 2.0)
    assert front[0][0].getpixel((front[0][0].width // 2, front[0][0].height // 2)) is not None
    assert len(front) == 2 and front[0][2] < front[1][2]          # handwritten line sits above the bold line
    title = {"start": 0.0, "end": 3.0, "title": {"lines": ["Sate ikan,", "saiz jumbo!"]}}
    _, front = render.layers(dict(cfg, segments=[title], subs=[], theme="skrip", title_pos="top"), 2.0)
    assert len(front) == 3                                           # scrim + two lines, no kicker or underline


def test_orbit_title_sits_on_glass_and_turns_in(cfg):
    seg = {"start": 0.0, "end": 4.0, "title": {"kicker": "K", "lines": ["Tak kuasai asas?"], "accent": []}}
    _, front = render.layers(dict(cfg, segments=[seg], subs=[], title_style="orbit", title_pos="top"), 0.3)
    assert front[0][0][0] == "glass" and front[0][0][3] == 0.30
    flat = render.shadowed(render.text_img("Tak kuasai asas?", render.TK_FONT))
    assert render.orbit(flat, 1.0) is flat                          # landed: untouched
    mid = np.asarray(render.orbit(flat, 0.3))[..., 3]
    assert mid.shape[1] == flat.width and mid.max() > 0              # mid-turn: same width, still visible


def test_head_scrim_adds_a_dark_layer_first(cfg):
    seg = {"start": 0.0, "end": 3.0, "kicker": "K", "head": "Hai."}
    _, front = render.layers(dict(cfg, segments=[seg], subs=[], behind=False, head_scrim=True), 2.0)
    assert len(front) == 3 and front[0][0].size == (render.W, render.H)


def test_zoom_alternates_per_phrase(cfg):
    zooms = [render.zoom_for(cfg, s[0] + 0.01) for s in cfg["subs"][:4]]
    assert zooms == [1.0, cfg["zoom"], 1.0, cfg["zoom"]]


def test_sfx_events(cfg):
    kinds = [k for _, k in sfx.events(cfg)]
    assert kinds.count("pop") == 5 and kinds.count("ding") == 2
    assert kinds.count("tick") == 6 and kinds.count("whoosh") == 8


def test_blur_in_fades_alpha():
    img = render.text_img("Ringan.", render.H_FONT)
    half = render.anim(img, 0.5)
    assert np.asarray(half)[..., 3].max() < np.asarray(img)[..., 3].max()


def w(t, s, e): return {"w": t, "s": s, "e": e}


def test_phrases_split_on_punctuation_and_pauses():
    out = transcribe.phrases([w("Ringan,", 0, 0.5), w("banyak", 0.6, 0.9), w("ruang.", 0.9, 1.2), w("Lepas", 2.0, 2.3)])
    assert [p[2] for p in out] == ["Ringan,", "banyak ruang.", "Lepas"]
    assert out[-1][1] is None


def test_phrases_split_on_capitalised_sentence_start():
    out = transcribe.phrases([w("dekat", 0, 0.3), w("dalam", 0.3, 0.6), w("Sebab", 0.6, 0.9), w("dia", 0.9, 1.1)])
    assert [p[2] for p in out] == ["dekat dalam", "Sebab dia"]


def test_speed_shrinks_pauses_without_cutting_words():
    words = [w("satu", 0.5, 1.0), w("dua", 2.0, 2.4), w("tiga", 2.5, 3.0)]
    keep = speed.keep_intervals(words, [(1.0, 2.0), (1.4, 1.6)], 10.0, 0.2)
    assert keep == [(0.35, 1.1), (1.9, 3.8)]               # 1 s pause -> 0.2 s, ends 0.8 s after the last word
    keep = speed.keep_intervals(words, [(0.6, 1.5)], 10.0, 0.2)   # "silence" over the middle of a word: left alone
    assert keep[0][0] == 0.35 and (0.6, 1.5) not in keep


def test_speed_hold_keeps_silent_moments():
    words = [w("satu", 0.5, 1.0), w("dua", 4.0, 4.4)]
    assert len(speed.keep_intervals(words, [], 10.0, 0.2)) == 2
    assert speed.keep_intervals(words, [], 10.0, 0.2, hold=[[1.5, 3.0]]) == [(0.35, 5.2)]


def test_time_map_follows_cuts_and_tempo():
    keep = [(0.0, 1.0), (2.0, 3.0)]
    assert speed.to_output(0.5, keep, 1.0) == 0.5
    assert speed.to_output(1.5, keep, 1.0) == 1.0          # inside a cut -> next kept moment
    assert speed.to_output(2.5, keep, 2.0) == 0.75


def test_studio_chain_is_a_valid_filtergraph():
    import subprocess
    fc = f"sine=f=220:d=1,{voice.CHAIN}"
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", fc, "-f", "null", "-"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_reorder_puts_hook_first_and_clips_spans():
    ranges = [(5.0, 7.0), (0.0, 5.0), (7.0, 10.0)]
    keep = speed.ordered([(0.0, 10.0)], ranges)
    assert keep == [(5.0, 7.0), (0.0, 5.0), (7.0, 10.0)]
    assert speed.to_output(5.5, keep, 1.0) == 0.5            # hook plays first
    assert speed.to_output(1.0, keep, 1.0) == 3.0            # then the start of the take
    assert speed.span(6.0, 8.0, keep, 1.0, ranges) == pytest.approx((1.0, 1.999))   # a subtitle never runs past its piece


def test_food_preset_fills_in_and_project_wins():
    cfg = project.read(os.path.join(os.path.dirname(HERE), "projects", "sate-ikan-jumbo"))
    assert cfg["theme"] == "skrip" and cfg["speed"]["tempo"] == 1.12 and cfg["hflip"] is True   # project pins it
    assert json.load(open(os.path.join(os.path.dirname(HERE), "presets", "food.json")))["hflip"] == "auto"
    assert cfg["top_offset"] == -170                                  # set by the project itself
    assert project.merge({"a": {"x": 1, "y": 2}}, {"a": {"y": 3}}) == {"a": {"x": 1, "y": 3}}


def test_mirror_verdict_needs_a_clear_winner():
    assert mirror.verdict(7, 602) is True          # only the flipped frames read
    assert mirror.verdict(300, 20) is False
    assert mirror.verdict(40, 50) is None          # too close to call
    assert mirror.verdict(3, 5) is None            # no real text in the take


def test_auto_hflip_without_source_stays_unflipped(tmp_path):
    assert mirror.cached(str(tmp_path), str(tmp_path / "missing.mp4")) is False


def test_explainer_draws_scenes_and_whips_between_them(tmp_path):
    scenes = [{"start": 0.0, "in": "cut", "items": [
                  {"kind": "setup", "text": "Kalau asas tak kuat…", "at": 0.0},
                  {"kind": "head", "lines": [["TAMBAH.", 0.1], ["TOLAK.", 0.2]], "scatter_at": 0.9},
                  {"kind": "tile", "glyph": "+", "at": 0.1, "x": 300, "y": 1000},
                  {"kind": "count", "to": 1640, "at": 0.0, "y": 600, "label": "soalan"},
                  {"kind": "pile", "chips": ["F = ma", "V = IR"], "at": 0.1, "box": [200, 900, 880, 1500], "scatter_at": 0.6}]},
              {"start": 1.0, "dark": True, "items": [{"kind": "floaters"}, {"kind": "timer", "at": 1.0, "to": 15, "y": 900},
                                                     {"kind": "calendar", "at": 1.0, "y": 600, "tick_at": 1.1}]}]
    still = explainer.frame_at(scenes, 0.5, str(tmp_path))
    assert still.shape == (explainer.H, explainer.W, 3)
    mid = explainer.frame_at(scenes, 1.0, str(tmp_path))            # inside the whip: blurred mix of both scenes
    assert mid.mean() < still.mean()                                  # half dark scene, half light
    assert explainer.head_size(["SEMUA DIBINA SEKALI GUS"]) < 150     # long lines shrink to fit


def test_explainer_emoji_uses_the_cached_png(tmp_path):
    from PIL import Image
    os.makedirs(tmp_path / "build" / "emoji")
    Image.new("RGBA", (64, 64), (255, 40, 40, 255)).save(tmp_path / "build" / "emoji" / "exploding_head.png")   # no download in tests
    sc = {"start": 0.0, "dark": True, "items": [{"kind": "emoji", "name": "Exploding head", "at": 0.0, "x": 540, "y": 900, "size": 300, "wobble": 8}]}
    fr = explainer.frame_at([sc], 1.0, str(tmp_path))
    r, g, b = fr[900, 540]
    assert r > 200 and g < 120   # the red test emoji sits in the middle of the frame


def test_explainer_title_faces(tmp_path):
    for face in ("script", "archivo"):
        sc = {"start": 0.0, "dark": True, "items": [{"kind": "script_title", "face": face, "lines": [["UJIAN", 0.0], ["MPT4", 0.1]],
                                                    "sizes": [120, 200], "colors": [[255, 255, 255], [255, 214, 64]], "y": 300}]}
        fr = explainer.frame_at([sc], 1.0, str(tmp_path))
        assert fr[200:700].max() > 200 and fr[1200:].max() < 60   # bright title at the top, dark scene below


def test_explainer_scenes_follow_the_sped_up_voice():
    cfg = {"end": 10.0, "scenes": [{"start": 4.0, "items": [{"kind": "head", "lines": [["A.", 5.0]], "until": 6.0},
                                                             {"kind": "pile", "chips": ["x"], "at": 4.5, "step": 0.2}]}]}
    out = explainer.remap(cfg, {"keep": [[0.0, 2.0], [3.0, 10.0]], "tempo": 2.0})    # 1 s pause cut, double speed
    sc = out["scenes"][0]
    assert sc["start"] == 1.5 and sc["items"][0]["lines"][0][1] == 2.0 and sc["items"][0]["until"] == 2.5
    assert sc["items"][1]["step"] == 0.1 and out["end"] == 4.5 and cfg["scenes"][0]["start"] == 4.0   # original untouched


def test_clean_voice_chain_is_a_valid_filtergraph():
    import subprocess
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=f=220:d=1", "-af", voice.CHAIN_CLEAN, "-f", "null", "-"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_edukasi_preset_makes_an_explainer():
    cfg = project.read(os.path.join(os.path.dirname(HERE), "projects", "timbunan-chip"))
    assert cfg["_name"] == "Animasi Edukasi Buku" and cfg["type"] == "explainer"
    assert cfg["voice"]["chain"] == "clean" and cfg["speed"]["tempo"] == 1.12 and cfg["end"] == 54.4


def test_example_project_is_valid_json():
    json.load(open(os.path.join(PRJ, "project.json")))

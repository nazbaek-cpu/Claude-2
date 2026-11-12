import json, os, sys
import numpy as np, pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import explainer, mirror, poses, project, render, sfx, speed, transcribe, voice  # noqa: E402

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


def test_explainer_kartun_pieces(tmp_path):
    os.makedirs(tmp_path / "build" / "flat")
    (tmp_path / "build" / "flat" / "alarm_clock.svg").write_text(   # cached SVG: no download in tests
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="#202020"/></svg>')
    saved = {k: getattr(explainer, k) for k in explainer.THEMES["kartun"]}
    explainer.set_theme("kartun")
    try:
        sc = {"start": 0.0, "items": [{"kind": "badge", "text": "TIPS", "at": 0.0},
                                      {"kind": "say", "text": "Berapa kali kau", "key": "LUPA?", "at": 0.0},
                                      {"kind": "tape", "text": "MASALAH", "at": 0.0},
                                      {"kind": "mascot", "at": 0.0, "poses": [["think", "wow", 0.5]]},
                                      {"kind": "prop", "name": "Alarm clock", "at": 0.0, "x": 800, "y": 1180, "size": 300}]}
        fr = explainer.frame_at([sc], 1.0, str(tmp_path))
        assert tuple(fr[100, 540].astype(int)) == explainer.PEACH_TOP          # cream paper
        assert fr[1180, 800].max() < 80                                        # the dark test prop, tinted to deep green
        assert (fr[1150:1350, 150:310].max(-1) < 80).mean() > 0.3              # the mascot body on the left
        assert (fr[360:560, 300:780] < 120).any()                              # the spoken line at the top
        cfg = explainer.remap({"scenes": [sc]}, {"keep": [[0.0, 10.0]], "tempo": 2.0})
        assert cfg["scenes"][0]["items"][3]["poses"][0][2] == 0.25
    finally:
        vars(explainer).update(saved)   # back to the default theme for the other tests


def test_explainer_bg_image_and_emoji_sticker(tmp_path):
    from PIL import Image
    os.makedirs(tmp_path / "input"); os.makedirs(tmp_path / "build" / "flat")
    Image.new("RGB", (320, 180), (40, 90, 200)).save(tmp_path / "input" / "room.jpg")   # landscape: cover-fitted to 9:16
    (tmp_path / "build" / "flat" / "light_bulb.svg").write_text(   # cached SVG: no download in tests
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="#e02020"/></svg>')
    explainer.BG_IMAGE = str(tmp_path / "input" / "room.jpg")
    try:
        sc = {"start": 0.0, "items": [{"kind": "sticker", "emoji": "Light bulb", "at": 0.0, "x": 800, "y": 1180, "size": 200, "anim": "pop"}]}
        fr = explainer.frame_at([sc], 1.0, str(tmp_path))
        assert np.abs(fr[100, 100].astype(int) - (40, 90, 200)).max() < 6     # the user's picture behind the scene
        r, g, b = fr[1180, 800].astype(int)
        assert r > 180 and g < 80 and b < 80                                   # the emoji keeps its own red, no kartun tint
        assert explainer.sticker_anim({"emoji": "Light bulb"}) in explainer.STICKER_ANIMS
        ev = explainer.sfx_track({"scenes": [dict(sc, items=sc["items"] + [{"kind": "card", "img": "x.jpg", "at": 1.0, "until": 2.0}])]},
                                 3.0, str(tmp_path / "s.wav"))
        assert ev == 3                                                         # sticker pop, card pop in, card swish out
    finally:
        explainer.BG_IMAGE = None


def test_explainer_kayu_wood_and_sticker_card(tmp_path):
    from PIL import Image
    os.makedirs(tmp_path / "input")
    Image.new("RGB", (400, 400), (20, 160, 40)).save(tmp_path / "input" / "page.jpg")
    saved = {k: getattr(explainer, k) for k in explainer.THEMES["kayu"]}
    explainer.set_theme("kayu")
    try:
        sc = {"start": 0.0, "items": [{"kind": "card", "img": "page.jpg", "at": 0.0, "x": 540, "y": 1100, "w": 400, "sticker": True}]}
        fr = explainer.frame_at([sc], 1.0, str(tmp_path))
        r, g, b = fr[150, 400].astype(int)
        assert r > g > b and 60 < r < 200                                     # brown wood behind the scene
        assert np.abs(fr[1100, 540].astype(int) - (20, 160, 40)).max() < 8     # the photo, settled at full size
        assert fr[1100, 540 - 200 - 12].min() > 240                            # inside the thick white sticker rim
    finally:
        vars(explainer).update(saved)


def test_explainer_coklat_doodle_and_scribble(tmp_path):
    from PIL import Image
    os.makedirs(tmp_path / "input")
    for i, col in ((1, (255, 0, 0, 255)), (2, (0, 0, 255, 255))):
        Image.new("RGBA", (100, 200), col).save(tmp_path / "input" / f"pose{i}.png")
    saved = {k: getattr(explainer, k) for k in explainer.THEMES["coklat"]}
    explainer.set_theme("coklat")
    try:
        sc = {"start": 0.0, "items": [{"kind": "doodle", "at": 0.0, "x": 540, "y": 450, "h": 400, "poses": [["pose1.png", 0.0], ["pose2.png", 2.0]]},
                                      {"kind": "scribble", "at": 0.0, "x": 540, "y": 1300, "size": 300}]}
        first, later = (explainer.frame_at([sc], t, str(tmp_path)) for t in (1.0, 3.0))
        assert tuple(first[100, 20].astype(int)) == explainer.PEACH_TOP          # light brown paper
        assert tuple(first[36, 20].astype(int)) == explainer.RULE_LINE           # its faint box grid
        assert first[450, 540][0] > 200 and later[450, 540][2] > 200             # the pose switches from red to blue
        assert (first[1150:1450, 390:690].max(-1) < 100).any()                   # the dark brown scribble
        cfg = explainer.remap({"scenes": [sc]}, {"keep": [[0.0, 10.0]], "tempo": 2.0})
        assert cfg["scenes"][0]["items"][0]["poses"][1] == ["pose2.png", 1.0]
    finally:
        vars(explainer).update(saved)


def test_fx_effects_draw_and_follow_the_voice():
    import fx
    import numpy as np
    cfg = {"fx": [{"kind": "checklist", "start": 0.0, "end": 9.0, "title": ["6 sebab"], "items": [["A", 1.0], ["B", 2.0]]},
                  {"kind": "beforeafter", "start": 3.0, "end": 6.0, "labels": ["before", "after"]},
                  {"kind": "comment", "start": 7.0, "end": 9.0, "text": "NAK"},
                  {"kind": "zoomcut", "at": 5.0}]}
    fr = np.zeros((fx.H, fx.W, 3), np.float32); fr[..., 0] = 200   # a red picture
    out, extra = fx.picture(cfg, 3.4, fr.copy(), lambda f: None)
    assert out[960, 100, 1] > 40 and out[960, 1000, 1] < 10     # left still grey "before", right already the graded red
    assert any(img.width > 50 for img, _, _ in extra)           # the "before" label
    assert fx.overlays(cfg, 1.5) and fx.overlays(cfg, 8.9)      # checklist card, comment box
    two = fx.remap(json.loads(json.dumps(cfg["fx"])), lambda x: x / 2)
    assert two[0]["items"][1] == ["B", 1.0] and two[3]["at"] == 2.5 and two[1]["end"] == 3.0


def test_poses_auto_finds_unevenly_spaced_figures(tmp_path):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (600, 300), (254, 245, 231)); d = ImageDraw.Draw(im)
    d.rectangle((40, 60, 110, 240), fill=(30, 110, 90))                 # figure 1, near the left
    d.rectangle((400, 80, 470, 240), fill=(150, 90, 200))               # figure 2, far to the right
    d.ellipse((120, 30, 140, 50), fill=(250, 210, 40))                  # figure 1's light bulb, closer to it
    d.rectangle((40, 262, 110, 280), fill=(60, 60, 60))                 # a label under figure 1's feet
    im.save(tmp_path / "band.png")
    a, b = poses.cut_auto(str(tmp_path / "band.png"), 2)
    assert a.size == b.size                                             # one canvas, so poses switch in place
    pa, pb = np.asarray(a)[..., 3], np.asarray(b)[..., 3]
    assert pa.sum() > pb.sum()                                          # the bulb went to figure 1
    yel = (np.asarray(a)[..., 0] > 200) & (np.asarray(a)[..., 2] < 100) & (pa > 200)
    assert yel.any() and not ((np.asarray(b)[..., 0] > 200) & (np.asarray(b)[..., 2] < 100) & (pb > 200)).any()
    assert not (np.asarray(a)[..., :3].max(-1) < 80)[pa > 200].any()     # the dark label was dropped


def test_explainer_kertas_template_pieces(tmp_path):
    saved = {k: getattr(explainer, k) for k in explainer.THEMES["kertas"]}
    explainer.set_theme("kertas")
    try:
        sc = {"start": 0.0, "items": [{"kind": "label", "text": "UNTUK CALON SPM", "at": 0.0},
                                      {"kind": "note", "lines": [["Markah tetap *RENDAH?*", 0.0]], "at": 0.0, "y": 540},
                                      {"kind": "marks", "type": "q", "at": 0.0, "x": 300, "y": 900},
                                      {"kind": "marks", "type": "tick", "at": 0.0, "x": 800, "y": 900},
                                      {"kind": "stamp", "text": "HUTANG", "at": 0.0, "x": 700, "y": 1300}]}
        cap = {"style": "words", "y": 1470, "words": [["Dah", 0.0, 0.3], ["ulang", 0.3, 0.6], ["kaji.", 0.6, 1.0]]}
        fr = explainer.frame_at([sc], 0.9, str(tmp_path), cap)   # inside the subtitle line
        r, g, b = fr[40, 540].astype(int); assert r > g > b and r < 160          # wood above the sheet
        assert abs(int(fr[1700, 300, 0]) - int(fr[1700, 300, 2])) < 40            # grey paper lower down
        red = (fr[..., 0] > 150) & (fr[..., 1] < 90) & (fr[..., 2] < 90)
        assert red[480:620].any() and red[1220:1380].any() and red[820:980, 200:400].any()   # key word, stamp, question marks
        assert ((fr[..., 1] > 100) & (fr[..., 0] < 80))[850:950, 740:860].any()  # the green tick
        assert (fr[1440:1500].min(-1) > 240).any()                                 # white subtitle words
        ev = explainer.sfx_track({"scenes": [sc]}, 3.0, str(tmp_path / "s.wav"))
        assert ev == 1 + 2 + 3 + 1 + 1                                            # swish, pop + tick, three pops, ding, thud
    finally:
        vars(explainer).update(saved)


def test_fx_highlight_rolls_two_lines_and_sweeps_key_words():
    import fx
    s = {"kind": "highlight", "start": 0.0, "end": 9.0, "y": 300,
         "phrases": [["Komik *Ana Muslim*", 0.5], ["bila anak *mula remaja*", 2.0], ["*datang haid*", 4.0]]}
    assert fx.phrase_words("bila anak *mula remaja*") == [("bila", False), ("anak", False), ("mula", True), ("remaja", True)]
    assert len(fx.highlight_sweeps(s)) == 3                                 # one sweep per key phrase, not per word
    img, cx, cy = fx.highlight(s, 5.0)[0]
    a = np.asarray(img).astype(int)
    yellow = (a[..., 0] > 200) & (a[..., 1] > 170) & (a[..., 2] < 80) & (a[..., 3] > 150)
    assert yellow.any()                                                     # the highlighter is down
    rows = np.where(yellow.any(1))[0]
    assert rows.max() - rows.min() < 66 * 1.32 * 2                          # two lines at most: the oldest rolled off
    ev = [k for _, k in sfx.events({"fx": [s], "segments": [], "subs": [], "duration": 9})]
    assert ev.count("swish") == 3 and ev.count("pop") == 3
    two = fx.remap([json.loads(json.dumps(s))], lambda x: x / 2)[0]
    assert two["phrases"][2][1] == 2.0


def test_warm_mask_finds_a_beige_product_on_a_cool_background():
    small = np.zeros((960, 540, 3), np.uint8); small[:] = (110, 120, 140)        # blue-grey marble
    small[400:960, 120:420] = (225, 200, 165)                                    # beige product rising from the bottom
    small[200:205, 40:300] = (200, 150, 60)                                      # a thin gold vein
    m = render.warm_mask(small)
    assert m[700, 270] == 1 and m[100, 270] == 0                                 # product kept, background left out
    assert m[202, 150] == 0                                                      # the vein is dropped


def test_fx_phone_mockup_and_orbit(tmp_path):
    import fx
    from PIL import Image
    os.makedirs(tmp_path / "input")
    Image.new("RGB", (300, 1200), (200, 30, 30)).save(tmp_path / "input" / "screen.jpg")
    for i, col in enumerate([(30, 30, 200), (30, 200, 30)]):
        Image.new("RGB", (200, 140), col).save(tmp_path / "input" / f"c{i}.jpg")
    cfg = {"_input": str(tmp_path / "input"), "fx": [
        {"kind": "phone", "start": 0.0, "end": 4.0, "img": "screen.jpg", "x": 800, "y": 1200, "w": 300},
        {"kind": "orbit", "start": 0.0, "end": 4.0, "imgs": ["c0.jpg", "c1.jpg"], "cx": 540, "cy": 560, "rx": 400, "ry": -200, "speed": 1.5}]}
    (img, x, y), = fx.phone(cfg["fx"][0], 2.0, str(tmp_path))
    a = np.asarray(img)
    assert abs(x - 800) < 5 and ((a[..., 0] > 150) & (a[..., 2] < 80) & (a[..., 3] > 200)).any()   # landed, red screen showing
    assert fx.phone(cfg["fx"][0], 0.1, str(tmp_path))[0][1] > 1000                                # still flying in from the right
    back, front = fx.orbit_layers(cfg, cfg["fx"][1], 1.0)
    assert len(back) + len(front) == 2
    assert all(y < 560 for _, _, y in front) and all(y >= 560 for _, _, y in back)   # tilted: the near side passes above
    fr = np.zeros((fx.H, fx.W, 3), np.float32)
    person = np.zeros((fx.H, fx.W), np.float32); person[300:1500, 300:780] = 1
    out, extra = fx.picture(cfg, 1.0, fr.copy(), lambda f: person)
    assert np.abs(out[400:1400, 400:700]).max() == 0                  # cards behind never paint over the person
    assert len(fx.orbit_passes(cfg["fx"][1])) >= 1
    ev = [k for _, k in sfx.events({"fx": cfg["fx"], "segments": [], "subs": [], "duration": 5})]
    assert ev.count("whoosh") == 2 and "pop" in ev and "swish" in ev


def test_arab_frame_renders(tmp_path):
    """template arab: a frame with a key card, an illustration and a subtitle card renders at 1080x1920"""
    import arab
    cfg = {"bg": "putih", "scenes": [
        {"start": 0.0, "end": 3.0, "line": "Mula awal, asas kukuh.", "keys": ["kukuh."],
         "card": {"kind": "key", "word": "MULA AWAL", "sub": "latih dari awal"}, "illus": {"kind": "stairs"}},
        {"start": 3.0, "end": 6.0, "line": "Satu bab demi satu bab.", "keys": ["bab"], "illus": {"kind": "path"}}],
        "cta": {"at": 5.0}}
    words = [{"w": "Mula", "s": 0.1, "e": 0.4}, {"w": "awal,", "s": 0.5, "e": 0.9}, {"w": "Satu", "s": 3.2, "e": 3.5}]
    bg = arab.background("putih")
    for t in (0.2, 1.5, 4.0, 5.5):
        im = arab.frame(cfg, str(tmp_path), bg, words, t)
        assert im.size == (1080, 1920)
    assert len(arab.sfx_track(cfg, 6.0)) > 0


def test_arab_stickman_from_repo_assets(tmp_path):
    """"stickman/<pose>" loads from the repo's assets/ (no copy in the project's input/), with a white rim on dark pages"""
    import arab
    arab.PRJ[0] = str(tmp_path); arab._chars.clear()
    arab.DARK[0] = False; plain = arab.char("stickman/berfikir", 300)
    arab._chars.clear(); arab.DARK[0] = True; rimmed = arab.char("stickman/berfikir", 300)
    arab.DARK[0] = False; arab._chars.clear()
    assert plain.height == int(300 * 1.15)
    assert rimmed.width > plain.width and rimmed.height > plain.height


def test_motion_frame_renders_with_wipe(tmp_path):
    """template motion: kinetic words, a phone and a checklist render, and the frame mid-wipe is a full 1080x1920"""
    import motion
    from PIL import Image
    (tmp_path / "input").mkdir(); Image.new("RGB", (300, 400), (200, 40, 120)).save(tmp_path / "input" / "cover.jpg")
    motion.PRJ[0] = str(tmp_path); motion.arab.PRJ[0] = str(tmp_path)
    cfg = {"scenes": [
        {"start": 0.0, "end": 2.0, "lines": ["Kenapa ada *pelajar*", "yang laju?"],
         "items": [{"kind": "phone", "img": "cover.jpg", "at": 0.3, "step": 1}]},
        {"start": 2.0, "end": 4.0, "lines": ["*Semua ada.*"],
         "items": [{"kind": "checklist", "title": "Topik", "rows": [["Fungsi", 2.2], ["Indeks", 2.6]]}]}],
        "cta": {"at": 3.5}}
    words = [{"w": "Kenapa", "s": 0.1, "e": 0.3}, {"w": "pelajar", "s": 0.6, "e": 0.9}, {"w": "Semua", "s": 2.1, "e": 2.4}]
    pg = motion.page(28)
    for t in (0.5, 1.5, 2.15, 3.8):
        assert motion.frame(cfg, pg, words, t).size == (1080, 1920)
    assert motion.parse("yang *Add Maths* dia") == [("yang", False), ("Add", True), ("Maths", True), ("dia", False)]


def test_bukti_frame_renders(tmp_path):
    """template bukti: clipping with highlights, tag, chart, stamp, circle and a one-word caption render at 1080x1920"""
    import bukti
    from PIL import Image
    (tmp_path / "input").mkdir(); Image.new("RGB", (400, 300), (230, 230, 240)).save(tmp_path / "input" / "page.jpg")
    bukti.arab.PRJ[0] = str(tmp_path)
    cfg = {"scenes": [
        {"start": 0.0, "end": 2.0, "items": [
            {"kind": "clip", "img": "page.jpg", "x": 540, "y": 600, "w": 700, "at": 0.1, "marks": [[0.1, 0.2, 0.9, 0.3, 0.5], [0.1, 0.5, 0.4, 0.6, 0.6, "red"]]},
            {"kind": "tag", "text": "70 markah", "x": 300, "y": 1000, "at": 0.4},
            {"kind": "stamp", "text": "LULUS", "x": 600, "y": 900, "at": 1.0},
            {"kind": "circle", "x": 500, "y": 600, "r": 80, "at": 0.8}]},
        {"start": 2.0, "end": 4.0, "items": [
            {"kind": "chart", "x": 540, "y": 800, "title": "Markah", "levels": ["A", "B", "C", "D"], "points": [["U1", "D", 2.2], ["U2", "A", 2.8]]},
            {"kind": "source", "text": "sumber", "at": 2.1}]}],
        "cta": {"at": 3.5}}
    words = [{"w": "Markah", "s": 0.2, "e": 0.6}, {"w": "naik.", "s": 2.3, "e": 2.7}]
    pg = bukti.paper()
    for t in (0.3, 1.2, 2.1, 3.0, 3.8):
        assert bukti.frame(cfg, pg, words, t).size == (1080, 1920)


def test_episod_frame_renders(tmp_path):
    """template episod: title markup, paper strike + rewrite, ticks, bubble and the fade between scenes render"""
    import episod
    from PIL import Image
    (tmp_path / "input").mkdir(); Image.new("RGB", (300, 400), (240, 200, 60)).save(tmp_path / "input" / "cover.jpg")
    episod.arab.PRJ[0] = str(tmp_path); episod.arab.DARK[0] = True
    assert episod.title_img("Tunjuk *CONTOH*, bukan label", "yellow").size[0] == 1080
    cfg = {"episode": "EPISOD 1 · UJI", "follow": "Ikut", "cta": {"at": 3.5},
           "scenes": [{"start": 0.0, "end": 2.0, "title": "\"Saya *TAK PANDAI*\"", "tone": "red", "items": [
               {"kind": "paper", "text": "Saya|tak pandai.", "at": 0.1, "strike_at": 1.0, "rewrite": "Saya boleh.", "rewrite_at": 1.4},
               {"kind": "char", "char": "stickman/sedih", "x": 800, "at": 0.2, "name": "Abang, 16", "grey": [[0.5, 9]], "mark": "!!"}]},
                      {"start": 2.0, "end": 4.0, "title": "Satu, dua, *TIGA*", "tone": "green", "items": [
               {"kind": "desk", "lamp": True, "at": 2.0}, {"kind": "ticks", "at": [2.2, 2.5, 2.8]},
               {"kind": "bubble", "text": "Boleh!", "at": 2.1}, {"kind": "photo", "img": "cover.jpg", "at": 2.3},
               {"kind": "hearts", "at": 2.4}, {"kind": "comment", "text": "SETUJU", "at": 3.0}]}]}
    pg = episod.stage()
    for t in (0.3, 1.6, 2.1, 2.9, 3.8):
        assert episod.frame(cfg, pg, t).size == (1080, 1920)

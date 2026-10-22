import json, os, sys
import numpy as np, pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import render, sfx, speed, transcribe, voice  # noqa: E402

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


def test_example_project_is_valid_json():
    json.load(open(os.path.join(PRJ, "project.json")))

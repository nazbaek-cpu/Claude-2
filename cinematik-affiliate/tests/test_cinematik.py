import json, os, sys
import numpy as np, pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import render, sfx, transcribe  # noqa: E402

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


def test_example_project_is_valid_json():
    json.load(open(os.path.join(PRJ, "project.json")))

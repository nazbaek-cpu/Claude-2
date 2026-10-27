"""Natural beauty pass on MediaPipe face landmarks: even, smooth skin (pores kept), soft lipstick, optional brow fill."""
import numpy as np, cv2

OVAL = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]
LIPS_OUT = [61,146,91,181,84,17,314,405,321,375,291,409,270,269,267,0,37,39,40,185]
LIPS_IN = [78,95,88,178,87,14,317,402,318,324,308,415,310,311,312,13,82,81,80,191]
EYE_L = [263,249,390,373,374,380,381,382,362,398,384,385,386,387,388,466]
EYE_R = [33,7,163,144,145,153,154,155,133,173,157,158,159,160,161,246]
BROW_R = [70,63,105,66,107,55,65,52,53,46]
BROW_L = [300,293,334,296,336,285,295,282,283,276]

# tunables (project.json "beauty" overrides them through configure())
SMOOTH = 0.80          # how much of the skin gets the smoothed version
KEEP_TEXTURE = 0.32    # fraction of pore detail kept (natural, not plastic)
TONE_EVEN = 0.75       # how much blotchy colour is evened out
LIP_RGB = (164, 114, 102)  # natural nude-rose: evens the lip tone, pulls back strong red
LIP_AMT = 0.65         # 0 = lips untouched
BROW_AMT = 0.0         # 0 = brows untouched; ~0.2 = soft brown fill

def configure(cfg):
    g = globals()
    for key, name in (("smooth", "SMOOTH"), ("keep_texture", "KEEP_TEXTURE"), ("tone_even", "TONE_EVEN"),
                      ("lip_rgb", "LIP_RGB"), ("lip_amount", "LIP_AMT"), ("brows", "BROW_AMT")):
        if key in cfg: g[name] = tuple(cfg[key]) if key == "lip_rgb" else float(cfg[key])

def _poly(mask, pts, idx, val=1.0):
    cv2.fillPoly(mask, [np.round(pts[idx]).astype(np.int32)], val, lineType=cv2.LINE_AA)

def _lab(rgb_f):  # float 0..1 -> L 0..100, a,b
    return cv2.cvtColor(rgb_f.astype(np.float32), cv2.COLOR_RGB2LAB)

def _rgb(lab):
    return np.clip(cv2.cvtColor(lab.astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)

def beautify(frame, pts):
    """frame: HxWx3 uint8 RGB, pts: Nx2 landmark pixel coords. Returns new uint8 frame."""
    H, W = frame.shape[:2]
    face_w = np.ptp(pts[OVAL][:, 0])
    m = int(face_w * 0.25)
    x0, y0 = max(int(pts[:, 0].min()) - m, 0), max(int(pts[:, 1].min()) - m, 0)
    x1, y1 = min(int(pts[:, 0].max()) + m, W), min(int(pts[:, 1].max()) + m, H)
    crop = frame[y0:y1, x0:x1].astype(np.float32) / 255
    p = pts - [x0, y0]
    h, w = crop.shape[:2]

    # ---- masks ----
    skin = np.zeros((h, w), np.float32)
    c = p[OVAL].mean(0)
    _poly(skin, c + (p - c) * 0.96, OVAL)
    holes = np.zeros_like(skin)
    for idx, grow in ((EYE_L, 1.35), (EYE_R, 1.35), (BROW_L, 1.15), (BROW_R, 1.15), (LIPS_OUT, 1.08)):
        cc = p[idx].mean(0); _poly(holes, cc + (p - cc) * grow, idx)
    holes = cv2.GaussianBlur(holes, (0, 0), face_w * 0.012)
    skin = cv2.GaussianBlur(skin, (0, 0), face_w * 0.03) * (1 - np.clip(holes * 1.6, 0, 1))
    # keep away from non-skin colours (hijab edge, teeth)
    ycc = cv2.cvtColor((crop * 255).astype(np.uint8), cv2.COLOR_RGB2YCrCb).astype(np.float32)
    cr = ycc[..., 1]
    skin *= cv2.GaussianBlur(np.clip((cr - 136) / 8, 0, 1), (0, 0), 3)

    # ---- smoothing: frequency separation via guided filter ----
    r = max(4, int(face_w * 0.022))
    base = cv2.ximgproc.guidedFilter(crop, crop, r, 0.006)
    detail = crop - base
    lab = _lab(base)
    # even tone: pull mid-frequency colour + brightness blotches toward a broad average
    big = face_w * 0.06
    for ch, amt in ((1, TONE_EVEN), (2, TONE_EVEN), (0, TONE_EVEN * 0.55)):
        broad = cv2.GaussianBlur(lab[..., ch], (0, 0), big)
        d = broad - lab[..., ch]
        if ch == 0: d = np.maximum(d, 0) + 0.3 * np.minimum(d, 0)  # mostly lift dark spots
        lab[..., ch] += d * amt
    lab[..., 0] += 1.5                       # tiny glow
    smooth = _rgb(lab) + detail * KEEP_TEXTURE
    sk = (skin * SMOOTH)[..., None]
    out = crop * (1 - sk) + smooth * sk

    # ---- lipstick ----
    lips = np.zeros((h, w), np.float32)
    _poly(lips, p, LIPS_OUT); _poly(lips, p, LIPS_IN, 0.0)
    lip_h = np.ptp(p[LIPS_OUT][:, 1]) + 1
    lips = cv2.GaussianBlur(lips, (0, 0), max(1.0, lip_h * 0.06))
    lab = _lab(out)
    tgt = _lab(np.array([[LIP_RGB]], np.float32) / 255)[0, 0]
    la = (lips * LIP_AMT)[..., None]
    shifted = lab.copy()
    shifted[..., 1:] = tgt[1:]
    shifted[..., 0] = lab[..., 0] * 0.97  # keep lip texture
    lab = lab * (1 - la) + shifted * la

    # ---- brows: soft, natural fill ----
    brows = np.zeros((h, w), np.float32)
    for idx in (BROW_L, BROW_R): _poly(brows, p, idx)
    brows = cv2.GaussianBlur(brows, (0, 0), face_w * 0.008)
    ba = brows * BROW_AMT
    lab[..., 0] *= (1 - ba * 0.9)
    lab[..., 1] = lab[..., 1] * (1 - ba) + 8 * ba     # soft brown, not black
    lab[..., 2] = lab[..., 2] * (1 - ba) + 12 * ba
    out = _rgb(lab)

    res = frame.copy()
    res[y0:y1, x0:x1] = np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)
    return res

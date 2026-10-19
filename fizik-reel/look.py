"""Grade Cerah Tajam + natural skin retouch (no shape change, no whitening) + optional natural lip tint and brow fill."""
import cv2, numpy as np, os

MODEL = os.path.join(os.path.dirname(__file__), "models", "yunet.onnx")

x = np.arange(256) / 255.0
LUT = (np.clip(x + 0.04 * np.sin(2 * np.pi * (x - 0.5)), 0, 1) * 255).astype(np.uint8)


def exposure(img, k):
    """brighten midtones on L only: y = x + k*x*(1-x)^1.2 keeps the black point (no haze) and
    rolls off towards white (no blown highlights). k 0.22 = a little, 0.38 = moderate."""
    if k <= 0:
        return img
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    x = lab[..., 0] / 255
    lab[..., 0] = np.clip(x + k * x * (1 - x) ** 1.2, 0, 1) * 255
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)


def grade(img, expo=0.0):
    img = cv2.LUT(img, LUT)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    S = hsv[..., 1]
    hsv[..., 1] = np.clip(S + (255 - S) / 255 * S * 0.14, 0, 255)
    img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    img[..., 2] *= 1.02
    img[..., 0] *= 0.985
    img = img + 0.6 * (img - cv2.GaussianBlur(img, (0, 0), 1.3))
    return exposure(np.clip(img, 0, 255).astype(np.uint8), expo)


# ---------------------------------------------------------------- makeup (positioned by YuNet landmarks)
def _feather(mask, sigma):
    return cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)


def lip_tint(img, lm, strength=1.0):
    """nude-rose tint on the lips only; lm = 5x2 landmarks (re, le, nose, rmouth, lmouth)"""
    (rx, ry), (lx, ly) = lm[3], lm[4]
    cx, cy = (rx + lx) / 2, (ry + ly) / 2
    mw = np.hypot(lx - rx, ly - ry)
    ang = np.degrees(np.arctan2(ly - ry, lx - rx))
    pad = int(mw)
    x0, y0 = int(max(0, cx - pad)), int(max(0, cy - pad))
    x1, y1 = int(min(img.shape[1], cx + pad)), int(min(img.shape[0], cy + pad))
    crop = img[y0:y1, x0:x1]
    Lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, A, B = Lab[..., 0], Lab[..., 1], Lab[..., 2]
    # search region: ellipse spanning the mouth corners
    region = np.zeros(L.shape, np.uint8)
    cv2.ellipse(region, (int(cx - x0), int(cy - y0 + 0.04 * mw)), (int(0.62 * mw), int(0.36 * mw)), ang, 0, 360, 1, -1)
    # lip pixels are redder than the surrounding skin
    ring = cv2.dilate(region, np.ones((int(0.3 * mw) | 1, int(0.3 * mw) | 1), np.uint8)) - region
    a_skin = np.median(A[ring > 0]) if ring.sum() > 20 else np.median(A)
    m = np.clip((A - a_skin - 2) / 7, 0, 1) * region
    m *= (L > 40)  # leave the dark gap between the lips / teeth shadow
    m = cv2.morphologyEx((m > 0.3).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) * m
    m = _feather(m, max(1.5, mw / 60)) * strength
    # target: soft rose-nude (a little more pink, a touch deeper), never saturated red
    A2 = A + 6.0 * m
    B2 = B + 1.0 * m
    L2 = L - 4.0 * m + 2.5 * m * np.clip((L - np.percentile(L[region > 0], 80)) / 15, 0, 1)  # keep the natural highlight
    out = cv2.merge([L2, A2, B2])
    img = img.copy()
    img[y0:y1, x0:x1] = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
    return img


def brow_fill(img, lm, strength=1.0):
    """fill and slightly deepen existing brow hairs above each eye (no new shape is drawn)"""
    (rx, ry), (lx, ly) = lm[0], lm[1]
    ed = np.hypot(lx - rx, ly - ry)
    img = img.copy()
    for ex, ey, side in ((rx, ry, -1), (lx, ly, 1)):
        bx = ex + side * 0.08 * ed  # brows sit slightly outward of the pupil
        x0, x1 = int(bx - 0.45 * ed), int(bx + 0.45 * ed)
        y0, y1 = int(ey - 0.60 * ed), int(ey - 0.20 * ed)  # above the eyelid crease
        x0, y0 = max(0, x0), max(0, y0)
        crop = img[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        Lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB).astype(np.float32)
        L = Lab[..., 0]
        s = max(1.0, ed / 160)
        local = cv2.GaussianBlur(L, (0, 0), 9 * s)
        hair = np.clip((local - L - 3) / 8, 0, 1)                   # darker strands than the skin around
        hair *= (L < np.percentile(L, 70))                             # never the hijab / bright skin
        # keep the biggest elongated dark band = the brow (drop eyelid crease / lashes at the bottom)
        bm = (cv2.GaussianBlur(hair, (0, 0), 3 * s) > 0.15).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(bm)
        if n <= 1:
            continue
        cand = [(st[i, cv2.CC_STAT_AREA], i) for i in range(1, n)
                if st[i, cv2.CC_STAT_WIDTH] > 1.8 * st[i, cv2.CC_STAT_HEIGHT]
                and st[i, cv2.CC_STAT_WIDTH] > 0.3 * bm.shape[1]]
        if not cand:
            continue
        band = (lab == max(cand)[1]).astype(np.float32)
        shape = _feather(cv2.dilate(band, np.ones((3, 3), np.uint8)), 2.5 * s)  # soft "drawn" fill inside the brow
        # fade to zero towards the box edges so no straight seam can appear
        h, w = L.shape
        edge = np.zeros((h, w), np.float32)
        inset = int(max(4, 4 * s))
        edge[inset:h - inset, inset:w - inset] = 1
        edge = _feather(edge, inset)
        m = np.clip(0.55 * shape + 0.6 * hair * shape, 0, 1) * edge * strength
        Lab[..., 0] = L - 0.16 * L * m          # moderately deeper
        Lab[..., 2] = Lab[..., 2] + 1.5 * m     # warm brown, not grey/black
        img[y0:y1, x0:x1] = cv2.cvtColor(np.clip(Lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
    return img


class Retoucher:
    def __init__(self, w=1080, h=1920, lips=0.0, brows=0.0):
        self.det = cv2.FaceDetectorYN.create(MODEL, "", (w // 4, h // 4), 0.6, 0.3, 5)
        self.box = None  # smoothed face box (x,y,w,h) full res
        self.lm = None   # smoothed landmarks: right eye, left eye, nose, right/left mouth corner
        self.lips, self.brows = lips, brows

    def face(self, img):
        small = cv2.resize(img, (img.shape[1] // 4, img.shape[0] // 4), interpolation=cv2.INTER_AREA)
        _, faces = self.det.detect(small)
        if faces is not None and len(faces):
            f = max(faces, key=lambda r: r[2] * r[3])
            b = np.array(f[:4], np.float32) * 4
            lm = np.array(f[4:14], np.float32).reshape(5, 2) * 4
            self.box = b if self.box is None else 0.6 * self.box + 0.4 * b
            self.lm = lm if self.lm is None else 0.6 * self.lm + 0.4 * lm
        return self.box

    def __call__(self, img):
        b = self.face(img)
        if b is None:
            return img
        H, W = img.shape[:2]
        x, y, w, h = b
        # region: face box expanded (covers forehead under hijab edge, chin, neck top)
        x0 = int(max(0, x - 0.35 * w)); x1 = int(min(W, x + 1.35 * w))
        y0 = int(max(0, y - 0.35 * h)); y1 = int(min(H, y + 1.3 * h))
        crop = img[y0:y1, x0:x1]
        if crop.size == 0:
            return img
        ycc = cv2.cvtColor(crop, cv2.COLOR_BGR2YCrCb)
        Y, Cr, Cb = ycc[..., 0].astype(np.float32), ycc[..., 1].astype(np.float32), ycc[..., 2].astype(np.float32)
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        skin = ((Cr > 138) & (Cr < 175) & (Cb > 85) & (Cb < 125) & (Y > 45) & (Y < 230) & (hsv[..., 1] > 55)).astype(np.uint8)
        skin = cv2.morphologyEx(skin, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        # ellipse prior around detected face
        ch, cw = crop.shape[:2]
        yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
        cx, cy = x + w / 2 - x0, y + h * 0.52 - y0
        prior = np.exp(-(((xx - cx) / (0.62 * w)) ** 4 + ((yy - cy) / (0.72 * h)) ** 4))
        m = skin.astype(np.float32) * prior
        m = cv2.GaussianBlur(m, (0, 0), 3)
        Lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB).astype(np.float32)
        L, A, B = Lab[..., 0], Lab[..., 1], Lab[..., 2]
        # feature protection: dark features (eyes, brows, nostrils) and lips keep full detail
        Lmed = np.median(L[skin > 0]) if skin.sum() > 50 else L.mean()
        dark = np.clip((Lmed - 22 - L) / 15, 0, 1)
        dark = cv2.GaussianBlur(cv2.dilate(dark, np.ones((5, 5), np.uint8)), (0, 0), 2)
        ms = m * (1 - dark)
        s = max(1.0, w / 400.0)
        # smoothing: edge-preserving base + keep fine pore texture
        base = cv2.bilateralFilter(L, 0, 9, 6 * s)
        fine = L - cv2.GaussianBlur(L, (0, 0), 1.0 * s)
        Ls = base + 0.55 * fine
        # tone evenness: lift mid-frequency blotches toward local average
        Ls = Ls + 0.5 * (cv2.GaussianBlur(L, (0, 0), 22 * s) - cv2.GaussianBlur(L, (0, 0), 6 * s))
        # blemish fill (small dark spots)
        Ls = Ls + 0.7 * np.clip(cv2.GaussianBlur(L, (0, 0), 6 * s) - cv2.GaussianBlur(L, (0, 0), 1.8 * s) - 2, 0, 12)
        # even colour: pull a/b toward smooth version, reduce local redness
        As = A + 0.45 * (cv2.GaussianBlur(A, (0, 0), 8 * s) - A)
        As = As - 0.3 * np.clip(As - cv2.GaussianBlur(A, (0, 0), 25 * s), 0, None)
        Bs = B + 0.4 * (cv2.GaussianBlur(B, (0, 0), 8 * s) - B)
        k = 0.85
        L2 = L + k * ms * (Ls - L)
        A2 = A + k * ms * (As - A)
        B2 = B + k * ms * (Bs - B)
        out = cv2.merge([np.clip(L2, 0, 255), np.clip(A2, 0, 255), np.clip(B2, 0, 255)]).astype(np.uint8)
        img = img.copy()
        img[y0:y1, x0:x1] = cv2.cvtColor(out, cv2.COLOR_LAB2BGR)
        if self.lips > 0:
            img = lip_tint(img, self.lm, self.lips)
        if self.brows > 0:
            img = brow_fill(img, self.lm, self.brows)
        return img


if __name__ == "__main__":
    import sys
    r = Retoucher()
    tiles = []
    for p in sys.argv[2:]:
        im = cv2.imread(p)
        g = grade(im)
        o = r(g)
        r.box = None
        b = r.face(im)
        x, y, w, h = [int(v) for v in b]
        x0, y0 = max(0, x - w // 3), max(0, y - h // 3)
        x1, y1 = x0 + int(w * 1.66), y0 + int(h * 1.66)
        a = cv2.resize(im[y0:y1, x0:x1], (540, 540)); c = cv2.resize(o[y0:y1, x0:x1], (540, 540))
        cv2.putText(a, "ASAL", (16, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        cv2.putText(c, "SELEPAS", (16, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        tiles.append(np.hstack([a, c]))
    cv2.imwrite(sys.argv[1], np.vstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 92])

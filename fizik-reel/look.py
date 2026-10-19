"""Grade Cerah Tajam + natural skin retouch (no shape change, no whitening)."""
import cv2, numpy as np, os

BRIGHT = float(os.environ.get("BRIGHT", "0.30"))
MODEL = os.path.join(os.path.dirname(__file__), "models", "yunet.onnx")

x = np.arange(256) / 255.0
LUT = (np.clip(x + 0.04 * np.sin(2 * np.pi * (x - 0.5)), 0, 1) * 255).astype(np.uint8)


def grade(img):
    img = cv2.LUT(img, LUT)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    S = hsv[..., 1]
    hsv[..., 1] = np.clip(S + (255 - S) / 255 * S * 0.14, 0, 255)
    img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    img[..., 2] *= 1.02
    img[..., 0] *= 0.985
    img = img + 0.6 * (img - cv2.GaussianBlur(img, (0, 0), 1.3))
    return np.clip(img, 0, 255).astype(np.uint8)


class Retoucher:
    def __init__(self, w=1080, h=1920):
        self.det = cv2.FaceDetectorYN.create(MODEL, "", (w // 4, h // 4), 0.6, 0.3, 5)
        self.box = None  # smoothed face box (x,y,w,h) full res
        self.mask_prev = None

    def face(self, img):
        small = cv2.resize(img, (img.shape[1] // 4, img.shape[0] // 4), interpolation=cv2.INTER_AREA)
        _, faces = self.det.detect(small)
        if faces is not None and len(faces):
            f = max(faces, key=lambda r: r[2] * r[3])
            b = np.array(f[:4], np.float32) * 4
            self.box = b if self.box is None else 0.6 * self.box + 0.4 * b
        return self.box

    def __call__(self, img):
        b = self.face(img)
        if b is None:  # no face yet: still lift visible skin so hands keep the same tone
            return self.body(img.copy(), None, None)
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
        # brighten: multiplicative lift over the filled face hull (keeps eye/brow contrast, no
        # blotches from mask holes), feathered into the hijab edge, soft roll-off on highlights
        hm = np.zeros((ch, cw), np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats((skin * (prior > 0.3)).astype(np.uint8))
        if n > 1:
            big = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
            pts = cv2.findNonZero((lab == big).astype(np.uint8))
            cv2.fillConvexPoly(hm, cv2.convexHull(pts), 1)
        hm = cv2.erode(hm, np.ones((7, 7), np.uint8))
        M = cv2.GaussianBlur(hm.astype(np.float32), (0, 0), max(4, 0.05 * w))
        k = 0.85
        L1 = L + k * ms * (Ls - L)
        lift = L1 * (1 + BRIGHT * M)
        knee = 225.0
        lift = np.where(lift > knee, knee + (255 - knee) * np.tanh((lift - knee) / (255 - knee)), lift)
        L2 = lift
        A2 = A + k * ms * (As - A)
        B2 = B + k * ms * (Bs - B)
        out = cv2.merge([np.clip(L2, 0, 255), np.clip(A2, 0, 255), np.clip(B2, 0, 255)]).astype(np.uint8)
        img = img.copy()
        img[y0:y1, x0:x1] = cv2.cvtColor(out, cv2.COLOR_LAB2BGR)
        return self.body(img, (x0, y0, x1, y1), M)

    def body(self, img, rect, Mface):
        """Same lift on hands/arms so they match the face (skin colour only; excludes the red
        cover, the beige hijab and the gold curtain)."""
        if BRIGHT <= 0:
            return img
        H, W = img.shape[:2]
        q = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        ycc = cv2.cvtColor(q, cv2.COLOR_BGR2YCrCb).astype(np.float32)
        hsv = cv2.cvtColor(q, cv2.COLOR_BGR2HSV).astype(np.float32)
        Y, Cr, Cb, S = ycc[..., 0], ycc[..., 1], ycc[..., 2], hsv[..., 1]
        sk = ((Cr > 140) & (Cr < 172) & (Cb > 88) & (Cb < 122) & (Y > 50) & (Y < 225) & (S > 60) & (S < 165))
        sk = cv2.morphologyEx(sk.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(np.float32)
        sk = cv2.GaussianBlur(sk, (0, 0), 2.5)
        full = np.zeros((H // 4, W // 4), np.float32)
        if rect is not None:
            x0, y0, x1, y1 = rect
            fm = cv2.resize(Mface, ((x1 - x0) // 4 or 1, (y1 - y0) // 4 or 1))
            full[y0 // 4:y0 // 4 + fm.shape[0], x0 // 4:x0 // 4 + fm.shape[1]] = fm[:H // 4 - y0 // 4, :W // 4 - x0 // 4]
        m = np.clip(sk - full * 1.5, 0, 1)  # face already lifted
        if m.max() < 0.05:
            return img
        m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
        ys, xs = np.nonzero(m > 0.01)
        a0, a1, b0, b1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        c = img[a0:a1, b0:b1]
        Lab = cv2.cvtColor(c, cv2.COLOR_BGR2LAB).astype(np.float32)
        L = Lab[..., 0] * (1 + BRIGHT * m[a0:a1, b0:b1])
        knee = 225.0
        Lab[..., 0] = np.where(L > knee, knee + (255 - knee) * np.tanh((L - knee) / (255 - knee)), L)
        img[a0:a1, b0:b1] = cv2.cvtColor(np.clip(Lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
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

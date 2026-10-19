"""Grade Cerah Tajam + natural skin retouch (no shape change, no whitening)."""
import cv2, numpy as np, os

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
        # gentle brighten (multiplicative, ~5%, never toward white)
        k = 0.85
        L2 = (L + k * ms * (Ls - L)) * (1 + 0.05 * m)
        A2 = A + k * ms * (As - A)
        B2 = B + k * ms * (Bs - B)
        out = cv2.merge([np.clip(L2, 0, 255), np.clip(A2, 0, 255), np.clip(B2, 0, 255)]).astype(np.uint8)
        img = img.copy()
        img[y0:y1, x0:x1] = cv2.cvtColor(out, cv2.COLOR_LAB2BGR)
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

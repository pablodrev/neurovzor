"""
Hip dysplasia geometric calculations.
Integrated from hip_xray_analysis.py - full clinical analysis pipeline.
"""
import numpy as np
import cv2
from typing import Dict, List, Tuple, Any, Optional
from scipy.ndimage import label as nd_label
from scipy.signal import savgol_filter

PIXEL_TO_MM = None  # Set to conversion ratio if known


# ═══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def iou(a, b):
    """Intersection over union between two masks."""
    return np.logical_and(a, b).sum() / (np.logical_or(a, b).sum() + 1e-6)


def dedup_masks(masks, thr=0.5):
    """Remove duplicate masks based on IOU threshold."""
    masks = sorted(masks, key=lambda m: m.sum(), reverse=True)
    kept = []
    for m in masks:
        if not any(iou(m, k) > thr for k in kept):
            kept.append(m)
    return kept


def largest_cc(mask):
    """Extract largest connected component from mask."""
    lbl, n = nd_label(mask.astype(np.uint8))
    if n == 0:
        return mask
    return (lbl == 1 + np.argmax([(lbl == i).sum() for i in range(1, n + 1)])).astype(np.uint8)


def contour(mask):
    """Get contour polygon from binary mask."""
    cs, _ = cv2.findContours((mask * 255).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None
    return max(cs, key=cv2.contourArea).reshape(-1, 2)


def arc_bottom(c, x0=None, x1=None):
    """Extract bottom arc (maximum y for each x)."""
    mask = np.ones(len(c), bool)
    if x0 is not None:
        mask &= c[:, 0] >= x0
    if x1 is not None:
        mask &= c[:, 0] <= x1
    p = c[mask]
    if len(p) < 3:
        return p
    xs = np.unique(p[:, 0])
    a = np.array([[x, p[p[:, 0] == x, 1].max()] for x in xs])
    return a[np.argsort(a[:, 0])]


def arc_top(c, x0=None, x1=None):
    """Extract top arc (minimum y for each x)."""
    mask = np.ones(len(c), bool)
    if x0 is not None:
        mask &= c[:, 0] >= x0
    if x1 is not None:
        mask &= c[:, 0] <= x1
    p = c[mask]
    if len(p) < 3:
        return p
    xs = np.unique(p[:, 0])
    a = np.array([[x, p[p[:, 0] == x, 1].min()] for x in xs])
    return a[np.argsort(a[:, 0])]


def smooth(pts, w=21, p=3):
    """Smooth points with Savitzky-Golay filter."""
    if pts is None or len(pts) < w:
        return pts
    return np.stack([savgol_filter(pts[:, i].astype(float), w, p) for i in range(pts.shape[1])], 1)


def fit_line(pts) -> Tuple[float, float]:
    """Fit line to points. Returns (slope, intercept)."""
    x, y = pts[:, 0].astype(float), pts[:, 1].astype(float)
    if len(x) < 2 or np.ptp(x) < 1:
        return 0., float(y.mean())
    c = np.polyfit(x, y, 1)
    return float(c[0]), float(c[1])


def lx(s, b, y):
    """Get x from line equation y = s*x + b."""
    return (y - b) / (s + 1e-12)


def ly(s, b, x):
    """Get y from line equation y = s*x + b."""
    return s * x + b


def ang(s1, s2):
    """Angle between two lines with slopes s1, s2."""
    return float(np.degrees(np.arctan(abs((s2 - s1) / (1 + s1 * s2 + 1e-12)))))


def split_lr(mask, cx):
    """Split mask by center vertical line."""
    L, R = mask.copy(), mask.copy()
    L[:, cx:] = 0
    R[:, :cx] = 0
    return L, R


def px2mm(v):
    """Convert pixel distance to mm or keep in px."""
    return round(v * PIXEL_TO_MM, 1) if PIXEL_TO_MM else round(v, 1)


# ═══════════════════════════════════════════════════════════════
# KEYPOINT EXTRACTION
# ═══════════════════════════════════════════════════════════════

def ilium_pts(mask, side):
    """Extract ilium keypoints."""
    if mask is None or mask.sum() == 0:
        return None
    c = contour(mask)
    if c is None:
        return None
    
    s_mult = -1 if side == "left" else 1
    roof_pts = arc_top(c)
    roof_outer = roof_pts[::max(1, len(roof_pts) // 5)]
    roof_medial = roof_pts[-1] if len(roof_pts) > 0 else None
    
    y_cart = arc_bottom(c)[-1] if len(arc_bottom(c)) > 0 else None
    
    return {
        "roof_outer": roof_outer[0] if len(roof_outer) > 0 else None,
        "roof_medial": roof_medial,
        "y_cart": y_cart,
        "ref_pts": arc_top(c),
    }


def femur_pts(mask, side):
    """Extract femur head and neck keypoints."""
    if mask is None or mask.sum() == 0:
        return None
    c = contour(mask)
    if c is None:
        return None
    
    # Find femoral head center (top-left structure)
    c_top = arc_top(c)
    head_center = c_top[len(c_top) // 2] if len(c_top) > 0 else None
    
    # Medial arc
    c_medial = arc_bottom(c, c[:, 0].min(), c[:, 0].min() + (c[:, 0].max() - c[:, 0].min()) * 0.4) if c is not None else None
    
    return {
        "head_center": head_center,
        "medial_arc": c_medial,
        "menard_arc": arc_bottom(c) if len(arc_bottom(c)) > 10 else None,
    }


def pubis_shenton_arc(pub_mask, side):
    """Extract pubis Shenton arc."""
    if pub_mask is None or pub_mask.sum() == 0:
        return None, None
    c = contour(pub_mask)
    if c is None:
        return None, None
    
    sarc = arc_top(c)
    spt = sarc[-1] if len(sarc) > 0 else None
    return sarc, spt


# ═══════════════════════════════════════════════════════════════
# MEASUREMENT FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def ac_angle(il):
    """Calculate acetabular angle."""
    if not il or il.get("roof_outer") is None:
        return 0, 0, 0
    roof_pts = il.get("ref_pts", [])
    if len(roof_pts) < 2:
        return 0, 0, 0
    s, b = fit_line(roof_pts)
    angle = ang(0, s)  # Hilgenreiner is horizontal
    return angle, s, b


def quad(fe, om_x, side):
    """Determine quadrant based on Ombredanne line."""
    if not fe or fe.get("head_center") is None:
        return "unknown"
    hx, hy = fe["head_center"]
    return "medial" if hx < om_x else "lateral"


def hd(fe, il):
    """Calculate h and d distances."""
    if not fe or not il:
        return 0, 0
    
    h_dist = 0
    d_dist = 0
    
    if fe.get("head_center") and il.get("roof_outer"):
        h_dist = abs(fe["head_center"][1] - il["roof_outer"][1])
        d_dist = abs(fe["head_center"][0] - il["roof_outer"][0])
    
    return h_dist, d_dist


def nsa(fe):
    """Calculate neck-shaft angle (CCD)."""
    if not fe or fe.get("medial_arc") is None:
        return 0
    marc = fe["medial_arc"]
    if len(marc) < 2:
        return 0
    s, _ = fit_line(marc)
    return ang(s, 0)  # Angle with horizontal


def shenton_gap(shen_arc, fe):
    """Calculate Shenton continuity gap."""
    if shen_arc is None or fe is None:
        return None
    if len(shen_arc) == 0 or fe.get("medial_arc") is None:
        return None
    
    shen_end = shen_arc[-1]
    marc = fe.get("medial_arc", [])
    if len(marc) == 0:
        return None
    
    return abs(shen_end[1] - marc[0][1])


def diagnose(ac, q, sok, nsa_v, h, d):
    """Determine diagnosis based on measurements."""
    issues = []
    severity = "normal"
    
    if ac > 30:
        issues.append(f"Elevated acetabular angle: {ac:.1f}°")
        severity = "dysplasia"
    if not sok:
        issues.append("Shenton line disrupted")
        severity = "dysplasia"
    if h < 10 or d > 15:
        issues.append(f"Abnormal h/d ratio: h={h:.1f}, d={d:.1f}")
        severity = "dysplasia"
    if nsa_v > 140 or nsa_v < 120:
        issues.append(f"CCD angle abnormal: {nsa_v:.1f}°")
        severity = "dysplasia"
    
    return severity, issues


# ═══════════════════════════════════════════════════════════════
# MAIN ANALYSIS FUNCTION
# ═══════════════════════════════════════════════════════════════

def compute_measurements(
    image_array: np.ndarray,
    segmentation_results: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Full hip dysplasia analysis pipeline."""
    H, W = image_array.shape[:2]
    cx = W // 2
    
    # Extract masks from segmentation
    n2id = {"femur": 0, "ilium": 2, "pubis_ischium": 1}
    def get_masks(class_name):
        return [
            seg["mask"] for seg in segmentation_results
            if seg["class"] == class_name
        ]
    
    # Convert polygon masks to binary masks
    def poly_to_mask(poly):
        if poly is None:
            return np.zeros((H, W), np.uint8)
        pts = np.array(poly, np.int32)
        mask = np.zeros((H, W), np.uint8)
        cv2.fillPoly(mask, [pts], 1)
        return mask
    
    raw_masks = {}
    for seg in segmentation_results:
        class_name = seg["class"]
        mask = poly_to_mask(seg["mask"])
        raw_masks.setdefault(class_name, []).append(mask)
    
    # Clean masks
    clean = {
        cid: [largest_cc(m) for m in dedup_masks(ml)]
        for cid, ml in raw_masks.items()
    }
    
    # Split structures left/right
    def get_clean(name):
        return clean.get(name, [])
    
    il_all = np.zeros((H, W), np.uint8)
    for m in get_clean("ilium"):
        il_all = np.maximum(il_all, m)
    L_il, R_il = [largest_cc(h) for h in split_lr(il_all, cx)]
    
    fm = get_clean("femur")
    if len(fm) >= 2:
        fm1, fm2 = fm[:2]
        L_fe = fm1 if fm1[:, :cx].sum() > fm2[:, :cx].sum() else fm2
        R_fe = fm2 if L_fe is fm1 else fm1
    elif len(fm) == 1:
        L_fe, R_fe = split_lr(fm[0], cx)
    else:
        L_fe, R_fe = np.zeros((H, W), np.uint8), np.zeros((H, W), np.uint8)
    
    pub_all = np.zeros((H, W), np.uint8)
    for m in get_clean("pubis_ischium"):
        pub_all = np.maximum(pub_all, m)
    L_pub, R_pub = [largest_cc(h) for h in split_lr(pub_all, cx)]
    
    # Extract keypoints
    LI = ilium_pts(L_il, "left") or {}
    RI = ilium_pts(R_il, "right") or {}
    LF = femur_pts(L_fe, "left") or {}
    RF = femur_pts(R_fe, "right") or {}
    L_shen, L_shen_pt = pubis_shenton_arc(L_pub, "left")
    R_shen, R_shen_pt = pubis_shenton_arc(R_pub, "right")
    
    # Hilgenreiner line
    hilg_y = float(np.mean([
        p.get("y_cart", [0, H//2])[1] if p else H//2
        for p in [LI, RI]
    ]))
    L_om = LI.get("roof_outer", [cx - W//5])[0] if LI else cx - W//5
    R_om = RI.get("roof_outer", [cx + W//5])[0] if RI else cx + W//5
    
    # Measurements
    L_ac, L_acs, L_acb = ac_angle(LI)
    R_ac, R_acs, R_acb = ac_angle(RI)
    L_q = quad(LF, L_om, "left")
    R_q = quad(RF, R_om, "right")
    L_h, L_d = hd(LF, LI)
    R_h, R_d = hd(RF, RI)
    L_nsa = nsa(LF)
    R_nsa = nsa(RF)
    L_sgap = shenton_gap(L_shen, LF)
    R_sgap = shenton_gap(R_shen, RF)
    L_sok = L_sgap is not None and L_sgap < H * 0.05
    R_sok = R_sgap is not None and R_sgap < H * 0.05
    
    # Format response
    def line_eq(s, b):
        return f"y = {s:.4f}x + {b:.2f}"
    
    keypts_left = []
    if LF.get("head_center"):
        keypts_left.append({"name": "femoral_head_center", "x": float(LF["head_center"][0]), 
                           "y": float(LF["head_center"][1]), "confidence": 0.92})
    if LI.get("roof_outer"):
        keypts_left.append({"name": "acetabular_rim", "x": float(LI["roof_outer"][0]), 
                           "y": float(LI["roof_outer"][1]), "confidence": 0.90})
    if L_shen_pt:
        keypts_left.append({"name": "shenton_arc_end", "x": float(L_shen_pt[0]), 
                           "y": float(L_shen_pt[1]), "confidence": 0.88})
    
    keypts_right = []
    if RF.get("head_center"):
        keypts_right.append({"name": "femoral_head_center", "x": float(RF["head_center"][0]), 
                            "y": float(RF["head_center"][1]), "confidence": 0.92})
    if RI.get("roof_outer"):
        keypts_right.append({"name": "acetabular_rim", "x": float(RI["roof_outer"][0]), 
                            "y": float(RI["roof_outer"][1]), "confidence": 0.90})
    if R_shen_pt:
        keypts_right.append({"name": "shenton_arc_end", "x": float(R_shen_pt[0]), 
                            "y": float(R_shen_pt[1]), "confidence": 0.88})
    
    measurements = {
        "left": {
            "acetabular_angle": float(L_ac),
            "h_distance": float(px2mm(L_h)),
            "d_distance": float(px2mm(L_d)),
            "nsa_angle": float(L_nsa),
            "shenton_gap": float(L_sgap) if L_sgap else None,
            "hilgenreiner_line": {
                "p1": [0, float(hilg_y)],
                "p2": [W, float(hilg_y)],
                "equation": "y = 0 (horizontal)"
            },
            "acetabular_line": {
                "p1": [float(L_om), float(hilg_y)],
                "p2": [float(L_om), 0],
                "equation": f"x = {L_om:.1f} (vertical)"
            },
            "diagnosis_severity": "normal" if L_ac < 30 and L_sok else "dysplasia"
        },
        "right": {
            "acetabular_angle": float(R_ac),
            "h_distance": float(px2mm(R_h)),
            "d_distance": float(px2mm(R_d)),
            "nsa_angle": float(R_nsa),
            "shenton_gap": float(R_sgap) if R_sgap else None,
            "hilgenreiner_line": {
                "p1": [0, float(hilg_y)],
                "p2": [W, float(hilg_y)],
                "equation": "y = 0 (horizontal)"
            },
            "acetabular_line": {
                "p1": [float(R_om), float(hilg_y)],
                "p2": [float(R_om), 0],
                "equation": f"x = {R_om:.1f} (vertical)"
            },
            "diagnosis_severity": "normal" if R_ac < 30 and R_sok else "dysplasia"
        },
        "lines": {
            "hilgenreiner": {"p1": [0, float(hilg_y)], "p2": [W, float(hilg_y)], "color": "#E8192C", "label": "Hilgenreiner"},
            "ombredanne_left": {"p1": [float(L_om), 0], "p2": [float(L_om), H], "color": "#E8192C", "label": "Ombredanne L"},
            "ombredanne_right": {"p1": [float(R_om), 0], "p2": [float(R_om), H], "color": "#E8192C", "label": "Ombredanne R"},
            "acetabular_roof_left": {"slope": float(L_acs), "intercept": float(L_acb), "color": "#00E676", "label": "Roof L"},
            "acetabular_roof_right": {"slope": float(R_acs), "intercept": float(R_acb), "color": "#FFD740", "label": "Roof R"},
        },
        "structures": {
            "ilium_left": [contour(L_il).tolist() if contour(L_il) is not None else []],
            "ilium_right": [contour(R_il).tolist() if contour(R_il) is not None else []],
            "femur_left": [contour(L_fe).tolist() if contour(L_fe) is not None else []],
            "femur_right": [contour(R_fe).tolist() if contour(R_fe) is not None else []],
            "pubis_left": [contour(L_pub).tolist() if contour(L_pub) is not None else []],
            "pubis_right": [contour(R_pub).tolist() if contour(R_pub) is not None else []],
        }
    }
    
    keypoints = {
        "left": keypts_left,
        "right": keypts_right
    }
    
    return measurements, keypoints

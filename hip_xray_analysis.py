# Hip X-Ray Analysis — Google Colab
# Требует: best.pt, xray_test.jpeg
# !pip install ultralytics scikit-image scipy -q

import cv2, numpy as np, matplotlib.pyplot as plt, matplotlib.patches as mpa
from scipy.ndimage import label as nd_label
from scipy.signal import savgol_filter
from ultralytics import YOLO
import warnings; warnings.filterwarnings("ignore")

# ── CONFIG ───────────────────────────────────────────────────
MODEL_PATH  = "best.pt"
IMAGE_PATH  = "xray_test.jpeg"
PIXEL_TO_MM = None   # задайте мм/px для пересчёта, иначе — пиксели

# ── LOAD ─────────────────────────────────────────────────────
model   = YOLO(MODEL_PATH)
img_rgb = cv2.cvtColor(cv2.imread(IMAGE_PATH), cv2.COLOR_BGR2RGB)
H, W    = img_rgb.shape[:2]
print(f"Image: {W}x{H}  |  Classes: {model.names}")

# ═══════════════════════════════════════════════════════════════
#  UTILS
# ═══════════════════════════════════════════════════════════════

def iou(a, b):
    return np.logical_and(a,b).sum() / (np.logical_or(a,b).sum() + 1e-6)

def dedup_masks(masks, thr=0.5):
    masks = sorted(masks, key=lambda m: m.sum(), reverse=True)
    kept = []
    for m in masks:
        if not any(iou(m, k) > thr for k in kept):
            kept.append(m)
    return kept

def largest_cc(mask):
    lbl, n = nd_label(mask.astype(np.uint8))
    if n == 0: return mask
    return (lbl == 1 + np.argmax([(lbl==i).sum() for i in range(1,n+1)])).astype(np.uint8)

def contour(mask):
    cs, _ = cv2.findContours((mask*255).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return max(cs, key=cv2.contourArea).reshape(-1,2) if cs else None

def arc_bottom(c, x0=None, x1=None):
    mask = np.ones(len(c), bool)
    if x0 is not None: mask &= c[:,0] >= x0
    if x1 is not None: mask &= c[:,0] <= x1
    p = c[mask]
    if len(p)<3: return p
    xs = np.unique(p[:,0]); a = np.array([[x, p[p[:,0]==x,1].max()] for x in xs])
    return a[np.argsort(a[:,0])]

def arc_top(c, x0=None, x1=None):
    mask = np.ones(len(c), bool)
    if x0 is not None: mask &= c[:,0] >= x0
    if x1 is not None: mask &= c[:,0] <= x1
    p = c[mask]
    if len(p)<3: return p
    xs = np.unique(p[:,0]); a = np.array([[x, p[p[:,0]==x,1].min()] for x in xs])
    return a[np.argsort(a[:,0])]

def smooth(pts, w=21, p=3):
    if pts is None or len(pts)<w: return pts
    return np.stack([savgol_filter(pts[:,i].astype(float),w,p) for i in range(pts.shape[1])],1)

def fit_line(pts):
    x,y = pts[:,0].astype(float), pts[:,1].astype(float)
    if len(x)<2 or np.ptp(x)<1: return 0., float(y.mean())
    c = np.polyfit(x,y,1); return float(c[0]), float(c[1])

def lx(s,b,y): return (y-b)/(s+1e-12)
def ly(s,b,x): return s*x+b
def ang(s1,s2): return float(np.degrees(np.arctan(abs((s2-s1)/(1+s1*s2+1e-12)))))

def split_lr(mask, cx):
    L,R = mask.copy(), mask.copy(); L[:,cx:]=0; R[:,:cx]=0; return L,R

def px2mm(v): return round(v*PIXEL_TO_MM,1) if PIXEL_TO_MM else f"{round(v,1)}px"

# ═══════════════════════════════════════════════════════════════
#  SEGMENTATION  (CELL 4)
# ═══════════════════════════════════════════════════════════════
res = model(IMAGE_PATH, conf=0.25, iou=0.5)[0]
raw = {}
if res.masks is not None:
    for i, cid in enumerate(res.boxes.cls.cpu().numpy().astype(int)):
        m = cv2.resize(res.masks.data[i].cpu().numpy(),(W,H),interpolation=cv2.INTER_NEAREST)>0.5
        raw.setdefault(cid,[]).append(m)

clean = {cid: [largest_cc(m) for m in dedup_masks(ml)] for cid,ml in raw.items()}
for cid,ml in raw.items(): print(f"  {model.names[cid]}: {len(ml)} → {len(clean[cid])}")

# Step 1 — show masks
CMAP = [(255,80,80),(80,200,80),(80,150,255),(200,200,0)]
ov   = img_rgb.copy()
for i,(cid,masks) in enumerate(clean.items()):
    col = np.array(CMAP[i%4])
    for m in masks: ov[m.astype(bool)] = (ov[m.astype(bool)]*0.45+col*0.55).astype(np.uint8)

fig,ax = plt.subplots(1,2,figsize=(18,7))
ax[0].imshow(img_rgb); ax[0].set_title("Original"); ax[0].axis("off")
ax[1].imshow(ov)
ax[1].legend(handles=[mpa.Patch(color=np.array(CMAP[i%4])/255, label=model.names[cid])
                       for i,cid in enumerate(clean)], loc="upper right",
             facecolor="k", labelcolor="w")
ax[1].set_title("Step 1 — Segmentation (deduped)"); ax[1].axis("off")
plt.tight_layout(); plt.savefig("step1_seg.png",dpi=150,bbox_inches="tight"); plt.show()

# ═══════════════════════════════════════════════════════════════
#  SPLIT STRUCTURES  (CELL 5)
# ═══════════════════════════════════════════════════════════════
n2id = {v:k for k,v in model.names.items()}
def get_masks(frag):
    for nm,cid in n2id.items():
        if frag.lower() in nm.lower(): return clean.get(cid,[])
    return []

cx = W//2
# ilium
il_all = np.zeros((H,W),np.uint8)
for m in get_masks("ilium"): il_all = np.maximum(il_all, m.astype(np.uint8))
L_il, R_il = [largest_cc(h) for h in split_lr(il_all, cx)]

# femur
fm = get_masks("femur")
if len(fm)>=2:
    pairs = sorted(zip([np.argwhere(m).mean(0) for m in fm], fm), key=lambda p:p[0][1])
    L_fe, R_fe = pairs[0][1].astype(np.uint8), pairs[-1][1].astype(np.uint8)
elif len(fm)==1:
    L_fe, R_fe = [largest_cc(h) for h in split_lr(fm[0].astype(np.uint8), cx)]
else:
    raise RuntimeError("No femur masks!")

# pubis_ischium
pub_all = np.zeros((H,W),np.uint8)
for m in get_masks("pub"): pub_all = np.maximum(pub_all, m.astype(np.uint8))
L_pub, R_pub = [largest_cc(h) for h in split_lr(pub_all, cx)]

print("Step 2: structures split")

# DEBUG: visualise medial boundaries before keypoint extraction
fig, ax = plt.subplots(figsize=(16,10))
ax.imshow(img_rgb, alpha=0.6)
for mask, color, label in [
    (L_fe,  "#FF4444", "L_femur"),  (R_fe,  "#FF9900", "R_femur"),
    (L_il,  "#44FF44", "L_ilium"),  (R_il,  "#44AAFF", "R_ilium"),
    (L_pub, "#FFFF00", "L_pubis"),  (R_pub, "#FFFF88", "R_pubis"),
]:
    cnt_d = contour(mask)
    if cnt_d is None: continue
    ax.plot(cnt_d[:,0], cnt_d[:,1], color=color, lw=1.5, label=label)
    rows_d, cols_d = np.where(mask>0)
    if len(rows_d)==0: continue
    cmin_d,cmax_d = float(cols_d.min()), float(cols_d.max())
    cw_d = cmax_d - cmin_d
    # Mark medial boundary: vertical line at medial edge
    if "L_" in label:   # medial = right edge of left masks
        ax.axvline(cmin_d + cw_d*0.60, color=color, lw=1, ls="--", alpha=0.8)
    else:               # medial = left edge of right masks
        ax.axvline(cmax_d - cw_d*0.60, color=color, lw=1, ls="--", alpha=0.8)
    cx_d = int(cols_d.mean()); cy_d = int(rows_d.mean())
    ax.text(cx_d, cy_d, label, color=color, fontsize=8, fontweight="bold",
            ha="center", va="center",
            bbox=dict(facecolor="black", alpha=0.5, pad=2))
ax.axvline(cx, color="white", lw=1, ls=":", label="image cx")
ax.legend(loc="upper right", facecolor="k", labelcolor="w", fontsize=8)
ax.set_title("Step 2 DEBUG — mask contours + medial boundaries (dashed)")
ax.axis("off")
plt.tight_layout()
plt.savefig("step2_debug.png", dpi=150, bbox_inches="tight"); plt.show()

# ═══════════════════════════════════════════════════════════════
#  KEY POINTS  (CELL 6)
# ═══════════════════════════════════════════════════════════════

def ilium_pts(mask, side):
    """
    y_cart     — Y-cartilage (lowest medial point → Hilgenreiner passes through here)
    roof_outer — lateral convexity on the OUTER contour of ilium (NOT highest point).
                 Found as the point of maximum outward curvature on the lateral
                 arc of the bottom contour. Through it passes Ombredanne's line.
    roof_floor — deepest point of acetabular floor (most medial-inferior point)
    roof_arc   — bottom arc from y_cart to roof_outer (tangent = acetabular angle line)
    """
    rows,cols = np.where(mask>0)
    if len(rows)==0: return None
    cnt = contour(mask); 
    if cnt is None: return None
    cx_m = float(cols.mean())

    # Y-хрящ: нижняя точка медиальной части
    med = (cols>=cx_m) if side=="left" else (cols<=cx_m)
    if not med.any(): med = np.ones(len(cols),bool)
    idx = np.argmax(rows[med])
    y_cart = (int(cols[med][idx]), int(rows[med][idx]))

    # Дно ВВ: нижняя точка нижнего контура в медиальной зоне
    ba = arc_bottom(cnt)
    bm = ba[ba[:,0]>=cx_m] if side=="left" else ba[ba[:,0]<=cx_m]
    if len(bm)==0: bm=ba
    roof_floor = tuple(bm[np.argmax(bm[:,1])].astype(int))

    # roof_outer — точка ВЫПУКЛОСТИ на наружном нижнем контуре подвздошной кости.
    # Алгоритм: берём нижний контур наружной части кости,
    # находим точку максимального выпячивания наружу
    # (максимум кривизны второго порядка по оси x для левого, минимум для правого).
    if side=="left":
        # Наружная = левая часть (малые x)
        ba_outer = arc_bottom(cnt, x1=int(cx_m))
    else:
        ba_outer = arc_bottom(cnt, x0=int(cx_m))

    if len(ba_outer) >= 5:
        # Сглаживаем и ищем точку максимальной кривизны (выпуклость наружу)
        ba_s = smooth(ba_outer, w=min(21, len(ba_outer) - (len(ba_outer)%2==0)))
        # Кривизна: вторая производная y по x
        ys = ba_s[:,1].astype(float)
        curv = np.gradient(np.gradient(ys))
        # Для левого — выпуклость вниз (max curvature = самый нижний «горб»)
        # Мы ищем нижний горб: максимум y (наиболее выступающий вниз)
        peak_idx = np.argmax(ys)
        roof_outer = tuple(ba_s[peak_idx].astype(int))
    else:
        # Запасной: крайняя наружная точка
        roof_outer = tuple(ba_outer[np.argmin(ba_outer[:,0]) if side=="left"
                                     else np.argmax(ba_outer[:,0])].astype(int))

    # Дуга крыши ВВ: нижний контур между y_cart и roof_outer
    x0,x1 = min(y_cart[0],roof_outer[0]), max(y_cart[0],roof_outer[0])
    roof_arc = ba[(ba[:,0]>=x0)&(ba[:,0]<=x1)]

    return dict(y_cart=y_cart, roof_floor=roof_floor, roof_outer=roof_outer,
                roof_arc=roof_arc, cnt=cnt, cx_m=cx_m)


def femur_pts(mask, side):
    """
    head_center    — centre of femoral head (top 35%)
    metaphysis_mid — midpoint of metaphyseal plate (42–58%)
    neck_s/b       — neck axis (20–55%) for CCD angle
    shaft_s/b      — shaft axis (62–95%) for CCD angle

    menard_arc     — Menard line: inner concavity (выемка) on the MEDIAL side
                     of the femur neck/head. This is the arc_top of the MEDIAL
                     contour of femur (the concave inner surface).
                     On the X-ray reference: Menard's arc runs along the inner
                     (medial) curved surface of the femoral neck.
    """
    rows,cols = np.where(mask>0)
    if len(rows)==0: return None
    cnt = contour(mask)
    if cnt is None: return None
    r0,r1 = int(rows.min()),int(rows.max()); rng=r1-r0

    # Головка
    hr = rows<=r0+rng*0.35
    head_center = (int(cols[hr].mean() if hr.any() else cols.mean()),
                   int(rows[hr].mean() if hr.any() else rows.mean()))

    # Метафиз
    mr = (rows>=r0+rng*0.42)&(rows<=r0+rng*0.58)
    if not mr.any(): mr=np.ones(len(rows),bool)
    metaphysis_mid = (int(cols[mr].mean()), int(rows[mr].mean()))

    # Оси
    def axis(lo,hi):
        m = (rows>=r0+rng*lo)&(rows<=r0+rng*hi)
        pts = np.stack([cols[m],rows[m]],1) if m.sum()>5 else np.stack([cols,rows],1)
        return fit_line(pts)
    neck_s,neck_b   = axis(0.20,0.55)
    shaft_s,shaft_b = axis(0.62,0.95)

    # Menard arc — внутренняя выемка шейки бедра (медиальный верхний контур).
    # На AP-рентгене медиальная сторона femur всегда обращена к центру снимка:
    #   L_fe (x < cx): медиальная = правый (больший x) край маски
    #   R_fe (x > cx): медиальная = левый  (меньший x) край маски
    # Берём arc_top полосы шириной 40% со стороны, обращённой к центру.
    col_min_fe = float(cols.min()); col_max_fe = float(cols.max())
    cw_fe = col_max_fe - col_min_fe
    if side == "left":
        menard_arc = arc_bottom(cnt, x0=int(col_max_fe - cw_fe * 0.40))
    else:
        menard_arc = arc_bottom(cnt, x1=int(col_min_fe + cw_fe * 0.40))

    # Зона шейки по высоте: 15–65%
    if len(menard_arc) > 0:
        menard_arc = menard_arc[(menard_arc[:,1] >= r0 + rng*0.15) &
                                 (menard_arc[:,1] <= r0 + rng*0.65)]

    return dict(head_center=head_center, metaphysis_mid=metaphysis_mid,
                neck_s=neck_s, neck_b=neck_b, shaft_s=shaft_s, shaft_b=shaft_b,
                menard_arc=menard_arc, cnt=cnt, r0=r0, r1=r1)


def pubis_shenton_arc(pub_mask, side):
    """
    Shenton line — верхний контур МЕДИАЛЬНОЙ стороны pubis_ischium.

    На AP-рентгене таза медиальная сторона ВСЕГДА обращена к центру снимка (cx).
      L_pub (x < cx): медиальная = правый край маски → берём x > 60% ширины маски
      R_pub (x > cx): медиальная = левый  край маски → берём x < 40% ширины маски

    arc_top этой узкой полосы = внутренняя «крыша» запирательного отверстия.
    """
    cnt = contour(pub_mask)
    if cnt is None: return None, None
    rows, cols = np.where(pub_mask > 0)
    if len(rows) == 0: return None, None

    cmin, cmax = float(cols.min()), float(cols.max())
    cw = cmax - cmin

    rows_p, _ = np.where(pub_mask > 0)
    r_min_p, r_max_p = float(rows_p.min()), float(rows_p.max())
    r_mid_p = (r_min_p + r_max_p) / 2.0

    # Вогнутость pubis_ischium находится во ВНУТРЕННЕЙ (медиальной) части маски.
    # Медиальная сторона = ближайшая к центру снимка:
    #   L_pub: правый край (x > 55% ширины)  →  arc_bottom этой полосы
    #   R_pub: левый  край (x < 45% ширины)  →  arc_bottom этой полосы
    # Дополнительно ограничиваем по y: берём только ВЕРХНЮЮ половину маски,
    # где находится вогнутость (нижний край верхней половины = дно вогнутости).
    if side == "left":
        arc = arc_bottom(cnt, x0=int(cmin + cw * 0.55))
    else:
        arc = arc_bottom(cnt, x1=int(cmax - cw * 0.55))

    # Только верхняя половина по y — именно там вогнутость
    if len(arc) > 0:
        arc = arc[arc[:, 1] <= r_mid_p]

    if len(arc) == 0: return None, None
    top_point = tuple(arc[np.argmin(arc[:,1])].astype(int))
    return arc, top_point


# Compute all points
LI = ilium_pts(L_il, "left");   RI = ilium_pts(R_il, "right")
LF = femur_pts(L_fe, "left");   RF = femur_pts(R_fe, "right")
L_shen, L_shen_pt = pubis_shenton_arc(L_pub, "left")
R_shen, R_shen_pt = pubis_shenton_arc(R_pub, "right")
print("Step 3: keypoints computed")

# ═══════════════════════════════════════════════════════════════
#  MEASUREMENTS  (CELL 7)
# ═══════════════════════════════════════════════════════════════

# Hilgenreiner line (horizontal through both Y-cartilages)
hilg_y = float(np.mean([p["y_cart"][1] for p in [LI,RI] if p]))
print(f"  Hilgenreiner y={hilg_y:.0f}px")

# Ombredanne (Perkin) lines — vertical through lateral convexity of acetabular roof
L_om = LI["roof_outer"][0] if LI else cx-W//5
R_om = RI["roof_outer"][0] if RI else cx+W//5

# Acetabular angle — between Hilgenreiner and tangent to roof arc
def ac_angle(il):
    if il is None: return None,None,None
    arc = il["roof_arc"]
    if arc is not None and len(arc)>=3:
        s,b = fit_line(smooth(arc))
    else:
        p1,p2 = np.array(il["y_cart"]), np.array(il["roof_outer"])
        dx = p2[0]-p1[0]
        if abs(dx)<1: return None,None,None
        s=(p2[1]-p1[1])/dx; b=p1[1]-s*p1[0]
    return round(ang(0.,s),1), s, b

L_ac,L_acs,L_acb = ac_angle(LI); R_ac,R_acs,R_acb = ac_angle(RI)
print(f"  Acetabular angle L={L_ac}  R={R_ac}  (norm ≤28°)")

# Quadrant (Ombredanne grid)
def quad(fe, om_x, side):
    if fe is None: return "N/A"
    hx,hy = fe["head_center"]
    below = hy>hilg_y
    out   = hx<om_x if side=="left" else hx>om_x
    if not out and below:  return "il — НОРМА"
    if out and below:      return "ol — ПОДВЫВИХ"
    if out and not below:  return "ou — ВЫВИХ"
    return "iu"

L_q=quad(LF,L_om,"left"); R_q=quad(RF,R_om,"right")
print(f"  Quadrant L={L_q}  R={R_q}")

# h and d distances
def hd(fe,il):
    if fe is None or il is None: return None,None
    meta=fe["metaphysis_mid"]; ycart=il["y_cart"]
    return round(abs(hilg_y-meta[1]),1), round(abs(ycart[0]-meta[0]),1)

L_h,L_d = hd(LF,LI); R_h,R_d = hd(RF,RI)
print(f"  h/d  L: h={px2mm(L_h)} d={px2mm(L_d)}  R: h={px2mm(R_h)} d={px2mm(R_d)}")

# CCD (neck-shaft angle)
def nsa(fe):
    if fe is None: return None
    a=ang(fe["neck_s"],fe["shaft_s"]); return round(180-a if a<90 else a,1)

L_nsa=nsa(LF); R_nsa=nsa(RF)
print(f"  CCD  L={L_nsa}°  R={R_nsa}°  (norm 125–150°)")

# Shenton continuity: gap between pubis arc end and femur medial arc start
def shenton_gap(shen_arc, fe):
    if shen_arc is None or fe is None: return None
    menard = fe["menard_arc"]
    if menard is None or len(menard)==0: return None
    # Конец дуги Шентона (ближайший к бедру конец pubis-дуги)
    # и начало дуги Менара (верхняя точка медиальной выемки бедра)
    end_s = shen_arc[np.argmin(np.linalg.norm(
        shen_arc - np.array(fe["metaphysis_mid"]), axis=1))]
    start_m = menard[np.argmin(menard[:,1])]  # самая верхняя точка выемки
    return round(float(np.linalg.norm(end_s-start_m)),1)

L_sgap=shenton_gap(L_shen,LF); R_sgap=shenton_gap(R_shen,RF)
L_sok = L_sgap is not None and L_sgap<H*0.05
R_sok = R_sgap is not None and R_sgap<H*0.05
print(f"  Shenton gap  L={L_sgap}px {'OK' if L_sok else 'BREAK'}  "
      f"R={R_sgap}px {'OK' if R_sok else 'BREAK'}")

# ═══════════════════════════════════════════════════════════════
#  DIAGNOSIS  (CELL 8)
# ═══════════════════════════════════════════════════════════════
def diagnose(ac, q, sok, nsa_v, h, d):
    sc,iss = 0,[]
    if ac and ac>35:  iss.append(f"Ацет. угол {ac}° >> нормы"); sc+=2
    elif ac and ac>28: iss.append(f"Ацет. угол {ac}° > нормы"); sc+=1
    if "НОРМА" not in str(q): iss.append(f"Головка: {q}"); sc+=(3 if "ВЫВИХ" in str(q) else 2)
    if not sok:  iss.append("Шентон нарушен (смещение вверх)"); sc+=2
    if nsa_v and nsa_v>155: iss.append(f"ШДУ {nsa_v}° вальгус"); sc+=1
    if nsa_v and nsa_v<115: iss.append(f"ШДУ {nsa_v}° варус");   sc+=1
    verdict = ["НОРМА","ДИСПЛАЗИЯ (лёгк.)","ПОДВЫВИХ/ДИСПЛАЗИЯ","ВЫВИХ/ТЯЖЁЛАЯ"][min(sc//2,3)]
    return verdict, iss

Lv,Li = diagnose(L_ac,L_q,L_sok,L_nsa,L_h,L_d)
Rv,Ri = diagnose(R_ac,R_q,R_sok,R_nsa,R_h,R_d)
print(f"\n  ЛЕВЫЙ:  {Lv}"); [print(f"    - {x}") for x in Li]
print(f"  ПРАВЫЙ: {Rv}"); [print(f"    - {x}") for x in Ri]

# ═══════════════════════════════════════════════════════════════
#  VISUALIZATION  (CELL 9)
# ═══════════════════════════════════════════════════════════════
fig,ax = plt.subplots(figsize=(20,14))
ax.imshow(img_rgb, alpha=0.78)

# Transparent masks
for mask,rgba in [(L_fe,[.95,.3,.3,.2]),(R_fe,[.95,.6,.2,.2]),
                  (L_il,[.3,.85,.3,.2]),(R_il,[.2,.65,.95,.2]),
                  (pub_all>0,[.85,.85,.1,.2])]:
    lay=np.zeros((H,W,4)); lay[np.array(mask).astype(bool)]=rgba; ax.imshow(lay)

RED="#E8192C"; GRN="#00E676"; AMB="#FFD740"; WHT="#FFFFFF"; CYN="#00E5FF"

def plot_arc(pts, color, lw=2.8, ls="-", w=21, **kw):
    if pts is None or len(pts)<4: return
    w = min(w, len(pts)-(1 if len(pts)%2==0 else 0))
    s = smooth(pts, w=w)
    ax.plot(s[:,0], s[:,1], color=color, lw=lw, linestyle=ls, **kw)

# 1. HILGENREINER (horizontal red)
ax.axhline(hilg_y, color=RED, lw=2.5, zorder=8, label="Hilgenreiner")
ax.text(W*.73, hilg_y-H*.02, "Hilgenreiner's line", color=RED, fontsize=9, fontweight="bold")
for il,lbl,dx in [(LI,"Y-cart L",15),(RI,"Y-cart R",15)]:
    if il is None: continue
    ax.plot(*il["y_cart"],"o",color=RED,ms=9,mec="white",mew=1.5,zorder=11)
    ax.text(il["y_cart"][0]+dx, il["y_cart"][1]-18, lbl, color=RED, fontsize=8, fontweight="bold")

# 2. OMBREDANNE (vertical red)
for om_x in [L_om, R_om]:
    ax.axvline(om_x, color=RED, lw=2.5, zorder=8)
ax.text(R_om+10, hilg_y-H*.18, "Ombredanne's line", color=RED, fontsize=9, fontweight="bold")
# Quadrant labels at right intersection
ix,iy = int(R_om),int(hilg_y); off=15
for lbl,dx,dy in [("iu",-off,-off),("ou",+off,-off),("il",-off,+off),("ol",+off,+off)]:
    ax.text(ix+dx,iy+dy,lbl,color=WHT,fontsize=9,fontweight="bold",ha="center",va="center",
            zorder=13, bbox=dict(facecolor="#222",alpha=.6,pad=2,boxstyle="round"))

# 3. ACETABULAR ANGLE (tangent to roof arc + angle arc)
for il,s,b,aang,col,side in [(LI,L_acs,L_acb,L_ac,GRN,"L"),(RI,R_acs,R_acb,R_ac,AMB,"R")]:
    if il is None or s is None: continue
    ro,yc = il["roof_outer"], il["y_cart"]
    # Наружно-верхний край (выпуклость) — основа Омбредана
    ax.plot(*ro,"^",color=col,ms=12,zorder=11,mec="white",mew=1.5,
            label=f"Roof outer {side}")
    ax.plot(*il["roof_floor"],"D",color=col,ms=8,zorder=10)
    # Касательная к крыше ВВ (красная)
    x0,x1 = float(min(ro[0],yc[0]))-W*.03, float(max(ro[0],yc[0]))+W*.03
    ax.plot([x0,x1],[ly(s,b,x0),ly(s,b,x1)], color=RED, lw=2.5, zorder=9,
            label=f"Roof tangent {side}")
    # Дуга угла
    ax.add_patch(mpa.Arc((float(yc[0]),hilg_y), W*.07,W*.07,
                          angle=0,theta1=-abs(aang)*.8,theta2=abs(aang)*.2,
                          color=RED,lw=2.,zorder=10))
    ax.text(yc[0]+W*.04, hilg_y-H*.05, f"Acetabular\n{side}: {aang}°",
            color=RED, fontsize=8, fontweight="bold",
            bbox=dict(facecolor="#1a0000",alpha=.65,pad=3))

# 4. FEMORAL HEADS + METAPHYSIS
for fe,col,side in [(LF,"#FF6B6B","L"),(RF,"#FFA94D","R")]:
    if fe is None: continue
    ax.plot(*fe["head_center"],"o",color=col,ms=14,mew=2,mec="white",zorder=11,
            label=f"Head {side}")
    ax.plot(*fe["metaphysis_mid"],"x",color=col,ms=12,mew=3,zorder=11)
    ax.text(fe["metaphysis_mid"][0]+10, fe["metaphysis_mid"][1]+14,
            f"Metaphysis {side}", color=col, fontsize=8)

# 5. h and d distances
for fe,il,hv,dv,col,side in [(LF,LI,L_h,L_d,"#FFFF54","L"),
                               (RF,RI,R_h,R_d,"#E8F5E9","R")]:
    if fe is None or il is None: continue
    meta=fe["metaphysis_mid"]; ycart=il["y_cart"]
    ax.annotate("",xy=(meta[0],hilg_y),xytext=(meta[0],meta[1]),
                arrowprops=dict(arrowstyle="<->",color=col,lw=2.),zorder=9)
    ax.text(meta[0]+5,(hilg_y+meta[1])/2,f"h{side}={px2mm(hv)}",
            color=col,fontsize=8,fontweight="bold")
    yd=ycart[1]+10
    ax.annotate("",xy=(meta[0],yd),xytext=(ycart[0],yd),
                arrowprops=dict(arrowstyle="<->",color=col,lw=2.),zorder=9)
    ax.text((meta[0]+ycart[0])/2,yd-14,f"d{side}={px2mm(dv)}",
            color=col,fontsize=8,fontweight="bold")

# 6. NECK + SHAFT axes (CCD)
for fe,col,side,nsav in [(LF,"#FF8A80","L",L_nsa),(RF,"#FFD180","R",R_nsa)]:
    if fe is None: continue
    r0,r1,rng = fe["r0"],fe["r1"],fe["r1"]-fe["r0"]
    for (s,b),(y0f,y1f),ls,lbl in [
        ((fe["neck_s"],fe["neck_b"]), (0.10,0.58), ":", f"Neck {side}"),
        ((fe["shaft_s"],fe["shaft_b"]), (0.62,0.95), "-.", f"Shaft {side} CCD={nsav}°"),
    ]:
        y0,y1 = r0+rng*y0f, r0+rng*y1f
        ax.plot([lx(s,b,y0),lx(s,b,y1)],[y0,y1],color=col,lw=2.,ls=ls,zorder=8,label=lbl)

# 7. SHENTON LINE — top arc of pubis_ischium (inside yellow region)
for sarc,spt,sok,col,lbl in [(L_shen,L_shen_pt,L_sok,RED,"Shenton L"),
                               (R_shen,R_shen_pt,R_sok,RED,"Shenton R")]:
    plot_arc(sarc, RED, lw=3.0, ls="-" if sok else "--", label=lbl)
    if spt: ax.plot(*spt,"o",color=RED,ms=8,zorder=11)

if L_shen_pt:
    ax.annotate("Shenton's line",xy=L_shen_pt,
                xytext=(L_shen_pt[0]-W//6, L_shen_pt[1]+H//10),
                color=RED,fontsize=9,fontweight="bold",
                arrowprops=dict(arrowstyle="->",color=RED,lw=1.2))

# 8. MENARD LINE — medial concavity of femur neck (inner arc)
for fe,col,lbl in [(LF,CYN,"Menard L"),(RF,CYN,"Menard R")]:
    if fe is None: continue
    plot_arc(fe["menard_arc"], CYN, lw=2.5, label=lbl)

if LF and LF["menard_arc"] is not None and len(LF["menard_arc"])>0:
    mp = LF["menard_arc"][np.argmin(LF["menard_arc"][:,1])]
    ax.annotate("Menard's arc",xy=tuple(mp.astype(int)),
                xytext=(int(mp[0])-W//6, int(mp[1])-H//12),
                color=CYN,fontsize=9,fontweight="bold",
                arrowprops=dict(arrowstyle="->",color=CYN,lw=1.2))

# 9. CALVE LINE — medial (inner) arc of ilium + medial top of femur neck
# Линия Кальве проходит по ВНУТРЕННЕЙ поверхности подвздошной кости
# (медиальный нижний контур ilium) и продолжается на внутреннюю
# верхнюю поверхность шейки бедра (медиальный верхний контур femur).
# Медиальная сторона = обращена к центру снимка.
for il,fe,fe_mask,col,lbl,is_left in [
        (LI,LF,L_fe,"#69F0AE","Calve L",True),
        (RI,RF,R_fe,"#40C4FF","Calve R",False)]:
    if il is None or fe is None: continue

    # Медиальная сторона ilium: правая часть L_il, левая часть R_il
    il_cols = np.where(L_il if is_left else R_il)[1].astype(float)
    il_cmin, il_cmax = il_cols.min(), il_cols.max()
    il_cw = il_cmax - il_cmin
    if is_left:   # L_il: медиальная = правый край
        il_med = arc_bottom(il["cnt"], x0=int(il_cmin + il_cw * 0.55))
    else:         # R_il: медиальная = левый край
        il_med = arc_bottom(il["cnt"], x1=int(il_cmax - il_cw * 0.55))
    plot_arc(il_med, col, lw=2.2)

    # Медиальная сторона femur neck: правый край L_fe, левый край R_fe
    fe_cols = np.where(fe_mask)[1].astype(float)
    fe_cmin, fe_cmax = fe_cols.min(), fe_cols.max()
    fe_cw = fe_cmax - fe_cmin
    rng_fe = fe["r1"] - fe["r0"]
    if is_left:
        fe_med = arc_bottom(fe["cnt"], x0=int(fe_cmax - fe_cw * 0.40))
    else:
        fe_med = arc_bottom(fe["cnt"], x1=int(fe_cmin + fe_cw * 0.40))
    # Только зона шейки по высоте
    if len(fe_med) > 0:
        fe_med = fe_med[(fe_med[:,1] >= fe["r0"] + rng_fe*0.15) &
                        (fe_med[:,1] <= fe["r0"] + rng_fe*0.60)]
    plot_arc(fe_med, col, lw=2.2, label=lbl)

# Diagnosis box
txt=(f"ЛЕВЫЙ:   {Lv}\n  ∠ВВ={L_ac}°  ШДУ={L_nsa}°  {L_q}\n"
     f"  Шентон: {'OK' if L_sok else 'BREAK'}\n\n"
     f"ПРАВЫЙ:  {Rv}\n  ∠ВВ={R_ac}°  ШДУ={R_nsa}°  {R_q}\n"
     f"  Шентон: {'OK' if R_sok else 'BREAK'}")
ax.text(10,10,txt,fontsize=9,color=WHT,va="top",zorder=15,
        bbox=dict(facecolor="#1a1a2e",alpha=.82,pad=8,boxstyle="round"))

ax.set_title("Hip Dysplasia Analysis — Hilgenreiner · Ombredanne · "
             "Shenton · Menard · Acetabular Angle · Calve", fontsize=13)
ax.legend(loc="lower right",fontsize=7,ncol=2,facecolor="#111",labelcolor="w",framealpha=.75)
ax.axis("off"); plt.tight_layout()
plt.savefig("step_final_analysis.png",dpi=180,bbox_inches="tight"); plt.show()

# ═══════════════════════════════════════════════════════════════
#  SUMMARY TABLE  (CELL 10)
# ═══════════════════════════════════════════════════════════════
print("\n"+"="*60)
print(f"  {'PARAMETER':<32} {'LEFT':>12} {'RIGHT':>12}")
print("="*60)
for name,lv,rv in [
    ("Acetabular angle (norm ≤28°)", f"{L_ac}°",   f"{R_ac}°"),
    ("CCD / ШДУ (norm 125–150°)",   f"{L_nsa}°",  f"{R_nsa}°"),
    ("h-distance (norm 8–12mm)",    px2mm(L_h),   px2mm(R_h)),
    ("d-distance (norm 10–15mm)",   px2mm(L_d),   px2mm(R_d)),
    ("Shenton line",                "OK" if L_sok else "BREAK", "OK" if R_sok else "BREAK"),
    ("Head quadrant",               L_q.split("—")[0].strip(), R_q.split("—")[0].strip()),
]:
    print(f"  {name:<32} {lv:>12} {rv:>12}")
print("-"*60)
print(f"  {'VERDICT':<32} {Lv[:12]:>12} {Rv[:12]:>12}")
print("="*60)
print("\n⚠ Supplementary tool — final diagnosis by radiologist.")

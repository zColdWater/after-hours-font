#!/usr/bin/env python3
"""
After Hours — Original Gothic-Cyberpunk Latin Display & Web Heading Font Family.
Builds two installable OpenType CFF (.otf) fonts + WOFF2 web fonts:
  1. AfterHours-Display.otf  (Expressive Gothic-Cyberpunk Hero Display)
  2. AfterHours-Heading.otf  (Cleaner Mobile-Legible Web Heading Cut)

100% original parametric cubic-Bezier + skia-pathops boolean architecture.
"""
import math
import os
import pathops
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.roundingPen import RoundingPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

UPM = 1000
ASC = 820
DESC = -220
CAP = 740
XH = 505


def _norm(p):
    """Normalize every primitive contour to uniform CCW winding before boolean ops."""
    if p is None or len(p) == 0:
        return None
    return pathops.simplify(p, fix_winding=True, clockwise=False)


def p_union(*paths):
    res = pathops.Path()
    valid = []
    for p in paths:
        np = _norm(p)
        if np is not None and len(np) > 0:
            valid.append(np)
    if not valid:
        return res
    pathops.union(valid, res.getPen())
    return pathops.simplify(res, fix_winding=True, clockwise=False)


def p_diff(base, *cuts):
    nb = _norm(base)
    if nb is None or len(nb) == 0:
        return pathops.Path()
    valid_cuts = []
    for c in cuts:
        nc = _norm(c)
        if nc is not None and len(nc) > 0:
            valid_cuts.append(nc)
    if not valid_cuts:
        return nb
    cut_all = p_union(*valid_cuts)
    res = pathops.Path()
    pathops.difference([nb], [cut_all], res.getPen())
    return pathops.simplify(res, fix_winding=True, clockwise=False)


def p_intersect(a, b):
    na, nb = _norm(a), _norm(b)
    if na is None or nb is None:
        return pathops.Path()
    res = pathops.Path()
    pathops.intersection([na], [nb], res.getPen())
    return pathops.simplify(res, fix_winding=True, clockwise=False)


def poly(pts):
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo(pts[0])
    for pt in pts[1:]:
        pen.lineTo(pt)
    pen.closePath()
    return p


def rect(x0, y0, x1, y1):
    if x1 <= x0 or y1 <= y0:
        return pathops.Path()
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def chamfer_rect(x0, y0, x1, y1, tl=0, tr=0, br=0, bl=0):
    pts = []
    if bl > 0:
        pts += [(x0 + bl, y0)]
    else:
        pts += [(x0, y0)]
    if br > 0:
        pts += [(x1 - br, y0), (x1, y0 + br)]
    else:
        pts += [(x1, y0)]
    if tr > 0:
        pts += [(x1, y1 - tr), (x1 - tr, y1)]
    else:
        pts += [(x1, y1)]
    if tl > 0:
        pts += [(x0 + tl, y1), (x0, y1 - tl)]
    else:
        pts += [(x0, y1)]
    if bl > 0:
        pts += [(x0, y0 + bl)]
    return poly(pts)


def diamond(cx, cy, rx, ry=None):
    if ry is None:
        ry = rx
    return poly([(cx, cy - ry), (cx + rx, cy), (cx, cy + ry), (cx - rx, cy)])


def gothic_stem(x, y0, y1, sw, top="crown", bot="spur", ch=24, display=True):
    """
    Signature vertical stem with Gothic blackletter 45-deg crown & foot spur.
    """
    x0, x1 = x, x + sw
    pts = []
    # Bottom terminal
    if bot == "spur":
        # Blackletter angled foot with subtle right-facing Gothic beak
        pts += [(x0 + ch * 0.85, y0), (x1 + ch * 0.55, y0), (x1, y0 + ch * 0.95)]
    elif bot == "spur_l":
        pts += [(x0 - ch * 0.55, y0), (x1 - ch * 0.85, y0), (x1, y0 + ch * 0.85)]
    elif bot == "bevel_l":
        pts += [(x0 + ch, y0), (x1, y0)]
    elif bot == "bevel_r":
        pts += [(x0, y0), (x1 - ch, y0), (x1, y0 + ch)]
    elif bot == "point":
        pts += [(x0 + sw * 0.5, y0 - ch * 0.45), (x1, y0 + ch * 1.1)]
    elif bot == "flat":
        pts += [(x0, y0), (x1, y0)]
    else:
        pts += [(x0, y0), (x1, y0)]

    # Top terminal
    if top == "crown":
        # Pointed Gothic crown rising from left bevel to peak, chamfered right
        pts += [(x1, y1 - ch * 0.7), (x1 - ch * 0.5, y1 + ch * 0.55), (x0 - ch * 0.45, y1 - ch * 0.35), (x0, y1 - ch * 0.95)]
    elif top == "spire":
        # Symmetric Gothic cathedral spire
        pts += [(x1, y1 - ch * 0.9), (x0 + sw * 0.5, y1 + ch * 0.65), (x0, y1 - ch * 0.9)]
    elif top == "bevel_l":
        pts += [(x1, y1), (x0 + ch, y1), (x0, y1 - ch)]
    elif top == "bevel_r":
        pts += [(x1, y1 - ch), (x1 - ch, y1), (x0, y1)]
    elif top == "flat":
        pts += [(x1, y1), (x0, y1)]
    else:
        pts += [(x1, y1), (x0, y1)]

    if bot == "spur":
        pts += [(x0, y0 + ch * 0.85)]
    elif bot == "spur_l":
        pts += [(x0, y0 + ch * 0.95)]
    elif bot == "bevel_l":
        pts += [(x0, y0 + ch)]
    elif bot == "point":
        pts += [(x0, y0 + ch * 1.1)]

    return poly(pts)


def hbar(x0, x1, y, thick, bevel_l=True, bevel_r=True, spur_r=False):
    """Horizontal Gothic-cyberpunk bar with 45-deg PCB end chamfers."""
    y0, y1 = y, y + thick
    c = thick * 0.48
    pts = []
    if bevel_l:
        pts += [(x0 + c, y0)]
    else:
        pts += [(x0, y0)]
    if spur_r:
        pts += [(x1, y0), (x1 + c * 1.1, y0 + thick * 0.5), (x1 - c * 0.4, y1 + c * 0.9), (x1 - c * 1.2, y1)]
    elif bevel_r:
        pts += [(x1 - c, y0), (x1, y0 + c), (x1, y1), (x1 - c * 0.3, y1)]
    else:
        pts += [(x1, y0), (x1, y1)]
    if bevel_l:
        pts += [(x0, y1), (x0, y0 + c)]
    else:
        pts += [(x0, y1)]
    return poly(pts)


def diag_stroke(x0, y0, x1, y1, width, cap_flat=True):
    """Broad-nib diagonal stroke of horizontal width `width`."""
    hw = width / 2.0
    if cap_flat:
        return poly([(x0 - hw, y0), (x0 + hw, y0), (x1 + hw, y1), (x1 - hw, y1)])
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L * hw, dx / L * hw
    return poly([(x0 - nx, y0 - ny), (x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny)])


def lancet_solid(x0, y0, x1, y1, arch_top=True, arch_bot=True, top_h=None, bot_h=None, chamfer=0):
    """
    Smooth cubic-Bezier Gothic pointed lancet / ogive shape.
    """
    cx = (x0 + x1) / 2.0
    H = y1 - y0
    W = x1 - x0
    th = top_h if top_h is not None else min(H * 0.34, W * 0.48)
    bh = bot_h if bot_h is not None else min(H * 0.34, W * 0.48)
    y_ta = y1 - th
    y_ba = y0 + bh

    p = pathops.Path()
    pen = p.getPen()

    if arch_bot:
        pen.moveTo((cx, y0))
        pen.curveTo(
            (cx + (x1 - cx) * 0.50, y0 + bh * 0.22),
            (x1, y0 + bh * 0.50),
            (x1, y_ba),
        )
    else:
        if chamfer > 0:
            pen.moveTo((x0 + chamfer, y0))
            pen.lineTo((x1 - chamfer, y0))
            pen.lineTo((x1, y0 + chamfer))
        else:
            pen.moveTo((x0, y0))
            pen.lineTo((x1, y0))

    if arch_top:
        pen.lineTo((x1, y_ta))
        pen.curveTo(
            (x1, y1 - th * 0.50),
            (cx + (x1 - cx) * 0.50, y1 - th * 0.22),
            (cx, y1),
        )
        pen.curveTo(
            (cx - (cx - x0) * 0.50, y1 - th * 0.22),
            (x0, y1 - th * 0.50),
            (x0, y_ta),
        )
    else:
        if chamfer > 0:
            pen.lineTo((x1, y1 - chamfer))
            pen.lineTo((x1 - chamfer, y1))
            pen.lineTo((x0 + chamfer, y1))
            pen.lineTo((x0, y1 - chamfer))
        else:
            pen.lineTo((x1, y1))
            pen.lineTo((x0, y1))

    if arch_bot:
        pen.lineTo((x0, y_ba))
        pen.curveTo(
            (x0, y0 + bh * 0.50),
            (cx - (cx - x0) * 0.50, y0 + bh * 0.22),
            (cx, y0),
        )
    else:
        if chamfer > 0:
            pen.lineTo((x0, y0 + chamfer))
            pen.lineTo((x0 + chamfer, y0))
        else:
            pen.lineTo((x0, y0))

    pen.closePath()
    return p


def lancet_ring(x0, y0, x1, y1, sw, tw, arch_top=True, arch_bot=True, top_h=None, bot_h=None):
    outer = lancet_solid(x0, y0, x1, y1, arch_top, arch_bot, top_h, bot_h)
    ix0, ix1 = x0 + sw, x1 - sw
    iy0, iy1 = y0 + tw * 1.15, y1 - tw * 1.15
    if ix1 <= ix0 + 14 or iy1 <= iy0 + 14:
        return outer
    ith = (top_h * 0.88) if top_h is not None else None
    ibh = (bot_h * 0.88) if bot_h is not None else None
    inner = lancet_solid(ix0, iy0, ix1, iy1, arch_top, arch_bot, ith, ibh)
    return p_diff(outer, inner)


def right_bowl(x0, y0, x1, y1, sw, tw, ch=22):
    """Right-facing Gothic pointed-shoulder bowl with subtle 45-deg cyberpunk corner facets."""
    H = y1 - y0
    W = x1 - x0
    r = min(H * 0.44, W * 0.56)
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo((x0, y0))
    pen.lineTo((x1 - r * 0.88, y0))
    pen.curveTo((x1 - r * 0.30, y0 + r * 0.14), (x1, y0 + r * 0.44), (x1, y0 + r * 0.96))
    pen.lineTo((x1, y1 - r * 0.96))
    pen.curveTo((x1, y1 - r * 0.44), (x1 - r * 0.30, y1 - r * 0.14), (x1 - r * 0.88, y1))
    pen.lineTo((x0, y1))
    pen.closePath()

    # Inner Gothic pointed corner counter
    ix0 = x0 + sw * 0.88
    ix1 = x1 - sw
    iy0 = y0 + tw * 1.12
    iy1 = y1 - tw * 1.12
    if ix1 <= ix0 + 12 or iy1 <= iy0 + 12:
        return p
    ir = min((iy1 - iy0) * 0.45, (ix1 - ix0) * 0.68)
    ip = pathops.Path()
    ipen = ip.getPen()
    ipen.moveTo((ix0, iy0))
    ipen.lineTo((ix1 - ir * 0.84, iy0))
    ipen.curveTo((ix1 - ir * 0.28, iy0 + ir * 0.16), (ix1, iy0 + ir * 0.44), (ix1, iy0 + ir * 0.96))
    ipen.lineTo((ix1, iy1 - ir * 0.96))
    ipen.curveTo((ix1, iy1 - ir * 0.44), (ix1 - ir * 0.28, iy1 - ir * 0.16), (ix1 - ir * 0.84, iy1))
    ipen.lineTo((ix0, iy1))
    ipen.closePath()
    return p_diff(p, ip)


def glitch_notch_cut(x_edge, y_mid, depth, height=22, from_left=True):
    """
    Signature cyberpunk 45-deg PCB bus notch carved into Display stems
    at a shared horizontal scan-line axis across the entire font.
    """
    h2 = height / 2.0
    if from_left:
        return poly([
            (x_edge - 8, y_mid - h2),
            (x_edge + depth, y_mid - h2),
            (x_edge + depth + h2 * 1.1, y_mid + h2),
            (x_edge - 8, y_mid + h2),
        ])
    else:
        return poly([
            (x_edge + 8, y_mid - h2),
            (x_edge - depth - h2 * 1.1, y_mid - h2),
            (x_edge - depth, y_mid + h2),
            (x_edge + 8, y_mid + h2),
        ])


def circuit_slice_cut(x0, x1, y_mid, thickness=18):
    """45-deg diagonal micro-slice (used sparingly on signature Display accents)."""
    h = thickness / 2.0
    return poly([
        (x0 - 10, y_mid - h - 10),
        (x1 + 10, y_mid - h + 14),
        (x1 + 10, y_mid + h + 14),
        (x0 - 10, y_mid + h - 10),
    ])


def make_glyphs(style="Display"):
    is_disp = (style == "Display")
    # Master typographic parameters
    SW = 114 if is_disp else 98       # Primary vertical stem
    TW = 34 if is_disp else 54        # Thin crossbar / arch roof (Display 3.35:1 vs Heading 1.81:1)
    SW_L = 98 if is_disp else 88      # Lowercase stem
    TW_L = 33 if is_disp else 50      # Lowercase thin
    WS = 1.00 if is_disp else 1.08    # Heading cut opens counters horizontally for phone clarity
    CH = 25 if is_disp else 15        # Gothic bevel size (crisp display drama vs calm heading)
    HY_CAP = 420                      # Shared Cyberpunk Horizon Line (uppercase)
    HY_LOW = 285                      # Shared Cyberpunk Horizon Line (lowercase)
    OVER = 16 if is_disp else 9       # Pointed arch overshoot

    def W(val):
        return val * WS

    def cap_notch(p, x_edge, from_left=True, y=HY_CAP, depth_mult=0.42):
        if not is_disp:
            return p
        return p_diff(p, glitch_notch_cut(x_edge, y, SW * depth_mult, height=22, from_left=from_left))

    def low_notch(p, x_edge, from_left=True, y=HY_LOW, depth_mult=0.38):
        if not is_disp:
            return p
        return p_diff(p, glitch_notch_cut(x_edge, y, SW_L * depth_mult, height=18, from_left=from_left))

    glyphs = {}

    # ------------------------------------------------------------
    # UPPERCASE A-Z (Gothic Lancet Bones + Cyberpunk PCB Geometry)
    # ------------------------------------------------------------

    # A: Iconic Gothic pointed cathedral A — thin left diagonal, thick right diagonal,
    #    sharp gothic apex crest, cyberpunk stepped crossbar + subtle horizon glitch cut
    def g_A():
        w = W(540)
        cx = w / 2.0
        left_w = TW * 1.45
        right_w = SW * 0.96
        # Left thin leg rising to pointed Gothic spire
        l_leg = poly([
            (0, 0), (left_w, 0),
            (cx + TW * 0.25, CAP + OVER),
            (cx - left_w * 0.55, CAP - 12),
        ])
        # Right thick leg
        r_leg = poly([
            (cx - TW * 0.25, CAP + OVER),
            (cx + right_w * 0.55, CAP - 18),
            (w, 0), (w - right_w, 0),
        ])
        # Gothic diamond foot spurs
        l_foot = poly([(-18, 0), (left_w + 18, 0), (left_w + 4, TW * 0.85), (0, TW * 0.85)])
        r_foot = poly([(w - right_w - 14, 0), (w + 18, 0), (w + 4, TW * 0.85), (w - right_w, TW * 0.85)])
        # Stepped cyberpunk crossbar (double-tier PCB bar in Display, crisp single bar in Heading)
        y_bar = 235
        x_bl = (y_bar / CAP) * cx + 10
        x_br = w - (y_bar / CAP) * cx - 10
        bar1 = hbar(x_bl, x_br, y_bar, TW * 1.05, bevel_l=True, bevel_r=False)
        parts = [l_leg, r_leg, l_foot, r_foot, bar1]
        if is_disp:
            # Playful Gothic-cyber diamond core suspended below arch peak
            parts.append(diamond(cx, 505, 16, 26))
        p = p_union(*parts)
        # Cyberpunk notch on outer right thick diagonal at horizon line
        if is_disp:
            xr_hy = w - (HY_CAP / CAP) * (w - cx)
            p = p_diff(p, glitch_notch_cut(xr_hy + 12, HY_CAP, SW * 0.40, 22, from_left=False))
        return p

    # B: Gothic stem + twin pointed right bowls + horizon circuit notch
    def g_B():
        w = W(485)
        stem = gothic_stem(0, 0, CAP, SW, top="crown", bot="bevel_l", ch=CH)
        mid_y = 390
        top_bowl = right_bowl(0, mid_y - TW * 0.55, w - 26, CAP, SW, TW)
        bot_bowl = right_bowl(0, 0, w, mid_y + TW * 0.55, SW, TW)
        p = p_union(stem, top_bowl, bot_bowl)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        return p

    # C: Pointed lancet arch C with 45-deg cyberpunk open terminals & horizon cut
    def g_C():
        w = W(485)
        ring = lancet_ring(0, -OVER, w, CAP + OVER, SW, TW, top_h=210, bot_h=210)
        # Clean diagonal cyberpunk mouth opening on right
        cut = poly([
            (w * 0.54, 185), (w + 30, 120),
            (w + 30, CAP - 120), (w * 0.54, CAP - 185),
        ])
        p = p_diff(ring, cut)
        # Sharp Gothic finials at top/bottom mouths
        if is_disp:
            p = p_union(p, diamond(w - SW * 0.42, CAP - 150, 14, 18))
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        return p

    # D: Gothic stem + cathedral pointed right lancet shield
    def g_D():
        w = W(505)
        stem = gothic_stem(0, 0, CAP, SW, top="crown", bot="bevel_l", ch=CH)
        bowl = right_bowl(0, 0, w, CAP, SW, TW)
        # Give D's outer right edge a subtle Gothic chamfer facet
        p = p_union(stem, bowl)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        if is_disp:
            p = cap_notch(p, w, from_left=False, y=HY_CAP, depth_mult=0.35)
        return p

    # E: Tall Gothic spine + 3 PCB-chamfered arms with pointed Gothic terminal spurs
    def g_E():
        w = W(435)
        stem = gothic_stem(0, 0, CAP, SW, top="bevel_l", bot="bevel_l", ch=CH)
        top_arm = hbar(SW * 0.4, w, CAP - TW * 1.15, TW * 1.15, bevel_l=False, bevel_r=False, spur_r=True)
        mid_arm = hbar(SW * 0.4, w - 58, HY_CAP - TW * 0.55, TW * 1.08, bevel_l=False, bevel_r=True)
        bot_arm = hbar(SW * 0.4, w + 8, 0, TW * 1.22, bevel_l=False, bevel_r=False, spur_r=True)
        # Sharp Gothic inner triangular bracket at top-right & bottom-right
        top_drop = poly([(w - TW * 1.1, CAP - TW * 1.15), (w, CAP - TW * 1.15), (w, CAP - TW * 2.55)])
        bot_rise = poly([(w + 8 - TW * 1.1, TW * 1.22), (w + 8, TW * 1.22), (w + 8, TW * 2.65)])
        p = p_union(stem, top_arm, mid_arm, bot_arm, top_drop, bot_rise)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        return p

    # F: Matches E's Gothic-cyber spine & pointed upper spur
    def g_F():
        w = W(420)
        stem = gothic_stem(0, 0, CAP, SW, top="bevel_l", bot="spur", ch=CH)
        top_arm = hbar(SW * 0.4, w, CAP - TW * 1.15, TW * 1.15, bevel_l=False, bevel_r=False, spur_r=True)
        mid_arm = hbar(SW * 0.4, w - 65, HY_CAP - TW * 0.55, TW * 1.08, bevel_l=False, bevel_r=True)
        top_drop = poly([(w - TW * 1.1, CAP - TW * 1.15), (w, CAP - TW * 1.15), (w, CAP - TW * 2.55)])
        p = p_union(stem, top_arm, mid_arm, top_drop)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        return p

    # G: Pointed lancet C + horizontal cyberpunk gate + vertical pillar
    def g_G():
        w = W(505)
        ring = lancet_ring(0, -OVER, w, CAP + OVER, SW, TW, top_h=210, bot_h=210)
        cut = poly([
            (w * 0.55, 340), (w + 30, 340),
            (w + 30, CAP - 125), (w * 0.55, CAP - 185),
        ])
        p = p_diff(ring, cut)
        # Inner crossbar & spur
        bar = hbar(w * 0.48, w, 340 - TW * 1.05, TW * 1.05, bevel_l=True, bevel_r=False)
        pillar = gothic_stem(w - SW, 110, 340, SW, top="bevel_r", bot="flat", ch=16)
        p = p_union(p, bar, pillar)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        return p

    # H: Twin cathedral pillars bridged by a Gothic pointed crossbar + horizon notch!
    def g_H():
        w = W(510)
        s1 = gothic_stem(0, 0, CAP, SW, top="crown", bot="spur", ch=CH)
        s2 = gothic_stem(w - SW, 0, CAP, SW, top="crown", bot="spur", ch=CH)
        # Signature crossbar at horizon line with subtle upward Gothic arch point in middle
        y_b = HY_CAP - TW * 0.55
        cx = w / 2.0
        bridge = poly([
            (SW * 0.6, y_b), (w - SW * 0.6, y_b),
            (w - SW * 0.6, y_b + TW * 1.08),
            (cx, y_b + TW * 1.08 + (24 if is_disp else 12)),
            (SW * 0.6, y_b + TW * 1.08),
        ])
        p = p_union(s1, s2, bridge)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        if is_disp:
            p = cap_notch(p, w, from_left=False, y=HY_CAP)
        return p

    # I: Gothic cathedral spire pillar with top & bottom faceted serifs
    def g_I():
        w = W(230)
        sx = (w - SW) / 2.0
        stem = gothic_stem(sx, 0, CAP, SW, top="flat", bot="flat", ch=CH)
        top_s = hbar(0, w, CAP - TW * 1.05, TW * 1.05, bevel_l=True, bevel_r=True)
        bot_s = hbar(0, w, 0, TW * 1.05, bevel_l=True, bevel_r=True)
        p = p_union(stem, top_s, bot_s)
        p = cap_notch(p, sx, from_left=True, y=HY_CAP)
        return p

    # J: Gothic right pillar curving into pointed lancet hook
    def g_J():
        w = W(385)
        stem = gothic_stem(w - SW, 195, CAP, SW, top="crown", bot="flat", ch=CH)
        hook = lancet_ring(0, -OVER, w, 410, SW, TW, arch_top=False, arch_bot=True, bot_h=195)
        cut = rect(-20, 215, w - SW + 2, 430)
        hook = p_diff(hook, cut)
        # Top Gothic finial on left hook tip
        tip = poly([(0, 215), (SW, 215), (SW, 255), (0, 232)])
        p = p_union(stem, hook, tip)
        p = cap_notch(p, w, from_left=False, y=HY_CAP)
        return p

    # K: Gothic pillar + razor-sharp cyberpunk forked diagonals
    def g_K():
        w = W(490)
        stem = gothic_stem(0, 0, CAP, SW, top="crown", bot="spur", ch=CH)
        # Thin upper diagonal rising to Gothic top right spur
        up = diag_stroke(SW * 0.72, 310, w - 25, CAP, TW * 1.45)
        # Thick lower diagonal launching from upper stroke (cyberpunk offset junction!)
        dn = diag_stroke(SW * 1.35, 395, w - SW * 0.45, 0, SW * 0.96)
        r_foot = poly([(w - SW - 6, 0), (w + 18, 0), (w + 4, TW * 0.85), (w - SW, TW * 0.85)])
        p = p_union(stem, up, dn, r_foot)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        return p

    # L: Gothic spine + PCB-chamfered foot with sharp Gothic rising spur
    def g_L():
        w = W(410)
        stem = gothic_stem(0, 0, CAP, SW, top="crown", bot="bevel_l", ch=CH)
        base = hbar(SW * 0.4, w, 0, TW * 1.25, bevel_l=False, bevel_r=False, spur_r=True)
        spur = poly([(w - TW * 1.2, TW * 1.25), (w, TW * 1.25), (w, TW * 3.1)])
        p = p_union(stem, base, spur)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        return p

    # M: Twin cathedral arches + dramatic thick/thin Gothic V-trough
    def g_M():
        w = W(630)
        cx = w / 2.0
        s1 = gothic_stem(0, 0, CAP, SW * 0.90, top="crown", bot="spur", ch=CH)
        s2 = gothic_stem(w - SW * 0.96, 0, CAP, SW * 0.96, top="crown", bot="spur", ch=CH)
        d1 = diag_stroke(SW * 0.48, CAP, cx, 165, SW * 0.84)
        d2 = diag_stroke(cx, 165, w - SW * 0.50, CAP, TW * 1.42)
        p = p_union(s1, s2, d1, d2)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        if is_disp:
            p = cap_notch(p, w, from_left=False, y=HY_CAP)
        return p

    # N: Twin pillars + thick calligraphic diagonal + Gothic spire top
    def g_N():
        w = W(510)
        s1 = gothic_stem(0, 0, CAP, SW * 0.88, top="crown", bot="spur", ch=CH)
        s2 = gothic_stem(w - SW * 0.88, 0, CAP, SW * 0.88, top="crown", bot="bevel_r", ch=CH)
        d = diag_stroke(SW * 0.46, CAP, w - SW * 0.46, 0, SW * 0.92)
        p = p_union(s1, s2, d)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        return p

    # O: Crown jewel pointed Gothic lancet window O with cyberpunk outer notch!
    def g_O():
        w = W(520)
        p = lancet_ring(0, -OVER, w, CAP + OVER, SW, TW, top_h=225, bot_h=225)
        if is_disp:
            p = cap_notch(p, 0, from_left=True, y=HY_CAP, depth_mult=0.38)
            p = cap_notch(p, w, from_left=False, y=HY_CAP, depth_mult=0.38)
            # Subtle inner diamond glint at center? No—keep O counter crisp & pure for phone readability!
        return p

    # P: Gothic spine + pointed right bowl
    def g_P():
        w = W(475)
        stem = gothic_stem(0, 0, CAP, SW, top="crown", bot="spur", ch=CH)
        bowl = right_bowl(0, 320, w, CAP, SW, TW)
        p = p_union(stem, bowl)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        return p

    # Q: Pointed lancet O + sharp cyberpunk slashing tail
    def g_Q():
        w = W(520)
        p = lancet_ring(0, -OVER, w, CAP + OVER, SW, TW, top_h=225, bot_h=225)
        tail = poly([
            (w * 0.56, 175), (w * 0.72, 195),
            (w + 35, -75), (w - 35, -85),
        ])
        p = p_union(p, tail)
        if is_disp:
            p = cap_notch(p, 0, from_left=True, y=HY_CAP, depth_mult=0.38)
        return p

    # R: Hero letter in "AFTER HOURS" — Gothic spine, pointed bowl, razor-angled cyberpunk leg!
    def g_R():
        w = W(495)
        stem = gothic_stem(0, 0, CAP, SW, top="crown", bot="spur", ch=CH)
        bowl = right_bowl(0, 335, w - 18, CAP, SW, TW)
        # Angled leg sweeping from bowl bottom to crisp spurred foot
        leg = diag_stroke(w * 0.52, 355, w - SW * 0.48, 0, SW * 0.94)
        foot = poly([(w - SW - 8, 0), (w + 18, 0), (w + 4, TW * 0.85), (w - SW, TW * 0.85)])
        p = p_union(stem, bowl, leg, foot)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        return p

    # S: Sharp Gothic-Cyberpunk S — pointed upper/lower arches + dramatic thick diagonal spine
    def g_S():
        w = W(465)
        top_r = lancet_ring(10, 330, w - 8, CAP + OVER, SW * 0.90, TW * 1.05, arch_top=True, arch_bot=True, top_h=175, bot_h=115)
        top_c = p_diff(top_r, poly([(w * 0.30, 315), (w + 30, 315), (w + 30, 520), (w * 0.36, 480)]))
        bot_r = lancet_ring(0, -OVER, w, 420, SW * 0.94, TW * 1.05, arch_top=True, arch_bot=True, top_h=115, bot_h=175)
        bot_c = p_diff(bot_r, poly([(-30, 220), (w * 0.64, 260), (w * 0.70, 440), (-30, 440)]))
        spine = poly([
            (10, 448), (10 + SW * 0.92, 488),
            (w, 302), (w - SW * 0.94, 260),
        ])
        p = p_union(top_c, bot_c, spine)
        if is_disp:
            p = cap_notch(p, w, from_left=False, y=205, depth_mult=0.35)
        return p

    # T: Gothic cathedral cross-beam with hanging dagger spurs + notched central pillar
    def g_T():
        w = W(480)
        sx = (w - SW) / 2.0
        stem = gothic_stem(sx, 0, CAP - TW * 0.5, SW, top="flat", bot="spur", ch=CH)
        beam = hbar(0, w, CAP - TW * 1.20, TW * 1.20, bevel_l=True, bevel_r=True)
        # Twin Gothic hanging spurs at beam ends
        l_drop = poly([(0, CAP - TW * 1.20), (TW * 1.15, CAP - TW * 1.20), (0, CAP - TW * 2.85)])
        r_drop = poly([(w - TW * 1.15, CAP - TW * 1.20), (w, CAP - TW * 1.20), (w, CAP - TW * 2.85)])
        p = p_union(stem, beam, l_drop, r_drop)
        p = cap_notch(p, sx, from_left=True, y=HY_CAP)
        return p

    # U: Twin Gothic crowned pillars flowing into a pointed cathedral bottom lancet!
    def g_U():
        w = W(505)
        ring = lancet_ring(0, -OVER, w, CAP, SW, TW, arch_top=False, arch_bot=True, bot_h=225)
        # Open top
        open_top = rect(SW - 2, CAP - TW * 1.6, w - SW + 2, CAP + 20)
        p = p_diff(ring, open_top)
        # Add Gothic crowns to both top stems
        c1 = gothic_stem(0, CAP - 140, CAP, SW, top="crown", bot="flat", ch=CH)
        c2 = gothic_stem(w - SW, CAP - 140, CAP, SW, top="crown", bot="flat", ch=CH)
        p = p_union(p, c1, c2)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP)
        if is_disp:
            p = cap_notch(p, w, from_left=False, y=HY_CAP)
        return p

    # V: Thick left diagonal + thin right diagonal meeting at razor Gothic apex
    def g_V():
        w = W(520)
        cx = w / 2.0
        l_leg = poly([
            (0, CAP), (SW * 0.96, CAP),
            (cx + TW * 0.25, -OVER), (cx - SW * 0.45, 16),
        ])
        r_leg = poly([
            (w - TW * 1.45, CAP), (w, CAP),
            (cx + TW * 0.35, -OVER), (cx - TW * 0.25, 10),
        ])
        l_cap = poly([(-16, CAP), (SW + 10, CAP), (SW, CAP - TW * 0.85), (0, CAP - TW * 0.85)])
        r_cap = poly([(w - TW * 1.6, CAP), (w + 16, CAP), (w, CAP - TW * 0.85), (w - TW * 1.45, CAP - TW * 0.85)])
        p = p_union(l_leg, r_leg, l_cap, r_cap)
        if is_disp:
            xl_hy = (1.0 - HY_CAP / CAP) * cx
            p = p_diff(p, glitch_notch_cut(xl_hy - 12, HY_CAP, SW * 0.38, 22, from_left=True))
        return p

    # W: Double Gothic V with sharp intersecting cyber rhythm
    def g_W():
        w = W(720)
        q1, mid, q3 = w * 0.25, w * 0.50, w * 0.75
        s1 = diag_stroke(SW * 0.46, CAP, q1, -OVER, SW * 0.88)
        s2 = diag_stroke(q1, -OVER, mid, CAP * 0.78, TW * 1.38)
        s3 = diag_stroke(mid, CAP * 0.78, q3, -OVER, SW * 0.88)
        s4 = diag_stroke(q3, -OVER, w - TW * 0.7, CAP, TW * 1.38)
        p = p_union(s1, s2, s3, s4)
        return p

    # X: Dramatic thick backslash + razor-thin forward slash
    def g_X():
        w = W(500)
        d1 = diag_stroke(SW * 0.48, CAP, w - SW * 0.48, 0, SW * 0.96)
        d2 = diag_stroke(TW * 0.72, 0, w - TW * 0.72, CAP, TW * 1.45)
        t1 = poly([(-14, CAP), (SW + 10, CAP), (SW, CAP - TW * 0.8), (0, CAP - TW * 0.8)])
        b2 = poly([(w - SW - 10, 0), (w + 16, 0), (w, TW * 0.8), (w - SW, TW * 0.8)])
        p = p_union(d1, d2, t1, b2)
        return p

    # Y: Forked Gothic V upper + notched cathedral lower pillar
    def g_Y():
        w = W(500)
        cx = w / 2.0
        fork_y = 330
        l_arm = diag_stroke(SW * 0.48, CAP, cx, fork_y, SW * 0.92)
        r_arm = diag_stroke(w - TW * 0.75, CAP, cx, fork_y, TW * 1.45)
        stem = gothic_stem(cx - SW / 2.0, 0, fork_y + 35, SW, top="flat", bot="spur", ch=CH)
        p = p_union(l_arm, r_arm, stem)
        if is_disp:
            p = cap_notch(p, cx - SW / 2.0, from_left=True, y=190)
        return p

    # Z: Gothic-cyberpunk top/bottom bars + sweeping thick slash + spurs
    def g_Z():
        w = W(465)
        top_b = hbar(0, w, CAP - TW * 1.18, TW * 1.18, bevel_l=True, bevel_r=False)
        bot_b = hbar(0, w, 0, TW * 1.22, bevel_l=False, bevel_r=True)
        slash = diag_stroke(w - SW * 0.52, CAP - TW * 0.6, SW * 0.52, TW * 0.6, SW * 0.96)
        l_drop = poly([(0, CAP - TW * 1.18), (TW * 1.15, CAP - TW * 1.18), (0, CAP - TW * 2.65)])
        r_rise = poly([(w - TW * 1.15, TW * 1.22), (w, TW * 1.22), (w, TW * 2.65)])
        p = p_union(top_b, bot_b, slash, l_drop, r_rise)
        return p

    # ------------------------------------------------------------
    # LOWERCASE a-z (Same Gothic Lancet + PCB Grammar at x-height!)
    # ------------------------------------------------------------

    # a: Double-story Gothic-cyberpunk 'a' — arched top roof + lancet lower bowl
    def g_a():
        w = W(435)
        # Right vertical stem
        stem = gothic_stem(w - SW_L, 0, XH - 95, SW_L, top="flat", bot="spur", ch=18)
        # Top Gothic arch hood
        hood = lancet_ring(26, XH - 220, w, XH + OVER * 0.8, SW_L, TW_L, arch_top=True, arch_bot=False, top_h=145)
        hood = p_diff(hood, rect(-20, XH - 240, w - SW_L + 2, XH - 95))
        # Lower pointed bowl
        bowl = lancet_ring(0, -OVER * 0.7, w - SW_L * 0.15, 295, SW_L * 0.92, TW_L, arch_top=True, arch_bot=True, top_h=105, bot_h=105)
        p = p_union(stem, hood, bowl)
        p = low_notch(p, w, from_left=False, y=HY_LOW)
        return p

    # b: Tall Gothic ascender spine + pointed lancet bowl
    def g_b():
        w = W(455)
        stem = gothic_stem(0, 0, ASC, SW_L, top="crown", bot="bevel_l", ch=CH)
        bowl = lancet_ring(0, -OVER * 0.7, w, XH + OVER * 0.7, SW_L, TW_L, top_h=165, bot_h=165)
        p = p_union(stem, bowl)
        p = low_notch(p, 0, from_left=True, y=HY_LOW)
        return p

    # c: Lowercase pointed Gothic lancet c
    def g_c():
        w = W(405)
        ring = lancet_ring(0, -OVER * 0.7, w, XH + OVER * 0.7, SW_L, TW_L, top_h=160, bot_h=160)
        cut = poly([(w * 0.52, 130), (w + 30, 85), (w + 30, XH - 85), (w * 0.52, XH - 130)])
        p = p_diff(ring, cut)
        p = low_notch(p, 0, from_left=True, y=HY_LOW)
        return p

    # d: Pointed lancet bowl + tall Gothic ascender right spine
    def g_d():
        w = W(455)
        stem = gothic_stem(w - SW_L, 0, ASC, SW_L, top="crown", bot="spur", ch=CH)
        bowl = lancet_ring(0, -OVER * 0.7, w, XH + OVER * 0.7, SW_L, TW_L, top_h=165, bot_h=165)
        p = p_union(stem, bowl)
        p = low_notch(p, w, from_left=False, y=HY_LOW)
        return p

    # e: Pointed lancet bowl + crisp horizontal cyberpunk bar + open lower right mouth
    def g_e():
        w = W(425)
        ring = lancet_ring(0, -OVER * 0.7, w, XH + OVER * 0.7, SW_L, TW_L, top_h=165, bot_h=165)
        cut = poly([(w * 0.52, 125), (w + 30, 80), (w + 30, 265), (w * 0.52, 265)])
        p = p_diff(ring, cut)
        bar = hbar(SW_L * 0.5, w - SW_L * 0.1, 255, TW_L * 1.05, bevel_l=False, bevel_r=False)
        p = p_union(p, bar)
        p = low_notch(p, 0, from_left=True, y=HY_LOW)
        return p

    # f: Tall Gothic lancet-arched ascender + sharp crossbar
    def g_f():
        w = W(330)
        stem = gothic_stem(65, 0, ASC - 155, SW_L, top="flat", bot="spur", ch=18)
        arch = lancet_ring(65, ASC - 310, w + 45, ASC + OVER * 0.7, SW_L, TW_L, arch_top=True, arch_bot=False, top_h=150)
        arch = p_diff(arch, rect(65 + SW_L - 2, ASC - 330, w + 80, ASC - 105))
        bar = hbar(0, w - 15, XH - TW_L * 1.1, TW_L * 1.1, bevel_l=True, bevel_r=True)
        p = p_union(stem, arch, bar)
        p = low_notch(p, 65, from_left=True, y=HY_LOW)
        return p

    # g: Single-story Gothic pointed bowl + descending cyber-lancet hook
    def g_g():
        w = W(455)
        bowl = lancet_ring(0, -OVER * 0.6, w, XH + OVER * 0.7, SW_L, TW_L, top_h=160, bot_h=160)
        stem = gothic_stem(w - SW_L, DESC + 150, XH, SW_L, top="bevel_r", bot="flat", ch=16)
        hook = lancet_ring(15, DESC - OVER * 0.5, w, DESC + 310, SW_L, TW_L, arch_top=False, arch_bot=True, bot_h=150)
        hook = p_diff(hook, rect(-20, DESC + 135, w - SW_L + 2, DESC + 330))
        p = p_union(bowl, stem, hook)
        p = low_notch(p, w, from_left=False, y=HY_LOW)
        return p

    # h: Tall ascender + pointed Gothic cathedral shoulder arch!
    def g_h():
        w = W(455)
        s1 = gothic_stem(0, 0, ASC, SW_L, top="crown", bot="spur", ch=CH)
        arch = lancet_ring(0, 0, w, XH + OVER * 0.7, SW_L, TW_L, arch_top=True, arch_bot=False, top_h=175)
        # Remove bottom bar of ring
        arch = p_diff(arch, rect(-20, -20, w + 20, TW_L * 1.4))
        s2 = gothic_stem(w - SW_L, 0, XH - 165, SW_L, top="flat", bot="spur", ch=18)
        p = p_union(s1, arch, s2)
        p = low_notch(p, 0, from_left=True, y=HY_LOW)
        return p

    # i: Gothic pillar + signature floating diamond-LED tittle!
    def g_i():
        w = W(205)
        sx = (w - SW_L) / 2.0
        stem = gothic_stem(sx, 0, XH, SW_L, top="crown", bot="spur", ch=18)
        dot = diamond(w / 2.0, XH + 138, SW_L * 0.58, SW_L * 0.66)
        p = p_union(stem, dot)
        p = low_notch(p, sx, from_left=True, y=HY_LOW)
        return p

    # j: Descending Gothic lancet hook + signature diamond-LED tittle!
    def g_j():
        w = W(260)
        sx = w - SW_L
        stem = gothic_stem(sx, DESC + 140, XH, SW_L, top="crown", bot="flat", ch=18)
        hook = lancet_ring(-5, DESC - OVER * 0.5, w, DESC + 300, SW_L, TW_L, arch_top=False, arch_bot=True, bot_h=145)
        hook = p_diff(hook, rect(-35, DESC + 125, sx + 2, DESC + 320))
        dot = diamond(sx + SW_L / 2.0, XH + 138, SW_L * 0.58, SW_L * 0.66)
        p = p_union(stem, hook, dot)
        p = low_notch(p, w, from_left=False, y=HY_LOW)
        return p

    # k: Tall Gothic spine + sharp angled cyber diagonals
    def g_k():
        w = W(435)
        stem = gothic_stem(0, 0, ASC, SW_L, top="crown", bot="spur", ch=CH)
        up = diag_stroke(SW_L * 0.70, 215, w - 25, XH, TW_L * 1.45)
        dn = diag_stroke(SW_L * 1.25, 290, w - SW_L * 0.45, 0, SW_L * 0.94)
        foot = poly([(w - SW_L - 6, 0), (w + 14, 0), (w, TW_L * 0.85), (w - SW_L, TW_L * 0.85)])
        p = p_union(stem, up, dn, foot)
        p = low_notch(p, 0, from_left=True, y=HY_LOW)
        return p

    # l: Tall Gothic cathedral ascender pillar
    def g_l():
        w = W(205)
        sx = (w - SW_L) / 2.0
        stem = gothic_stem(sx, 0, ASC, SW_L, top="crown", bot="spur", ch=CH)
        p = low_notch(stem, sx, from_left=True, y=HY_LOW)
        return p

    # m: Double Gothic pointed lancet arches
    def g_m():
        w = W(680)
        mid = (w + SW_L) / 2.0
        s1 = gothic_stem(0, 0, XH, SW_L * 0.92, top="crown", bot="spur", ch=18)
        a1 = lancet_ring(0, 0, mid, XH + OVER * 0.7, SW_L * 0.92, TW_L, arch_top=True, arch_bot=False, top_h=155)
        a1 = p_diff(a1, rect(-20, -20, mid + 20, TW_L * 1.4))
        a2 = lancet_ring(mid - SW_L * 0.92, 0, w, XH + OVER * 0.7, SW_L * 0.92, TW_L, arch_top=True, arch_bot=False, top_h=155)
        a2 = p_diff(a2, rect(mid - SW_L, -20, w + 20, TW_L * 1.4))
        s2 = gothic_stem(mid - SW_L * 0.92, 0, XH - 145, SW_L * 0.92, top="flat", bot="spur", ch=16)
        s3 = gothic_stem(w - SW_L * 0.92, 0, XH - 145, SW_L * 0.92, top="flat", bot="spur", ch=16)
        p = p_union(s1, a1, a2, s2, s3)
        p = low_notch(p, 0, from_left=True, y=HY_LOW)
        return p

    # n: Single Gothic pointed lancet arch
    def g_n():
        w = W(450)
        s1 = gothic_stem(0, 0, XH, SW_L, top="crown", bot="spur", ch=18)
        arch = lancet_ring(0, 0, w, XH + OVER * 0.7, SW_L, TW_L, arch_top=True, arch_bot=False, top_h=170)
        arch = p_diff(arch, rect(-20, -20, w + 20, TW_L * 1.4))
        s2 = gothic_stem(w - SW_L, 0, XH - 160, SW_L, top="flat", bot="spur", ch=18)
        p = p_union(s1, arch, s2)
        p = low_notch(p, 0, from_left=True, y=HY_LOW)
        return p

    # o: Miniature pointed Gothic lancet window
    def g_o():
        w = W(445)
        p = lancet_ring(0, -OVER * 0.7, w, XH + OVER * 0.7, SW_L, TW_L, top_h=165, bot_h=165)
        if is_disp:
            p = low_notch(p, 0, from_left=True, y=HY_LOW, depth_mult=0.36)
            p = low_notch(p, w, from_left=False, y=HY_LOW, depth_mult=0.36)
        return p

    # p: Descending Gothic spine + pointed lancet bowl
    def g_p():
        w = W(455)
        stem = gothic_stem(0, DESC, XH, SW_L, top="crown", bot="spur", ch=18)
        bowl = lancet_ring(0, -OVER * 0.7, w, XH + OVER * 0.7, SW_L, TW_L, top_h=165, bot_h=165)
        p = p_union(stem, bowl)
        p = low_notch(p, 0, from_left=True, y=HY_LOW)
        return p

    # q: Pointed lancet bowl + descending Gothic spine
    def g_q():
        w = W(455)
        stem = gothic_stem(w - SW_L, DESC, XH, SW_L, top="bevel_r", bot="spur", ch=18)
        bowl = lancet_ring(0, -OVER * 0.7, w, XH + OVER * 0.7, SW_L, TW_L, top_h=165, bot_h=165)
        p = p_union(stem, bowl)
        p = low_notch(p, w, from_left=False, y=HY_LOW)
        return p

    # r: Gothic spine + sharp cyberpunk overhanging spur arch
    def g_r():
        w = W(330)
        s1 = gothic_stem(0, 0, XH, SW_L, top="crown", bot="spur", ch=18)
        arch = lancet_ring(0, XH - 275, w + 75, XH + OVER * 0.7, SW_L, TW_L, arch_top=True, arch_bot=False, top_h=155)
        arch = p_diff(arch, rect(w - 15, XH - 300, w + 100, XH + 30))
        arch = p_diff(arch, rect(SW_L - 2, XH - 300, w + 100, XH - 120))
        p = p_union(s1, arch)
        p = low_notch(p, 0, from_left=True, y=HY_LOW)
        return p

    # s: Compact pointed Gothic-cyberpunk s
    def g_s():
        w = W(385)
        top_r = lancet_ring(8, 220, w - 6, XH + OVER * 0.7, SW_L * 0.88, TW_L, top_h=125, bot_h=90)
        top_c = p_diff(top_r, poly([(w * 0.32, 205), (w + 30, 205), (w + 30, 365), (w * 0.38, 335)]))
        bot_r = lancet_ring(0, -OVER * 0.7, w, 300, SW_L * 0.90, TW_L, top_h=90, bot_h=125)
        bot_c = p_diff(bot_r, poly([(-30, 145), (w * 0.62, 175), (w * 0.68, 320), (-30, 320)]))
        spine = poly([
            (8, 316), (8 + SW_L * 0.90, 350),
            (w, 208), (w - SW_L * 0.90, 172),
        ])
        return p_union(top_c, bot_c, spine)

    # t: Tall Gothic cross-spire + pointed bottom kick
    def g_t():
        w = W(320)
        sx = 65
        stem = gothic_stem(sx, 85, ASC - 110, SW_L, top="spire", bot="flat", ch=18)
        foot = lancet_ring(sx, -OVER * 0.6, w + 65, 250, SW_L, TW_L, arch_top=False, arch_bot=True, bot_h=115)
        foot = p_diff(foot, rect(w - 5, -30, w + 90, 270))
        foot = p_diff(foot, rect(sx + SW_L - 2, 110, w + 90, 270))
        bar = hbar(0, w - 10, XH - TW_L * 1.1, TW_L * 1.1, bevel_l=True, bevel_r=True)
        p = p_union(stem, foot, bar)
        p = low_notch(p, sx, from_left=True, y=HY_LOW)
        return p

    # u: Inverted Gothic pointed lancet arch + right foot spur
    def g_u():
        w = W(450)
        ring = lancet_ring(0, -OVER * 0.7, w, XH, SW_L, TW_L, arch_top=False, arch_bot=True, bot_h=170)
        ring = p_diff(ring, rect(SW_L - 2, XH - TW_L * 1.6, w - SW_L + 2, XH + 20))
        s1 = gothic_stem(0, XH - 130, XH, SW_L, top="crown", bot="flat", ch=18)
        s2 = gothic_stem(w - SW_L, 0, XH, SW_L, top="crown", bot="spur", ch=18)
        p = p_union(ring, s1, s2)
        p = low_notch(p, 0, from_left=True, y=HY_LOW)
        return p

    # v: Thick left / thin right Gothic v
    def g_v():
        w = W(430)
        cx = w / 2.0
        l_leg = poly([(0, XH), (SW_L * 0.94, XH), (cx + TW_L * 0.25, -OVER * 0.7), (cx - SW_L * 0.42, 12)])
        r_leg = poly([(w - TW_L * 1.42, XH), (w, XH), (cx + TW_L * 0.30, -OVER * 0.7), (cx - TW_L * 0.22, 10)])
        return p_union(l_leg, r_leg)

    # w: Double Gothic v
    def g_w():
        w = W(615)
        q1, mid, q3 = w * 0.25, w * 0.50, w * 0.75
        s1 = diag_stroke(SW_L * 0.45, XH, q1, -OVER * 0.7, SW_L * 0.88)
        s2 = diag_stroke(q1, -OVER * 0.7, mid, XH * 0.80, TW_L * 1.38)
        s3 = diag_stroke(mid, XH * 0.80, q3, -OVER * 0.7, SW_L * 0.88)
        s4 = diag_stroke(q3, -OVER * 0.7, w - TW_L * 0.68, XH, TW_L * 1.38)
        return p_union(s1, s2, s3, s4)

    # x: Thick \ + thin /
    def g_x():
        w = W(425)
        d1 = diag_stroke(SW_L * 0.46, XH, w - SW_L * 0.46, 0, SW_L * 0.94)
        d2 = diag_stroke(TW_L * 0.72, 0, w - TW_L * 0.72, XH, TW_L * 1.45)
        return p_union(d1, d2)

    # y: Thick left / sweeping thin descender
    def g_y():
        w = W(435)
        cx = w * 0.50
        l_leg = diag_stroke(SW_L * 0.46, XH, cx, 10, SW_L * 0.92)
        r_leg = diag_stroke(w - TW_L * 0.72, XH, w * 0.20, DESC, TW_L * 1.50)
        return p_union(l_leg, r_leg)

    # z: Crisp cyber-Gothic z
    def g_z():
        w = W(395)
        top_b = hbar(0, w, XH - TW_L * 1.15, TW_L * 1.15, bevel_l=True, bevel_r=False)
        bot_b = hbar(0, w, 0, TW_L * 1.18, bevel_l=False, bevel_r=True)
        slash = diag_stroke(w - SW_L * 0.50, XH - TW_L * 0.5, SW_L * 0.50, TW_L * 0.5, SW_L * 0.94)
        return p_union(top_b, bot_b, slash)

    # ------------------------------------------------------------
    # NUMERALS 0-9 (Cohesive Gothic-Cyberpunk Lining Figures)
    # ------------------------------------------------------------

    # 0: Pointed Gothic lancet zero with signature 45-deg cyberpunk diamond slash core!
    def g_0():
        w = W(490)
        p = lancet_ring(0, -OVER, w, CAP + OVER, SW, TW, top_h=220, bot_h=220)
        # Signature cyber-gothic center diamond slash (instant distinction from 'O')
        slash = poly([
            (w * 0.34, 245), (w * 0.42, 245),
            (w * 0.66, CAP - 245), (w * 0.58, CAP - 245),
        ])
        core = diamond(w / 2.0, CAP / 2.0, 26, 38) if is_disp else slash
        p = p_union(p, slash, core)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP, depth_mult=0.36)
        return p

    # 1: Gothic spire pillar + sharp diagonal nose + base pedestal
    def g_1():
        w = W(330)
        sx = w * 0.48
        stem = gothic_stem(sx, 0, CAP, SW, top="spire", bot="flat", ch=CH)
        nose = poly([
            (sx + 10, CAP + 10), (sx + 10, CAP - TW * 1.6),
            (20, CAP - 175), (20, CAP - 175 + TW * 1.25),
        ])
        base = hbar(35, w, 0, TW * 1.15, bevel_l=True, bevel_r=True)
        p = p_union(stem, nose, base)
        p = cap_notch(p, sx + SW, from_left=False, y=HY_CAP)
        return p

    # 2: Pointed Gothic upper hood + razor diagonal + PCB base
    def g_2():
        w = W(465)
        hood = lancet_ring(0, 350, w, CAP + OVER, SW, TW, top_h=190, bot_h=95)
        hood = p_diff(hood, rect(-20, 330, w + 20, 495))
        hood = p_diff(hood, poly([(-20, 490), (SW * 1.15, 555), (-20, 555)]))
        diag = diag_stroke(w - SW * 0.52, 505, SW * 0.52, TW * 0.5, SW * 0.96)
        base = hbar(0, w, 0, TW * 1.25, bevel_l=False, bevel_r=False, spur_r=True)
        spur = poly([(w - TW * 1.1, TW * 1.25), (w, TW * 1.25), (w, TW * 2.75)])
        p = p_union(hood, diag, base, spur)
        return p

    # 3: Twin pointed Gothic right arches + razor center beak
    def g_3():
        w = W(465)
        top_b = right_bowl(20, 365, w - 12, CAP + OVER * 0.5, SW * 0.95, TW)
        top_b = p_diff(top_b, rect(-20, 365 + TW * 1.15, w * 0.36, CAP - TW * 1.15))
        bot_b = right_bowl(0, -OVER * 0.5, w, 365 + TW * 1.15, SW, TW)
        bot_b = p_diff(bot_b, rect(-20, TW * 1.15, w * 0.36, 365))
        p = p_union(top_b, bot_b)
        p = cap_notch(p, w, from_left=False, y=220, depth_mult=0.35)
        return p

    # 4: Sharp Gothic triangular roof + cyberpunk cantilevered crossbar + pillar
    def g_4():
        w = W(485)
        sx = w - SW - 55
        stem = gothic_stem(sx, 0, CAP, SW, top="spire", bot="spur", ch=CH)
        diag = diag_stroke(sx + SW * 0.25, CAP, 25, 225, TW * 1.55)
        bar = hbar(0, w, 220, TW * 1.18, bevel_l=True, bevel_r=True)
        p = p_union(stem, diag, bar)
        p = cap_notch(p, sx + SW, from_left=False, y=HY_CAP)
        return p

    # 5: Sharp Gothic top bar + left spine + pointed lower bowl
    def g_5():
        w = W(465)
        top_b = hbar(25, w - 15, CAP - TW * 1.20, TW * 1.20, bevel_l=False, bevel_r=True)
        stem = gothic_stem(25, 365, CAP, SW * 0.92, top="bevel_l", bot="flat", ch=18)
        bot_b = right_bowl(0, -OVER * 0.5, w, 445, SW, TW)
        bot_b = p_diff(bot_b, rect(-20, TW * 1.15, w * 0.34, 365))
        p = p_union(top_b, stem, bot_b)
        p = cap_notch(p, w, from_left=False, y=230, depth_mult=0.35)
        return p

    # 6: Tall Gothic lancet left spine + pointed lower bowl
    def g_6():
        w = W(475)
        outer = lancet_ring(0, -OVER, w, CAP + OVER, SW, TW, top_h=215, bot_h=215)
        outer = p_diff(outer, poly([(w * 0.52, 405), (w + 30, 405), (w + 30, CAP - 125), (w * 0.52, CAP - 175)]))
        bowl = lancet_ring(0, -OVER, w, 455, SW, TW, top_h=150, bot_h=185)
        p = p_union(outer, bowl)
        p = cap_notch(p, 0, from_left=True, y=HY_CAP, depth_mult=0.38)
        return p

    # 7: Iconic cyberpunk-Gothic 7 — sharp top bar with hanging dagger + bold slashing leg
    def g_7():
        w = W(460)
        top_b = hbar(0, w, CAP - TW * 1.22, TW * 1.22, bevel_l=True, bevel_r=False)
        l_drop = poly([(0, CAP - TW * 1.22), (TW * 1.2, CAP - TW * 1.22), (0, CAP - TW * 2.95)])
        leg = diag_stroke(w - SW * 0.52, CAP - TW * 0.5, w * 0.32, 0, SW * 0.98)
        # Optional crisp cyberpunk cross-tick in Display cut
        parts = [top_b, l_drop, leg]
        if is_disp:
            parts.append(hbar(w * 0.34, w * 0.80, HY_CAP - TW * 0.45, TW * 0.90, bevel_l=True, bevel_r=True))
        return p_union(*parts)

    # 8: Twin stacked Gothic pointed lancet windows!
    def g_8():
        w = W(475)
        top_r = lancet_ring(22, 355, w - 22, CAP + OVER, SW * 0.92, TW, top_h=165, bot_h=120)
        bot_r = lancet_ring(0, -OVER, w, 415, SW, TW, top_h=125, bot_h=175)
        p = p_union(top_r, bot_r)
        if is_disp:
            p = cap_notch(p, 0, from_left=True, y=210, depth_mult=0.36)
        return p

    # 9: Inverted 6 — pointed upper lancet bowl + sweeping lower Gothic tail
    def g_9():
        w = W(475)
        outer = lancet_ring(0, -OVER, w, CAP + OVER, SW, TW, top_h=215, bot_h=215)
        outer = p_diff(outer, poly([(-30, 125), (w * 0.48, 175), (w * 0.48, 335), (-30, 335)]))
        bowl = lancet_ring(0, 285, w, CAP + OVER, SW, TW, top_h=185, bot_h=150)
        p = p_union(outer, bowl)
        p = cap_notch(p, w, from_left=False, y=HY_CAP, depth_mult=0.38)
        return p

    # ------------------------------------------------------------
    # PUNCTUATION & SYMBOLS (Consistent Diamond Lozenge + PCB DNA)
    # ------------------------------------------------------------
    def g_period():
        return diamond(70, 56, 56, 56)

    def g_comma():
        d = diamond(75, 64, 54, 54)
        tail = poly([(75, 45), (125, 64), (42, -110), (14, -95)])
        return p_union(d, tail)

    def g_colon():
        return p_union(diamond(75, 56, 54, 54), diamond(75, 385, 54, 54))

    def g_semicolon():
        return p_union(g_comma(), diamond(75, 385, 54, 54))

    def g_exclam():
        stem = poly([
            (36, 185), (114, 185),
            (132, CAP), (18, CAP),
        ])
        dot = diamond(75, 56, 56, 56)
        p = p_union(stem, dot)
        p = cap_notch(p, 24, from_left=True, y=HY_CAP, depth_mult=0.35)
        return p

    def g_question():
        w = W(420)
        hook = lancet_ring(0, 355, w, CAP + OVER, SW * 0.92, TW, top_h=180, bot_h=120)
        hook = p_diff(hook, rect(-20, 340, w * 0.48, 520))
        stem = gothic_stem(w * 0.42, 185, 395, SW * 0.85, top="flat", bot="flat", ch=14)
        dot = diamond(w * 0.42 + SW * 0.425, 56, 54, 54)
        return p_union(hook, stem, dot)

    def g_hyphen():
        return hbar(0, W(290), 275, TW * 1.25, bevel_l=True, bevel_r=True)

    def g_emdash():
        return hbar(0, W(620), 275, TW * 1.20, bevel_l=True, bevel_r=True)

    def g_underscore():
        return hbar(0, W(480), -110, TW * 1.15, bevel_l=True, bevel_r=True)

    def g_slash():
        return diag_stroke(TW * 0.8, -90, W(340) - TW * 0.8, CAP + 30, SW * 0.72)

    def g_plus():
        w = W(410)
        cx, cy = w / 2.0, 340
        h = hbar(0, w, cy - TW * 0.65, TW * 1.30, bevel_l=True, bevel_r=True)
        v = gothic_stem(cx - TW * 0.65, cy - 195, cy + 195, TW * 1.30, top="spire", bot="point", ch=18)
        return p_union(h, v)

    def g_ampersand():
        w = W(520)
        top_o = lancet_ring(55, 360, w - 125, CAP + OVER, SW * 0.82, TW, top_h=145, bot_h=110)
        bot_o = lancet_ring(0, -OVER, w - 75, 420, SW * 0.90, TW, top_h=125, bot_h=160)
        bot_o = p_diff(bot_o, rect(w * 0.56, 130, w, 395))
        diag = diag_stroke(w * 0.25, 465, w - SW * 0.45, 0, SW * 0.88)
        tail = diag_stroke(w - 25, 335, w * 0.54, 15, TW * 1.35)
        return p_union(top_o, bot_o, diag, tail)

    def g_parenleft():
        w = W(220)
        r = lancet_ring(0, -110, w * 2.1, CAP + 60, SW * 0.78, TW, top_h=240, bot_h=240)
        return p_diff(r, rect(w, -150, w * 2.4, CAP + 100))

    def g_parenright():
        w = W(220)
        r = lancet_ring(-w * 1.1, -110, w, CAP + 60, SW * 0.78, TW, top_h=240, bot_h=240)
        return p_diff(r, rect(-w * 1.4, -150, 0, CAP + 100))

    def g_bracketleft():
        w = W(215)
        s = gothic_stem(0, -100, CAP + 30, SW * 0.78, top="flat", bot="flat", ch=14)
        t = hbar(0, w, CAP + 30 - TW * 1.1, TW * 1.1, bevel_l=False, bevel_r=True)
        b = hbar(0, w, -100, TW * 1.1, bevel_l=False, bevel_r=True)
        return p_union(s, t, b)

    def g_bracketright():
        w = W(215)
        s = gothic_stem(w - SW * 0.78, -100, CAP + 30, SW * 0.78, top="flat", bot="flat", ch=14)
        t = hbar(0, w, CAP + 30 - TW * 1.1, TW * 1.1, bevel_l=True, bevel_r=False)
        b = hbar(0, w, -100, TW * 1.1, bevel_l=True, bevel_r=False)
        return p_union(s, t, b)

    def g_quotesingle():
        return poly([(25, CAP), (105, CAP), (82, CAP - 210), (48, CAP - 210)])

    def g_quotedbl():
        q1 = g_quotesingle()
        q2 = poly([(155, CAP), (235, CAP), (212, CAP - 210), (178, CAP - 210)])
        return p_union(q1, q2)

    def g_hash():
        w = W(500)
        s1 = diag_stroke(145, 70, 215, CAP - 50, SW * 0.65)
        s2 = diag_stroke(315, 70, 385, CAP - 50, SW * 0.65)
        b1 = hbar(25, w - 10, 475, TW * 1.20, bevel_l=True, bevel_r=True)
        b2 = hbar(0, w - 35, 220, TW * 1.20, bevel_l=True, bevel_r=True)
        return p_union(s1, s2, b1, b2)

    def g_at():
        w = W(580)
        outer = lancet_ring(0, -60, w, CAP + 10, SW * 0.65, TW * 0.95, top_h=220, bot_h=220)
        outer = p_diff(outer, rect(w * 0.55, -80, w + 30, 155))
        inner = lancet_ring(145, 160, w - 155, 540, SW * 0.65, TW * 0.90, top_h=120, bot_h=120)
        stem = rect(w - 155 - SW * 0.60, 160, w - 155, 520)
        return p_union(outer, inner, stem)

    def g_asterisk():
        cx, cy = 140, CAP - 120
        parts = [diamond(cx, cy, 38, 38)]
        for ang in (0, 60, 120):
            rad = math.radians(ang)
            dx, dy = math.cos(rad) * 115, math.sin(rad) * 115
            parts.append(diag_stroke(cx - dx, cy - dy, cx + dx, cy + dy, 34, cap_flat=False))
        return p_union(*parts)

    def g_notdef():
        return p_diff(rect(40, 0, 460, CAP), rect(105, 65, 395, CAP - 65))

    builders = {
        ".notdef": g_notdef,
        "A": g_A, "B": g_B, "C": g_C, "D": g_D, "E": g_E, "F": g_F, "G": g_G,
        "H": g_H, "I": g_I, "J": g_J, "K": g_K, "L": g_L, "M": g_M, "N": g_N,
        "O": g_O, "P": g_P, "Q": g_Q, "R": g_R, "S": g_S, "T": g_T, "U": g_U,
        "V": g_V, "W": g_W, "X": g_X, "Y": g_Y, "Z": g_Z,
        "a": g_a, "b": g_b, "c": g_c, "d": g_d, "e": g_e, "f": g_f, "g": g_g,
        "h": g_h, "i": g_i, "j": g_j, "k": g_k, "l": g_l, "m": g_m, "n": g_n,
        "o": g_o, "p": g_p, "q": g_q, "r": g_r, "s": g_s, "t": g_t, "u": g_u,
        "v": g_v, "w": g_w, "x": g_x, "y": g_y, "z": g_z,
        "zero": g_0, "one": g_1, "two": g_2, "three": g_3, "four": g_4,
        "five": g_5, "six": g_6, "seven": g_7, "eight": g_8, "nine": g_9,
        "period": g_period, "comma": g_comma, "colon": g_colon, "semicolon": g_semicolon,
        "exclam": g_exclam, "question": g_question, "hyphen": g_hyphen, "emdash": g_emdash,
        "underscore": g_underscore, "slash": g_slash, "plus": g_plus, "ampersand": g_ampersand,
        "parenleft": g_parenleft, "parenright": g_parenright, "bracketleft": g_bracketleft,
        "bracketright": g_bracketright, "quotesingle": g_quotesingle, "quotedbl": g_quotedbl,
        "numbersign": g_hash, "at": g_at, "asterisk": g_asterisk,
    }

    # Build and normalize each glyph path with optical sidebearings
    lsb_base = 52 if is_disp else 62
    rsb_base = 52 if is_disp else 62
    results = {}
    for gname, fn in builders.items():
        raw = fn()
        # Simplify and set PostScript CFF winding (CCW outer, CW inner)
        clean = pathops.simplify(raw, fix_winding=True, clockwise=False)
        bounds = clean.bounds
        if bounds is None:
            results[gname] = (pathops.Path(), 400, 0)
            continue
        x0, y0, x1, y1 = bounds
        # Sidebearings: slightly tighter on round/angled glyphs for visual rhythm
        if gname in ("A", "V", "W", "Y", "X", "T", "v", "w", "x", "y"):
            lsb, rsb = lsb_base - 18, rsb_base - 18
        elif gname in ("O", "C", "G", "Q", "S", "o", "c", "e", "s", "zero", "eight"):
            lsb, rsb = lsb_base - 8, rsb_base - 8
        elif gname in ("I", "i", "l", "exclam", "period", "comma", "colon", "semicolon"):
            lsb, rsb = lsb_base + 4, rsb_base + 4
        else:
            lsb, rsb = lsb_base, rsb_base
        dx = round(lsb - x0)
        shifted = pathops.Path()
        tpen = TransformPen(shifted.getPen(), (1, 0, 0, 1, dx, 0))
        clean.draw(tpen)
        adv = int(round((x1 - x0) + lsb + rsb))
        results[gname] = (shifted, adv, int(round(lsb)))

    # Space character
    results["space"] = (pathops.Path(), 280 if is_disp else 310, 0)
    return results


CMAP = {
    0x0020: "space",
    **{ord(c): c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"},
    0x0030: "zero", 0x0031: "one", 0x0032: "two", 0x0033: "three", 0x0034: "four",
    0x0035: "five", 0x0036: "six", 0x0037: "seven", 0x0038: "eight", 0x0039: "nine",
    0x002E: "period", 0x002C: "comma", 0x003A: "colon", 0x003B: "semicolon",
    0x0021: "exclam", 0x003F: "question", 0x002D: "hyphen", 0x2014: "emdash",
    0x005F: "underscore", 0x002F: "slash", 0x002B: "plus", 0x0026: "ampersand",
    0x0028: "parenleft", 0x0029: "parenright", 0x005B: "bracketleft",
    0x005D: "bracketright", 0x0027: "quotesingle", 0x0022: "quotedbl",
    0x0023: "numbersign", 0x0040: "at", 0x002A: "asterisk",
}

KERN_FEA = """
feature kern {
    pos A F -18;
    pos A T -48;
    pos A V -55;
    pos A W -45;
    pos A Y -55;
    pos A O -16;
    pos F A -48;
    pos F O -14;
    pos F T 10;
    pos F E -8;
    pos T A -48;
    pos T E -12;
    pos T O -22;
    pos T a -28;
    pos T e -28;
    pos T o -28;
    pos T r -24;
    pos V A -55;
    pos W A -42;
    pos Y A -55;
    pos L T -45;
    pos L V -40;
    pos L Y -48;
    pos P A -42;
    pos R S -10;
    pos H O -10;
    pos O U -10;
    pos U R -8;
    pos R T -16;
    pos E R -8;
    pos T R -10;
    pos A U -14;
    pos f t -10;
    pos r s -8;
    pos a f -8;
} kern;
"""


def compile_font(style="Display"):
    glyph_data = make_glyphs(style)
    glyph_order = [".notdef", "space"] + [g for g in glyph_data.keys() if g not in (".notdef", "space")]

    fb = FontBuilder(UPM, isTTF=False)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(CMAP)

    charstrings = {}
    metrics = {}
    for gname in glyph_order:
        p, adv, lsb = glyph_data[gname]
        t2pen = T2CharStringPen(adv, None)
        rpen = RoundingPen(t2pen)
        p.draw(rpen)
        charstrings[gname] = t2pen.getCharString()
        metrics[gname] = (adv, lsb)

    family = f"After Hours {style}" if style == "Heading" else "After Hours"
    ps_name = f"AfterHours-{style}"
    full_name = f"After Hours {style}"

    fb.setupCFF(
        psName=ps_name,
        fontInfo={
            "FullName": full_name,
            "FamilyName": "After Hours",
            "Weight": "Bold" if style == "Display" else "SemiBold",
            "Notice": "Original Gothic-Cyberpunk Latin typeface created for After Hours. Open use with credit.",
        },
        charStringsDict=charstrings,
        privateDict={
            "defaultWidthX": 0,
            "nominalWidthX": 0,
            "BlueValues": [-14, 0, 505, 520, 740, 756],
        },
    )
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ASC, descent=DESC, lineGap=60)
    fb.setupNameTable({
        "familyName": "After Hours",
        "styleName": style,
        "uniqueFontIdentifier": f"1.000;AFTH;{ps_name}",
        "fullName": full_name,
        "version": "Version 1.000",
        "psName": ps_name,
        "manufacturer": "OmniForge Type Lab",
        "designer": "OmniForge Type Lab (deal-closer)",
        "description": (
            "Original Gothic-Cyberpunk Latin display typeface fusing pointed cathedral lancet arches "
            "and high-contrast blackletter spurs with 45-degree PCB chamfers and aligned cyberpunk circuit cuts."
        ),
        "typographicFamily": "After Hours",
        "typographicSubfamily": style,
    })
    fb.setupOS2(
        sTypoAscender=ASC,
        sTypoDescender=DESC,
        sTypoLineGap=60,
        usWinAscent=ASC + 20,
        usWinDescent=abs(DESC) + 20,
        sxHeight=XH,
        sCapHeight=CAP,
        usWeightClass=700 if style == "Display" else 600,
        fsType=0,  # Installable embedding
        achVendID="AFTH",
    )
    fb.setupPost(formatType=3.0)

    # Add OpenType GPOS kerning feature
    addOpenTypeFeaturesFromString(fb.font, KERN_FEA)

    otf_path = os.path.join(OUT_DIR, f"{ps_name}.otf")
    woff2_path = os.path.join(OUT_DIR, f"{ps_name}.woff2")
    fb.font.save(otf_path)

    # Also save WOFF2 for ultra-fast website loading
    fb.font.flavor = "woff2"
    fb.font.save(woff2_path)
    print(f"Built {otf_path} ({os.path.getsize(otf_path):,} bytes) + {woff2_path} ({os.path.getsize(woff2_path):,} bytes), {len(glyph_order)} glyphs")
    return otf_path, woff2_path


if __name__ == "__main__":
    compile_font("Display")
    compile_font("Heading")

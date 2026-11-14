# Madarek studio shots: the brand's own pieces (thermos, folder, notebook, pencil cup, gift box, desk flag, cap, award) rendered
# as product photography, alone or as a group on one floor with its real shadow. Blender as a Python module (pip install bpy), Cycles.
#
#   LAYOUT=tools/studio/layouts/family.json python3 tools/studio/shots.py shot x /abs/path/raw.png 128 1700
#   python3 tools/studio/finish.py /abs/path/raw.png family
#
# Arguments after the script: two placeholders (kept from the single-piece script this grew from), the output PNG (absolute path),
# the samples, and pixels per metre. The layout file lists the pieces: i (piece), v (navy / blue / white), x and y on the floor in
# metres, and optionally tilt (camera), look (contrast), rig (how far the lights stand back: larger for a wider group).
# The home page uses: family (the «why» section), thermos-trio and folder-trio (the two leading category cards) and the six
# single pieces (the other category cards). Ammar 14 Nov 2026, asked for studio photos of the products: «ماعنا دبر حالك».
import bpy, bmesh, math, sys, os, addon_utils
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex')
item, var, out = sys.argv[1], sys.argv[2], sys.argv[3]
SAMPLES = int(sys.argv[4]) if len(sys.argv) > 4 else 96
PXM = float(sys.argv[5]) if len(sys.argv) > 5 else 2900.0   # pixels per metre
TILT = 11.0  # camera looks down by this many degrees
LSCALE = float(os.environ.get('LSCALE', '0.26'))
VIEW = os.environ.get('VIEW', 'Standard')
FLOOR = os.environ.get('FLOOR', '0') == '1'

def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1.0,)

NAVY, BLUE, TEAL, GOLD = '#0D244C', '#3263DB', '#50C4C8', '#D1B22B'
WHITE = '#F3F2EF'
VCOL = {'navy': NAVY, 'blue': BLUE, 'white': WHITE}
LOGO = {'navy': 'white', 'blue': 'white', 'white': 'navy'}

# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable('cycles', default_set=True, persistent=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.cycles.use_adaptive_sampling = True
sc.render.film_transparent = True
sc.cycles.film_transparent_glass = True
sc.view_settings.view_transform = VIEW
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'
sc.render.image_settings.color_depth = '8'

world = bpy.data.worlds.new('w'); sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs[0].default_value = lin('#E9E6E0'); bg.inputs[1].default_value = 0.42 * LSCALE

def link(a, b): a.id_data.links.new(a, b)

def mat(name, color, rough=0.5, metal=0.0, coat=0.0, sheen=0.0, trans=0.0, ior=1.45, spec=0.5, bump=0.0, bscale=900.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = lin(color) if isinstance(color, str) else color
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Coat Weight'].default_value = coat
    p.inputs['Coat Roughness'].default_value = 0.12
    p.inputs['Sheen Weight'].default_value = sheen
    p.inputs['Transmission Weight'].default_value = trans
    p.inputs['IOR'].default_value = ior
    p.inputs['Specular IOR Level'].default_value = spec
    if bump > 0:
        nt = m.node_tree
        tc = nt.nodes.new('ShaderNodeTexCoord'); n = nt.nodes.new('ShaderNodeTexNoise')
        n.inputs['Scale'].default_value = bscale; n.inputs['Detail'].default_value = 2.0
        b = nt.nodes.new('ShaderNodeBump'); b.inputs['Strength'].default_value = bump; b.inputs['Distance'].default_value = 0.0004
        link(tc.outputs['Object'], n.inputs['Vector']); link(n.outputs['Fac'], b.inputs['Height']); link(b.outputs['Normal'], p.inputs['Normal'])
    return m

def mat_img(name, path, rough=0.5, alpha=False, sheen=0.0, tint=None, emit=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; p = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path)
    t.interpolation = 'Cubic'; t.extension = 'CLIP'
    if tint is not None:
        p.inputs['Base Color'].default_value = lin(tint)
    else:
        link(t.outputs['Color'], p.inputs['Base Color'])
    if alpha:
        link(t.outputs['Alpha'], p.inputs['Alpha'])
    p.inputs['Roughness'].default_value = rough
    p.inputs['Sheen Weight'].default_value = sheen
    p.inputs['Coat Weight'].default_value = coat
    if emit > 0:
        p.inputs['Emission Color'].default_value = (1, 1, 1, 1); p.inputs['Emission Strength'].default_value = emit
    return m

def obj_from_bm(bm, name, material=None, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    if material: o.data.materials.append(material)
    if smooth:
        for f in o.data.polygons: f.use_smooth = True
    return o

def bevel(o, w, segs=4, angle=None):
    m = o.modifiers.new('bev', 'BEVEL'); m.width = w; m.segments = segs
    if angle is not None:
        m.limit_method = 'ANGLE'; m.angle_limit = math.radians(angle)
    m.harden_normals = False
    return m

def box(name, sx, sy, sz, loc=(0, 0, 0), material=None, bev=0.0015, segs=4):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz)) + Vector(loc)
    o = obj_from_bm(bm, name, material, smooth=False)
    if bev > 0: bevel(o, bev, segs)
    o.data.shade_smooth() if bev > 0 else None
    return o

def lathe(name, prof, n=128, material=None, cap_top=True, cap_bot=True):
    """prof: list of (r, z) from bottom to top."""
    bm = bmesh.new(); rings = []
    for (r, z) in prof:
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    if cap_bot and prof[0][0] > 0: bm.faces.new(list(reversed(rings[0])))
    if cap_top and prof[-1][0] > 0: bm.faces.new(rings[-1])
    return obj_from_bm(bm, name, material)

def decal_cyl(name, r, zc, w, h, img, face_ang=-math.pi / 2, nx=48, ny=12, material=None):
    """Curved logo decal on a cylinder of radius r, centred on angle face_ang (−90° = facing −Y)."""
    bm = bmesh.new(); uv = bm.loops.layers.uv.new()
    span = w / r; vs = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u = i / nx; v = j / ny
            a = face_ang + (u - 0.5) * span   # u grows to the right as seen from front
            row.append((bm.verts.new((r * math.cos(a), r * math.sin(a), zc - h / 2 + v * h)), u, v))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            q = [vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]]
            f = bm.faces.new([x[0] for x in q])
            for l, x in zip(f.loops, q): l[uv].uv = (x[1], x[2])
    m = material or mat_img(name + 'm', img, rough=0.45, alpha=True)
    return obj_from_bm(bm, name, m)

def decal_plane(name, w, h, img, loc, rot=(math.pi / 2, 0, 0), material=None, flip=False):
    """Plane facing −Y by default (rot x=90°)."""
    bm = bmesh.new(); uv = bm.loops.layers.uv.new()
    pts = [(-w / 2, -h / 2, 0, 0), (w / 2, -h / 2, 1, 0), (w / 2, h / 2, 1, 1), (-w / 2, h / 2, 0, 1)]
    vs = [bm.verts.new((p[0], p[1], 0)) for p in pts]
    f = bm.faces.new(vs)
    for l, p in zip(f.loops, pts): l[uv].uv = ((1 - p[2]) if flip else p[2], p[3])
    o = obj_from_bm(bm, name, material or mat_img(name + 'm', img, rough=0.5, alpha=True), smooth=False)
    o.rotation_euler = Euler((-rot[0], rot[1], rot[2])) if False else Euler(rot)
    o.location = loc
    return o

def group(objs, yaw=0.0, roll=0.0, pitch=0.0, loc=(0, 0, 0)):
    e = bpy.data.objects.new('grp', None); sc.collection.objects.link(e)
    for o in objs: o.parent = e
    e.rotation_euler = Euler((math.radians(pitch), math.radians(roll), math.radians(yaw)))
    e.location = loc
    return e

def logo_path(c): return os.path.join(TEX, f'dlogo_{c}.png')
LOGO_AR = 860 / 1600.0  # h / w of logo canvas

# ---------------------------------------------------------------- items
def thermos():
    c = VCOL[var]
    body_m = mat('body', c, rough=0.38, coat=0.25, bump=0.04, bscale=2500)
    steel = mat('steel', '#C9CDD2', rough=0.22, metal=1.0)
    R, H = 0.036, 0.192
    prof = [(0.0, 0.0), (R - 0.004, 0.0), (R - 0.0012, 0.0006), (R, 0.003), (R, H - 0.012)]
    for k in range(1, 9):
        t = k / 8; prof.append((R - (R - 0.0285) * (1 - math.cos(t * math.pi / 2)) ** 1.0 * 1.0, H - 0.012 + 0.014 * math.sin(t * math.pi / 2)))
    prof.append((0.0285, H + 0.004))
    body = lathe('body', prof, material=body_m, cap_top=True)
    ring = lathe('ring', [(0.0284, H + 0.002), (0.0288, H + 0.003), (0.0288, H + 0.007), (0.0284, H + 0.008)], material=steel)
    cz = H + 0.008; ch = 0.026
    capp = [(0.0, cz), (0.0292, cz), (0.0298, cz + 0.001), (0.0298, cz + ch - 0.004), (0.0292, cz + ch - 0.0012), (0.027, cz + ch), (0.0, cz + ch)]
    cap = lathe('cap', capp, material=steel)
    lw = 0.044
    d = decal_cyl('logo', R + 0.0003, 0.105, lw, lw * LOGO_AR, logo_path(LOGO[var]))
    return [body, ring, cap, d], dict(yaw=-12)

def folder():
    c = VCOL[var]
    W, Hh, T = 0.22, 0.31, 0.005
    edge = mat('edge', c, rough=0.55)
    f = box('folder', W, T, Hh, loc=(0, 0, Hh / 2), material=edge, bev=0.0012, segs=3)
    front = decal_plane('front', W - 0.0016, Hh - 0.0016, os.path.join(TEX, f'folder_{var}.png'), loc=(0, -T / 2 - 0.0002, Hh / 2),
                        material=mat_img('frontm', os.path.join(TEX, f'folder_{var}.png'), rough=0.42, coat=0.15))
    paper = mat_img('lh', os.path.join(TEX, 'letterhead.png'), rough=0.7)
    sheet = box('sheet', 0.205, 0.0006, 0.29, loc=(0.004, 0.0002, 0.29 / 2 + 0.045), material=mat('pw', '#F7F6F2', rough=0.7), bev=0.0002, segs=1)
    # visible part of the letterhead (only top shows)
    lhp = decal_plane('lhp', 0.203, 0.288, None, loc=(0.004, -0.0003 - 0.00001, 0.29 / 2 + 0.045), material=paper)
    return [f, front, sheet, lhp], dict(yaw=-24, pitch=-4)

def notebook():
    c = VCOL[var]
    W, Hh, T = 0.148, 0.21, 0.018
    cover = mat('cover', c, rough=0.62, bump=0.12, bscale=1800)
    pages = mat('pages', '#F1EBDD', rough=0.8, bump=0.25, bscale=4000)
    band_c = TEAL if var != 'blue' else NAVY
    band = mat('band', band_c, rough=0.5, sheen=0.3)
    ct = 0.0025
    fc = box('fc', W, ct, Hh, loc=(0, -T / 2 + ct / 2, Hh / 2), material=cover, bev=0.0012, segs=3)
    bc = box('bc', W, ct, Hh, loc=(0, T / 2 - ct / 2, Hh / 2), material=cover, bev=0.0012, segs=3)
    pb = box('pb', W - 0.006, T - 2 * ct + 0.0004, Hh - 0.006, loc=(-0.003, 0, Hh / 2), material=pages, bev=0.0006, segs=2)
    # spine on the RIGHT (Arabic binding)
    sp = lathe('spine', [(0.0, 0.0), (T / 2, 0.0), (T / 2, Hh), (0.0, Hh)], n=64, material=cover)
    sp.scale = (0.45, 1, 1); sp.location = (W / 2 - 0.0015, 0, 0)
    # elastic band near the opening (left) edge
    bw = 0.008; bx = -W / 2 + 0.018
    b1 = box('b1', bw, 0.0012, Hh + 0.0016, loc=(bx, -T / 2 - 0.0006, Hh / 2), material=band, bev=0.0003, segs=2)
    b2 = box('b2', bw, 0.0012, Hh + 0.0016, loc=(bx, T / 2 + 0.0006, Hh / 2), material=band, bev=0.0003, segs=2)
    b3 = box('b3', bw, T + 0.0024, 0.0012, loc=(bx, 0, Hh + 0.0008), material=band, bev=0.0003, segs=2)
    lw = 0.074
    lm = mat_img('lm', logo_path(LOGO[var]), rough=0.35, alpha=True, coat=0.3)
    d = decal_plane('logo', lw, lw * LOGO_AR, None, loc=(0.006, -T / 2 - 0.00025, Hh * 0.6), material=lm)
    return [fc, bc, pb, sp, b1, b2, b3, d], dict(yaw=28)

def pencilcup():
    c = VCOL[var]
    cupm = mat('cup', c, rough=0.42, coat=0.2, bump=0.03, bscale=2500)
    inner = mat('inner', '#1A1F2A' if var != 'white' else '#CFCBC3', rough=0.6)
    R, H, t = 0.040, 0.105, 0.0022
    outer = lathe('cup', [(0.0, 0.0), (R - 0.003, 0.0), (R - 0.0006, 0.0005), (R, 0.003), (R, H - 0.0012), (R - 0.0008, H), (R - t + 0.0008, H), (R - t, H - 0.0012), (R - t, 0.006), (0.0, 0.006)], material=cupm)
    objs = [outer]
    # pencils
    pal = [NAVY, BLUE, TEAL, GOLD, '#F4F2EC', '#7FA3EE', '#2E8F93', '#E7CF63', BLUE, NAVY, TEAL]
    wood = mat('wood', '#E2BE8C', rough=0.7, bump=0.3, bscale=600)
    lead = mat('lead', '#2B2B2E', rough=0.35, metal=0.3)
    import random; random.seed(7)
    spots = [(-0.020, 0.008), (-0.008, 0.016), (0.006, 0.014), (0.019, 0.006), (-0.014, -0.006), (0.000, -0.002), (0.014, -0.010), (-0.024, -0.016), (-0.004, -0.019), (0.012, 0.022), (0.025, -0.018)]
    for k, (px, py) in enumerate(spots):
        L = 0.165 + random.uniform(-0.012, 0.016) - (0.01 if py < -0.01 else 0)
        rr = 0.0037
        pm = mat(f'p{k}', pal[k % len(pal)], rough=0.32, coat=0.4)
        # hex body via lathe with n=6
        body = lathe(f'pb{k}', [(0.0, 0.0), (rr, 0.0), (rr, L)], n=6, material=pm)
        for f in body.data.polygons: f.use_smooth = False
        cone = lathe(f'pc{k}', [(rr * 0.98, L), (rr * 0.45, L + 0.014), (0.0, L + 0.0195)], n=24, material=wood)
        tip = lathe(f'pt{k}', [(rr * 0.40, L + 0.0145), (0.0, L + 0.020)], n=16, material=lead, cap_top=False)
        g = group([body, cone, tip])
        px, py = px * 0.85, py * 0.85
        ang = math.atan2(py, px); lean = 3 + 5 * (math.hypot(px, py) / 0.03)
        g.location = (px, py, 0.008)
        g.rotation_euler = Euler((math.radians(-lean * math.sin(ang)), math.radians(lean * math.cos(ang)), random.uniform(0, 1)))
        objs += [g]
    lw = 0.050
    d = decal_cyl('logo', R + 0.0003, 0.052, lw, lw * LOGO_AR, logo_path(LOGO[var]))
    objs.append(d)
    return objs, dict(yaw=-8)

def giftbox():
    c = VCOL[var]
    S, Hb, Hl = 0.15, 0.10, 0.034
    bm_ = mat('box', c, rough=0.55, bump=0.1, bscale=2000)
    lid_c = c
    lm_ = mat('lid', lid_c, rough=0.5, bump=0.1, bscale=2000)
    base = box('base', S, S, Hb, loc=(0, 0, Hb / 2), material=bm_, bev=0.0012, segs=3)
    lid = box('lid', S + 0.004, S + 0.004, Hl, loc=(0, 0, Hb - Hl / 2 + 0.002), material=lm_, bev=0.0012, segs=3)
    rib_c = GOLD if var == 'navy' else (NAVY if var == 'white' else '#F3F2EF')
    rib = mat('rib', rib_c, rough=0.28, sheen=0.4, coat=0.3, metal=0.0)
    rw = 0.014
    r1 = box('r1', rw, S + 0.0052, 0.0009, loc=(0, 0, Hb + 0.0024), material=rib, bev=0.0002, segs=1)
    r2 = box('r2', rw, 0.0009, Hl + 0.0006, loc=(0, -S / 2 - 0.0024, Hb - Hl / 2 + 0.0022), material=rib, bev=0.0002, segs=1)
    r3 = box('r3', rw, 0.0009, Hl + 0.0006, loc=(0, S / 2 + 0.0024, Hb - Hl / 2 + 0.0022), material=rib, bev=0.0002, segs=1)
    lw = 0.074
    d = decal_plane('logo', lw, lw * LOGO_AR, None, loc=(0, -S / 2 - 0.0003, (Hb - Hl) / 2 + 0.002),
                    material=mat_img('lgm', logo_path(LOGO[var]), rough=0.3, alpha=True, coat=0.5))
    return [base, lid, r1, r2, r3, d], dict(yaw=30)

def deskflag():
    c = VCOL[var]
    chrome = mat('chrome', '#D7DADF', rough=0.08, metal=1.0)
    base = lathe('base', [(0.0, 0.0), (0.034, 0.0), (0.036, 0.002), (0.036, 0.008), (0.033, 0.012), (0.012, 0.016), (0.006, 0.018), (0.0, 0.018)], material=chrome)
    P = 0.30
    pole = lathe('pole', [(0.0, 0.016), (0.0022, 0.016), (0.0022, P), (0.0, P)], n=32, material=chrome)
    ball = lathe('ball', [(0.0, P - 0.001)] + [(0.0055 * math.sin(t * math.pi / 16), P + 0.0055 - 0.0055 * math.cos(t * math.pi / 16)) for t in range(1, 16)] + [(0.0, P + 0.011)], n=48, material=chrome)
    FW, FH = 0.165, 0.112
    img = os.path.join(TEX, f'flag_{var}.png')
    fm = mat_img('flagm', img, rough=0.85, sheen=0.6)
    # wavy cloth grid: attached at pole (x=0) and extending to −x
    bm = bmesh.new(); uv = bm.loops.layers.uv.new(); nx, ny = 64, 32; vs = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u = i / nx; v = j / ny
            x = -0.003 - u * FW
            amp = 0.0105 * (u ** 0.9)
            y = amp * math.sin(u * 2.3 * math.pi + 0.4 + v * 0.35)
            z = P - 0.006 - (1 - v) * FH - 0.004 * u * (1 - v)
            row.append((bm.verts.new((x, y, z)), 1 - u, v))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            q = [vs[j][i], vs[j + 1][i], vs[j + 1][i + 1], vs[j][i + 1]]
            f = bm.faces.new([x[0] for x in q])
            for l, x in zip(f.loops, q): l[uv].uv = (x[1], x[2])
    cloth = obj_from_bm(bm, 'cloth', fm)
    so = cloth.modifiers.new('sol', 'SOLIDIFY'); so.thickness = 0.0006
    return [base, pole, ball, cloth], dict(yaw=-14)

def cap():
    c = VCOL[var]
    fab = mat('fab', c, rough=0.88, sheen=0.7, bump=0.35, bscale=5200)
    a, b, hh = 0.094, 0.104, 0.108   # crown half-width (x), half-depth (y), height
    def CZ(th, yy):
        top = hh * math.sin(th) ** 0.85
        lift = 0.014 * max(0.0, yy) ** 1.5 * (1 - math.sin(th))
        return top + lift
    def RR(th, yy):
        w = max(0.0, -yy)
        return math.cos(th) ** (1.0 - 0.38 * w)
    # crown: squashed hemisphere, slightly fuller at front
    bm = bmesh.new(); n, m = 96, 40; rings = []
    for k in range(m + 1):
        th = (k / m) * (math.pi / 2)        # 0 at base → 90° at top
        ring = []
        for i in range(n):
            ph = 2 * math.pi * i / n
            yy = math.sin(ph)
            front = 1.0 + (0.06 if yy < 0 else 0.0) * (-yy)
            r = RR(th, yy)
            x = a * r * math.cos(ph)
            y = b * r * yy * front
            z = CZ(th, yy)
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
    for k in range(m):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    crown = obj_from_bm(bm, 'crown', fab)
    so = crown.modifiers.new('sol', 'SOLIDIFY'); so.thickness = 0.002; so.offset = -1
    # panel seams: thin dark lines (6 panels) as slightly raised tubes
    seam = mat('seam', c, rough=0.9, sheen=0.5)
    objs = [crown]
    for s in range(6):
        ph = 2 * math.pi * s / 6 + math.pi / 2 + math.pi / 6
        pts = []
        for k in range(0, m + 1):
            th = (k / m) * (math.pi / 2); yy = math.sin(ph)
            front = 1.0 + (0.06 if yy < 0 else 0.0) * (-yy)
            r = RR(th, yy) * 1.012
            pts.append(Vector((a * r * math.cos(ph), b * r * yy * front, CZ(th, yy) * 1.006)))
        cu = bpy.data.curves.new(f'seam{s}', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0011; cu.bevel_resolution = 2
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for p, v in zip(sp.points, pts): p.co = (v.x, v.y, v.z, 1)
        o = bpy.data.objects.new(f'seam{s}', cu); sc.collection.objects.link(o); o.data.materials.append(seam); objs.append(o)
    btn = lathe('btn', [(0.0, hh - 0.002), (0.0075, hh - 0.002), (0.0078, hh + 0.001), (0.006, hh + 0.0035), (0.0, hh + 0.0045)], n=48, material=fab)
    objs.append(btn)
    # brim
    bm = bmesh.new(); L = 0.088; nt, ns = 24, 48; vs = []
    for j in range(nt + 1):
        row = []
        t = j / nt
        for i in range(ns + 1):
            th = math.pi * (0.02 + 0.96 * i / ns)   # across the front
            sn = math.sin(th)
            x0, y0 = a * 0.99 * math.cos(th), -b * sn * (1 + 0.06 * sn) + 0.001
            x1, y1 = a * 0.86 * math.cos(th), -(b * 1.06 + L * sn ** 0.6) * sn ** 0.7
            x = x0 + (x1 - x0) * t; y = y0 + (y1 - y0) * t
            z = 0.006 - 0.008 * t - 0.016 * (x / a) ** 2 * t
            row.append(bm.verts.new((x, y, z)))
        vs.append(row)
    for j in range(nt):
        for i in range(ns):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    brim = obj_from_bm(bm, 'brim', fab)
    so = brim.modifiers.new('sol', 'SOLIDIFY'); so.thickness = 0.0035
    bv = brim.modifiers.new('bev', 'BEVEL'); bv.width = 0.0012; bv.segments = 2
    objs.append(brim)
    # embroidered logo projected on the front panel
    lw = 0.068; lh = lw * LOGO_AR; zc = 0.056
    bm = bmesh.new(); uv = bm.loops.layers.uv.new(); nx, ny = 40, 20; vs = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x = (u - 0.5) * lw; z = zc - lh / 2 + v * lh
            # solve on the front meridian region: find th so that CZ(th, yy≈-1) = z
            lo, hi = 0.0, math.pi / 2
            for _ in range(40):
                md = (lo + hi) / 2
                if CZ(md, -0.95) < z: lo = md
                else: hi = md
            th = lo; r = RR(th, -0.95)
            yy = -math.sqrt(max(0.0, 1 - (x / (a * r)) ** 2))
            y = b * r * yy * (1.0 + 0.06 * (-yy)) - 0.0014
            row.append((bm.verts.new((x, y, z)), u, v))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            q = [vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]]
            f = bm.faces.new([x[0] for x in q])
            for l, x in zip(f.loops, q): l[uv].uv = (x[1], x[2])
    em = mat_img('emb', logo_path(LOGO[var]), rough=0.55, alpha=True, sheen=0.5)
    objs.append(obj_from_bm(bm, 'logo', em))
    return objs, dict(yaw=-48)

def award():
    c = VCOL[var]
    glass = mat('glass', (0.93, 0.97, 1.0, 1.0), rough=0.0, trans=1.0, ior=1.5, spec=0.5)
    W, Hh, T = 0.105, 0.165, 0.022
    # outline: rectangle with an arched top
    pts = [(-W / 2, 0.0), (W / 2, 0.0), (W / 2, Hh - 0.04)]
    for k in range(1, 24):
        t = k / 24; ang = t * math.pi
        pts.append((W / 2 * math.cos(ang), Hh - 0.04 + 0.04 * math.sin(ang) + 0.0 * t))
    pts.append((-W / 2, Hh - 0.04))
    bm = bmesh.new()
    fv = [bm.verts.new((x, -T / 2, z)) for (x, z) in pts]
    bv_ = [bm.verts.new((x, T / 2, z)) for (x, z) in pts]
    bm.faces.new(fv); bm.faces.new(list(reversed(bv_)))
    nP = len(pts)
    for i in range(nP):
        j = (i + 1) % nP
        bm.faces.new((fv[j], fv[i], bv_[i], bv_[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    g = obj_from_bm(bm, 'glass', glass, smooth=False)
    bevel(g, 0.004, segs=5, angle=40)
    base_m = mat('base', c, rough=0.4, coat=0.35, bump=0.03, bscale=2500)
    BH = 0.032
    base = box('base', 0.125, 0.058, BH, loc=(0, 0, BH / 2), material=base_m, bev=0.002, segs=4)
    g.location = (0, 0, BH)
    plate = box('plate', 0.07, 0.0008, 0.012, loc=(0, -0.029 - 0.0004, BH / 2), material=mat('gold', GOLD if var != 'white' else '#B8BEC8', rough=0.22, metal=1.0), bev=0.0002, segs=1)
    # laser-engraved logo floating inside the glass
    lw = 0.070
    fm = mat_img('frost', logo_path('white'), rough=0.6, alpha=True, emit=0.05)
    d = decal_plane('logo', lw, lw * LOGO_AR, None, loc=(0, -0.002, BH + Hh * 0.56), material=fm)
    return [g, base, plate, d], dict(yaw=-18)

def calib():
    a = box('w', 0.06, 0.004, 0.08, loc=(-0.04, 0, 0.04), material=mat('wm', WHITE, rough=0.6), bev=0)
    b = box('n', 0.06, 0.004, 0.08, loc=(0.04, 0, 0.04), material=mat('nm', NAVY, rough=0.6), bev=0)
    c = box('b', 0.06, 0.004, 0.08, loc=(0.12, 0, 0.04), material=mat('bm', BLUE, rough=0.6), bev=0)
    return [a, b, c], dict(yaw=0)

BUILD = dict(calib=calib, thermos=thermos, folder=folder, notebook=notebook, pencilcup=pencilcup, giftbox=giftbox, deskflag=deskflag, cap=cap, award=award)

# ---------------------------------------------------------------- the family shot: several items on one floor
import json
LAYOUT = json.load(open(os.environ['LAYOUT']))
K = float(LAYOUT.get('rig', 2.2))          # the light rig grows with the scene
for it in LAYOUT['items']:
    var = it['v']
    objs, pose = BUILD[it['i']]()
    g = group(objs, yaw=pose.get('yaw', 0) + it.get('yaw', 0), pitch=pose.get('pitch', 0), loc=(it['x'], it['y'], 0))
    if it.get('s'): g.scale = (it['s'],) * 3
bpy.context.view_layer.update()
FLOOR = True
TILT = float(LAYOUT.get('tilt', TILT))
if LAYOUT.get('look'): sc.view_settings.look = LAYOUT['look']
# ---------------------------------------------------------------- lights & shadow catcher
def area(name, loc, size, power, color='#FFFFFF', target=(0, 0, 0.1), shape='RECTANGLE', sy=None, cam=False):
    loc = tuple(v * K for v in loc); size = size * K; power = power * K * K
    l = bpy.data.lights.new(name, 'AREA'); l.energy = power * LSCALE; l.size = size; l.shape = shape
    if sy: l.size_y = sy
    l.color = lin(color)[:3]
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    d = Vector(target) - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return o

area('key', (-0.75, -0.95, 0.95), 0.9, 95, '#FFF8F0')
area('fill', (0.95, -0.70, 0.35), 1.2, 28, '#F0F4FF')
area('rim', (0.35, 0.85, 0.85), 0.8, 60)
area('top', (0.0, -0.15, 1.3), 0.7, 30)
# vertical strip softboxes – only seen in reflections / refraction
for nm, x in (('stripL', -0.55), ('stripR', 0.6)):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    o = obj_from_bm(bm, nm, smooth=False)
    o.scale = (0.14 * K, 0.9 * K, 1); o.location = (x * K, -0.6 * K, 0.25 * K)
    o.rotation_euler = (math.radians(90), 0, math.radians(-35 if x < 0 else 35))
    em = bpy.data.materials.new(nm + 'm'); em.use_nodes = True
    nt = em.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Strength'].default_value = 3.0 * LSCALE
    link(e.outputs[0], nt.nodes['Material Output'].inputs[0]); o.data.materials.append(em)
    o.visible_camera = False; o.visible_diffuse = False; o.visible_shadow = False

bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=6.0)
floor = obj_from_bm(bm, 'floor', smooth=False); floor.is_shadow_catcher = True
if not FLOOR: floor.hide_render = True

# ---------------------------------------------------------------- camera & framing
cam_d = bpy.data.cameras.new('cam'); cam_d.type = 'ORTHO'
cam = bpy.data.objects.new('cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.rotation_euler = Euler((math.radians(90 - TILT), 0, 0))
cam.location = (0, -3.0, 0)
bpy.context.view_layer.update()
inv = cam.matrix_world.inverted()
xs, ys = [], []
dg = bpy.context.evaluated_depsgraph_get()
for o in sc.objects:
    if o.type not in ('MESH', 'CURVE') or o.name in ('floor',) or o.name.startswith('strip'): continue
    ev = o.evaluated_get(dg)
    try:
        me = ev.to_mesh()
    except Exception:
        continue
    for v in me.vertices:
        p = inv @ (ev.matrix_world @ v.co); xs.append(p.x); ys.append(p.y)
    ev.to_mesh_clear()
mx = LAYOUT.get('mx', 0.06); my_top = LAYOUT.get('mt', 0.03); my_bot = LAYOUT.get('mb', 0.07)
x0, x1, y0, y1 = min(xs) - mx, max(xs) + mx, min(ys) - my_bot, max(ys) + my_top
w, h = x1 - x0, y1 - y0
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
cam.location = cam.matrix_world @ Vector((cx, cy, 0))
cam_d.ortho_scale = max(w, h)
if LAYOUT.get('tilt'): pass
sc.render.resolution_x = int(round(w * PXM)); sc.render.resolution_y = int(round(h * PXM))
sc.render.resolution_percentage = 100
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
# record where the floor contact line sits (fraction from bottom) for page alignment
floor_y = (inv @ Vector((0, 0, 0))).y
print('FRAME', item, var, sc.render.resolution_x, sc.render.resolution_y, 'floor_frac', round((floor_y - y0) / h, 4))

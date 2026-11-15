"""The box of the opening film on the home page.

Ammar, 14 Nov 2026, about the box: «ما حلو الموديل اعمل واحد حديث اكتر وانيق وبسيط», then «طوره», then «طوره اكثر».
The old model was a navy box with a short lid, a large logo and wave lines on the lid and the front. The new one is a rigid
box with a full lid that slides down over the base (the way phone boxes are made): matt navy with nothing on it but the logo
in the middle of the lid, and a blue base that shows as a thin line under the lid and comes into view when the lid lifts.

The second pass («طوره اكثر») keeps the same box and its sizes and works on how it is made and lit:
  - the logo is a silver foil stamp (a silver layer cut to the logo's shape) that catches the light as the film moves, and it
    is set across the lid, so it reads upright when the box stands up;
  - a thumb cut in the near side of the lid shows the blue base, the way stationery boxes are opened;
  - the faces are lit from one side: a lighter top, a half-lit near side, a dark far side, and edges that catch the light;
  - the box stands up with its lid to the viewer before it goes into the bag (it used to show its plain underside);
  - the bag is plain white with the logo and blue handles, without the wave band, like the box.
The first moments (the lid settling, the light crossing it) are CSS in assets/css/home.css.

Then, the same evening, from his phone at the «افتح العلبة» chapter: «فايت ببعضه شوف». The lid used to be put down beside
the base. Since the lid became as tall as the box it cut into the base there, and on a phone the screen edge cut the lid.
Now the lid lifts straight up until it clears the base, slides out of the screen to the left, and comes back the same way
to close the box. It is never put down, so it has nothing to cut into, and it only tilts once it is above the base.
The other things in the film that went through something are settled the same way:
  - the empty base used to sink under the floor before the pieces are laid out, and the bag used to rise from under it;
    on a phone both showed behind the bottom bar. They slide in and out on the left like the lid;
  - the paper cup used to fly in and out through the pile of pieces, half see-through. It appears and goes where it stands.
Left on the screen means back and to the left on the floor (x and y together): along x alone a piece would also drift down
the screen and pass behind the phone's bottom bar. A piece that is off the screen is switched off (visibility), so a very
wide screen does not show it waiting at the edge.

    python3 tools/home_box_2026_11_14.py

It rewrites the block that builds the box inside the film's script (content/pages-raw.json, the home page, first part) and
the lines outside it that depend on the box. Running it twice changes nothing.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START, END = '  // ---------- box ----------', '  // ---------- items ----------'

NEW_BLOCK = r'''  // ---------- box ----------
  // موديل العلبة (عمار 14 ت2: «ما حلو الموديل اعمل واحد حديث اكتر وانيق وبسيط»، وبعدها «طوره» و«طوره اكثر»): علبة صلبة
  // بغطا كامل بينزل لتحت متل علب الموبايلات، كحلي مطفي بلا خطوط ولا زخرفة، وقاعدة زرقا بيبيّن منها خط رفيع تحت الغطا.
  // التطوير التاني: الشعار ختم فضّي بيلمع مع الحركة ومكتوب بعرض الغطا (بيضل مقروء لما توقف العلبة لتنزل بالكيس)، فتحة إصبع
  // بالغطا بتبيّن القاعدة الزرقا، وإضاءة أوضح للوجوه والحواف. الملمس (TEX) من نسخة 12 ت1: «العلبة لو تكون واقعية أكتر».
  var BW = 300, BD = 400, BH = 96, LH = 92, LIP = 8, MID = (LIP + LH) / 2;
  __TEX__
  function face(w, h, bg, tf, inner) {
    return el('ms-face', 'width:' + w + 'px;height:' + h + 'px;margin:' + (-h / 2) + 'px 0 0 ' + (-w / 2) + 'px;background:' + bg + ';transform:' + tf, inner || '');
  }
  // طبقات: الإضاءة فوق، ثم الملمس (soft-light)، ثم لون الورق.
  function mface(w, h, light, base, tf, inner, edge) {
    var imgs = (light ? light + ',' : '') + TEX + ',' + base;
    var n = light ? light.split('-gradient(').length - 1 : 0;
    var rep = [], size = [], blend = [];
    for (var i = 0; i < n; i++) { rep.push('no-repeat'); size.push('100% 100%'); blend.push('normal'); }
    rep.push('repeat', 'no-repeat'); size.push('192px 192px', '100% 100%'); blend.push('soft-light', 'normal');
    return el('ms-face ms-mat', 'width:' + w + 'px;height:' + h + 'px;margin:' + (-h / 2) + 'px 0 0 ' + (-w / 2) + 'px;background-image:' + imgs +
      ';background-repeat:' + rep.join(',') + ';background-size:' + size.join(',') + ';background-blend-mode:' + blend.join(',') +
      ';box-shadow:' + (edge || 'inset 0 0 0 1px rgba(255,255,255,.05)') + ';transform:' + tf, inner || '');
  }
  var grp = el('ms-el ms-grp'); world.appendChild(grp);
  // القاعدة: زرقا، وجدرانها من جوّا أغمق من فوق (ظل الحافة).
  var box = el('ms-el ms-box');
  var RIM = 'linear-gradient(to bottom,rgba(6,18,58,.5),rgba(6,18,58,0) 30%,rgba(6,18,58,0) 82%,rgba(6,18,58,.2))';
  box.appendChild(mface(BW, BD, 'radial-gradient(78% 72% at 50% 50%,rgba(0,0,0,0) 42%,rgba(6,18,58,.5) 100%)', 'linear-gradient(135deg,#2a54c0,#1f44a4)', 'translate3d(0,0,4px)'));
  box.appendChild(mface(BW, BH, RIM, 'linear-gradient(#1a3a8e,#2850b8)', 'translate3d(0,' + (-BD / 2) + 'px,' + (BH / 2) + 'px) rotateX(-90deg)'));
  box.appendChild(mface(BH, BD, 'linear-gradient(90deg,rgba(6,18,58,.45),rgba(6,18,58,0) 30%)', 'linear-gradient(90deg,#2850b8,#1c3e94)', 'translate3d(' + (BW / 2) + 'px,0,' + (BH / 2) + 'px) rotateY(-90deg)'));
  box.appendChild(mface(BW, BH, 'linear-gradient(100deg,rgba(255,255,255,.16),rgba(255,255,255,0) 46%)', 'linear-gradient(172deg,#5384f6,#3263DB 52%,#2851bd)', 'translate3d(0,' + (BD / 2) + 'px,' + (BH / 2) + 'px) rotateX(-90deg)', '',
    'inset 0 0 0 1px rgba(255,255,255,.07),inset 0 1px 0 rgba(255,255,255,.26)'));
  box.appendChild(mface(BH, BD, 'linear-gradient(270deg,rgba(6,18,58,.3),rgba(6,18,58,0) 30%)', 'linear-gradient(90deg,#2143a0,#2c57c6)', 'translate3d(' + (-BW / 2) + 'px,0,' + (BH / 2) + 'px) rotateY(-90deg)', '',
    'inset 0 0 0 1px rgba(255,255,255,.05),inset -1px 0 0 rgba(255,255,255,.18)'));
  // الظل: تلامس قريب داكن، وظل محيط واسع.
  box.appendChild(el('ms-face', 'width:' + (BW + 60) + 'px;height:' + (BD + 60) + 'px;margin:' + (-(BD + 60) / 2) + 'px 0 0 ' + (-(BW + 60) / 2) + 'px;border-radius:30px;' +
    'background:radial-gradient(closest-side,rgba(4,11,28,.6),rgba(4,11,28,0)) calc(50% - 11px) calc(50% - 15px)/' + (BW + 16) + 'px ' + (BD + 16) + 'px no-repeat,radial-gradient(closest-side,rgba(8,22,52,.4),rgba(8,22,52,0));transform:translate3d(16px,22px,-1px)'));
  var boxSh = box.lastChild;
  grp.appendChild(box);
  // الغطا: كحلي مطفي. الضو جاي من ورا ومن اليسار: السطح أفتح بالبعيد، والوجه القريب اليمين نص مضوّى، واليسار معتم.
  var lid = el('ms-el ms-lid');
  var LW = BW + 12, LD = BD + 12;
  // الشعار ختم فضّي: طبقة فضّة مقصوصة على شكل الشعار، والبروز من ظل فوقها وتحتها. الصورة البيضا بتضل للمتصفح يلي ما بيقص.
  var WM = A + 'wm_white.webp';
  lid.appendChild(mface(LW, LD,
    'linear-gradient(118deg,rgba(255,255,255,0) 18%,rgba(255,255,255,.05) 38%,rgba(255,255,255,.035) 46%,rgba(255,255,255,0) 66%),radial-gradient(120% 86% at 42% 0%,rgba(120,168,255,.3),rgba(120,168,255,0) 64%),radial-gradient(90% 80% at 4% 100%,rgba(3,10,26,.3),rgba(3,10,26,0) 70%)',
    'linear-gradient(165deg,#26509c,#163877 46%,#0e2757)', 'translate3d(0,0,' + LH + 'px)',
    '<span class="ms-foil"><img decoding="async" src="' + WM + '" alt=""><i style="-webkit-mask-image:url(' + WM + ');mask-image:url(' + WM + ')"></i></span><b class="ms-sheen"></b>',
    'inset 0 0 0 1px rgba(255,255,255,.07),inset 0 -1.5px 0 rgba(255,255,255,.22),inset 1.5px 0 0 rgba(255,255,255,.17),inset 0 1px 0 rgba(255,255,255,.1)'));
  var foil = lid.lastChild.querySelector('.ms-foil i');
  // جوانب الغطا: الحافة العليا بتلقط الضو، والسفلية أغمق.
  var LEDGE = 'inset 0 1px 0 rgba(255,255,255,.28),inset 0 -1px 0 rgba(0,0,0,.4),inset 0 -6px 8px -6px rgba(0,0,0,.35)';
  // الوجه القريب فيه فتحة الإصبع: نص دايرة مقصوصة من تحت، بتبيّن القاعدة الزرقا وهي مسكّرة.
  var NR = 22, NOTCH = 'radial-gradient(circle at 50% 100%,transparent ' + (NR - .5) + 'px,#000 ' + (NR + .5) + 'px)';
  lid.appendChild(mface(LW, LH, 'linear-gradient(100deg,rgba(255,255,255,.1),rgba(255,255,255,0) 50%)', 'linear-gradient(#214890,#143170 58%,#0c214b)', 'translate3d(0,' + (LD / 2) + 'px,' + (LH / 2) + 'px) rotateX(-90deg)', '', LEDGE));
  lid.lastChild.style.webkitMaskImage = NOTCH; lid.lastChild.style.maskImage = NOTCH;
  // ظل سماكة الكرتون جوّا الفتحة: غامق عند القوس وبيخفّ لتحت.
  lid.appendChild(el('ms-face', 'width:' + (NR * 2) + 'px;height:' + NR + 'px;margin:' + (-NR / 2) + 'px 0 0 ' + (-NR) + 'px;border-radius:' + NR + 'px ' + NR + 'px 0 0;' +
    'background:radial-gradient(circle at 50% 100%,rgba(4,12,38,0) ' + (NR * .35) + 'px,rgba(4,12,38,.62) ' + NR + 'px);transform:translate3d(0,' + (LD / 2 - 2) + 'px,' + (NR / 2) + 'px) rotateX(-90deg)'));
  // الوجه الخلفي بيصير سطح العلبة لما توقف لتنزل بالكيس، لهيك مضوّى.
  lid.appendChild(mface(LW, LH, 'linear-gradient(100deg,rgba(255,255,255,.1),rgba(255,255,255,0) 60%)', 'linear-gradient(#27519e,#1a3f84)', 'translate3d(0,' + (-LD / 2) + 'px,' + (LH / 2) + 'px) rotateX(-90deg)', '', LEDGE));
  lid.appendChild(mface(LH, LD, '', 'linear-gradient(90deg,#081735,#0e2554)', 'translate3d(' + (-LW / 2) + 'px,0,' + (LH / 2) + 'px) rotateY(-90deg)', '', 'inset -1px 0 0 rgba(255,255,255,.2),inset 1px 0 0 rgba(0,0,0,.4),inset 6px 0 8px -6px rgba(0,0,0,.35)'));
  lid.appendChild(mface(LH, LD, '', 'linear-gradient(90deg,#0b1f45,#102a5c)', 'translate3d(' + (LW / 2) + 'px,0,' + (LH / 2) + 'px) rotateY(-90deg)', '', 'inset -1px 0 0 rgba(255,255,255,.14)'));
  lid.appendChild(el('ms-face', 'width:' + (LW + 40) + 'px;height:' + (LD + 40) + 'px;margin:' + (-(LD + 40) / 2) + 'px 0 0 ' + (-(LW + 40) / 2) + 'px;border-radius:24px;' +
    'background:radial-gradient(closest-side,rgba(4,11,28,.5),rgba(4,11,28,0)) calc(50% - 9px) calc(50% - 13px)/' + (LW + 10) + 'px ' + (LD + 10) + 'px no-repeat,radial-gradient(closest-side,rgba(8,22,52,.34),rgba(8,22,52,0));transform:translate3d(14px,20px,-1px)'));
  var lidSh = lid.lastChild;
  grp.appendChild(lid);
'''

BAG_WAVES = """  var bwaves = '<svg viewBox="0 0 350 90" preserveAspectRatio="none" style="position:absolute;left:0;bottom:0;width:100%;height:27%">' +
    '<rect width="350" height="90" fill="#0D244C"/>' +
    [0, 1, 2, 3, 4].map(function (i) { return '<path d="M-10 ' + (34 + i * 9) + ' C 90 ' + (8 + i * 9) + ', 190 ' + (66 + i * 9) + ', 360 ' + (22 + i * 9) + '" fill="none" stroke="#50C4C8" stroke-width="1.3" stroke-opacity="' + (.75 - i * .13) + '"/>'; }).join('') + '</svg>';
"""
BAG_FRONT_OLD = """holes + bwaves +
    '<img decoding="async" src="' + A + 'wm_navy.webp" style="position:absolute;left:50%;top:40%;width:46%;transform:translate(-50%,-50%);opacity:.95" alt="">' +
    '<span style="position:absolute;left:0;right:0;top:61%;text-align:center;font:600 10px/1 system-ui,sans-serif;letter-spacing:3px;color:#3263DB">MADAREKMATBAA.COM</span></div>'"""
BAG_FRONT = """holes +
    '<img decoding="async" src="' + A + 'wm_navy.webp" style="position:absolute;left:50%;top:50%;width:44%;transform:translate(-50%,-50%);opacity:.96" alt=""></div>'"""

# The lid's path (see the note at the top): straight up, out to the left, back, straight down.
LID_PATH = """  K.lid = fill([[0, { x: 0, y: 0, z: LIP, rz: 0, rx: 0 }], [.07, { x: 0, y: 0, z: 150, rz: 0, rx: 0 }], [.14, { x: -1240, y: -835, z: 215, rz: -12, rx: -5 }],
    [.82, { x: -1240, y: -835, z: 230, rz: -12, rx: -5 }], [.88, { x: 0, y: 0, z: 170, rz: 0, rx: 0 }], [.915, { x: 0, y: 0, z: LIP, rz: 0, rx: 0 }], [1, { x: 0, y: 0, z: LIP, rz: 0, rx: 0 }]]);
"""
BASE_PATH = """  K.box = fill([[0, { x: 0, y: 0, z: 0 }], [.45, { x: 0, y: 0, z: 0 }], [.56, { x: -1240, y: -835, z: 0 }], [.76, { x: -1240, y: -835, z: 0 }], [.84, { x: 0, y: 0, z: 0 }], [1, { x: 0, y: 0, z: 0, rz: 0 }]]);
"""
CUP_PATH = """  K.cup = fill([[0, { x: -395, y: 165, z: 50, o: 0 }], [.53, { x: -395, y: 165, z: 50, o: 0 }], [.62, { x: -395, y: 165, z: 0, o: 1 }], [.76, { x: -395, y: 165, z: 0, o: 1 }],
    [.81, { x: -395, y: 165, z: 30, o: 0 }], [1, { x: -395, y: 165, z: 30, o: 0 }]]);
"""
BAG_PATH = """  K.bag = fill([[0, { x: -1240, y: -835, z: 0 }], [.3, { x: -1240, y: -835, z: 0 }], [.56, { x: 0, y: 0, z: 0 }], [1, { x: 0, y: 0, z: 0 }]]);
"""
# In the frame: the lid, the base and the bag are switched off while they are off the screen, the lid's own shadow shows
# only while it sits on the box, and the foil of the logo moves with the film (three passes of light from start to end).
FRAME = """css(lid, 'visibility', p > .145 && p < .815 ? 'hidden' : 'visible');
    css(box, 'visibility', p > .565 && p < .755 ? 'hidden' : 'visible');
    css(bag, 'visibility', q < .29 ? 'hidden' : 'visible');
    css(boxSh, 'opacity', fadeG.toFixed(3)); css(lidSh, 'opacity', (fadeG * (1 - clamp((sample(K.lid, p, 'z') - LIP) / 40, 0, 1))).toFixed(3));
    css(foil, 'backgroundPosition', ((pp * 450) % 150).toFixed(1) + '% 0');
    """
# Whole statements, found by where they start and end, so the tool gives the same result from any earlier version.
SETS = [
    (r"  K\.lid = fill\(\[.*?\]\]\);\n", LID_PATH),
    (r"  K\.box = fill\(\[.*?\]\]\);\n", BASE_PATH),
    (r"  K\.cup = fill\(\[.*?\]\]\);\n", CUP_PATH),
    (r"  K\.bag = fill\(\[.*?\]\]\);\n", BAG_PATH),
    (r"(?:var lidO = [^\n]*\n\s*lidFaces[^\n]*\n\s*|css\(lid, 'visibility'[^\n]*\n\s*css\(box, 'visibility'[^\n]*\n\s*css\(bag, 'visibility'[^\n]*\n\s*)?css\(boxSh, 'opacity'.*?(?=css\(world,)", FRAME),
]
# Single lines, as (what was there, what is there now).
EDITS = [
    # the lid is as tall as the box, so the middle the box turns around when it stands up moved
    ("K.grp = fill([[0, { z: 72, rx: 0 }], [.04, { z: 72, rx: 0 }],", "K.grp = fill([[0, { z: MID, rx: 0 }], [.04, { z: MID, rx: 0 }],"),
    ("ga.toFixed(2) + 'deg) translate3d(0,0,-72px)');", "ga.toFixed(2) + 'deg) translate3d(0,0,' + (-MID) + 'px)');"),
    # the box stands up with its lid to the viewer, so the logo shows before it goes into the bag
    ("[.32, { z: 690, rx: 90 }], [.5, { z: 690, rx: 90 }], [.82, { z: 213, rx: 90 }], [1, { z: 213, rx: 90 }]]);",
     "[.32, { z: 690, rx: -90 }], [.5, { z: 690, rx: -90 }], [.82, { z: 213, rx: -90 }], [1, { z: 213, rx: -90 }]]);"),
    # the bag: plain white with the logo and blue handles
    (BAG_WAVES, ""),
    (BAG_FRONT_OLD, BAG_FRONT),
    ("""fill="none" stroke="#50C4C8" stroke-width="5" stroke-linecap="round"/></svg>';""", """fill="none" stroke="#3263DB" stroke-width="5" stroke-linecap="round"/></svg>';"""),
]


def box_edit(h):
    a, b = h.index(START), h.index(END)
    tex = re.search(r'  var TEX = "url\(data:image/webp;base64,[^"]*";\n', h[a:b])
    if not tex:
        raise SystemExit('the paper texture line of the box was not found')
    h = h[:a] + NEW_BLOCK.replace('  __TEX__\n', tex.group(0)) + h[b:]
    for pattern, statement in SETS:
        h, n = re.subn(pattern, lambda m: statement, h, count=1, flags=re.S)
        if n != 1:
            raise SystemExit('a statement the box depends on was not found: ' + pattern[:40])
    for old, new in EDITS:
        if new and h.count(new) == 1:
            continue  # already there
        if h.count(old) != 1:
            if not new and old not in h:
                continue  # already removed
            raise SystemExit('a line the box depends on has moved: ' + old[:60])
        h = h.replace(old, new, 1)
    return h


if __name__ == '__main__':
    path = os.path.join(ROOT, 'content/pages-raw.json')
    pages = json.load(open(path, encoding='utf-8'))
    home = next(p for p in pages if p.get('path') == '/')
    kind, film = home['parts'][0]
    if 'class="mdk-story"' not in film:
        raise SystemExit('the first part of the home page is not the opening film')
    new = box_edit(film)
    if new == film:
        print('the box is already in place')
    else:
        home['parts'][0] = [kind, new]
        json.dump(pages, open(path, 'w', encoding='utf-8'), ensure_ascii=False)  # the file's own format: one line, no ASCII escapes
        print('the box is written to content/pages-raw.json')

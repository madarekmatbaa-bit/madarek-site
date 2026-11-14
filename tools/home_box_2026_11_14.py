"""The new box of the opening film on the home page.

Ammar, 14 Nov 2026, about the box: «ما حلو الموديل اعمل واحد حديث اكتر وانيق وبسيط», then «طوره».
The old model was a navy box with a short lid, a large logo and wave lines on the lid and the front. The new one is a rigid
box with a full lid that slides down over the base (the way phone boxes are made): matt navy with nothing on it but a small
logo in the middle of the lid, and a blue base that shows as a thin line under the lid and comes into view when the lid lifts.

    python3 tools/home_box_2026_11_14.py

It rewrites the block that builds the box inside the film's script (content/pages-raw.json, the home page, first part) and
the numbers that depended on the old heights: where the lid rests, how high it lifts, and the middle the box turns around
when it stands up to go into the bag. Running it twice changes nothing.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START, END = '  // ---------- box ----------', '  // ---------- items ----------'

NEW_BLOCK = r'''  // ---------- box ----------
  // موديل العلبة (عمار 14 ت2: «ما حلو الموديل اعمل واحد حديث اكتر وانيق وبسيط»): علبة صلبة بغطا كامل بينزل لتحت متل علب
  // الموبايلات، كحلي مطفي بلا خطوط ولا زخرفة، شعار صغير بنص الغطا، وقاعدة زرقا بيبيّن منها خط رفيع تحت الغطا وبتطلع كلها
  // لما ينرفع. قبلها كانت علبة بغطا قصير وشعار كبير وخطوط موج (12 ت1: «العلبة لو تكون واقعية أكتر»)، والإضاءة والملمس من هديك النسخة.
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
  box.appendChild(mface(BW, BH, 'linear-gradient(100deg,rgba(255,255,255,.14),rgba(255,255,255,0) 46%)', 'linear-gradient(170deg,#4b7cf2,#3263DB 55%,#2a55c4)', 'translate3d(0,' + (BD / 2) + 'px,' + (BH / 2) + 'px) rotateX(-90deg)', '',
    'inset 0 0 0 1px rgba(255,255,255,.07),inset 0 1px 0 rgba(255,255,255,.22)'));
  box.appendChild(mface(BH, BD, 'linear-gradient(270deg,rgba(6,18,58,.3),rgba(6,18,58,0) 30%)', 'linear-gradient(90deg,#2347a8,#2c57c6)', 'translate3d(' + (-BW / 2) + 'px,0,' + (BH / 2) + 'px) rotateY(-90deg)', '',
    'inset 0 0 0 1px rgba(255,255,255,.05),inset -1px 0 0 rgba(255,255,255,.16)'));
  // الظل: تلامس قريب داكن، وظل محيط واسع.
  box.appendChild(el('ms-face', 'width:' + (BW + 60) + 'px;height:' + (BD + 60) + 'px;margin:' + (-(BD + 60) / 2) + 'px 0 0 ' + (-(BW + 60) / 2) + 'px;border-radius:30px;' +
    'background:radial-gradient(closest-side,rgba(4,11,28,.55),rgba(4,11,28,0)) calc(50% - 11px) calc(50% - 15px)/' + (BW + 16) + 'px ' + (BD + 16) + 'px no-repeat,radial-gradient(closest-side,rgba(8,22,52,.36),rgba(8,22,52,0));transform:translate3d(16px,22px,-1px)'));
  var boxSh = box.lastChild;
  grp.appendChild(box);
  // الغطا: كحلي مطفي، سطح واحد نظيف، والشعار صغير بالنص ومطبوع فضّي خفيف.
  var lid = el('ms-el ms-lid');
  var LW = BW + 12, LD = BD + 12;
  lid.appendChild(mface(LW, LD,
    'radial-gradient(90% 68% at 22% 14%,rgba(255,255,255,.17),rgba(255,255,255,0) 60%),radial-gradient(130% 115% at 50% 46%,rgba(0,0,0,0) 62%,rgba(3,10,26,.3) 100%)',
    'linear-gradient(135deg,#224a96,#132f66 52%,#0d2350)', 'translate3d(0,0,' + LH + 'px)',
    '<img decoding="async" src="' + A + 'wm_white.webp" style="position:absolute;left:50%;top:50%;width:36%;transform:translate(-50%,-50%) rotate(90deg);opacity:.96;filter:drop-shadow(0 .8px 0 rgba(0,0,0,.45)) drop-shadow(0 -.5px 0 rgba(255,255,255,.22))" alt="">',
    'inset 0 0 0 1px rgba(255,255,255,.07),inset 1.5px 1.5px 0 rgba(255,255,255,.15),inset -1px -1px 0 rgba(0,0,0,.28)'));
  // جوانب الغطا: الحافة العليا بتلقط الضو، والسفلية أغمق.
  var LEDGE = 'inset 0 1px 0 rgba(255,255,255,.24),inset 0 -1px 0 rgba(0,0,0,.4),inset 0 -6px 8px -6px rgba(0,0,0,.35)';
  lid.appendChild(mface(LW, LH, 'linear-gradient(100deg,rgba(255,255,255,.09),rgba(255,255,255,0) 46%)', 'linear-gradient(#1e4590,#12306a 70%,#0e2552)', 'translate3d(0,' + (LD / 2) + 'px,' + (LH / 2) + 'px) rotateX(-90deg)', '', LEDGE));
  lid.appendChild(mface(LW, LH, '', 'linear-gradient(#0b1f45,#081633)', 'translate3d(0,' + (-LD / 2) + 'px,' + (LH / 2) + 'px) rotateX(-90deg)', '', LEDGE));
  lid.appendChild(mface(LH, LD, '', 'linear-gradient(90deg,#0d2350,#102a5e)', 'translate3d(' + (-LW / 2) + 'px,0,' + (LH / 2) + 'px) rotateY(-90deg)', '', 'inset 1px 0 0 rgba(255,255,255,.16),inset -1px 0 0 rgba(0,0,0,.4)'));
  lid.appendChild(mface(LH, LD, '', 'linear-gradient(90deg,#0b1f45,#0a1b3b)', 'translate3d(' + (LW / 2) + 'px,0,' + (LH / 2) + 'px) rotateY(-90deg)', '', 'inset -1px 0 0 rgba(255,255,255,.1)'));
  lid.appendChild(el('ms-face', 'width:' + (LW + 40) + 'px;height:' + (LD + 40) + 'px;margin:' + (-(LD + 40) / 2) + 'px 0 0 ' + (-(LW + 40) / 2) + 'px;border-radius:24px;' +
    'background:radial-gradient(closest-side,rgba(4,11,28,.45),rgba(4,11,28,0)) calc(50% - 9px) calc(50% - 13px)/' + (LW + 10) + 'px ' + (LD + 10) + 'px no-repeat,radial-gradient(closest-side,rgba(8,22,52,.32),rgba(8,22,52,0));transform:translate3d(14px,20px,-1px)'));
  var lidSh = lid.lastChild;
  grp.appendChild(lid);
'''

# the three places that knew the old heights: where the lid rests, and the middle the box turns around when it stands up
CONSTS = [
    ("K.lid = fill([[0, { x: 0, y: 0, z: BH, rz: 0, rx: 0 }]", "K.lid = fill([[0, { x: 0, y: 0, z: LIP, rz: 0, rx: 0 }]"),
    ("[.93, { x: 0, y: 0, z: BH, rz: 0, rx: 0 }], [1, { x: 0, y: 0, z: BH, rz: 0, rx: 0 }]]);", "[.93, { x: 0, y: 0, z: LIP, rz: 0, rx: 0 }], [1, { x: 0, y: 0, z: LIP, rz: 0, rx: 0 }]]);"),
    ("K.grp = fill([[0, { z: 72, rx: 0 }], [.04, { z: 72, rx: 0 }],", "K.grp = fill([[0, { z: MID, rx: 0 }], [.04, { z: MID, rx: 0 }],"),
    # the lid is taller now, so it lifts less: its top stays below where the old lid's top went
    ("[.08, { x: -40, y: -10, z: 330, rz: -6, rx: -8 }]", "[.08, { x: -40, y: -10, z: 250, rz: -6, rx: -8 }]"),
    ("[.86, { x: -80, y: -20, z: 360, rz: -6, rx: -6 }]", "[.86, { x: -80, y: -20, z: 270, rz: -6, rx: -6 }]"),
    ("ga.toFixed(2) + 'deg) translate3d(0,0,-72px)');", "ga.toFixed(2) + 'deg) translate3d(0,0,' + (-MID) + 'px)');"),
]


def box_edit(h):
    a, b = h.index(START), h.index(END)
    old = h[a:b]
    tex = re.search(r'  var TEX = "url\(data:image/webp;base64,[^"]*";\n', old)
    if not tex:
        raise SystemExit('the paper texture line of the old box was not found')
    h = h[:a] + NEW_BLOCK.replace('  __TEX__\n', tex.group(0)) + h[b:]
    for o, n in CONSTS:
        if h.count(o) != 1:
            raise SystemExit('a number of the old box moved: ' + o[:50])
        h = h.replace(o, n, 1)
    return h


if __name__ == '__main__':
    path = os.path.join(ROOT, 'content/pages-raw.json')
    pages = json.load(open(path, encoding='utf-8'))
    home = next(p for p in pages if p.get('path') == '/')
    kind, film = home['parts'][0]
    if 'class="mdk-story"' not in film:
        raise SystemExit('the first part of the home page is not the opening film')
    if 'var BW = 300, BD = 400, BH = 96, LH = 92, LIP = 8' in film:
        print('the new box is already in place')
    else:
        home['parts'][0] = [kind, box_edit(film)]
        json.dump(pages, open(path, 'w', encoding='utf-8'), ensure_ascii=False)  # the file's own format: one line, no ASCII escapes
        print('the new box is written to content/pages-raw.json')

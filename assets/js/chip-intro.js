/*
 * Intro: zoom continuo desde la PCB hasta el interior del chip.
 * PCB -> encapsulado (se vuelve transparente) -> die de silicio -> bloques
 * -> celdas -> firma "YJS" en el nivel más profundo -> destello -> página.
 *
 * La cámara se calcula en doble precisión en JS y cada bloque del die se dibuja
 * en coordenadas locales 0..100, para que el zoom (~x50,000) no pierda precisión
 * en el canvas.
 */
(function () {
  'use strict';

  var root = document.documentElement;
  var overlay = document.getElementById('chipIntro');
  if (!overlay) return;
  if (!root.classList.contains('intro-on')) { overlay.remove(); return; }

  overlay.style.animation = 'none'; // cancela el failsafe de CSS: el JS sí cargó
  document.body.style.overflow = 'hidden';

  var canvas = overlay.querySelector('canvas');
  var ctx = canvas.getContext('2d');
  var capTitle = overlay.querySelector('.intro-caption b');
  var capZoom = overlay.querySelector('.intro-caption span');
  var skipBtn = overlay.querySelector('.intro-skip');

  // ---------- utilidades ----------
  function rng(seed) {
    return function () {
      seed = (seed + 0x6D2B79F5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function hash(a, b) {
    var h = Math.imul(a ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul(b + 0x7f4a7c15, 0xc2b2ae35);
    h ^= h >>> 13; h = Math.imul(h, 0x27d4eb2f);
    return (h ^ (h >>> 15)) >>> 0;
  }
  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
  function smooth(a, b, v) { var t = clamp01((v - a) / (b - a)); return t * t * (3 - 2 * t); }

  // ---------- viewport ----------
  var W, H, M, DIAG, dpr;
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    M = Math.min(W, H); DIAG = Math.hypot(W, H);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
  }
  resize();
  window.addEventListener('resize', resize);

  // ---------- escena (unidades de mundo; el chip mide ~110) ----------
  var BODY = 44, PIN_OUT = 55, NPIN = 16, DIE = 22, CORE = 18, MAX_LVL = 6;
  var PATH = [5, 10, 6, 9, 5, 10]; // hijo elegido en cada nivel (camino del zoom)
  var SIDES = [[1, 0], [0, 1], [-1, 0], [0, -1]];
  var R = rng(2026);

  var pins = [], traces = [];
  SIDES.forEach(function (d) {
    var p = [-d[1], d[0]];
    function pt(a, b) { return [d[0] * a + p[0] * b, d[1] * a + p[1] * b]; }
    for (var i = 0; i < NPIN; i++) {
      var o = -40 + i * 80 / (NPIN - 1);
      pins.push({ pt: pt, o: o });
      var sg = o < 0 ? -1 : 1, L2 = Math.abs(o) * 1.5 + 6;
      var pts = [
        pt(PIN_OUT + 60 + L2 + 12 + R() * 260, o + sg * L2),
        pt(PIN_OUT + 12 + L2, o + sg * L2),
        pt(PIN_OUT + 12, o),
        pt(PIN_OUT, o)
      ];
      var lens = [0];
      for (var k = 1; k < pts.length; k++) {
        lens.push(lens[k - 1] + Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]));
      }
      traces.push({ pts: pts, lens: lens, phase: R(), speed: 0.7 + R() * 0.6 });
    }
  });

  var parts = [];
  while (parts.length < 60) {
    var px = (R() * 2 - 1) * 560, py = (R() * 2 - 1) * 520;
    if (Math.abs(px) < 150 && Math.abs(py) < 150) continue;
    parts.push({ x: px, y: py, type: Math.floor(R() * 4), rot: R() < 0.5, n: 1 + Math.floor(R() * 40) });
  }

  // Punto final del zoom: centro del bloque más profundo en PATH
  var tx = -CORE, ty = -CORE, tsz = 2 * CORE;
  for (var l = 0; l < MAX_LVL; l++) {
    tsz /= 4; tx += (PATH[l] % 4) * tsz; ty += ((PATH[l] / 4) | 0) * tsz;
  }
  var TX = tx + tsz / 2, TY = ty + tsz / 2, TSZ = tsz;

  // ---------- cámara ----------
  var s, s0, cx, cy, cr, sr;
  function toScreen(wx, wy) {
    var dx = wx - cx, dy = wy - cy;
    return [(dx * cr - dy * sr) * s + W / 2, (dx * sr + dy * cr) * s + H / 2];
  }
  // Coloca el origen local en (ox, oy) con k píxeles por unidad local
  function setT(ox, oy, k) {
    var p = toScreen(ox, oy);
    ctx.setTransform(dpr * k * cr, dpr * k * sr, -dpr * k * sr, dpr * k * cr, dpr * p[0], dpr * p[1]);
  }

  // ---------- PCB ----------
  function along(tr, u) {
    var target = u * tr.lens[tr.lens.length - 1];
    for (var k = 1; k < tr.lens.length; k++) {
      if (target <= tr.lens[k]) {
        var f = (target - tr.lens[k - 1]) / (tr.lens[k] - tr.lens[k - 1]);
        var a = tr.pts[k - 1], b = tr.pts[k];
        return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
      }
    }
    return tr.pts[tr.pts.length - 1];
  }

  function drawPCB(t) {
    setT(0, 0, s);
    var g = ctx.createRadialGradient(0, 0, 40, 0, 0, 700);
    g.addColorStop(0, '#11593d'); g.addColorStop(1, '#072a1d');
    ctx.fillStyle = g;
    ctx.fillRect(-600, -560, 1200, 1120);

    // pistas
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    ctx.beginPath();
    traces.forEach(function (tr) {
      ctx.moveTo(tr.pts[0][0], tr.pts[0][1]);
      for (var k = 1; k < tr.pts.length; k++) ctx.lineTo(tr.pts[k][0], tr.pts[k][1]);
    });
    ctx.strokeStyle = '#1d8457'; ctx.lineWidth = 2.4; ctx.stroke();
    ctx.strokeStyle = 'rgba(80,200,140,.35)'; ctx.lineWidth = 0.8; ctx.stroke();

    // vías
    ctx.beginPath();
    traces.forEach(function (tr) { ctx.moveTo(tr.pts[0][0] + 3.4, tr.pts[0][1]); ctx.arc(tr.pts[0][0], tr.pts[0][1], 3.4, 0, 6.2832); });
    ctx.fillStyle = '#c9a857'; ctx.fill();
    ctx.beginPath();
    traces.forEach(function (tr) { ctx.moveTo(tr.pts[0][0] + 1.5, tr.pts[0][1]); ctx.arc(tr.pts[0][0], tr.pts[0][1], 1.5, 0, 6.2832); });
    ctx.fillStyle = '#050505'; ctx.fill();

    // componentes
    ctx.font = '600 5px "JetBrains Mono", monospace';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    parts.forEach(function (pt) {
      ctx.save();
      ctx.translate(pt.x, pt.y);
      if (pt.rot) ctx.rotate(Math.PI / 2);
      if (pt.type === 0 || pt.type === 1) { // resistencia / capacitor 0805
        ctx.fillStyle = '#cfd3d6'; ctx.fillRect(-9, -4, 18, 8);
        ctx.fillStyle = pt.type === 0 ? '#161616' : '#b88b5c'; ctx.fillRect(-5.5, -4, 11, 8);
        if (pt.type === 0) { ctx.fillStyle = '#d8d8d8'; ctx.fillText('103', 0, 0.3); }
      } else if (pt.type === 2) { // SOT-23
        ctx.fillStyle = '#cfd3d6';
        ctx.fillRect(-6, 4, 2.4, 4); ctx.fillRect(3.6, 4, 2.4, 4); ctx.fillRect(-1.2, -8, 2.4, 4);
        ctx.fillStyle = '#1a1a1a'; ctx.fillRect(-7, -4.5, 14, 9);
      } else { // cristal
        ctx.fillStyle = '#d7dbe0'; ctx.fillRect(-13, -5.5, 26, 11);
        ctx.strokeStyle = '#9da3aa'; ctx.lineWidth = 0.8; ctx.strokeRect(-11, -3.5, 22, 7);
      }
      ctx.restore();
      ctx.fillStyle = 'rgba(235,242,236,.8)';
      ctx.fillText((pt.type === 0 ? 'R' : pt.type === 1 ? 'C' : pt.type === 2 ? 'Q' : 'Y') + pt.n, pt.x + (pt.rot ? 16 : 0), pt.y + (pt.rot ? 0 : 11));
    });

    // serigrafía
    ctx.strokeStyle = 'rgba(235,242,236,.85)'; ctx.lineWidth = 1.2;
    ctx.beginPath();
    [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(function (c) {
      ctx.moveTo(c[0] * 70, c[1] * 58); ctx.lineTo(c[0] * 70, c[1] * 70); ctx.lineTo(c[0] * 58, c[1] * 70);
    });
    ctx.stroke();
    ctx.beginPath(); ctx.arc(-76, -76, 2.5, 0, 6.2832); ctx.fillStyle = 'rgba(235,242,236,.85)'; ctx.fill();
    ctx.font = '700 9px "JetBrains Mono", monospace';
    ctx.fillText('U1', -82, -64);
    ctx.textAlign = 'left';
    ctx.font = '700 15px "JetBrains Mono", monospace';
    ctx.fillText('YEFFRIMIC · CORE BOARD · REV 2026', -560, 530);
    ctx.textAlign = 'center';

    // agujeros de montaje
    [[-570, -530], [570, -530], [570, 530], [-570, 530]].forEach(function (h) {
      ctx.beginPath(); ctx.arc(h[0], h[1], 11, 0, 6.2832); ctx.fillStyle = '#c9a857'; ctx.fill();
      ctx.beginPath(); ctx.arc(h[0], h[1], 6, 0, 6.2832); ctx.fillStyle = '#030303'; ctx.fill();
    });

    // pulsos de señal viajando hacia el chip
    ctx.globalCompositeOperation = 'lighter';
    traces.forEach(function (tr) {
      var u = (t / 1000 * tr.speed * 0.55 + tr.phase) % 1;
      var q = along(tr, u);
      ctx.beginPath(); ctx.arc(q[0], q[1], 8, 0, 6.2832); ctx.fillStyle = 'rgba(70,255,160,.14)'; ctx.fill();
      ctx.beginPath(); ctx.arc(q[0], q[1], 2.6, 0, 6.2832); ctx.fillStyle = 'rgba(170,255,210,.95)'; ctx.fill();
    });
    ctx.globalCompositeOperation = 'source-over';
  }

  function drawPins() {
    setT(0, 0, s);
    ctx.beginPath();
    pins.forEach(function (pn) {
      var a = pn.pt(BODY - 1, pn.o - 1.3), b = pn.pt(PIN_OUT, pn.o - 1.3),
          c = pn.pt(PIN_OUT, pn.o + 1.3), d = pn.pt(BODY - 1, pn.o + 1.3);
      ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.lineTo(c[0], c[1]); ctx.lineTo(d[0], d[1]); ctx.closePath();
    });
    ctx.fillStyle = '#c3c8cd'; ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,.45)'; ctx.lineWidth = 0.4; ctx.stroke();
  }

  function drawPackage(alpha) {
    if (alpha <= 0.01) return;
    setT(0, 0, s);
    ctx.globalAlpha = alpha;
    var g = ctx.createLinearGradient(-BODY, -BODY, BODY, BODY);
    g.addColorStop(0, '#26292c'); g.addColorStop(1, '#0f1011');
    ctx.fillStyle = g; ctx.fillRect(-BODY, -BODY, BODY * 2, BODY * 2);
    ctx.strokeStyle = '#2d3135'; ctx.lineWidth = 1; ctx.strokeRect(-BODY + 3, -BODY + 3, BODY * 2 - 6, BODY * 2 - 6);
    ctx.beginPath(); ctx.arc(-32, -32, 4, 0, 6.2832); ctx.fillStyle = '#0a0b0c'; ctx.fill();
    ctx.fillStyle = '#6a6f75'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = '700 11px "JetBrains Mono", monospace'; ctx.fillText('YJS-CORE', 0, -4);
    ctx.font = '600 5px "JetBrains Mono", monospace'; ctx.fillText('YEFFRI J. SALAZAR', 0, 8);
    ctx.fillText('GT 2026 · REV A', 0, 16);
    ctx.globalAlpha = 1;
  }

  // ---------- die ----------
  function drawDieBase() {
    setT(0, 0, s);
    ctx.fillStyle = '#62676d'; ctx.fillRect(-28, -28, 56, 56); // paleta de soporte

    // dedos del leadframe
    ctx.strokeStyle = '#a7adb3'; ctx.lineWidth = 2; ctx.lineCap = 'butt';
    ctx.beginPath();
    pins.forEach(function (pn) {
      var a = pn.pt(BODY, pn.o), b = pn.pt(31, pn.o * 0.72);
      ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]);
    });
    ctx.stroke();

    var g = ctx.createLinearGradient(-DIE, -DIE, DIE, DIE);
    g.addColorStop(0, '#2a2f55'); g.addColorStop(0.5, '#3a2750'); g.addColorStop(1, '#4a3b22');
    ctx.fillStyle = g; ctx.fillRect(-DIE, -DIE, DIE * 2, DIE * 2);
    ctx.strokeStyle = '#9c8a55'; ctx.lineWidth = 0.6; ctx.strokeRect(-DIE + 0.8, -DIE + 0.8, DIE * 2 - 1.6, DIE * 2 - 1.6);

    // pads y bond wires
    ctx.fillStyle = '#d6b660';
    var wires = new Path2D();
    SIDES.forEach(function (d, si) {
      var p = [-d[1], d[0]];
      for (var j = 0; j < 12; j++) {
        var o = -17 + j * 34 / 11;
        var pad = [d[0] * 20.2 + p[0] * o, d[1] * 20.2 + p[1] * o];
        ctx.fillRect(pad[0] - 0.9, pad[1] - 0.9, 1.8, 1.8);
        var pn = pins[si * NPIN + Math.round(j * (NPIN - 1) / 11)];
        var tip = pn.pt(31.5, pn.o * 0.72);
        var mx = (pad[0] + tip[0]) / 2 + p[0] * 1.5, my = (pad[1] + tip[1]) / 2 + p[1] * 1.5;
        wires.moveTo(pad[0], pad[1]); wires.quadraticCurveTo(mx, my, tip[0], tip[1]);
      }
    });
    ctx.strokeStyle = 'rgba(240,205,120,.95)'; ctx.lineWidth = 0.35; ctx.lineCap = 'round';
    ctx.stroke(wires);
  }

  var FILL = [
    ['#1c2a55', '#22336a'], // SRAM
    ['#3a2a16', '#45331c'], // lógica
    ['#123434', '#173f3f'], // enrutamiento
    ['#2c1c44', '#35224f'], // analógico
    ['#24252c', '#2c2d36']  // alimentación
  ];
  var PAT = [
    function () {
      ctx.beginPath();
      for (var i = 1; i < 9; i++) { var v = 4 + i * 92 / 9; ctx.moveTo(v, 6); ctx.lineTo(v, 94); ctx.moveTo(6, v); ctx.lineTo(94, v); }
      ctx.strokeStyle = '#6c86d6'; ctx.lineWidth = 0.9; ctx.stroke();
      ctx.beginPath();
      for (var a = 1; a < 9; a += 2) for (var b = 1; b < 9; b += 2) ctx.rect(4 + a * 92 / 9 - 1.4, 4 + b * 92 / 9 - 1.4, 2.8, 2.8);
      ctx.fillStyle = '#c3d0f5'; ctx.fill();
    },
    function (r) {
      ctx.beginPath();
      for (var row = 0; row < 7; row++) {
        var y = 8 + row * 12.4, x = 7;
        while (x < 90) { var w = Math.min(3 + r() * 10, 93 - x); ctx.rect(x, y, w, 8); x += w + 1.4; }
      }
      ctx.fillStyle = '#b8914a'; ctx.fill();
      ctx.beginPath();
      for (var k = 0; k < 8; k++) { var yy = 7 + k * 12.4; ctx.moveTo(6, yy); ctx.lineTo(94, yy); }
      ctx.strokeStyle = '#e8cb85'; ctx.lineWidth = 0.7; ctx.stroke();
    },
    function (r) {
      ctx.beginPath();
      for (var i = 0; i < 6; i++) { var x = 10 + r() * 80; ctx.moveTo(x, 6); ctx.lineTo(x, 94); }
      ctx.strokeStyle = '#c26d34'; ctx.lineWidth = 1.8; ctx.stroke();
      ctx.beginPath();
      for (var j = 0; j < 6; j++) { var y = 10 + r() * 80; ctx.moveTo(6, y); ctx.lineTo(94, y); }
      ctx.strokeStyle = '#dcb45c'; ctx.lineWidth = 2.4; ctx.stroke();
      ctx.beginPath();
      for (var v = 0; v < 8; v++) ctx.rect(10 + r() * 78, 10 + r() * 78, 3, 3);
      ctx.fillStyle = '#f3e6b8'; ctx.fill();
    },
    function () {
      ctx.beginPath(); ctx.moveTo(12, 14);
      for (var i = 0; i < 8; i++) { var x = 12 + i * 5; ctx.lineTo(x, i % 2 ? 14 : 58); ctx.lineTo(x + 5, i % 2 ? 14 : 58); }
      ctx.strokeStyle = '#b596ea'; ctx.lineWidth = 1.6; ctx.stroke();
      ctx.fillStyle = '#8f6fd0'; ctx.fillRect(60, 14, 28, 18); ctx.fillRect(60, 36, 28, 18);
      ctx.fillStyle = '#c9b3f5'; ctx.fillRect(14, 70, 72, 4); ctx.fillRect(14, 80, 72, 4);
    },
    function () {
      ctx.fillStyle = 'rgba(210,214,224,.85)';
      ctx.fillRect(6, 10, 88, 7); ctx.fillRect(6, 46, 88, 7); ctx.fillRect(6, 82, 88, 7);
      ctx.fillStyle = '#9aa3b5';
      ctx.fillRect(20, 6, 3, 88); ctx.fillRect(49, 6, 3, 88); ctx.fillRect(78, 6, 3, 88);
    }
  ];

  function drawSignature() {
    ctx.fillStyle = 'rgba(5,10,8,.82)'; ctx.fillRect(12, 26, 76, 48);
    ctx.shadowColor = 'rgba(255,210,110,.9)'; ctx.shadowBlur = 18 * dpr;
    ctx.strokeStyle = '#f0cf78'; ctx.lineWidth = 1.2; ctx.strokeRect(14, 28, 72, 44);
    ctx.fillStyle = '#ffe7a8'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = '800 22px "JetBrains Mono", monospace'; ctx.fillText('YJS', 50, 47);
    ctx.font = '600 5px "JetBrains Mono", monospace'; ctx.fillText('YEFFRIMIC · 2026', 50, 63);
    ctx.shadowBlur = 0;
  }

  function drawTile(x, y, sz, lvl, seed, onPath, alpha) {
    var ss = sz * s;
    var c = toScreen(x + sz / 2, y + sz / 2), rad = ss * 0.7072;
    if (c[0] + rad < 0 || c[0] - rad > W || c[1] + rad < 0 || c[1] - rad > H) return;

    var r = rng(seed), type = Math.floor(r() * 5);
    setT(x, y, ss / 100);
    ctx.globalAlpha = alpha;
    ctx.fillStyle = FILL[type][lvl % 2];
    ctx.fillRect(3, 3, 94, 94);

    var childA = lvl < MAX_LVL ? smooth(450, 1100, ss) : 0;
    var detA = smooth(30, 120, ss) * (1 - childA);
    if (detA > 0.01) { ctx.globalAlpha = alpha * detA; PAT[type](r); }
    if (onPath && lvl === MAX_LVL) { ctx.globalAlpha = alpha; drawSignature(); }
    ctx.globalAlpha = 1;

    if (childA > 0.01) {
      var q = sz / 4;
      for (var i = 0; i < 16; i++) {
        drawTile(x + (i % 4) * q, y + ((i / 4) | 0) * q, q, lvl + 1, hash(seed, i),
          onPath && PATH[lvl] === i, alpha * childA);
      }
    }
  }

  // ---------- línea de tiempo ----------
  // Versión suave (sistema con animaciones reducidas): más corta y sin giro
  var SOFT = root.classList.contains('intro-soft');
  var HOLD = SOFT ? 300 : 700, ZOOM = SOFT ? 1900 : 4200, DWELL = SOFT ? 350 : 450, FLASH = SOFT ? 300 : 260;
  var SPIN = SOFT ? 0 : 0.55;
  var END = HOLD + ZOOM + DWELL;
  var start = null, done = false, lastCap = '';

  function caption(txt) { if (txt !== lastCap) { capTitle.textContent = txt; lastCap = txt; } }

  function frame(now) {
    if (done) return;
    if (start === null) start = now;
    var t = now - start;

    s0 = M * 0.0021;
    var s1 = M * 0.8 / TSZ;
    var zt = clamp01((t - HOLD) / ZOOM);
    var e = zt * zt * zt * (zt * (zt * 6 - 15) + 10); // smootherstep
    s = Math.exp(Math.log(s0) + (Math.log(s1) - Math.log(s0)) * e);
    var rot = SPIN * e;
    cr = Math.cos(rot); sr = Math.sin(rot);
    var k = 1 - s0 / s;
    cx = TX * k; cy = TY * k;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = '#040706'; ctx.fillRect(0, 0, canvas.width, canvas.height);

    var dieC = toScreen(0, 0), off = Math.hypot(dieC[0] - W / 2, dieC[1] - H / 2);
    var dieCovers = DIE * s - off > DIAG / 2;
    var pkgPx = 100 * s / M, coreRel = 36 * s / M;
    var pkgAlpha = 1 - smooth(1.0, 2.3, pkgPx);

    if (!dieCovers) { drawPCB(t); drawPins(); drawDieBase(); }
    drawTile(-CORE, -CORE, 2 * CORE, 0, 1234, true, 1);
    if (!dieCovers) drawPackage(pkgAlpha);

    caption(pkgPx < 1.0 ? 'PCB · YJS-01 · rev 2026'
      : pkgPx < 2.3 ? 'Encapsulado QFP-64 · rayos X'
      : coreRel < 3 ? 'Die de silicio · bond wires'
      : coreRel < 40 ? 'Bloques funcionales'
      : coreRel < 2500 ? 'Celdas estándar y metal'
      : 'Capa de metal 1 · firma del diseñador');
    capZoom.textContent = '×' + Math.round(s / s0).toLocaleString('es-GT');

    if (t > END) {
      var f = clamp01((t - END) / FLASH);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      var g = ctx.createRadialGradient(canvas.width / 2, canvas.height / 2, 0, canvas.width / 2, canvas.height / 2, DIAG * dpr * 0.6);
      g.addColorStop(0, 'rgba(255,255,255,' + f + ')');
      g.addColorStop(0.5, 'rgba(190,255,220,' + f + ')');
      g.addColorStop(1, 'rgba(79,200,144,' + f + ')');
      ctx.fillStyle = g; ctx.fillRect(0, 0, canvas.width, canvas.height);
      if (f >= 1) { reveal(); return; }
    }
    requestAnimationFrame(frame);
  }

  function reveal() {
    done = true;
    try { sessionStorage.setItem('introSeen', '1'); } catch (e) {}
    root.classList.add('intro-reveal');
    overlay.classList.add('intro-out');
    document.body.style.overflow = '';
    window.removeEventListener('keydown', onKey);
    setTimeout(function () {
      overlay.remove();
      root.classList.remove('intro-on', 'intro-soft');
      window.removeEventListener('resize', resize);
    }, 900);
  }

  function skip() {
    if (done || start === null) return;
    var now = performance.now();
    if (now - start < END) start = now - END;
  }
  function onKey(e) { if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); skip(); } }

  skipBtn.addEventListener('click', function (e) { e.stopPropagation(); skip(); });
  overlay.addEventListener('click', skip);
  window.addEventListener('keydown', onKey);

  requestAnimationFrame(frame);
  // Si el navegador frena los cuadros (ahorro de batería, pestaña oculta), la página igual aparece
  setTimeout(function () { if (!done) reveal(); }, 12000);
})();

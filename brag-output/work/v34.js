// Minimal geometric motion versions (style of the supplied references).
const eOutBack = (x, s = 1.70158) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2);
const eInQuad = x => x * x;
const P = (x, y) => [bx + x * S, by + y * S];          // 1x crop coords -> screen
const BOLT_C = () => P(113, 238);                        // visual centre of the bolt
let silW, silB;                                          // flat white / black silhouettes

function makeSil(color) {
  const c = new OffscreenCanvas(W, H), g = c.getContext('2d');
  g.drawImage(BOLT, bx, by, bw, bh); g.globalCompositeOperation = 'source-in';
  g.fillStyle = color; g.fillRect(0, 0, W, H); return c;
}
// polygon resampled by arc length, starting at the top-left vertex
function polySamples(M) {
  const out = [], start = per[7] / perLen;
  for (let i = 0; i < M; i++) out.push(perimPoint(start + i / M));
  return out;
}
function circleSamples(M, cx, cy, r, a0) {
  const out = [];
  for (let i = 0; i < M; i++) { const a = a0 + i / M * Math.PI * 2; out.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]); }
  return out;
}
function fillPts(c, pts, color) { c.fillStyle = color; c.beginPath(); pts.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y)); c.closePath(); c.fill(); }

// half-plane cuts that split the bolt into its three facets
const CUTS = [[[11, 274.5], [127.1, 159]], [[32.3, 333], [137.3, 238]]];
function pieceClip(c, k) {
  // k=0 top, 1 middle, 2 bottom ; builds a clip from big half-plane quads
  const big = 3000;
  const half = ([a, b], above) => {
    const [x1, y1] = P(...a), [x2, y2] = P(...b), dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy);
    const ux = dx / L * big, uy = dy / L * big, nx = dy / L * big * (above ? 1 : -1), ny = -dx / L * big * (above ? 1 : -1);
    return [[x1 - ux, y1 - uy], [x2 + ux, y2 + uy], [x2 + ux + nx, y2 + uy + ny], [x1 - ux + nx, y1 - uy + ny]];
  };
  // 'above' side: normal (dy,-dx) of a line running down-left->up-right points up
  const regs = k === 0 ? [half(CUTS[0], true)] : k === 1 ? [half(CUTS[0], false), half(CUTS[1], true)] : [half(CUTS[1], false)];
  for (const q of regs) { c.beginPath(); q.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y)); c.closePath(); c.clip(); }
}
const PIECE_C = [[115, 130], [118, 228], [100, 330]];

function letterRise(c, t, t0, color, stagger = 0.032, dur = 0.55) {
  c.font = `700 ${fontPx}px Montserrat`;
  letters.forEach((L, i) => {
    const p = eOutExpo(lin(t, t0 + i * stagger, t0 + i * stagger + dur)); if (p <= 0) return;
    c.save(); c.beginPath(); c.rect(L.x - 10, textY - textCap - 30, L.w + 20, textCap + 34); c.clip();
    c.fillStyle = color; c.fillText(L.ch, L.x, textY + (1 - p) * (textCap + 30)); c.restore();
  });
}

// ---------- V3 · MORPH ----------
const V3 = { dur: 5.0 };
function v3(t) {
  if (!silW) { silW = makeSil('#f4f5f7'); silB = makeSil('#0a0a0a'); }
  ctx.fillStyle = '#050505'; ctx.fillRect(0, 0, W, H);
  const [bcx, bcy] = BOLT_C();
  const startDy = 960 - bcy;                                       // bolt starts centred on screen
  const dy = startDy * (1 - eInOut(lin(t, 2.25, 2.8)));
  const cx = CX, cy = bcy + startDy, R = 150, M = 260;
  if (t < 1.15) {
    // pop -> drop -> squash -> rebound and grow
    let x = cx, y = cy, r = 14, sx = 1, sy = 1;
    if (t < 0.35) { r = 14 * eOutBack(lin(t, 0.05, 0.3), 3); }
    else if (t < 0.62) { const p = eInQuad(lin(t, 0.35, 0.62)); y = cy + 300 * p; sy = 1 + 0.35 * p; sx = 1 - 0.15 * p; }
    else if (t < 0.72) { const p = Math.sin(lin(t, 0.62, 0.72) * Math.PI); y = cy + 300 + 14 * 0.45 * p; sx = 1 + 0.6 * p; sy = 1 - 0.45 * p; }
    else { const p = lin(t, 0.72, 1.15), e = eOutCubic(p); y = cy + 300 * (1 - e); r = 14 + (R - 14) * eOutBack(p, 1.4); const st = Math.sin(p * Math.PI) * 0.18; sx = 1 - st; sy = 1 + st; }
    if (r > 0) { ctx.save(); ctx.translate(x, y); ctx.scale(sx, sy); ctx.fillStyle = '#f4f5f7'; ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.fill(); ctx.restore(); }
  } else if (t < 1.62) {
    const p = eInOut(lin(t, 1.15, 1.6)), rot = (1 - p) * -0.5;
    const A = circleSamples(M, cx, cy, R, -Math.PI * 0.62), B = polySamples(M).map(([x, y]) => [x, y + startDy]);
    const pts = A.map(([ax, ay], i) => { const [qx, qy] = B[i]; let x = ax + (qx - ax) * p, y = ay + (qy - ay) * p; const dx = x - cx, dy2 = y - cy; return [cx + dx * Math.cos(rot) - dy2 * Math.sin(rot), cy + dx * Math.sin(rot) + dy2 * Math.cos(rot)]; });
    // tiny overshoot scale on lock
    fillPts(ctx, pts, '#f4f5f7');
  } else {
    const punch = 1 + 0.06 * Math.sin(lin(t, 1.6, 1.85) * Math.PI);
    ctx.save(); ctx.translate(CX, bcy + dy); ctx.scale(punch, punch); ctx.translate(-CX, -bcy);
    // diagonal wipe flat-white -> chrome
    const w = eInOut(lin(t, 1.75, 2.2)), edge = by - 200 + w * (bh + 500);
    ctx.drawImage(silW, 0, 0);
    if (w > 0) {
      ctx.save(); ctx.beginPath(); ctx.moveTo(-2000, -2000); ctx.lineTo(3000, -2000); ctx.lineTo(3000, edge - 260); ctx.lineTo(-2000, edge + 260); ctx.closePath(); ctx.clip();
      lctx.clearRect(0, 0, W, H); lctx.drawImage(BOLT, bx, by, bw, bh); shine(lctx, lin(t, 3.85, 4.5)); ctx.drawImage(layer, 0, 0); ctx.restore();
    }
    ctx.restore();
    letterRise(ctx, t, 2.55, '#f4f5f7');
  }
}

// ---------- V4 · TRI (three pieces) ----------
const V4 = { dur: 5.0 };
function v4(t) {
  if (!silW) { silW = makeSil('#f4f5f7'); silB = makeSil('#0a0a0a'); }
  const inv = t >= 0.92;                                    // background flips to white on the 3rd snap
  ctx.fillStyle = inv ? '#ffffff' : '#050505'; ctx.fillRect(0, 0, W, H);
  // bolt sits at its final lockup position throughout; pieces fly in
  const ins = [
    { t0: 0.12, from: [-700, -500], rot: -1.2 },
    { t0: 0.42, from: [760, 80], rot: 0.9 },
    { t0: 0.72, from: [-300, 900], rot: -0.7 },
  ];
  const flip = lin(t, 1.25, 1.75), sxF = Math.abs(Math.cos(Math.PI * eInOut(flip)));
  const chromeSide = eInOut(flip) > 0.5;
  const [bcx, bcy] = BOLT_C();
  ctx.save();
  // the flip squeezes the assembled bolt horizontally
  ctx.translate(bcx, bcy); ctx.scale(Math.max(sxF, 0.002), 1); ctx.translate(-bcx, -bcy);
  ins.forEach((pc, k) => {
    const p = lin(t, pc.t0, pc.t0 + 0.22); if (p <= 0) return;
    const e = eOutBack(p, 1.2);
    const [pcx, pcy] = P(...PIECE_C[k]);
    ctx.save();
    ctx.translate(pcx + pc.from[0] * (1 - e), pcy + pc.from[1] * (1 - e)); ctx.rotate(pc.rot * (1 - e)); ctx.translate(-pcx, -pcy);
    pieceClip(ctx, k);
    if (chromeSide) { lctx.clearRect(0, 0, W, H); lctx.drawImage(BOLT, bx, by, bw, bh); shine(lctx, lin(t, 3.6, 4.3)); ctx.drawImage(layer, 0, 0); }
    else ctx.drawImage(inv ? silB : silW, 0, 0);
    ctx.restore();
  });
  ctx.restore();
  // inversion flash ring on the 3rd snap
  // wordmark: black bar sweeps in, then out, leaving the name
  const a = eInOut(lin(t, 1.95, 2.3)), b = eInOut(lin(t, 2.35, 2.75));
  const x0 = letters[0].x - 18, x1 = letters[letters.length - 1].x + letters[letters.length - 1].w + 18;
  if (b > 0) { ctx.save(); ctx.beginPath(); ctx.rect(x0, 0, (x1 - x0) * b, H); ctx.clip(); drawText(ctx, () => 1); ctx.restore(); }
  ctx.font = `700 ${fontPx}px Montserrat`;
  if (a > 0) {
    const L = x0 + (x1 - x0) * b, R = x0 + (x1 - x0) * a;
    if (R > L) { ctx.fillStyle = '#0a0a0a'; ctx.fillRect(L, textY - textCap - 14, R - L, textCap + 28); }
  }
}
// text colour for V4 is black: override drawText's fill via a wrapper
const _drawText = drawText;
drawText = function (c, alphaFor) {
  if (window.__black) { c.font = `700 ${fontPx}px Montserrat`; c.fillStyle = '#0a0a0a'; letters.forEach((L, i) => { if (alphaFor(i) > 0) c.fillText(L.ch, L.x, textY); }); return; }
  _drawText(c, alphaFor);
};
const _v4 = v4;
VERS.v3 = [v3, V3];
VERS.v4 = [t => { window.__black = true; _v4(t); window.__black = false; }, V4];

/* app.js — browser port of generator + synth for the K.516f prototype.
 *
 *   Runs entirely client-side, no build step, no external deps.
 *   Loads bars.json (the 11x16 modular alphabet Σ), implements the
 *   R-C-M-R framework's choice/assembly/render, plays via Web Audio.
 */

// ---------- state ----------
let TABLE = null;           // loaded from bars.json
let OPTIONS_PER_BAR = null; // loaded from bars.json
let audioCtx = null;        // Web Audio context (lazy)
let currentSource = null;   // current AudioBufferSourceNode

// ---------- PRNG (mulberry32, seedable) ----------
function mulberry32(seed) {
  let t = seed >>> 0;
  return function () {
    t += 0x6D2B79F5;
    let r = t;
    r = Math.imul(r ^ (r >>> 15), r | 1);
    r ^= r + Math.imul(r ^ (r >>> 7), r | 61);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

function randint(rng, lo, hi) {  // inclusive on both ends
  return lo + Math.floor(rng() * (hi - lo + 1));
}

// ---------- P (distribution slot) ----------
function chooseBarIndex(barPosition, dist, rng) {
  const n = OPTIONS_PER_BAR[barPosition - 1];
  if (dist === 'uniform') {
    return Math.floor(rng() * n);
  }
  if (dist === 'triangular') {
    const s = randint(rng, 1, 6) + randint(rng, 1, 6);  // 2..12
    let idx = s - 2;                                     // 0..10
    if (idx >= n) idx = idx % n;
    return idx;
  }
  throw new Error('unknown distribution ' + dist);
}

// ---------- γ (composition operator) ----------
function assemble(indices) {
  const mel = [];
  const bass = [];
  let t = 0.0;
  for (let bar = 0; bar < 16; bar++) {
    const opt = TABLE[bar][indices[bar]];
    let bt = t;
    for (const [pitch, dur] of opt.melody) {
      mel.push({ start: bt, pitch, dur });
      bt += dur;
    }
    bt = t;
    for (const [pitch, dur] of opt.bass) {
      bass.push({ start: bt, pitch, dur });
      bt += dur;
    }
    t += 3.0;  // 3/4 bar
  }
  return { mel, bass };
}

function generate(dist, seed) {
  const rng = mulberry32(seed);
  const indices = [];
  for (let i = 1; i <= 16; i++) indices.push(chooseBarIndex(i, dist, rng));
  const { mel, bass } = assemble(indices);
  return { indices, mel, bass };
}

// ---------- additive synth (mirrors Python src/synth.py) ----------
const SAMPLE_RATE = 44100;
const BPM = 100;                           // matches TEMPO_MICROSEC_PER_QUARTER = 600_000
const SEC_PER_BEAT = 60 / BPM;
const HARMONICS = [1.00, 0.50, 0.33, 0.22, 0.14, 0.09, 0.06];

function midiToHz(m) { return 440 * Math.pow(2, (m - 69) / 12); }

function renderNote(pitch, durSec, buf, startIdx) {
  const f0 = midiToHz(pitch);
  const nSamples = Math.min(Math.floor(durSec * SAMPLE_RATE),
                            buf.length - startIdx);
  if (nSamples <= 0) return;
  const attack = Math.min(Math.floor(0.005 * SAMPLE_RATE), nSamples);
  for (let i = 0; i < nSamples; i++) {
    const t = i / SAMPLE_RATE;
    let env = Math.exp(-t / 0.6);
    if (i < attack) env *= i / attack;
    let s = 0;
    for (let h = 0; h < HARMONICS.length; h++) {
      const w = HARMONICS[h];
      s += w * Math.sin(2 * Math.PI * f0 * (h + 1) * t);
    }
    buf[startIdx + i] += s * env * (80 / 127);
  }
}

function renderEvents(events, nSamples, gain) {
  const buf = new Float32Array(nSamples);
  for (const ev of events) {
    const startIdx = Math.floor(ev.start * SEC_PER_BEAT * SAMPLE_RATE);
    if (startIdx >= nSamples) continue;
    const durSec = ev.dur * SEC_PER_BEAT + 0.15;
    renderNote(ev.pitch, durSec, buf, startIdx);
  }
  for (let i = 0; i < nSamples; i++) buf[i] *= gain;
  return buf;
}

function renderToAudioBuffer(ctx, mel, bass) {
  const totalBeats = 16 * 3;
  const totalSec = totalBeats * SEC_PER_BEAT + 1.0;
  const n = Math.floor(totalSec * SAMPLE_RATE);
  const melBuf = renderEvents(mel, n, 0.70);
  const bassBuf = renderEvents(bass, n, 0.55);
  // mix + normalise
  let peak = 0;
  for (let i = 0; i < n; i++) {
    melBuf[i] += bassBuf[i];
    if (Math.abs(melBuf[i]) > peak) peak = Math.abs(melBuf[i]);
  }
  if (peak > 0) {
    const scale = 0.88 / peak;
    for (let i = 0; i < n; i++) melBuf[i] *= scale;
  }
  const ab = ctx.createBuffer(1, n, SAMPLE_RATE);
  ab.copyToChannel(melBuf, 0);
  return ab;
}

// ---------- UI ----------
function loadJSON(url) {
  return fetch(url).then(r => r.json());
}

function el(id) { return document.getElementById(id); }

function log(msg, append = false) {
  const box = el('console');
  if (!box) return;
  if (append) box.textContent += msg + '\n';
  else box.textContent = msg + '\n';
  box.scrollTop = box.scrollHeight;
}

function ensureAudio() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === 'suspended') audioCtx.resume();
}

function stopPlayback() {
  if (currentSource) {
    try { currentSource.stop(); } catch (e) {}
    currentSource = null;
  }
}

async function rollAndPlay() {
  ensureAudio();
  stopPlayback();

  const dist = el('dist').value;
  let seed = parseInt(el('seed').value, 10);
  if (!isFinite(seed)) {
    seed = Math.floor(Math.random() * 2 ** 31);
    el('seed').value = seed;
  }

  const { indices, mel, bass } = generate(dist, seed);
  el('indices').textContent = indices.map(i => i + 1).join(', ');

  const lang = document.body.dataset.lang || 'en';
  const rollingMsg = {
    en: `Rolling under ${dist} P, seed ${seed}…`,
    kr: `${dist === 'uniform' ? '균등' : '삼각'} 분포, seed ${seed}로 굴리는 중…`,
  }[lang];
  log(rollingMsg);

  const ab = renderToAudioBuffer(audioCtx, mel, bass);
  const src = audioCtx.createBufferSource();
  src.buffer = ab;
  src.connect(audioCtx.destination);
  src.start();
  currentSource = src;
  log({
    en: `Playing ${ab.duration.toFixed(1)} s of newly generated minuet.`,
    kr: `새로 생성된 ${ab.duration.toFixed(1)}초 미뉴에트를 재생합니다.`,
  }[lang], true);
  src.onended = () => { currentSource = null; };
}

function randomSeed() {
  el('seed').value = Math.floor(Math.random() * 999999);
}

function setLanguage(lang) {
  document.body.dataset.lang = lang;
  document.querySelectorAll('[data-en]').forEach(node => {
    const en = node.dataset.en;
    const kr = node.dataset.kr;
    node.textContent = (lang === 'kr' && kr) ? kr : en;
  });
  document.querySelectorAll('.lang-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.setLang === lang);
  });
}

// ---------- init ----------
window.addEventListener('DOMContentLoaded', async () => {
  try {
    const data = await loadJSON('js/bars.json');
    TABLE = data.table;
    OPTIONS_PER_BAR = data.options_per_bar;
    el('status').textContent = `Σ loaded: ${data.n_bars} bars, option counts [${data.options_per_bar.join(', ')}].`;
    el('btn-roll').disabled = false;
  } catch (e) {
    el('status').textContent = 'Failed to load bars.json: ' + e.message;
    console.error(e);
  }

  el('btn-roll').addEventListener('click', rollAndPlay);
  el('btn-stop').addEventListener('click', stopPlayback);
  el('btn-random-seed').addEventListener('click', randomSeed);

  document.querySelectorAll('.lang-btn').forEach(b => {
    b.addEventListener('click', () => setLanguage(b.dataset.setLang));
  });

  setLanguage('en');
});

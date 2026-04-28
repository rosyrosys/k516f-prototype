/* app.js — Browser-side K.516f generator for the GitHub Pages demo.
 *
 * Mirrors src/generator.py: same alphabet, same triangular pmf, same
 * archetypes (loaded from ./js/bars.json).
 *
 * Renders to Web Audio with a small inline fortepiano voice that
 * approximates src/synth.py — additive partials with two-stage decay,
 * inharmonicity, and stereo spread. The browser version trades some
 * fidelity (no biquad soundboard formant) for code size.
 *
 * Wires up #playBtn / #seedInput / #distSelect on the host page if they
 * exist; otherwise exposes window.k516f = { play, seedInput, ... } so
 * the host page can drive it.
 */

(function () {
  "use strict";

  let BARS = null;
  let audioCtx = null;

  // ------------------------------------------------------------------ data
  async function loadBars() {
    if (BARS) return BARS;
    const res = await fetch("./js/bars.json");
    BARS = await res.json();
    return BARS;
  }

  // ------------------------------------------------------------------ rng
  // Mulberry32 — deterministic, matches numpy default_rng spectrum
  // approximately enough for a *demo*; exact reproducibility lives in
  // the Python reference.
  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function sample(rng, pmf) {
    const u = rng();
    let acc = 0;
    for (let i = 0; i < pmf.length; i++) {
      acc += pmf[i];
      if (u < acc) return i;
    }
    return pmf.length - 1;
  }

  function pmfFor(barPos, dist, k) {
    if (dist === "triangular" && k === 11) return BARS.triangular_11;
    if (dist === "triangular" && k === 2)  return [0.5, 0.5];
    if (dist === "triangular" && k === 1)  return [1.0];
    return Array(k).fill(1 / k);
  }

  function generate(dist, seed) {
    const rng = mulberry32(seed);
    const chosen = [];
    const mel = [];
    const bass = [];
    for (let bp = 1; bp <= BARS.n_bars; bp++) {
      const feasible = BARS.alphabet_at[String(bp)];
      const k = feasible.length;
      const pmf = pmfFor(bp, dist, k);
      const idx = feasible[sample(rng, pmf)];
      chosen.push(idx);
      const offset = (bp - 1) * BARS.time_sig[0];
      for (const [s, p, d] of BARS.mel_archetypes[idx])
        mel.push([offset + s, p, d]);
      for (const [s, p, d] of BARS.bass_archetypes[idx])
        bass.push([offset + s, p, d]);
    }
    return { chosen, mel, bass };
  }

  // ------------------------------------------------------------------ synth
  function midiToHz(m) { return 440 * Math.pow(2, (m - 69) / 12); }

  function scheduleNote(ctx, when, pitch, durBeats, secPerBeat, gain) {
    const f0 = midiToHz(pitch);
    const dur = durBeats * secPerBeat;
    const out = ctx.createGain();
    out.gain.value = gain;
    out.connect(ctx.destination);

    const weights = [0.55, 0.95, 0.70, 0.45, 0.32, 0.22, 0.16, 0.11, 0.08, 0.05];
    const B = 4e-4;

    for (let i = 1; i <= weights.length; i++) {
      const f = i * f0 * Math.sqrt(1 + B * i * i);
      const osc = ctx.createOscillator();
      const env = ctx.createGain();
      const pan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
      osc.type = "sine";
      osc.frequency.value = f;
      const w = weights[i - 1];
      env.gain.setValueAtTime(0.0, when);
      env.gain.linearRampToValueAtTime(w, when + 0.008);
      // two-stage decay
      env.gain.exponentialRampToValueAtTime(Math.max(0.001, w * 0.4),
                                             when + 0.10);
      env.gain.exponentialRampToValueAtTime(0.001,
                                             when + Math.max(dur, 0.4) + 1.0);
      osc.connect(env);
      if (pan) {
        pan.pan.value = (i % 2 === 0) ? 0.15 : -0.15;
        env.connect(pan);
        pan.connect(out);
      } else {
        env.connect(out);
      }
      osc.start(when);
      osc.stop(when + dur + 1.5);
    }
  }

  function play(events, secPerBeat, gain) {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const t0 = audioCtx.currentTime + 0.05;
    for (const [sb, p, db] of events) {
      scheduleNote(audioCtx, t0 + sb * secPerBeat, p, db, secPerBeat, gain);
    }
  }

  async function playRealisation(seed, dist) {
    await loadBars();
    const { chosen, mel, bass } = generate(dist, seed);
    const secPerBeat = 60 / BARS.tempo_bpm;
    play(mel,  secPerBeat, 0.18);
    play(bass, secPerBeat, 0.12);
    return chosen;
  }

  // ------------------------------------------------------------------ wire-up
  function wireUI() {
    const btn  = document.getElementById("playBtn");
    const seed = document.getElementById("seedInput");
    const dist = document.getElementById("distSelect");
    const out  = document.getElementById("chosenOut");
    if (!btn) return;
    btn.addEventListener("click", async () => {
      const s = parseInt((seed && seed.value) || "42", 10);
      const d = (dist && dist.value) || "triangular";
      const chosen = await playRealisation(s, d);
      if (out) out.textContent = "chosen archetype indices: " +
        JSON.stringify(chosen.map(i => i + 1));
    });
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", wireUI);
  else
    wireUI();

  // expose for host pages
  window.k516f = { generate, playRealisation, loadBars };
})();

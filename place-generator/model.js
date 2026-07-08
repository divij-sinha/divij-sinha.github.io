// Pure-JS port of model_np.py's NumpyCharRNN (LSTM inference + sampling).
// No dependencies. Mirrors the torch model in utils.py:
//   to_hidden: Linear(vocab -> 128)
//   layer:     LSTM(128 -> 128), single layer
//   fc:        Linear(128 -> vocab)
// PyTorch's LSTM packs gates in order [input, forget, cell(g), output],
// each of size hidden_size, stacked along axis 0 of weight_ih / weight_hh.

const MAX_LENGTH = 20;

function sigmoid(x) {
  return 1.0 / (1.0 + Math.exp(-x));
}

// y = W @ x + b, where W is (outDim x inDim) row-major nested array,
// x and b are flat arrays of length inDim / outDim.
function linear(W, b, x) {
  const outDim = W.length;
  const inDim = x.length;
  const y = new Array(outDim);
  for (let o = 0; o < outDim; o++) {
    let sum = b[o];
    const row = W[o];
    for (let i = 0; i < inDim; i++) {
      sum += row[i] * x[i];
    }
    y[o] = sum;
  }
  return y;
}

function addVec(a, b) {
  return a.map((v, i) => v + b[i]);
}

function createModel(weights, vocab, revVocab) {
  const W_ih_in = weights["to_hidden.weight"]; // (128, 40)
  const b_ih_in = weights["to_hidden.bias"]; // (128,)
  const W_ih = weights["layer.weight_ih_l0"]; // (512, 128)
  const W_hh = weights["layer.weight_hh_l0"]; // (512, 128)
  const b_ih = weights["layer.bias_ih_l0"]; // (512,)
  const b_hh = weights["layer.bias_hh_l0"]; // (512,)
  const W_fc = weights["fc.weight"]; // (40, 128)
  const b_fc = weights["fc.bias"]; // (40,)
  const H = W_hh[0].length; // 128
  const V = Object.keys(vocab).length; // 40

  function oneHot(s) {
    const rows = [];
    for (const ch of s) {
      const idx = vocab[ch];
      const row = new Array(V).fill(0);
      row[idx] = 1.0;
      rows.push(row);
    }
    return rows;
  }

  // Returns logits for every position in string s: array of length s.length,
  // each element a flat array of length V.
  function logits(s) {
    const oh = oneHot(s);
    // x[t] = oh[t] @ W_ih_in.T + b_ih_in  (linear() already does W @ x + b,
    // and W_ih_in is (128, 40) = (out, in), so linear(W_ih_in, b_ih_in, oh[t])
    // computes exactly oh[t] @ W_ih_in.T + b_ih_in).
    const x = oh.map((row) => linear(W_ih_in, b_ih_in, row));
    let h = new Array(H).fill(0);
    let c = new Array(H).fill(0);
    const outs = [];
    for (let t = 0; t < x.length; t++) {
      const gatesX = linear(W_ih, b_ih, x[t]);
      const gatesH = linear(W_hh, b_hh, h);
      const gates = addVec(gatesX, gatesH);
      const i = gates.slice(0, H).map(sigmoid);
      const f = gates.slice(H, 2 * H).map(sigmoid);
      const g = gates.slice(2 * H, 3 * H).map(Math.tanh);
      const o = gates.slice(3 * H, 4 * H).map(sigmoid);
      const newC = new Array(H);
      const newH = new Array(H);
      for (let k = 0; k < H; k++) {
        newC[k] = f[k] * c[k] + i[k] * g[k];
        newH[k] = o[k] * Math.tanh(newC[k]);
      }
      c = newC;
      h = newH;
      outs.push(h.slice());
    }
    return outs.map((hVec) => linear(W_fc, b_fc, hVec));
  }

  function sampleIndex(probs, rng) {
    const r = rng.random();
    let cum = 0;
    for (let i = 0; i < probs.length; i++) {
      cum += probs[i];
      if (r < cum) return i;
    }
    return probs.length - 1; // guard against floating-point rounding
  }

  function generate(startText, n, states, rng) {
    rng = rng || { random: Math.random };
    const validStates = states.filter((s) => s);
    const results = [];
    for (let k = 0; k < n; k++) {
      let inp = "?" + startText.toLowerCase();
      let code = 0;
      if (validStates.length > 0) {
        code = validStates[Math.floor(rng.random() * validStates.length)];
        inp = "~" + String(code) + inp;
      }
      while (inp.length < MAX_LENGTH) {
        const lg = logits(inp)[inp.length - 1];
        const maxLg = Math.max(...lg);
        const expLg = lg.map((v) => Math.exp(v - maxLg));
        const sumExp = expLg.reduce((a, b) => a + b, 0);
        const probs = expLg.map((v) => v / sumExp);
        const idx = sampleIndex(probs, rng);
        const ch = revVocab[idx];
        if (ch === "!") break;
        inp = inp + ch;
      }
      const name = inp
        .split("?")
        .slice(1)
        .join("?")
        .trim()
        .replace(/\w\S*/g, (w) => w.charAt(0).toUpperCase() + w.slice(1));
      results.push({ name, code });
    }
    return results;
  }

  return { logits, generate };
}

// Node (test harness) + browser <script> compatibility.
if (typeof module !== "undefined" && module.exports) {
  module.exports = { createModel };
}

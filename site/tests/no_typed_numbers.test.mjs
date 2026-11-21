// Every number in the narrative must come from data. This scans string literals in the
// text and layout code for digits, allowing only method constants that are not results.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const FILES = ["src/sections/text.js", "src/sections/render.js", "src/sections/methods.js", "src/components/anomalyCard.js", "src/tools/lab.js", "src/tools/placebo.js", "src/tools/timeline.js", "src/tools/explainer.js"];
const ALLOWED = [/95%/g, /\b5%/g, /0\.75/g, /\bT0\b/g, /T\+1\b/g, /T\+3\b/g, /T\+20\b/g, /\\u2212\d?/g,
  /\bh[1-6]\b/g, /\bt[+-]?\d\b/g, /h-t[01]p?/g, /\bt0\b/g, /\bt\+1\b/g, /\bt-[123]\b/g, /Phase \d/g, /CC-BY/g, /Story \d/g, /\bE1\b/g, /\bDay 0\b/g,
  /\(\d{4}\)/g, /\d+\(\d+\), \d+-\d+/g, /planet4589/g, /\bv\d/g, /\u00a7/g,
  /T\u2212[1-5]\b/g, /#[0-9A-Fa-f]{6}\b/g, /T00:00:00Z/g];  // stage labels, colour codes, ISO midnight  // citations in methods.js

/**
 * Text of every string literal, with ${...} expressions removed. A small tokenizer: handles comments,
 * regex-free code, and template literals nested inside ${...} (their text is collected too).
 */
function strings(src) {
  const out = [];
  let i = 0;
  function quoted(q) {                       // i is at the opening quote
    let s = ""; i++;
    while (i < src.length && src[i] !== q) { if (src[i] === "\\") { s += src[i] + src[i + 1]; i += 2; } else s += src[i++]; }
    i++; out.push(s);
  }
  function template() {                      // i is at the opening backtick
    let s = ""; i++;
    while (i < src.length && src[i] !== "`") {
      if (src[i] === "\\") { s += src[i] + src[i + 1]; i += 2; continue; }
      if (src[i] === "$" && src[i + 1] === "{") { i += 2; code(true); continue; }
      s += src[i++];
    }
    i++; out.push(s);
  }
  function code(inExpr) {                    // reads code until the matching } (inExpr) or end of file
    let depth = 0;
    while (i < src.length) {
      const c = src[i], n = src[i + 1];
      if (c === "/" && n === "/") { while (i < src.length && src[i] !== "\n") i++; continue; }
      if (c === "/" && n === "*") { i = src.indexOf("*/", i + 2); i = i < 0 ? src.length : i + 2; continue; }
      if (c === '"' || c === "'") { quoted(c); continue; }
      if (c === "`") { template(); continue; }
      if (c === "{") depth++;
      if (c === "}") { if (inExpr && depth === 0) { i++; return; } depth--; }
      i++;
    }
  }
  code(false);
  return out;
}

test("no result numbers typed into narrative strings", () => {
  const bad = [];
  for (const f of FILES) {
    for (let s of strings(readFileSync(f, "utf8"))) {
      if (/^[\w./-]+\.(js|css|json)$/.test(s) || /^(\.\.?\/)/.test(s) || /^\d$/.test(s)) continue; // import paths, padding chars
      for (const a of ALLOWED) s = s.replace(a, "");
      s = s.replace(/<[^>]+>/g, " ");                   // HTML tags and attributes
      if (/\d/.test(s)) bad.push(`${f}: ${s.trim().slice(0, 80)}`);
    }
  }
  assert.deepEqual(bad, []);
});

// Every number in the narrative must come from data. This scans string literals in the
// text and layout code for digits, allowing only method constants that are not results.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const FILES = ["src/sections/text.js", "src/sections/render.js", "src/components/anomalyCard.js"];
const ALLOWED = [/95%/g, /\b5%/g, /0\.75/g, /\bT0\b/g, /T\+1\b/g, /T\+3\b/g, /T\+20\b/g, /\\u2212\d?/g,
  /\bh[1-6]\b/g, /\bt[+-]?\d\b/g, /h-t[01]p?/g, /\bt0\b/g, /\bt\+1\b/g, /\bt-[123]\b/g, /Phase \d/g, /CC-BY/g, /Story \d/g, /\bE1\b/g, /\bDay 0\b/g];

function strings(src) {
  const out = [];
  const re = /`(?:[^`\\]|\\.)*`|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/gs;
  for (const m of src.matchAll(re)) {
    let s = m[0].slice(1, -1);
    // drop ${...} expressions (they are code, not typed text)
    let depth = 0, keep = "";
    for (let i = 0; i < s.length; i++) {
      if (s[i] === "$" && s[i + 1] === "{") { depth++; i++; continue; }
      if (depth && s[i] === "{") { depth++; continue; }
      if (depth && s[i] === "}") { depth--; continue; }
      if (!depth) keep += s[i];
    }
    out.push(keep);
  }
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

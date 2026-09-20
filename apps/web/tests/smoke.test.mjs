import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const source = await readFile(new URL("../src/App.tsx", import.meta.url), "utf8");

test("frontend keeps paper/live boundary and real data boundary visible", () => {
  assert.match(source, /PAPER/);
  assert.match(source, /NO FABRICATED DATA/);
  assert.match(source, /api\/paper\/orders/);
  assert.match(source, /api\/market\/option-chain/);
  assert.match(source, /api\/scanner/);
  assert.doesNotMatch(source, /ETradeLiveBroker\.submit/);
  assert.doesNotMatch(source, /fallbackDashboard/);
});

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const source = await readFile(new URL("../src/App.tsx", import.meta.url), "utf8");

test("dashboard keeps paper/live boundary visible", () => {
  assert.match(source, /PAPER/);
  assert.match(source, /live-options execution is unavailable/);
  assert.match(source, /Prepare paper ticket/);
  assert.doesNotMatch(source, /ETradeLiveBroker\.submit/);
});

"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { parseStickerCsv, expandAmpersandToken } = require("./sticker-csv.js");

test("comma shorthand: BIH1,2,5,10 expands to four codes", () => {
  assert.deepEqual(parseStickerCsv("BIH1,2,5,10"), ["BIH1", "BIH2", "BIH5", "BIH10"]);
});

test("comma shorthand: multi-digit base and continuation", () => {
  assert.deepEqual(parseStickerCsv("BIH10,11"), ["BIH10", "BIH11"]);
});

test("comma shorthand: stem resets after a full code", () => {
  assert.deepEqual(parseStickerCsv("BIH1,MEX2,3"), ["BIH1", "MEX2", "MEX3"]);
});

test("comma shorthand: works with count suffix on first token", () => {
  assert.deepEqual(parseStickerCsv("BIH1(2),3"), ["BIH1", "BIH1", "BIH3"]);
});

test("bare numbers at start stay literal when no prior stem", () => {
  assert.deepEqual(parseStickerCsv("2,3,4"), ["2", "3", "4"]);
});

test("legacy: comma-separated full codes and counts", () => {
  assert.deepEqual(parseStickerCsv("MEX1(2), BRA3"), ["MEX1", "MEX1", "BRA3"]);
});

test("legacy: empty slots ignored", () => {
  assert.deepEqual(parseStickerCsv("ESP10 ,,ALG2"), ["ESP10", "ALG2"]);
});

test("legacy: ampersand expansion unchanged", () => {
  assert.deepEqual(expandAmpersandToken("MEX1&2&3"), ["MEX1", "MEX2", "MEX3"]);
});

test("shorthand with spaces after commas", () => {
  assert.deepEqual(parseStickerCsv("BIH1, 2, 5"), ["BIH1", "BIH2", "BIH5"]);
});

import { describe, expect, it } from "vitest";

import {
  formatDuration,
  formatScore,
  shortTimecode,
  timecodeRange,
} from "./scene-format";

describe("formatDuration", () => {
  it("formats sub-hour durations as M:SS", () => {
    expect(formatDuration(0)).toBe("0:00");
    expect(formatDuration(9)).toBe("0:09");
    expect(formatDuration(75)).toBe("1:15");
  });

  it("formats hour-plus durations as H:MM:SS", () => {
    expect(formatDuration(3661)).toBe("1:01:01");
  });

  it("returns a dash for null/invalid input", () => {
    expect(formatDuration(null)).toBe("—");
    expect(formatDuration(-1)).toBe("—");
    expect(formatDuration(Number.NaN)).toBe("—");
  });
});

describe("shortTimecode", () => {
  it("drops the milliseconds fraction", () => {
    expect(shortTimecode("00:00:03.500")).toBe("00:00:03");
    expect(shortTimecode("00:01:00")).toBe("00:01:00");
  });
});

describe("formatScore", () => {
  it("renders a clamped percentage", () => {
    expect(formatScore(0.873)).toBe("87%");
    expect(formatScore(1.5)).toBe("100%");
    expect(formatScore(-0.2)).toBe("0%");
  });
});

describe("timecodeRange", () => {
  it("joins two short timecodes", () => {
    expect(timecodeRange("00:00:00.000", "00:00:03.000")).toBe(
      "00:00:00 – 00:00:03"
    );
  });
});

import type { HassEntity } from "home-assistant-js-websocket";
import { describe, expect, it } from "vitest";
import {
  formatCountdown,
  formatPreset,
  parseDuration,
  progress,
  remainingSeconds,
} from "./time";

const NOW = Date.parse("2026-10-19T08:00:00Z");

const entity = (state: string, attributes: Record<string, unknown>): HassEntity => ({
  entity_id: "sensor.waschmaschine",
  state,
  attributes,
  last_changed: "",
  last_updated: "",
  context: { id: "", parent_id: null, user_id: null },
});

describe("parseDuration", () => {
  it.each([
    ["1:30:00", 5400],
    ["0:00:59", 59],
    ["2:15", 8100],
  ])("parses %s", (value, expected) => {
    expect(parseDuration(value)).toBe(expected);
  });

  it.each([undefined, null, "", "abc", "1", "1:2:3:4", "-1:00"])(
    "rejects %s",
    (value) => {
      expect(parseDuration(value)).toBeUndefined();
    },
  );
});

describe("remaining and progress", () => {
  it("counts down while running", () => {
    const e = entity("running", {
      duration: "1:00:00",
      finishes_at: "2026-10-19T08:15:00+00:00",
    });
    expect(remainingSeconds(e, NOW)).toBe(900);
    expect(progress(e, NOW)).toBe(0.25);
  });

  it("never goes below zero", () => {
    const e = entity("running", {
      duration: "1:00:00",
      finishes_at: "2026-10-19T07:00:00+00:00",
    });
    expect(remainingSeconds(e, NOW)).toBe(0);
  });

  it("uses remaining while paused", () => {
    const e = entity("paused", { duration: "1:00:00", remaining: "0:45:00" });
    expect(remainingSeconds(e, NOW)).toBe(2700);
    expect(progress(e, NOW)).toBe(0.75);
  });

  it("shows a full ring when finished and an empty one when idle", () => {
    expect(progress(entity("finished", { duration: "1:00:00" }), NOW)).toBe(1);
    expect(progress(entity("idle", {}), NOW)).toBe(0);
  });
});

describe("formatting", () => {
  it.each([
    [3909, "1:05:09"],
    [249, "4:09"],
    [0.2, "0:01"],
    [0, "0:00"],
  ])("formats countdown %d", (seconds, expected) => {
    expect(formatCountdown(seconds)).toBe(expected);
  });

  it.each([
    [1800, "30 min"],
    [3600, "1 h"],
    [5400, "1:30 h"],
  ])("formats preset %d", (seconds, expected) => {
    expect(formatPreset(seconds)).toBe(expected);
  });
});

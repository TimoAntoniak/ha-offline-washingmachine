// Pure time helpers, mirroring how the frontend derives a timer's remaining time.
import type { HassEntity } from "./ha";

export type LaundryState = "idle" | "running" | "paused" | "finished";

export interface Duration {
  hours?: number;
  minutes?: number;
  seconds?: number;
}

/** Parse "H:MM:SS" or "H:MM" into seconds. */
export function parseDuration(value: unknown): number | undefined {
  if (typeof value !== "string") return undefined;
  const parts = value.split(":").map(Number);
  if (
    parts.length < 2 ||
    parts.length > 3 ||
    parts.some((p) => !Number.isFinite(p) || p < 0)
  )
    return undefined;
  const [h = 0, m = 0, s = 0] = parts;
  return h * 3600 + m * 60 + s;
}

export function durationToSeconds(d: Duration | undefined): number {
  return (d?.hours ?? 0) * 3600 + (d?.minutes ?? 0) * 60 + (d?.seconds ?? 0);
}

export function secondsToDuration(total: number): Duration {
  return { hours: Math.floor(total / 3600), minutes: Math.floor((total % 3600) / 60) };
}

/** Remaining seconds of a cycle at `now` (ms since epoch). */
export function remainingSeconds(stateObj: HassEntity, now: number): number {
  if (stateObj.state === "running") {
    const end = Date.parse(String(stateObj.attributes.finishes_at));
    return Number.isNaN(end) ? 0 : Math.max(0, (end - now) / 1000);
  }
  if (stateObj.state === "paused")
    return parseDuration(stateObj.attributes.remaining) ?? 0;
  return 0;
}

/** Fraction of the cycle still to go, 0..1. A finished cycle shows a full ring. */
export function progress(stateObj: HassEntity, now: number): number {
  if (stateObj.state === "finished") return 1;
  const duration = parseDuration(stateObj.attributes.duration);
  if (!duration) return 0;
  return Math.min(1, Math.max(0, remainingSeconds(stateObj, now) / duration));
}

/** Countdown like "1:05:09" or "4:09". */
export function formatCountdown(seconds: number): string {
  const total = Math.ceil(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = h ? String(m).padStart(2, "0") : String(m);
  return `${h ? `${String(h)}:` : ""}${mm}:${String(s).padStart(2, "0")}`;
}

/** Short label for presets like "30 min", "1 h", "1:30 h". */
export function formatPreset(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (!h) return `${String(m)} min`;
  return m ? `${String(h)}:${String(m).padStart(2, "0")} h` : `${String(h)} h`;
}

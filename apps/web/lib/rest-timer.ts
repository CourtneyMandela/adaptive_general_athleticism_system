export function remainingRestSeconds(deadlineMs: number, nowMs: number): number {
  if (!Number.isFinite(deadlineMs) || !Number.isFinite(nowMs)) return 0;
  return Math.max(0, Math.ceil((deadlineMs - nowMs) / 1000));
}

export function formatRestTime(totalSeconds: number): string {
  const bounded = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(bounded / 60);
  const seconds = bounded % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

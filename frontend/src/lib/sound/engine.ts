import { RECIPES } from "./recipes";
import { gainFor, MIN_GAP_MS, type SoundEvent, type SoundSettings } from "./settings";

export type ContextFactory = () => AudioContext;

/**
 * Sound engine. Browsers forbid audio before a user gesture, so nothing is
 * created until ``unlock()`` is called from a gesture handler. Sounds are
 * fire-and-forget, throttled, and never required for any function.
 */
export class SoundEngine {
  private ctx: AudioContext | null = null;
  private lastPlayed = new Map<SoundEvent, number>();
  private output: GainNode | null = null;

  constructor(
    private settings: SoundSettings,
    private readonly factory: ContextFactory | null,
    private readonly now: () => number = () => Date.now(),
  ) {}

  get unlocked(): boolean {
    return this.ctx !== null && this.ctx.state !== "closed";
  }

  update(settings: SoundSettings): void {
    this.settings = settings;
  }

  /** Call from a pointer/keyboard handler. Safe to call repeatedly. */
  unlock(): boolean {
    if (!this.factory) return false;
    try {
      if (!this.ctx) {
        this.ctx = this.factory();
        this.output = this.ctx.createGain();
        this.output.connect(this.ctx.destination);
      }
      if (this.ctx.state === "suspended") void this.ctx.resume();
      return true;
    } catch {
      return false; // audio unsupported: the app works silently
    }
  }

  play(event: SoundEvent): boolean {
    const gain = gainFor(this.settings, event);
    if (gain <= 0 || !this.ctx || !this.output) return false;
    const t = this.now();
    const gap = MIN_GAP_MS[event];
    const last = this.lastPlayed.get(event);
    if (gap && last !== undefined && t - last < gap) return false;
    this.lastPlayed.set(event, t);
    try {
      const bus = this.ctx.createGain();
      bus.gain.value = gain;
      bus.connect(this.output);
      RECIPES[event](this.ctx, bus, this.ctx.currentTime + 0.01);
      return true;
    } catch {
      return false;
    }
  }

  /** Mute-all takes effect immediately, including sounds already playing. */
  silenceNow(): void {
    if (this.output && this.ctx) this.output.gain.setValueAtTime(0, this.ctx.currentTime);
  }

  restore(): void {
    if (this.output && this.ctx) this.output.gain.setValueAtTime(1, this.ctx.currentTime);
  }
}

import {
  LitElement,
  css,
  html,
  nothing,
  svg,
  type PropertyValues,
  type SVGTemplateResult,
} from "lit";
import {
  ensureHaForm,
  fireEvent,
  type HassEntity,
  type HomeAssistant,
  type LovelaceCardConfig,
  type LovelaceGridOptions,
} from "./ha";
import { NewLoadDialog, type NewLoad } from "./new-load-dialog";
import {
  formatCountdown,
  parseDuration,
  progress,
  remainingSeconds,
  type LaundryState,
} from "./time";

const DOMAIN = "offline_laundry";
const CARD_TYPE = "offline-laundry-card";
const STATES: LaundryState[] = ["idle", "running", "paused", "finished"];
const DEFAULT_PRESETS = ["0:30", "1:00", "1:30", "2:00", "3:00"];
const CANCEL_CONFIRM_MS = 3000;

interface LaundryCardConfig extends LovelaceCardConfig {
  entity: string;
  name?: string;
  presets?: string[];
}

/** The status sensor exposes exactly our states as enum options. */
function isLaundryEntity(stateObj: HassEntity | undefined): boolean {
  const options: unknown = stateObj?.attributes.options;
  return (
    Array.isArray(options) &&
    options.length === STATES.length &&
    STATES.every((s) => options.includes(s))
  );
}

export class OfflineLaundryCard extends LitElement {
  static override properties = {
    hass: { attribute: false },
    preview: { type: Boolean },
    _config: { state: true },
    _now: { state: true },
    _dialogOpen: { state: true },
    _confirmCancel: { state: true },
  };

  declare hass?: HomeAssistant;
  declare preview: boolean;
  declare _config?: LaundryCardConfig;
  declare _now: number;
  declare _dialogOpen: boolean;
  declare _confirmCancel: boolean;

  private _ticker?: number;
  private _confirmTimeout?: number;

  constructor() {
    super();
    this.preview = false;
    this._now = Date.now();
    this._dialogOpen = false;
    this._confirmCancel = false;
  }

  static getConfigForm() {
    return {
      schema: [
        {
          name: "entity",
          required: true,
          selector: {
            entity: {
              filter: { integration: DOMAIN, domain: "sensor", device_class: "enum" },
            },
          },
        },
        { name: "name", selector: { text: {} } },
        {
          name: "presets",
          selector: {
            select: { multiple: true, custom_value: true, options: DEFAULT_PRESETS },
          },
        },
      ],
      computeLabel: (schema: { name: string }) =>
        ({ entity: "Gerät", name: "Name", presets: "Schnellwahl (H:MM)" })[schema.name],
    };
  }

  static getStubConfig(hass: HomeAssistant): Omit<LaundryCardConfig, "type"> {
    const entity = Object.values(hass.states).find(isLaundryEntity);
    return { entity: entity?.entity_id ?? "" };
  }

  setConfig(config: LaundryCardConfig): void {
    if (typeof config.entity !== "string" || !config.entity) {
      throw new Error("Bitte ein Wäschegerät als Entität wählen.");
    }
    const invalid = config.presets?.find((p) => !parseDuration(p));
    if (invalid !== undefined) {
      throw new Error(`Ungültige Schnellwahl: ${invalid} (Format H:MM)`);
    }
    this._config = config;
  }

  getCardSize(): number {
    return 6;
  }

  getGridOptions(): LovelaceGridOptions {
    return { columns: 12, rows: "auto", min_columns: 6 };
  }

  private get _stateObj(): HassEntity | undefined {
    return this._config ? this.hass?.states[this._config.entity] : undefined;
  }

  private get _presets(): number[] {
    return (this._config?.presets ?? DEFAULT_PRESETS)
      .map(parseDuration)
      .filter((s): s is number => s !== undefined && s > 0);
  }

  override connectedCallback(): void {
    super.connectedCallback();
    this._syncTicker();
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this._stopTicker();
    window.clearTimeout(this._confirmTimeout);
  }

  protected override shouldUpdate(changed: PropertyValues<this>): boolean {
    if (changed.size !== 1 || !changed.has("hass") || !this._config) return true;
    const old = changed.get("hass");
    return old?.states[this._config.entity] !== this._stateObj;
  }

  protected override updated(changed: PropertyValues<this>): void {
    if (changed.has("hass") || changed.has("preview")) this._syncTicker();
  }

  private _syncTicker(): void {
    const running = this._stateObj?.state === "running" && !this.preview;
    if (running && this._ticker === undefined) {
      this._now = Date.now();
      this._ticker = window.setInterval(() => {
        this._now = Date.now();
      }, 1000);
    } else if (!running) {
      this._stopTicker();
    }
  }

  private _stopTicker(): void {
    window.clearInterval(this._ticker);
    this._ticker = undefined;
  }

  protected override render() {
    if (!this._config || !this.hass) return nothing;
    const stateObj = this._stateObj;
    if (!stateObj) {
      return html`<ha-card class="message"
        >Entität nicht gefunden: ${this._config.entity}</ha-card
      >`;
    }

    const state = stateObj.state as LaundryState;
    const known = STATES.includes(state);
    const active = state === "running" || state === "paused";
    const name =
      this._config.name ?? stateObj.attributes.friendly_name ?? stateObj.entity_id;
    const load = stateObj.attributes.load as string | null | undefined;
    const status = this.hass.formatEntityState(stateObj);

    return html`
      <ha-card class=${known ? state : "unavailable"}>
        <div class="panel">
          <ha-state-icon .hass=${this.hass} .stateObj=${stateObj}></ha-state-icon>
          <div class="info">
            <div class="name">${name}</div>
            ${
              this._confirmCancel
                ? html`<div class="status warn" role="status">
                    Sicher? Nochmal tippen
                  </div>`
                : html`<div class="status">
                    ${load && state !== "idle" ? `${load} · ${status}` : status}
                  </div>`
            }
          </div>
          <span class="led" aria-hidden="true"></span>
          ${
            active
              ? html`
                  <ha-icon-button
                    .label=${state === "paused" ? "Fortsetzen" : "Pausieren"}
                    @click=${() => {
                      this._call(state === "paused" ? "resume" : "pause");
                    }}
                  >
                    <ha-icon
                      icon=${state === "paused" ? "mdi:play" : "mdi:pause"}
                    ></ha-icon>
                  </ha-icon-button>
                  <ha-icon-button
                    class=${this._confirmCancel ? "confirm" : ""}
                    .label=${this._confirmCancel ? "Wirklich abbrechen?" : "Abbrechen"}
                    @click=${this._cancelClicked}
                  >
                    <ha-icon
                      icon=${this._confirmCancel ? "mdi:check" : "mdi:close"}
                    ></ha-icon>
                  </ha-icon-button>
                `
              : nothing
          }
        </div>
        <div class="body">${this._renderDrum(stateObj, state, known)}</div>
      </ha-card>
      <offline-laundry-new-load-dialog
        .hass=${this.hass}
        .heading=${"Neue Wäsche"}
        .subheading=${name}
        .presets=${this._presets}
        .open=${this._dialogOpen}
        @start-load=${(ev: CustomEvent<NewLoad>) => {
          this._start(ev.detail);
        }}
        @closed=${() => {
          this._dialogOpen = false;
        }}
      ></offline-laundry-new-load-dialog>
    `;
  }

  private _renderDrum(stateObj: HassEntity, state: LaundryState, known: boolean) {
    const fraction = known ? progress(stateObj, this._now) : 0;
    // pathLength=1 lets the dash offset be the fraction itself. A negative offset
    // keeps the remaining arc ending at 12 o'clock, so it shrinks clockwise. Empty and
    // full rings are drawn without a dash to avoid a seam at the top.
    let arc: SVGTemplateResult | typeof nothing = nothing;
    if (fraction >= 1) {
      arc = svg`<circle class="progress" cx="100" cy="100" r="88" />`;
    } else if (fraction > 0) {
      arc = svg`
        <circle
          class="progress"
          cx="100"
          cy="100"
          r="88"
          pathLength="1"
          stroke-dasharray="1 1"
          stroke-dashoffset=${String(fraction - 1)}
          stroke-linecap="round"
          transform="rotate(-90 100 100)"
        />
      `;
    }
    const ring = svg`
      <svg viewBox="0 0 200 200" aria-hidden="true">
        <circle class="track" cx="100" cy="100" r="88" />
        ${arc}
        <circle class="door" cx="100" cy="100" r="72" />
        <circle class="glass" cx="100" cy="100" r="60" />
      </svg>
    `;

    if (state === "idle") {
      return html`
        <button class="drum" @click=${this._openDialog}>
          ${ring}
          <span class="center">
            <ha-icon icon="mdi:plus"></ha-icon>
            <span class="caption">Neue Wäsche</span>
          </span>
        </button>
      `;
    }
    if (state === "finished") {
      return html`
        <button
          class="drum"
          @click=${() => {
            this._call("empty");
          }}
        >
          ${ring}
          <span class="center">
            <ha-icon icon="mdi:basket-outline"></ha-icon>
            <span class="action">Leeren</span>
          </span>
        </button>
      `;
    }
    if (!known) {
      return html`
        <div class="drum">
          ${ring}
          <span class="center"><span class="caption">Nicht verfügbar</span></span>
        </div>
      `;
    }

    const remaining = remainingSeconds(stateObj, this._now);
    const countdown = formatCountdown(remaining);
    const caption =
      state === "paused"
        ? "pausiert"
        : `fertig um ${new Date(this._now + remaining * 1000).toLocaleTimeString(
            this.hass?.locale.language,
            { hour: "2-digit", minute: "2-digit" },
          )}`;
    return html`
      <div
        class="drum"
        role="progressbar"
        aria-label="Restzeit"
        aria-valuemin="0"
        aria-valuemax=${String(parseDuration(stateObj.attributes.duration) ?? 0)}
        aria-valuenow=${String(Math.round(remaining))}
        aria-valuetext=${`${countdown}, ${caption}`}
      >
        ${ring}
        <span class="center">
          <span class="time">${countdown}</span>
          <span class="caption">${caption}</span>
        </span>
      </div>
    `;
  }

  private async _openDialog(): Promise<void> {
    await ensureHaForm();
    this._dialogOpen = true;
  }

  private _cancelClicked(): void {
    window.clearTimeout(this._confirmTimeout);
    if (!this._confirmCancel) {
      this._confirmCancel = true;
      fireEvent(this, "haptic", "warning");
      this._confirmTimeout = window.setTimeout(() => {
        this._confirmCancel = false;
      }, CANCEL_CONFIRM_MS);
      return;
    }
    this._confirmCancel = false;
    this._call("cancel");
  }

  private _start({ duration, load }: NewLoad): void {
    const data: Record<string, unknown> = { duration: { seconds: duration } };
    if (load) data.load = load;
    this._call("start", data, "success");
  }

  private _call(
    service: string,
    data: Record<string, unknown> = {},
    haptic: "light" | "success" = "light",
  ): void {
    if (!this.hass || !this._config) return;
    fireEvent(this, "haptic", haptic);
    // Errors are shown as a toast by the frontend itself.
    this.hass
      .callService(DOMAIN, service, data, { entity_id: this._config.entity })
      .catch(() => undefined);
  }

  static override styles = css`
    ha-card {
      --laundry-color: var(--primary-color);
      --laundry-rgb: var(--rgb-primary-color);
      overflow: hidden;
      height: 100%;
      display: flex;
      flex-direction: column;
    }
    ha-card.paused {
      --laundry-color: var(--disabled-text-color);
    }
    ha-card.finished {
      --laundry-color: var(--accent-color);
      --laundry-rgb: var(--rgb-accent-color);
    }
    ha-card.message {
      padding: 16px;
    }
    .panel {
      display: flex;
      align-items: center;
      gap: 12px;
      min-height: 56px;
      padding: 4px 4px 4px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    ha-state-icon {
      color: var(--secondary-text-color);
    }
    .finished ha-state-icon {
      color: var(--laundry-color);
    }
    .info {
      flex: 1;
      min-width: 0;
    }
    .name {
      font-weight: 500;
      color: var(--primary-text-color);
    }
    .status {
      font-size: 12px;
      color: var(--secondary-text-color);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .status.warn {
      color: var(--error-color);
    }
    .led {
      flex: none;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--divider-color);
    }
    .running .led,
    .finished .led {
      background: var(--laundry-color);
    }
    .led:last-child {
      margin-right: 12px;
    }
    ha-icon-button {
      color: var(--secondary-text-color);
    }
    ha-icon-button.confirm {
      color: var(--error-color);
    }
    .body {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
    }
    .drum {
      position: relative;
      width: min(100%, 240px);
      aspect-ratio: 1;
      padding: 0;
      border: none;
      border-radius: 50%;
      background: none;
      color: inherit;
      font: inherit;
    }
    button.drum {
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }
    button.drum:focus-visible {
      outline: 2px solid var(--laundry-color);
      outline-offset: 4px;
    }
    svg {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      overflow: visible;
    }
    circle {
      fill: none;
    }
    .track {
      stroke: var(--divider-color);
      stroke-width: 10;
    }
    .progress {
      stroke: var(--laundry-color);
      stroke-width: 10;
      transition: stroke-dashoffset 1s linear;
    }
    .door {
      fill: var(--secondary-background-color);
      stroke: var(--divider-color);
      stroke-width: 1.5;
      transition: fill 0.2s ease;
    }
    button.drum:hover .door {
      fill: rgba(var(--laundry-rgb), 0.08);
    }
    .finished .door {
      fill: rgba(var(--laundry-rgb), 0.16);
      stroke: var(--laundry-color);
    }
    .finished button.drum:hover .door {
      fill: rgba(var(--laundry-rgb), 0.24);
    }
    .glass {
      stroke: var(--divider-color);
      stroke-width: 1;
    }
    .center {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 2px;
    }
    .center ha-icon {
      --mdc-icon-size: 40px;
      color: var(--laundry-color);
    }
    .time {
      font-size: 32px;
      font-weight: 500;
      font-variant-numeric: tabular-nums;
      color: var(--primary-text-color);
    }
    .caption {
      font-size: 13px;
      color: var(--secondary-text-color);
    }
    .action {
      font-size: 16px;
      font-weight: 500;
      color: var(--laundry-color);
    }
    @media (prefers-reduced-motion: reduce) {
      .progress,
      .door {
        transition: none;
      }
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    [CARD_TYPE]: OfflineLaundryCard;
  }
}

function register(): void {
  if (customElements.get(CARD_TYPE)) return;
  customElements.define("offline-laundry-new-load-dialog", NewLoadDialog);
  customElements.define(CARD_TYPE, OfflineLaundryCard);
  (window.customCards ??= []).push({
    type: CARD_TYPE,
    name: "Wäschegerät",
    description: "Waschmaschine oder Trockner mit Timer-Trommel.",
    preview: true,
    documentationURL: "https://github.com/TimoAntoniak/ha-offline-washingmachine",
    getEntitySuggestion: (hass, entityId) =>
      isLaundryEntity(hass.states[entityId])
        ? { config: { type: `custom:${CARD_TYPE}`, entity: entityId } }
        : null,
  });
}

// This module is loaded via add_extra_js_url in parallel with the frontend, which
// swaps in a scoped custom element registry when it boots. Definitions made before
// that are invisible to it, so register once the app element exists.
void customElements.whenDefined("home-assistant").then(register);

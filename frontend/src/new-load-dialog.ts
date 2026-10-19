import { LitElement, css, html, type PropertyValues } from "lit";
import type { HaFormSchema, HomeAssistant } from "./ha";
import {
  durationToSeconds,
  formatPreset,
  secondsToDuration,
  type Duration,
} from "./time";

export interface NewLoad {
  duration: number;
  load: string;
}

interface FormData {
  load: string;
  duration: Duration;
}

const SCHEMA: HaFormSchema[] = [
  { name: "load", selector: { text: {} } },
  { name: "duration", required: true, selector: { duration: { enable_second: false } } },
];

const LABELS: Record<string, string> = { load: "Name (optional)", duration: "Dauer" };

/**
 * Dialog to start a new load. Uses HA's own `ha-dialog` and `ha-form` (duration
 * selector) when available and falls back to a native `<dialog>` otherwise.
 * Fires `start-load` with the chosen duration and name, and `closed`.
 */
export class NewLoadDialog extends LitElement {
  static override properties = {
    hass: { attribute: false },
    heading: {},
    subheading: {},
    presets: { attribute: false },
    open: { type: Boolean },
    _data: { state: true },
  };

  declare hass: HomeAssistant;
  declare heading: string;
  declare subheading: string;
  declare presets: number[];
  declare open: boolean;
  declare _data: FormData;

  constructor() {
    super();
    this.presets = [];
    this.open = false;
    this._data = { load: "", duration: {} };
  }

  private get _seconds(): number {
    return durationToSeconds(this._data.duration);
  }

  protected override willUpdate(changed: PropertyValues<this>): void {
    if (changed.has("open") && this.open) {
      const first = this.presets[0];
      this._data = { load: "", duration: first ? secondsToDuration(first) : {} };
    }
  }

  protected override updated(changed: PropertyValues<this>): void {
    const native = this.renderRoot.querySelector("dialog");
    if (native && changed.has("open")) {
      if (this.open && !native.open) native.showModal();
      if (!this.open && native.open) native.close();
    }
  }

  protected override render() {
    const useHa = customElements.get("ha-dialog") && customElements.get("ha-form");
    const body = html`
      <div class="presets" role="group" aria-label="Schnellwahl Dauer">
        ${this.presets.map(
          (seconds) => html`
            <button
              type="button"
              class="chip"
              aria-pressed=${String(seconds === this._seconds)}
              @click=${() => {
                this._data = { ...this._data, duration: secondsToDuration(seconds) };
              }}
            >
              ${formatPreset(seconds)}
            </button>
          `,
        )}
      </div>
      ${useHa ? this._renderHaForm() : this._renderNativeForm()}
    `;
    const actions = html`
      <ha-button appearance="plain" @click=${this._close}>Abbrechen</ha-button>
      <ha-button ?disabled=${this._seconds <= 0} @click=${this._start}>Starten</ha-button>
    `;

    if (useHa) {
      return html`
        <ha-dialog
          .open=${this.open}
          header-title=${this.heading}
          header-subtitle=${this.subheading}
          width="small"
          @closed=${this._close}
        >
          ${body}
          <div slot="footer">${actions}</div>
        </ha-dialog>
      `;
    }
    return html`
      <dialog aria-label=${this.heading} @close=${this._close}>
        <h2>${this.heading}</h2>
        <p class="subheading">${this.subheading}</p>
        ${body}
        <div class="actions">${actions}</div>
      </dialog>
    `;
  }

  private _renderHaForm() {
    return html`
      <ha-form
        .hass=${this.hass}
        .data=${this._data}
        .schema=${SCHEMA}
        .computeLabel=${(schema: HaFormSchema) => LABELS[schema.name]}
        @value-changed=${(ev: CustomEvent<{ value: FormData }>) => {
          this._data = ev.detail.value;
        }}
      ></ha-form>
    `;
  }

  private _renderNativeForm() {
    const { hours = 0, minutes = 0 } = this._data.duration;
    const setDuration = (patch: Duration) => {
      this._data = { ...this._data, duration: { hours, minutes, ...patch } };
    };
    return html`
      <label>
        ${LABELS.load}
        <input
          .value=${this._data.load}
          @input=${(ev: InputEvent) => {
            this._data = { ...this._data, load: (ev.target as HTMLInputElement).value };
          }}
        />
      </label>
      <fieldset>
        <legend>${LABELS.duration}</legend>
        <label>
          <input
            type="number"
            min="0"
            max="24"
            .value=${String(hours)}
            @input=${(ev: InputEvent) => {
              setDuration({ hours: Number((ev.target as HTMLInputElement).value) });
            }}
          />
          h
        </label>
        <label>
          <input
            type="number"
            min="0"
            max="59"
            .value=${String(minutes)}
            @input=${(ev: InputEvent) => {
              setDuration({ minutes: Number((ev.target as HTMLInputElement).value) });
            }}
          />
          min
        </label>
      </fieldset>
    `;
  }

  private _start(): void {
    if (this._seconds <= 0) return;
    this.dispatchEvent(
      new CustomEvent<NewLoad>("start-load", {
        detail: { duration: this._seconds, load: this._data.load.trim() },
      }),
    );
    this._close();
  }

  private _close(): void {
    if (!this.open) return;
    this.open = false;
    this.dispatchEvent(new Event("closed"));
  }

  static override styles = css`
    .presets {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
    }
    .chip {
      font: inherit;
      font-size: 14px;
      padding: 6px 14px;
      border-radius: 16px;
      border: 1px solid var(--divider-color);
      background: none;
      color: var(--primary-text-color);
      cursor: pointer;
    }
    .chip[aria-pressed="true"] {
      border-color: var(--primary-color);
      background: rgba(var(--rgb-primary-color), 0.12);
      color: var(--primary-color);
    }
    .chip:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }
    div[slot="footer"],
    .actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }
    dialog {
      border: none;
      border-radius: var(--ha-dialog-border-radius, 24px);
      background: var(--card-background-color);
      color: var(--primary-text-color);
      padding: 24px;
      width: min(400px, calc(100vw - 32px));
      box-sizing: border-box;
    }
    dialog::backdrop {
      background: rgba(0, 0, 0, 0.32);
    }
    dialog h2 {
      margin: 0;
      font-size: 22px;
      font-weight: 400;
    }
    dialog .subheading {
      margin: 4px 0 16px;
      color: var(--secondary-text-color);
    }
    dialog label {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 12px;
      color: var(--secondary-text-color);
      font-size: 14px;
    }
    dialog fieldset {
      display: flex;
      gap: 12px;
      border: none;
      padding: 0;
      margin: 0 0 16px;
    }
    dialog legend {
      color: var(--secondary-text-color);
      font-size: 14px;
      margin-bottom: 4px;
    }
    dialog fieldset label {
      flex-direction: row;
      align-items: center;
    }
    dialog input {
      font: inherit;
      padding: 8px;
      border-radius: 4px;
      border: 1px solid var(--divider-color);
      background: var(--secondary-background-color);
      color: var(--primary-text-color);
    }
    dialog input[type="number"] {
      width: 64px;
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "offline-laundry-new-load-dialog": NewLoadDialog;
  }
}

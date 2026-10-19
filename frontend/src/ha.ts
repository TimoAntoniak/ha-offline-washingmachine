// Minimal slice of the Home Assistant frontend API used by the card.
import type { HassEntity } from "home-assistant-js-websocket";

export type { HassEntity };

export interface HomeAssistant {
  states: Record<string, HassEntity | undefined>;
  locale: { language: string };
  callService(
    domain: string,
    service: string,
    serviceData?: Record<string, unknown>,
    target?: { entity_id: string },
  ): Promise<unknown>;
  formatEntityState(stateObj: HassEntity): string;
}

export interface LovelaceCardConfig {
  type: string;
  [key: string]: unknown;
}

export interface LovelaceGridOptions {
  columns?: number | "full";
  rows?: number | "auto";
  min_columns?: number;
  min_rows?: number;
}

export interface HaFormSchema {
  name: string;
  required?: boolean;
  selector: Record<string, unknown>;
}

declare global {
  interface Window {
    customCards?: {
      type: string;
      name: string;
      description: string;
      preview?: boolean;
      documentationURL?: string;
      getEntitySuggestion?: (
        hass: HomeAssistant,
        entityId: string,
      ) => { config: LovelaceCardConfig } | null;
    }[];
  }
  interface HASSDomEvents {
    "hass-notification": { message: string };
    haptic:
      "success" | "warning" | "failure" | "light" | "medium" | "heavy" | "selection";
  }
}

export function fireEvent<K extends keyof HASSDomEvents>(
  node: EventTarget,
  type: K,
  detail: HASSDomEvents[K],
): void {
  node.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true }));
}

/**
 * `ha-form` is lazy-loaded by the frontend. Loading the editor of a built-in
 * card pulls it in, the same trick used by well-established custom cards.
 */
export async function ensureHaForm(): Promise<void> {
  if (customElements.get("ha-form")) return;
  const tile = customElements.get("hui-tile-card") as
    { getConfigElement?: () => Promise<unknown> } | undefined;
  await tile?.getConfigElement?.();
  await customElements.whenDefined("ha-form");
}

# Offline Laundry

Waschmaschine und Trockner für Home Assistant, auch wenn die Geräte nicht smart sind. Jedes Gerät ist im Kern ein Timer: Wäsche mit Dauer (und optional einem Namen) starten, pausieren, abbrechen. Ist sie fertig, kommt eine Push-Nachricht aufs Handy, und die Karte zeigt, dass geleert werden muss.

Die Integration bringt eine eigene Dashboard-Karte mit, die wie ein Gerät aussieht: Bedienleiste oben, darunter die Trommel mit einem Ring, der im Uhrzeigersinn abläuft.

## Installation

1. HACS öffnen › Menü › **Benutzerdefinierte Repositories** › URL dieses Repos, Typ **Integration**.
2. **Offline Laundry** installieren und Home Assistant neu starten.
3. **Einstellungen › Geräte & Dienste › Helfer › Helfer erstellen › Offline Laundry**.
   Name (z. B. „Waschmaschine“), Gerät (Waschmaschine/Trockner) und die Handys wählen, die benachrichtigt werden sollen. Für den Trockner wiederholen.

Voraussetzung: Home Assistant 2026.10 oder neuer. Für Benachrichtigungen die Companion-App auf den Handys.

## Dashboard-Karte

Die Karte wird automatisch geladen, eine Ressource muss nicht angelegt werden. Im Dashboard **Karte hinzufügen › Wäschegerät** wählen, oder per YAML:

```yaml
type: custom:offline-laundry-card
entity: sensor.waschmaschine
name: Waschmaschine        # optional
presets:                   # optional, Format H:MM
  - "0:30"
  - "1:30"
  - "2:45"
```

| Zustand | Darstellung |
|---|---|
| Bereit | Trommel ist ein **+**: neue Wäsche anlegen |
| Läuft | Restzeit in der Trommel, Ring läuft ab, Pause und Abbrechen oben |
| Pausiert | Ring grau, Fortsetzen oben |
| Fertig | Trommel in Akzentfarbe, Tippen = **Leeren** |

Abbrechen braucht ein zweites Tippen innerhalb von drei Sekunden („Sicher? Nochmal tippen“), damit nichts aus Versehen verloren geht. Die Farben kommen aus dem aktiven Theme (`--primary-color`, `--accent-color`).

## Benachrichtigungen

Ist die Wäsche fertig, bekommen die gewählten Handys eine Nachricht mit einem Knopf **Geleert**. Tippen darauf setzt das Gerät zurück. Wird das Gerät anders geleert, abgebrochen oder neu gestartet, verschwindet die Nachricht automatisch. Die Ziele lassen sich jederzeit unter **Optionen** des Helfers ändern.

## Entitäten

Pro Gerät:

| Entität | Beschreibung |
|---|---|
| `sensor.<name>` | Zustand: `idle`, `running`, `paused`, `finished`. Attribute `load`, `duration`, `finishes_at` (nur laufend), `remaining` (nur pausiert) |
| `sensor.<name>_fertig_um` | Zeitpunkt, zu dem die laufende Wäsche fertig ist |
| `event.<name>_waschgang` | Löst bei `started`, `paused`, `resumed`, `cancelled`, `finished`, `emptied` aus, z. B. für eigene Automationen |

## Aktionen

Alle Aktionen zielen auf den Zustandssensor.

| Aktion | Daten |
|---|---|
| `offline_laundry.start` | `duration` (Pflicht, z. B. `"01:30:00"`), `load` (optional) |
| `offline_laundry.pause` | – |
| `offline_laundry.resume` | – |
| `offline_laundry.cancel` | – |
| `offline_laundry.empty` | – |

```yaml
action: offline_laundry.start
target:
  entity_id: sensor.waschmaschine
data:
  duration: "01:30:00"
  load: Buntwäsche 40°
```

Läuft Home Assistant während einer Wäsche nicht, wird sie nach dem Start fortgesetzt. Ist sie in der Zwischenzeit fertig geworden, wird sie als fertig markiert und die Benachrichtigung verschickt.

## Entwicklung

```bash
uv sync --only-dev
uv run pytest
cd frontend && npm ci && npm run build
```

`npm run build` schreibt die Karte nach `custom_components/offline_laundry/frontend/`. Releases bauen sie automatisch und hängen `offline_laundry.zip` an das GitHub-Release an.

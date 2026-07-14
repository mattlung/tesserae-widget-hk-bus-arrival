# Hong Kong Bus Arrival for Tesserae

A two-plugin Tesserae bundle for tracking Kowloon Motor Bus (KMB) arrival times. It uses KMB's official public API, needs no API key, and supports Traditional Chinese, English, and Simplified Chinese.

## What it does

- Searches KMB routes by route number.
- Switches between inbound, outbound, and alternate service variants.
- Lists the stops for the selected route direction in sequence.
- Saves reusable journeys for Tesserae cells.
- Combines up to eight saved routes into one arrival board.
- Shows up to three live ETAs per route, service remarks, destination, stop, and data freshness.
- Falls back to the last cached ETA response when KMB is temporarily unavailable.
- Filters ETA records by route, direction, service type, and stop sequence. This matters at terminal stops, where KMB can return both directions in one response.

## Bundle layout

```text
hk_bus_core/       Route search, direction and stop selection, saved journeys
hk_bus_arrival/    Dashboard widget with live arrival times
```

Tesserae's `choices_from` callback receives a choice-list name, but not the values of other cell fields. A standard stop dropdown therefore cannot depend directly on a route field in the same editor. This bundle follows Tesserae's established companion-core pattern: configure and save journeys in `hk_bus_core`, then select one or more from the `hk_bus_arrival` cell multiselect.

## Install locally

Copy both plugin folders into a Tesserae checkout:

```sh
cp -R hk_bus_core hk_bus_arrival /path/to/tesserae/plugins/
```

Restart Tesserae so the plugin loader discovers both folders.

## Configure

1. Open **Settings -> Plugins -> Hong Kong Bus, Setup**.
2. Open its admin page.
3. Search for a route number, such as `1A`.
4. Choose a direction or service variant.
5. Choose a stop and save the journey.
6. Repeat for each route and stop you want to track.
7. Add **Hong Kong Bus, Arrival** to a cell and choose the saved journeys.

A cell supports up to eight routes and can also select its language, show one to three ETAs per route, and hide service remarks. Each route row shows its saved stop and destination together, so selected journeys may use different KMB stops. Existing cells configured with one saved journey continue to work.

## Data source

The bundle declares one network capability:

```text
network:data.etabus.gov.hk
```

It uses the documented KMB endpoints below:

- `GET /v1/transport/kmb/route/`
- `GET /v1/transport/kmb/stop`
- `GET /v1/transport/kmb/route-stop/{route}/{direction}/{service_type}`
- `GET /v1/transport/kmb/eta/{stop_id}/{route}/{service_type}`

Reference: KMB Real-time Arrival Information API Specification v1.05, dated 23 October 2024.

## Development

Create the local environment and run the focused tests:

```sh
python3 -m venv .venv
.venv/bin/pip install Flask pytest ruff jsonschema
.venv/bin/python -m pytest -q
.venv/bin/ruff check hk_bus_core hk_bus_arrival tests
```

The static preview uses representative multi-route data and the same four dimensions as Tesserae:

```sh
python3 -m http.server 4173
```

Open `http://127.0.0.1:4173/preview/?size=md`. Replace `md` with `xs`, `sm`, or `lg`; add `&language=en` or `&language=sc` to inspect other languages.

For host-level rendering, copy the two plugin folders into a Tesserae checkout and use:

```text
http://127.0.0.1:8765/_test/render?plugin=hk_bus_arrival&size=md
```

## Do I need to fork the official repositories?

No fork is required to build or use this widget. Keeping it in its own repository is the correct community-widget structure.

- Do **not** fork `dmellok/tesserae-widget-finance`; it is a reference implementation, not a starter dependency.
- Do **not** develop inside `dmellok/tesserae-widgets`; that repository is the marketplace index, not the widget runtime.
- Fork `dmellok/tesserae-widgets` only when you are ready to submit a marketplace PR, because you will need to add the catalog entry and screenshots there.
- Fork `dmellok/tesserae` only if you want to propose this as a built-in widget that ships with every Tesserae installation.

## Publish to the community catalog

1. Push this repository and tag a release, for example `v0.1.0`.
2. Calculate the release tarball SHA-256.
3. Capture at least `screenshots/hk_bus/lg.png` for the catalog PR.
4. Fork `dmellok/tesserae-widgets`.
5. Add the entry based on [`catalog-entry.example.json`](catalog-entry.example.json), replace the SHA placeholder, add the screenshot, and open a PR.

The catalog entry must keep `official` set to `false`; that flag is reserved for repositories owned by the catalog maintainer.

## License

MIT. See [LICENSE](LICENSE).

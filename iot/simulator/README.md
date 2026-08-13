# FloodGuard sensor simulator

This development-only tool produces JSON accepted by the MQTT ingestion bridge.
Every reading has `source: "simulator"`. It never registers a station and it
previews data by default, so running it without `--publish` cannot change the
database.

Use Python 3.11 or newer. From the repository root:

```powershell
python -m pip install -r .\iot\simulator\requirements.txt
python .\iot\simulator\simulate_sensor.py --station-id MAUBIN-01 --count 3
```

To publish, the station must already exist in the backend. Put the local broker
credential in process-scoped environment variables, then add the explicit
`--publish` flag:

```powershell
$env:FLOODGUARD_MQTT_USERNAME = "floodguard-backend"
$env:FLOODGUARD_MQTT_PASSWORD = "your-local-broker-password"
python .\iot\simulator\simulate_sensor.py `
  --station-id MAUBIN-01 `
  --water-level-cm 145 `
  --rainfall-mm 3.2 `
  --trend-cm 1.5 `
  --count 20 `
  --interval 5 `
  --publish
```

Defaults target `127.0.0.1:1884`. Override them with
`FLOODGUARD_MQTT_HOST`, `FLOODGUARD_MQTT_PORT`, or
`FLOODGUARD_MQTT_TOPIC`. Use `--tls` for a TLS-enabled field broker.

Do not treat simulator readings as observed evidence, training labels, or a
flood prediction. Remove test records after a demo, and keep production device
credentials separate from the local shared development credential.

# Production-Readiness Visual Verification

## 2026-08-16 Observability Release

The desktop dashboard was visually checked at a 1280 × 720 viewport after the data-freshness release. The **ERA5 archive refresh** card is visible in the rainfall panel above the hindcast panel, and its initial-state disclosure reads **“Awaiting first refresh”** rather than implying data availability. The status bar continues to show **“Monitoring”** for data refresh and retains the separate **“Monitoring only”** alert mode.

The verification confirms that the new operational status does not visually obscure the existing historical-hindcast disclaimer. It does not validate field data, model accuracy, or public-alert readiness.

The phone dashboard was also checked at a 375 × 812 viewport. The first review identified that the hindcast panel covered the ERA5 freshness card. The layout was adjusted and rechecked: the card is now visible between the rainfall sparkline and hindcast panel, retains its initial **“Awaiting first refresh”** state, and the five-item status grid remains legible without obscuring the **Monitoring only** alert label.

After the controlled ERA5 backfill, the desktop view correctly showed a **Current** source state and the populated sparkline. The visual check also exposed that the source-date label selected the earliest row when same-run updates shared a timestamp. The operational query was queued for correction to order by observed date rather than write time.

The corrected query subsequently displayed the latest completed ERA5 date. A further desktop review of the explicit prospective-input health row identified that the hindcast panel’s sticky historical disclaimer covered the row at this viewport. The layout requires a final adjustment so prospective freshness and six-hour job state remain visibly inspectable.

The final desktop verification moved the explicit prospective state into the always-visible status grid. The grid now shows **“Prospective job — Current · Healthy”** alongside the separate aggregate data-refresh state and **Monitoring only** alert mode. The safety disclaimer remains visible in the hindcast panel, and the prospective status is no longer hidden by that panel’s scroll treatment.

The final 375 × 812 phone verification shows the six-item status grid in three readable rows. **Prospective job — Current · Healthy** remains separate from the **Open alerts: 0** and **Alert mode: Monitoring only** rows, while the ERA5 history freshness card and hindcast safety limitation remain visible above it.

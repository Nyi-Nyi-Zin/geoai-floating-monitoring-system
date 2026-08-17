# Nationwide Coverage Visual Verification

**Development branch:** `feat/myanmar`  
**Verification date:** 2026-08-17

The map’s **Myanmar coverage** control was exercised in the development dashboard. Selecting it switched the viewport from Maubin to a country view, rendered all **18 Admin 1** regional boundaries, and displayed source provenance with the retained boundary validity date. The panel explicitly stated that source geometry is available while flood prediction, probability, and regional accuracy are not assessed.

The coverage endpoint was changed from the 4,926,527-byte full source geometry to a 662,877-byte simplified display geometry while retaining 18 region features. The boundary outlines remained legible at country view. Maubin terrain screening, historical hindcasts, and the site-wide **Monitoring only** safety disclosure remained separate from the nationwide coverage index.

After route code-splitting, the dashboard first displayed an accessible `Loading DeltaWatch monitoring workspace…` fallback and then returned to the normal Maubin dashboard. The nationwide evidence-readiness disclosure was added only to Myanmar coverage mode and is designed to state historical source coverage and **not a forecast**; it does not alter Maubin’s experimental hindcast panel or monitoring-only alert boundary.

Initial activation of Myanmar coverage mode displayed the source geometry and the historical-evidence panel with its `not a forecast` disclaimer, but the evidence value remained in the loading state. The endpoint and loader lifecycle require verification before this UI element can be treated as complete.

After restarting the spatial-service lifecycle, the evidence endpoint returned successfully and the panel displayed **16 regions with historical coverage only**. It retained the complete statement that the result is a historical source-coverage descriptor and is **not a forecast, risk score, probability, likelihood, or alert**. The country map outlines, Maubin panel, and site-wide monitoring-only controls remained visually distinct.

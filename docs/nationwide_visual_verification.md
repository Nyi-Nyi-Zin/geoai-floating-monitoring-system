# Nationwide Coverage Visual Verification

**Development branch:** `feat/myanmar`  
**Verification date:** 2026-08-17

The map’s **Myanmar coverage** control was exercised in the development dashboard. Selecting it switched the viewport from Maubin to a country view, rendered all **18 Admin 1** regional boundaries, and displayed source provenance with the retained boundary validity date. The panel explicitly stated that source geometry is available while flood prediction, probability, and regional accuracy are not assessed.

The coverage endpoint was changed from the 4,926,527-byte full source geometry to a 662,877-byte simplified display geometry while retaining 18 region features. The boundary outlines remained legible at country view. Maubin terrain screening, historical hindcasts, and the site-wide **Monitoring only** safety disclosure remained separate from the nationwide coverage index.

"use client";

import { useTranslation } from "@/lib/i18n";
import styles from "./dashboard.module.css";

export function MapLoading2D() {
  const { t } = useTranslation();
  return (
    <div className={styles.emptyMap}>
      <div className={styles.emptyOrb} />
      <p>{t("map.loadingMap")}</p>
      <span>{t("map.loadingMapHint")}</span>
    </div>
  );
}

export function MapLoading3D() {
  const { t } = useTranslation();
  return (
    <div className={styles.emptyMap}>
      <div className={styles.emptyOrb} />
      <p>{t("map.loading3d")}</p>
      <span>{t("map.loading3dHint")}</span>
    </div>
  );
}

export function MapLoadingCesium() {
  const { t } = useTranslation();
  return (
    <div className={styles.emptyMap}>
      <div className={styles.emptyOrb} />
      <p>{t("map.loadingCesium")}</p>
      <span>{t("map.loadingCesiumHint")}</span>
    </div>
  );
}

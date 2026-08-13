"use client";

import { useTranslation } from "@/lib/i18n";
import styles from "./dashboard.module.css";

export default function LanguageSwitcher() {
  const { locale, setLocale, t } = useTranslation();

  return (
    <div className={styles.languageSwitcher} aria-label={t("common.language")}>
      <button
        type="button"
        className={locale === "en" ? styles.activeLocale : ""}
        onClick={() => setLocale("en")}
        aria-pressed={locale === "en"}
      >
        EN
      </button>
      <button
        type="button"
        className={locale === "mm" ? styles.activeLocale : ""}
        onClick={() => setLocale("mm")}
        aria-pressed={locale === "mm"}
      >
        MM
      </button>
    </div>
  );
}

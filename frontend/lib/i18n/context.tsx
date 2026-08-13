"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { en } from "./locales/en";
import { mm } from "./locales/mm";
import type { Locale } from "./types";

const STORAGE_KEY = "deltawatch-locale";

const dictionaries = { en, mm } as const;

type Vars = Record<string, string | number>;

function getNestedValue(source: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((current, key) => {
    if (current && typeof current === "object" && key in current) {
      return (current as Record<string, unknown>)[key];
    }
    return undefined;
  }, source);
}

function interpolate(template: string, vars?: Vars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) =>
    key in vars ? String(vars[key]) : `{${key}}`,
  );
}

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, vars?: Vars) => string;
  formatNumber: (value: number, digits?: number) => string;
  formatDate: (value: string) => string;
  formatDateTime: (value: string) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function localeTag(locale: Locale): string {
  return locale === "mm" ? "my-MM" : "en-US";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "mm") {
      setLocaleState(stored);
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale === "mm" ? "my" : "en";
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const t = useCallback(
    (key: string, vars?: Vars) => {
      const value =
        getNestedValue(dictionaries[locale] as Record<string, unknown>, key) ??
        getNestedValue(dictionaries.en as Record<string, unknown>, key);
      if (typeof value !== "string") return key;
      return interpolate(value, vars);
    },
    [locale],
  );

  const formatNumber = useCallback(
    (value: number, digits = 0) =>
      new Intl.NumberFormat(localeTag(locale), {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      }).format(value),
    [locale],
  );

  const formatDate = useCallback(
    (value: string) =>
      new Intl.DateTimeFormat(localeTag(locale), {
        day: "2-digit",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      }).format(new Date(`${value}T00:00:00Z`)),
    [locale],
  );

  const formatDateTime = useCallback(
    (value: string) =>
      new Intl.DateTimeFormat(localeTag(locale), {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "Asia/Yangon",
      }).format(new Date(value)),
    [locale],
  );

  const value = useMemo(
    () => ({ locale, setLocale, t, formatNumber, formatDate, formatDateTime }),
    [locale, setLocale, t, formatNumber, formatDate, formatDateTime],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useTranslation() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useTranslation must be used within I18nProvider");
  }
  return context;
}

export function useOptionalTranslation() {
  return useContext(I18nContext);
}

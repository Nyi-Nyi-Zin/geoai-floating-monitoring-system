export type Locale = "en" | "mm";

export type TranslationDictionary = typeof import("./locales/en").en;

export type TranslationKey = string;

import type { RainfallForecast, RainfallHistory } from "./api";

export const WEATHER_API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

export type WeatherPageData = {
  forecast: RainfallForecast | null;
  history: RainfallHistory | null;
  apiBaseUrl: string;
  error: string | null;
};

async function parseJson<T>(response: Response): Promise<T | null> {
  if (!response.ok) return null;
  return (await response.json()) as T;
}

export async function fetchRainfallForecast(
  forecastDays = 7,
  apiBase = WEATHER_API_BASE,
): Promise<RainfallForecast | null> {
  const response = await fetch(
    `${apiBase}/weather/rainfall-forecast?forecast_days=${forecastDays}`,
    { cache: "no-store", signal: AbortSignal.timeout(20_000) },
  );
  return parseJson<RainfallForecast>(response);
}

export async function fetchRainfallHistory(
  options: {
    limit?: number;
    startDate?: string;
    endDate?: string;
    apiBase?: string;
  } = {},
): Promise<RainfallHistory | null> {
  const {
    limit = 366,
    startDate,
    endDate,
    apiBase = WEATHER_API_BASE,
  } = options;
  const params = new URLSearchParams({ limit: String(limit) });
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const response = await fetch(
    `${apiBase}/weather/rainfall-history?${params}`,
    { cache: "no-store", signal: AbortSignal.timeout(20_000) },
  );
  return parseJson<RainfallHistory>(response);
}

export async function fetchWeatherPageData(
  apiBase = WEATHER_API_BASE,
): Promise<WeatherPageData> {
  try {
    const [forecast, history] = await Promise.all([
      fetchRainfallForecast(7, apiBase),
      fetchRainfallHistory({ limit: 366, apiBase }),
    ]);
    if (!forecast && !history) {
      return {
        forecast: null,
        history: null,
        apiBaseUrl: apiBase,
        error: "Weather APIs could not be reached. Start the backend on port 8000.",
      };
    }
    return { forecast, history, apiBaseUrl: apiBase, error: null };
  } catch (error) {
    return {
      forecast: null,
      history: null,
      apiBaseUrl: apiBase,
      error:
        error instanceof Error
          ? error.message
          : "The weather API could not be reached.",
    };
  }
}

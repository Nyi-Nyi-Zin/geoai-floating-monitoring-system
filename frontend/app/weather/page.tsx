import type { Metadata } from "next";
import { connection } from "next/server";
import WeatherForecastPage from "../components/weather-forecast-page";
import { getWeatherPageData } from "@/lib/api";

export const metadata: Metadata = {
  title: "DeltaWatch | Weather Forecast",
  description:
    "Open-Meteo rainfall forecast and ERA5 historical rainfall for Maubin Township.",
};

export default async function Page() {
  await connection();
  const data = await getWeatherPageData();
  return <WeatherForecastPage initialData={data} />;
}

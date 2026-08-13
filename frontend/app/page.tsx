import { connection } from "next/server";
import FloodMonitoringView from "./components/flood-monitoring-view";
import { getDashboardData } from "@/lib/api";

export default async function Home() {
  await connection();
  const data = await getDashboardData();

  return <FloodMonitoringView {...data} />;
}

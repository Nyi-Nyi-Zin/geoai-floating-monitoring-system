import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { lazy, Suspense } from "react";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";

const Home = lazy(() => import("./pages/Home"));

export default function App() {
  return <ErrorBoundary><ThemeProvider defaultTheme="dark"><TooltipProvider><Suspense fallback={<main className="app-route-loading" aria-live="polite">Loading DeltaWatch monitoring workspace…</main>}><Home /></Suspense><Toaster /></TooltipProvider></ThemeProvider></ErrorBoundary>;
}

export default function WeatherLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <div className="features-scroll-root">{children}</div>;
}

export default function FeaturesLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <div className="features-scroll-root">{children}</div>;
}

import { Card, Metric, Text } from "@tremor/react";

export function KpiCard({
  label,
  value,
  accentColor,
}: {
  label: string;
  value: string;
  /** Nombre de color Tremor, ej. "teal" o "orange" (ver theme/colors.ts). */
  accentColor: string;
}) {
  return (
    <Card
      className="bg-surface ring-1 ring-line"
      decoration="top"
      decorationColor={accentColor}
    >
      <Text className="text-ink-muted">{label}</Text>
      <Metric className="text-ink">{value}</Metric>
    </Card>
  );
}

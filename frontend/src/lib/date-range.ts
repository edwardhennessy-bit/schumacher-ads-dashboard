import { subDays, subYears, startOfMonth, format } from "date-fns";

export interface DateRange {
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
}

export interface DatePreset {
  label: string;
  value: string;
  getRange: () => DateRange;
}

function today(): string {
  return format(new Date(), "yyyy-MM-dd");
}

function yesterday(): string {
  return format(subDays(new Date(), 1), "yyyy-MM-dd");
}

export const DATE_PRESETS: DatePreset[] = [
  {
    label: "MTD",
    value: "mtd",
    getRange: () => ({
      startDate: format(startOfMonth(new Date()), "yyyy-MM-dd"),
      endDate: yesterday(),
    }),
  },
  {
    label: "Last 7 Days",
    value: "last_7d",
    getRange: () => ({
      startDate: format(subDays(new Date(), 7), "yyyy-MM-dd"),
      endDate: today(),
    }),
  },
  {
    label: "Last 14 Days",
    value: "last_14d",
    getRange: () => ({
      startDate: format(subDays(new Date(), 14), "yyyy-MM-dd"),
      endDate: today(),
    }),
  },
  {
    label: "Last 30 Days",
    value: "last_30d",
    getRange: () => ({
      startDate: format(subDays(new Date(), 30), "yyyy-MM-dd"),
      endDate: today(),
    }),
  },
  {
    label: "Last 60 Days",
    value: "last_60d",
    getRange: () => ({
      startDate: format(subDays(new Date(), 60), "yyyy-MM-dd"),
      endDate: today(),
    }),
  },
  {
    label: "Last 90 Days",
    value: "last_90d",
    getRange: () => ({
      startDate: format(subDays(new Date(), 90), "yyyy-MM-dd"),
      endDate: today(),
    }),
  },
  {
    label: "Last Year",
    value: "last_year",
    getRange: () => ({
      startDate: format(subYears(new Date(), 1), "yyyy-MM-dd"),
      endDate: today(),
    }),
  },
];

export const DEFAULT_PRESET = "last_30d";

export function getPresetByValue(value: string): DatePreset | undefined {
  return DATE_PRESETS.find((p) => p.value === value);
}

export function formatDateRangeLabel(
  preset: string,
  customRange: DateRange | null
): string {
  if (customRange) {
    const start = new Date(customRange.startDate + "T00:00:00");
    const end = new Date(customRange.endDate + "T00:00:00");
    const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
    return `${start.toLocaleDateString("en-US", opts)} - ${end.toLocaleDateString("en-US", opts)}`;
  }
  const p = getPresetByValue(preset);
  return p?.label ?? "Last 30 Days";
}

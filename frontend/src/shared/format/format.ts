const LOCALE = "pt-BR";

const currencyFormatter = new Intl.NumberFormat(LOCALE, { style: "currency", currency: "BRL" });
const percentFormatter = new Intl.NumberFormat(LOCALE, {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 2,
});
const dateTimeFormatter = new Intl.DateTimeFormat(LOCALE, {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});
const MILLISECONDS_PER_DAY = 86_400_000;

export function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  return currencyFormatter.format(Number(value));
}

export function formatChange(ratio: string | number | null | undefined): string {
  if (ratio === null || ratio === undefined || ratio === "") {
    return "—";
  }
  const value = Number(ratio);
  const formatted = percentFormatter.format(value);
  return value > 0 ? `+${formatted}` : formatted;
}

export function formatIsoDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const [year, month, day] = value.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}

export function formatDateTime(value: string | null | undefined): string {
  return value ? dateTimeFormatter.format(new Date(value)) : "—";
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  return `${(bytes / 1024).toLocaleString(LOCALE, { maximumFractionDigits: 1 })} KB`;
}

export function todayIsoDate(now: Date = new Date()): string {
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

export function daysBetween(fromIsoDate: string, toIsoDate: string): number {
  const from = Date.UTC(...splitIsoDate(fromIsoDate));
  const to = Date.UTC(...splitIsoDate(toIsoDate));
  return Math.round((to - from) / MILLISECONDS_PER_DAY);
}

export function parseAges(text: string): number[] | null {
  const parts = text
    .split(/[,;\s]+/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length === 0) {
    return null;
  }
  const ages = parts.map(Number);
  const valid = ages.every((age) => Number.isInteger(age) && age >= 0 && age <= 120);
  return valid ? ages : null;
}

export function parseBrazilianMoney(text: string): string | null {
  const normalized = text.replace(/R\$|\s/g, "");
  if (!/^\d{1,3}(\.\d{3})*(,\d{1,2})?$|^\d+(,\d{1,2})?$/.test(normalized)) {
    return null;
  }
  const canonical = normalized.replace(/\./g, "").replace(",", ".");
  return Number(canonical).toFixed(2);
}

function splitIsoDate(value: string): [number, number, number] {
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  return [year, month - 1, day];
}

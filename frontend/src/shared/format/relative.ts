import { t } from "../i18n/translate";
import { daysBetween, todayIsoDate } from "./format";

export function describeDaysAgo(days: number | null | undefined): string {
  if (days === null || days === undefined) {
    return t("common.none");
  }
  return days <= 0 ? t("common.today") : t("common.daysAgo", { count: days });
}

export function describeDaysUntil(isoDate: string | null | undefined): string {
  if (!isoDate) {
    return t("common.none");
  }
  const days = daysBetween(todayIsoDate(), isoDate);
  if (days === 0) {
    return t("common.today");
  }
  return days > 0 ? t("common.inDays", { count: days }) : t("common.daysAgo", { count: -days });
}

export function describeActor(name: string | null | undefined): string {
  return name ? t("common.by", { name }) : t("common.automatic");
}

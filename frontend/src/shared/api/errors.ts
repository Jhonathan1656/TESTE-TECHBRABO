import { t } from "../i18n/translate";
import { ApiError } from "./http";

export function describeError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return t("common.errorGeneric");
  }
  if (error.body.detail) {
    return error.body.detail;
  }
  const fieldMessage = Object.values(error.body).find(
    (value): value is string[] => Array.isArray(value) && typeof value[0] === "string",
  );
  return fieldMessage?.[0] ?? t("common.errorGeneric");
}

export function readErrorParam(error: unknown, name: string): string | null {
  if (!(error instanceof ApiError)) {
    return null;
  }
  const value = error.body.params?.[name];
  return typeof value === "string" ? value : null;
}

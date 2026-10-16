import { createElement, Fragment, type ReactNode } from "react";

import { messages } from "./messages.pt-BR";

type Params = Record<string, string | number>;

export function t(key: string, params?: Params): string {
  const value = lookup(key);
  if (typeof value !== "string") {
    return key;
  }
  return interpolate(value, params);
}

/**
 * Interpolates React nodes (links, code, emphasis) into a message, so translated
 * sentences keep their word order instead of being split across several keys.
 */
export function tRich(key: string, params: Record<string, ReactNode>): ReactNode[] {
  return t(key)
    .split(/(\{\w+\})/)
    .filter((part) => part !== "")
    .map((part, index) => {
      const name = /^\{(\w+)\}$/.exec(part)?.[1];
      const node = name !== undefined && name in params ? params[name] : part;
      return createElement(Fragment, { key: index }, node);
    });
}

export function tList(key: string): string[] {
  const value = lookup(key);
  return Array.isArray(value) ? (value as string[]) : [];
}

export function tEnum(group: string, value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return messages.common.none;
  }
  // Enum values may contain dots (audit actions such as "batch.published"), so index directly.
  const labels = lookup(`enums.${group}`) as Record<string, unknown> | undefined;
  const label = labels?.[String(value)];
  return typeof label === "string" ? label : String(value);
}

function lookup(key: string): unknown {
  return key
    .split(".")
    .reduce<unknown>(
      (node, part) =>
        node && typeof node === "object" ? (node as Record<string, unknown>)[part] : undefined,
      messages,
    );
}

function interpolate(template: string, params?: Params): string {
  if (!params) {
    return template;
  }
  return template.replace(/\{(\w+)\}/g, (placeholder, name: string) =>
    name in params ? String(params[name]) : placeholder,
  );
}

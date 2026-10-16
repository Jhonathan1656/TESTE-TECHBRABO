import { createContext, use } from "react";

import type { CurrentUser, Role } from "../api/types";

export type AuthStatus = "checking" | "signed_in" | "signed_out";

export interface AuthContextValue {
  status: AuthStatus;
  user: CurrentUser | null;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  hasRole: (role: Role) => boolean;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = use(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}

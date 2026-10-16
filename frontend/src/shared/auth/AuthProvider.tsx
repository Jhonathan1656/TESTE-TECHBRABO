import { useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { authApi } from "../api/endpoints";
import { configureHttp } from "../api/http";
import type { CurrentUser, Role } from "../api/types";
import { AuthContext, type AuthContextValue, type AuthStatus } from "./AuthContext";
import { readStoredToken, storeToken } from "./tokenStorage";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [initialToken] = useState(readStoredToken);
  const tokenRef = useRef<string | null>(initialToken);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>(initialToken ? "checking" : "signed_out");

  const clearSession = useCallback(() => {
    tokenRef.current = null;
    storeToken(null);
    setUser(null);
    setStatus("signed_out");
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    configureHttp({ readToken: () => tokenRef.current, onUnauthorized: clearSession });
  }, [clearSession]);

  useEffect(() => {
    if (!tokenRef.current) {
      return;
    }
    authApi
      .me()
      .then((current) => {
        setUser(current);
        setStatus("signed_in");
      })
      .catch(clearSession);
  }, [clearSession]);

  const signIn = useCallback(async (username: string, password: string) => {
    const session = await authApi.login(username, password);
    tokenRef.current = session.token;
    storeToken(session.token);
    setUser(session.user);
    setStatus("signed_in");
  }, []);

  const signOut = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      signIn,
      signOut,
      hasRole: (role: Role) => Boolean(user?.roles.includes(role)),
    }),
    [status, user, signIn, signOut],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

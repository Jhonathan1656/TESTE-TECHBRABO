import { CheckCheck, CircleAlert, Eye, EyeOff, KeyRound } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { describeError } from "../../shared/api/errors";
import { useAuth } from "../../shared/auth/AuthContext";
import { Button } from "../../shared/components/Button";
import { messages } from "../../shared/i18n/messages.pt-BR";
import { t, tRich } from "../../shared/i18n/translate";

export function LoginPage() {
  const { status, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("analista");
  const [password, setPassword] = useState("");
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (status === "signed_in") {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(username, password);
      const target = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(target, { replace: true });
    } catch (caught) {
      setError(describeError(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <title>{t("app.documentTitle", { page: t("auth.title") })}</title>
      <aside className="login-aside">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <CheckCheck size={18} />
          </span>
          <span>
            <span className="brand-name">{t("app.name")}</span>
            <span className="brand-product">{t("app.product")}</span>
          </span>
        </div>
        <div>
          <p className="login-tagline">{t("auth.asideTitle")}</p>
          <ol className="login-steps">
            {messages.auth.asideSteps.map((step) => (
              <li key={step.title}>
                <span>
                  <span className="login-step-title">{step.title}.</span> {step.text}
                </span>
              </li>
            ))}
          </ol>
        </div>
        <p className="small">{t("auth.asideFooter")}</p>
      </aside>
      <main className="login-main">
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="stack-sm">
            <h1 className="page-title">{t("auth.title")}</h1>
            <p className="muted">{t("auth.subtitle")}</p>
          </div>
          <div className="field">
            <label className="label" htmlFor="login-username">
              {t("auth.username")}
            </label>
            <input
              id="login-username"
              className="input"
              name="username"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              aria-invalid={error ? true : undefined}
              required
            />
          </div>
          <div className="field">
            <label className="label" htmlFor="login-password">
              {t("auth.password")}
            </label>
            <div className="input-with-action">
              <input
                id="login-password"
                className="input"
                name="password"
                type={passwordVisible ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? "login-error" : undefined}
                required
              />
              <Button
                variant="ghost"
                size="sm"
                icon={passwordVisible ? <EyeOff size={16} /> : <Eye size={16} />}
                aria-label={passwordVisible ? t("auth.hidePassword") : t("auth.showPassword")}
                aria-pressed={passwordVisible}
                onClick={() => setPasswordVisible((visible) => !visible)}
              />
            </div>
          </div>
          {error && (
            <div id="login-error" className="form-error" role="alert">
              <CircleAlert size={16} aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? t("auth.submitting") : t("auth.submit")}
          </Button>
          <div className="login-hint">
            <KeyRound size={16} aria-hidden="true" />
            <p>
              <strong>{t("auth.demoHintTitle")}.</strong>{" "}
              {tRich("auth.demoHint", {
                analyst: <code translate="no">analista</code>,
                reviewer: <code translate="no">revisor</code>,
                variable: <code translate="no">DEMO_PASSWORD</code>,
                password: <code translate="no">cotador-demo</code>,
              })}
            </p>
          </div>
        </form>
      </main>
    </div>
  );
}

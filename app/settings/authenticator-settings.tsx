"use client";

import { useEffect, useState } from "react";
import { api, clearSession } from "../../lib/api";

type SecurityStatus = {
  available: boolean;
  required?: boolean;
  enabled: boolean;
  recovery_codes_remaining: number;
};

type Enrollment = {
  secret: string;
  qr_code: string;
  expires_in: number;
};

type SecurityResult = {
  message: string;
  recovery_codes?: string[];
  sign_in_required?: boolean;
};

export function AuthenticatorSettings() {
  const [status, setStatus] = useState<SecurityStatus | null>(null);
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null);
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState(false);
  const [signInRequired, setSignInRequired] = useState(false);

  useEffect(() => {
    api<SecurityStatus>("/v1/auth/totp/status")
      .then(setStatus)
      .catch(() => {
        setError(true);
        setNotice("Security settings are temporarily unavailable.");
      });
  }, []);

  async function perform(action: string) {
    if (busy) return;

    setBusy(true);
    setNotice("");
    setError(false);

    try {
      if (action === "setup") {
        const result = await api<Enrollment>(
          "/v1/auth/totp/setup",
          {
            method: "POST",
            body: JSON.stringify({ password })
          }
        );

        setEnrollment(result);
        setPassword("");
        setCode("");
        return;
      }

      const result = await api<SecurityResult>(
        "/v1/auth/totp/" + action,
        {
          method: "POST",
          body: JSON.stringify({ password, code })
        }
      );

      setPassword("");
      setCode("");
      setEnrollment(null);
      setRecoveryCodes(result.recovery_codes ?? []);
      setNotice(result.message);
      setSignInRequired(!!result.sign_in_required);

      // The server has revoked the session.
      // Allow the user to save recovery codes before redirecting.
    } catch (caught) {
      setError(true);
      setNotice(
        caught instanceof Error
          ? caught.message
          : "Security update failed."
      );
    } finally {
      setBusy(false);
    }
  }

  function finish() {
    setRecoveryCodes([]);
    setEnrollment(null);
    clearSession();
    window.location.assign("/auth/sign-in");
  }

  function downloadRecoveryCodes() {
    const content = [
      "handEwork emergency recovery codes",
      "Keep these codes private and stored securely.",
      "Each code can be used only once.",
      "",
      ...recoveryCodes
    ].join("\n");

    const url = URL.createObjectURL(
      new Blob([content], { type: "text/plain" })
    );

    const link = document.createElement("a");
    link.href = url;
    link.download = "handework-recovery-codes.txt";
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <section className="app-card settings-form">
      <h2>Account security</h2>

      <div className="phone-verification">
        <div className="phone-verification-heading">
          <strong>Two-factor authentication</strong>
          {status?.required && (
            <p role="status">
              Two-factor authentication is mandatory for administrator accounts.
            </p>
          )}

          {status && !signInRequired && (
            <span className={
              status.enabled
                ? "phone-status phone-status-verified"
                : "phone-status"
            }>
              {status.enabled ? "Enabled" : "Not enabled"}
            </span>
          )}
        </div>

        {signInRequired ? (
          <>
            {recoveryCodes.length > 0 && (
              <>
                <h3>Save your recovery codes</h3>
                <p>
                  Store these codes securely before continuing.
                  They will not be displayed again.
                </p>

                <div className="recovery-code-grid">
                  {recoveryCodes.map((value) => (
                    <code key={value}>{value}</code>
                  ))}
                </div>

                <button
                  type="button"
                  className="button"
                  onClick={downloadRecoveryCodes}
                >
                  Download recovery codes
                </button>
              </>
            )}

            <p>For your security, please sign in again.</p>

            <button
              type="button"
              className="button button-orange"
              onClick={finish}
            >
              Continue to sign in
            </button>
          </>
        ) : status ? (
          <>
            {!status.enabled && !status.available ? (
              <p>Authenticator enrollment is not currently available.</p>
            ) : enrollment ? (
              <>
                <p>
                  Scan this QR code using Google Authenticator
                  or another compatible authenticator app.
                </p>

                <img
                  src={enrollment.qr_code}
                  alt="Private authenticator enrollment QR code"
                  className="authenticator-qr"
                />

                <label>Manual setup key
                  <input
                    value={enrollment.secret}
                    readOnly
                    autoComplete="off"
                    style={{ fontSize: 14, letterSpacing: 1, width: "100%" }}
                  />
                </label>

                <label>Six-digit authenticator code
                  <input
                    value={code}
                    inputMode="numeric"
                    maxLength={6}
                    autoComplete="one-time-code"
                    onChange={(event) =>
                      setCode(event.target.value.replace(/\D/g, "").slice(0, 6))
                    }
                  />
                </label>

                <p>Complete setup within ten minutes.</p>

                <button
                  type="button"
                  className="button button-orange"
                  disabled={busy || code.length !== 6}
                  onClick={() => perform("enable")}
                >
                  Enable authenticator
                </button>

                <button
                  type="button"
                  className="button"
                  disabled={busy}
                  onClick={() => {
                    setEnrollment(null);
                    setCode("");
                  }}
                >
                  Cancel setup
                </button>
              </>
            ) : (
              <>
                <p>
                  {status.enabled
                    ? "Your account is protected by an authenticator."
                    : "Add another layer of protection to your account."}
                </p>

                {status.enabled && (
                  <p>
                    Recovery codes remaining:{" "}
                    {status.recovery_codes_remaining}
                  </p>
                )}

                <label>Current password
                  <input
                    type="password"
                    value={password}
                    autoComplete="current-password"
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </label>

                {status.enabled ? (
                  <>
                    <label>Authenticator or recovery code
                      <input
                        value={code}
                        maxLength={24}
                        autoComplete="one-time-code"
                        onChange={(event) => setCode(event.target.value)}
                        style={{ fontSize: 14, letterSpacing: 1, width: "100%" }}
                      />
                    </label>

                    <button
                      type="button"
                      className="button"
                      disabled={busy || !password || !code}
                      onClick={() => {
                        if (window.confirm(
                          "Replace all your existing recovery codes?"
                        )) {
                          void perform("recovery/regenerate");
                        }
                      }}
                    >
                      Generate new recovery codes
                    </button>

                    <button
                      type="button"
                      className="button"
                      disabled={busy || !password || !code || !!status.required}
                      onClick={() => {
                        if (window.confirm(
                          "Disable two-factor authentication?"
                        )) {
                          void perform("disable");
                        }
                      }}
                    >
                      Disable authenticator
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    className="button button-orange"
                    disabled={busy || !password}
                    onClick={() => perform("setup")}
                  >
                    Set up Google Authenticator
                  </button>
                )}
              </>
            )}
          </>
        ) : (
          <p>{error ? "Security settings unavailable." : "Loading security settings..."}</p>
        )}

        {busy && <p role="status">Processing secure request...</p>}

        {notice && (
          <p
            role={error ? "alert" : "status"}
            className={error ? "form-error" : "phone-verification-notice"}
          >
            {notice}
          </p>
        )}
      </div>
    </section>
  );
}

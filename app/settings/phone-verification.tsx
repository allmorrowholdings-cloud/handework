"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

type VerificationUser = {
  phone: string;
  phone_verified?: boolean;
};

type Props = {
  phone: string;
  verified: boolean;
  unsaved: boolean;
  disabled: boolean;
  onVerified: () => Promise<void>;
};

export function PhoneVerification({
  phone,
  verified,
  unsaved,
  disabled,
  onVerified
}: Props) {
  const [code, setCode] = useState("");
  const [requested, setRequested] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState(false);
  const [resendAt, setResendAt] = useState(0);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setCode("");
      setRequested(false);
      setNotice("");
      setResendAt(0);
      setSeconds(0);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [phone]);

  useEffect(() => {
    if (!resendAt) return;

    const update = () => {
      setSeconds(
        Math.max(0, Math.ceil((resendAt - Date.now()) / 1000))
      );
    };

    update();

    const timer = window.setInterval(update, 1000);

    return () => window.clearInterval(timer);
  }, [resendAt]);

  async function requestCode() {
    if (busy || disabled || unsaved || seconds > 0) return;

    setBusy(true);
    setNotice("");
    setError(false);

    try {
      const result = await api<{ message: string }>(
        "/v1/auth/phone/request",
        {
          method: "POST",
          body: JSON.stringify({})
        }
      );

      if (result.message === "Phone already verified") {
        await onVerified();
        return;
      }

      setRequested(true);
      setCode("");
      setSeconds(60);
      setResendAt(Date.now() + 60000);
      setNotice("Check your phone for a six-digit verification code.");
    } catch (caught) {
      setError(true);
      setNotice(
        caught instanceof Error
          ? caught.message
          : "Verification is temporarily unavailable."
      );
    } finally {
      setBusy(false);
    }
  }

  async function confirmCode() {
    if (
      busy ||
      disabled ||
      unsaved ||
      !/^[0-9]{6}$/.test(code)
    ) return;

    setBusy(true);
    setNotice("");
    setError(false);

    try {
      const result = await api<{
        message: string;
        user: VerificationUser;
      }>("/v1/auth/phone/confirm", {
        method: "POST",
        body: JSON.stringify({ code })
      });

      if (!result.user?.phone_verified) {
        throw new Error("Phone verification was not confirmed.");
      }

      await onVerified();

      setCode("");
      setRequested(false);
      setNotice("Your phone number has been verified.");
    } catch (caught) {
      setError(true);
      setNotice(
        caught instanceof Error
          ? caught.message
          : "Verification could not be completed."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="phone-verification"
      aria-label="Phone verification"
    >
      <div className="phone-verification-heading">
        <strong>Phone verification</strong>
        <span
          className={
            verified && !unsaved
              ? "phone-status phone-status-verified"
              : "phone-status"
          }
        >
          {verified && !unsaved ? "Verified" : "Not verified"}
        </span>
      </div>

      {unsaved ? (
        <p>Save your new mobile number before verifying it.</p>
      ) : verified ? (
        <p>Your registered mobile number is verified.</p>
      ) : (
        <>
          <p>
            Confirm that you own this mobile number.
            We will send you a six-digit code by SMS.
          </p>

          {requested && (
            <label>
              Verification code
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                placeholder="000000"
                value={code}
                disabled={busy || disabled}
                onChange={(event) =>
                  setCode(
                    event.target.value.replace(/\D/g, "").slice(0, 6)
                  )
                }
              />
              <small>The code expires after five minutes.</small>
            </label>
          )}

          <div className="phone-verification-actions">
            {requested && (
              <button
                type="button"
                className="button button-orange"
                disabled={
                  busy || disabled || code.length !== 6
                }
                onClick={confirmCode}
              >
                {busy ? "Please wait..." : "Confirm code"}
              </button>
            )}

            <button
              type="button"
              className="button"
              disabled={busy || disabled || seconds > 0}
              onClick={requestCode}
            >
              {seconds > 0
                ? `Resend in ${seconds}s`
                : requested
                  ? "Resend code"
                  : "Verify phone number"}
            </button>
          </div>
        </>
      )}

      {notice && (
        <p
          className={error ? "form-error" : "phone-verification-notice"}
          role={error ? "alert" : "status"}
        >
          {notice}
        </p>
      )}
    </section>
  );
}

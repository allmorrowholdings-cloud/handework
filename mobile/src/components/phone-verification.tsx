import React, { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { api } from "../api/client";
import { useAuth } from "../auth/context";
import { Button, Field } from "./ui";
import { colors } from "../theme";

export function PhoneVerification() {
  const { user, refresh } = useAuth();
  const [code, setCode] = useState("");
  const [requested, setRequested] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [resendAt, setResendAt] = useState(0);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    setCode("");
    setRequested(false);
    setNotice("");
    setResendAt(0);
    setSeconds(0);
  }, [user?.id, user?.phone]);

  useEffect(() => {
    if (!resendAt) return;

    const update = () =>
      setSeconds(
        Math.max(0, Math.ceil((resendAt - Date.now()) / 1000))
      );

    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [resendAt]);

  async function requestCode() {
    if (busy || seconds > 0) return;

    setBusy(true);
    setNotice("");

    try {
      const result = await api<{ message: string }>(
        "/v1/auth/phone/request",
        { method: "POST", body: JSON.stringify({}) }
      );

      if (result.message === "Phone already verified") {
        await refresh();
        return;
      }

      setRequested(true);
      setCode("");
      setSeconds(60);
      setResendAt(Date.now() + 60000);
      setNotice("Check your phone for a verification code.");
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Verification is temporarily unavailable."
      );
    } finally {
      setBusy(false);
    }
  }

  async function confirmCode() {
    if (busy || !/^[0-9]{6}$/.test(code)) return;

    setBusy(true);
    setNotice("");

    try {
      const result = await api<{
        user: { phone_verified: boolean }
      }>("/v1/auth/phone/confirm", {
        method: "POST",
        body: JSON.stringify({ code })
      });

      if (!result.user.phone_verified) {
        throw new Error("Verification was not confirmed.");
      }

      await refresh();
      setRequested(false);
      setCode("");
      setNotice("Your phone number has been verified.");
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Verification could not be completed."
      );
    } finally {
      setBusy(false);
    }
  }

  if (!user) return null;

  return (
    <View style={s.card}>
      <Text style={s.title}>Phone verification</Text>
      <Text style={s.phone}>{user.phone}</Text>

      <Text style={[
        s.status,
        user.phone_verified && s.verified
      ]}>
        {user.phone_verified ? "Verified" : "Not verified"}
      </Text>

      {!user.phone_verified && (
        <>
          <Text style={s.description}>
            Confirm that you own your registered mobile number.
          </Text>

          {requested && (
            <>
              <Field
                label="Verification code"
                keyboardType="number-pad"
                textContentType="oneTimeCode"
                maxLength={6}
                editable={!busy}
                value={code}
                onChangeText={(value) =>
                  setCode(value.replace(/\D/g, "").slice(0, 6))
                }
              />
              <Text style={s.description}>
                Your code expires after five minutes.
              </Text>

              <Button
                label="Confirm code"
                disabled={busy || code.length !== 6}
                onPress={confirmCode}
              />
            </>
          )}

          <Button
            dark
            disabled={busy || seconds > 0}
            label={
              busy ? "Please wait..." :
              seconds > 0 ? `Resend in ${seconds}s` :
              requested ? "Resend code" :
              "Verify phone number"
            }
            onPress={requestCode}
          />
        </>
      )}

      {!!notice && (
        <Text accessibilityLiveRegion="polite" style={s.description}>
          {notice}
        </Text>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  card: {
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: colors.line,
    marginBottom: 24
  },
  title: {
    fontSize: 16,
    fontWeight: "600",
    color: colors.ink
  },
  phone: {
    fontSize: 14,
    color: colors.ink
  },
  status: {
    color: "#A16207",
    fontWeight: "600",
    fontSize: 12
  },
  verified: {
    color: "#15803D"
  },
  description: {
    fontSize: 13,
    lineHeight: 20,
    color: colors.muted
  }
});

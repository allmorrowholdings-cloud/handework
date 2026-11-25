import React, { useEffect, useState } from "react";
import { Alert, Image, StyleSheet, Text, View } from "react-native";
import { api } from "../api/client";
import { useAuth } from "../auth/context";
import { Button, Field } from "./ui";
import { colors } from "../theme";

type Status = {
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

type Result = {
  message: string;
  recovery_codes?: string[];
  sign_in_required?: boolean;
};

export function AuthenticatorSettings() {
  const { signOut } = useAuth();

  const [status, setStatus] = useState<Status | null>(null);
  const [setup, setSetup] = useState<Enrollment | null>(null);
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    api<Status>("/v1/auth/totp/status")
      .then(setStatus)
      .catch(() => setNotice("Security settings are unavailable."));
  }, []);

  async function perform(action: string) {
    if (busy) return;

    setBusy(true);
    setNotice("");

    try {
      if (action === "setup") {
        const result = await api<Enrollment>(
          "/v1/auth/totp/setup",
          {
            method: "POST",
            body: JSON.stringify({ password })
          }
        );

        setSetup(result);
        setPassword("");
        setCode("");
        return;
      }

      const result = await api<Result>(
        "/v1/auth/totp/" + action,
        {
          method: "POST",
          body: JSON.stringify({ password, code })
        }
      );

      setPassword("");
      setCode("");
      setSetup(null);
      setCodes(result.recovery_codes ?? []);
      setNotice(result.message);
      setFinished(!!result.sign_in_required);

    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Security update failed."
      );
    } finally {
      setBusy(false);
    }
  }

  function confirmAction(action: string, title: string) {
    Alert.alert(
      title,
      "You will need to sign in again after this change.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Continue",
          onPress: () => void perform(action)
        }
      ]
    );
  }

  function finish() {
    Alert.alert(
      "Continue to sign in?",
      codes.length
        ? "Make sure you have securely saved your recovery codes."
        : "Your security settings have changed.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Continue",
          onPress: () => {
            setCodes([]);
            void signOut();
          }
        }
      ]
    );
  }

  return (
    <View style={s.card}>
      <Text style={s.title}>Account security</Text>
      <Text style={s.subtitle}>Two-factor authentication</Text>
      {status?.required && (
        <Text style={s.description}>
          Two-factor authentication is mandatory for administrator accounts.
        </Text>
      )}

      {finished ? (
        <>
          {codes.length > 0 && (
            <>
              <Text style={s.subtitle}>Emergency recovery codes</Text>
              <Text style={s.description}>
                Save these codes securely. Each can only be used once.
                They will not be displayed again.
              </Text>

              {codes.map(value => (
                <Text key={value} selectable style={s.recovery}>
                  {value}
                </Text>
              ))}
            </>
          )}

          <Button
            label="Continue to sign in"
            onPress={finish}
          />
        </>
      ) : !status ? (
        <Text style={s.description}>
          {notice || "Loading security settings..."}
        </Text>
      ) : !status.available && !status.enabled ? (
        <Text style={s.description}>
          Authenticator enrollment is not currently available.
        </Text>
      ) : setup ? (
        <>
          <Text style={s.description}>
            Scan this QR code from another device, or manually
            enter the setup key in your authenticator app.
          </Text>

          <Image
            source={{ uri: setup.qr_code }}
            style={s.qr}
            accessibilityLabel="Private authenticator QR code"
          />

          <Text style={s.description}>Manual setup key</Text>
          <Text selectable style={s.recovery}>
            {setup.secret}
          </Text>

          <Field
            label="Six-digit authenticator code"
            keyboardType="number-pad"
            maxLength={6}
            editable={!busy}
            value={code}
            onChangeText={value =>
              setCode(value.replace(/\D/g, "").slice(0, 6))
            }
          />

          <Text style={s.description}>
            Complete setup within ten minutes.
          </Text>

          <Button
            label="Enable authenticator"
            disabled={busy || code.length !== 6}
            onPress={() => void perform("enable")}
          />

          <Button
            dark
            label="Cancel setup"
            disabled={busy}
            onPress={() => {
              setSetup(null);
              setCode("");
            }}
          />
        </>
      ) : (
        <>
          <Text style={[
            s.status,
            status.enabled && s.enabled
          ]}>
            {status.enabled ? "Enabled" : "Not enabled"}
          </Text>

          {status.enabled && (
            <Text style={s.description}>
              Recovery codes remaining: {status.recovery_codes_remaining}
            </Text>
          )}

          <Field
            label="Current password"
            secureTextEntry
            editable={!busy}
            value={password}
            onChangeText={setPassword}
          />

          {status.enabled ? (
            <>
              <Field
                label="Authenticator or recovery code"
                value={code}
                editable={!busy}
                autoCapitalize="none"
                autoCorrect={false}
                maxLength={24}
                onChangeText={setCode}
              />

              <Button
                label="Generate new recovery codes"
                disabled={busy || !password || !code}
                onPress={() => confirmAction(
                  "recovery/regenerate",
                  "Replace existing recovery codes?"
                )}
              />

              <Button
                dark
                label="Disable authenticator"
                disabled={busy || !password || !code || !!status.required}
                onPress={() => confirmAction(
                  "disable",
                  "Disable two-factor authentication?"
                )}
              />
            </>
          ) : (
            <Button
              label="Set up Google Authenticator"
              disabled={busy || !password}
              onPress={() => void perform("setup")}
            />
          )}
        </>
      )}

      {busy && (
        <Text style={s.description}>Processing secure request...</Text>
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
    gap: 14,
    borderWidth: 1,
    borderColor: colors.line,
    marginBottom: 24
  },
  title: {
    fontSize: 18,
    fontWeight: "600",
    color: colors.ink
  },
  subtitle: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.ink
  },
  description: {
    fontSize: 13,
    lineHeight: 20,
    color: colors.muted
  },
  status: {
    fontSize: 12,
    fontWeight: "600",
    color: "#A16207"
  },
  enabled: {
    color: "#15803D"
  },
  qr: {
    width: 210,
    height: 210,
    backgroundColor: "#FFFFFF",
    alignSelf: "center"
  },
  recovery: {
    padding: 12,
    borderWidth: 1,
    borderColor: colors.line,
    color: colors.ink,
    fontSize: 13
  }
});

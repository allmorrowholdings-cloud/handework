import { getApp, getApps, initializeApp } from "firebase/app";
import {
  getMessaging,
  getToken,
  deleteToken,
  isSupported
} from "firebase/messaging";

import { api } from "./api";

const config = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID
};

const vapidKey = process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY;
const tokenKey = "handework_browser_push_token";

export function browserPushUnavailableReason() {
  if (typeof window === "undefined") return "Checking browser...";
  if (!window.isSecureContext) return "Notifications require a secure connection.";
  if (!("Notification" in window) || !("serviceWorker" in navigator))
    return "This browser does not support web notifications.";
  if (process.env.NEXT_PUBLIC_FIREBASE_PUSH_ENABLED !== "true")
    return "Browser notifications have not been enabled for this deployment.";
  if (!vapidKey || !Object.values(config).every(Boolean))
    return "Browser notification configuration is incomplete.";
  if (Notification.permission === "denied")
    return "Notifications are blocked. Allow them in your browser site settings.";
  return "";
}

export function browserPushAvailable() {
  return (
    typeof window !== "undefined" &&
    window.isSecureContext &&
    "Notification" in window &&
    "serviceWorker" in navigator &&
    process.env.NEXT_PUBLIC_FIREBASE_PUSH_ENABLED === "true" &&
    !!vapidKey &&
    Object.values(config).every(Boolean)
  );
}

async function messagingInstance() {
  if (!(await isSupported())) {
    throw new Error("Browser notifications are not supported.");
  }

  const app = getApps().length
    ? getApp()
    : initializeApp(config);

  return getMessaging(app);
}

export function browserPushRegistered() {
  return typeof window !== "undefined" &&
    !!localStorage.getItem(tokenKey);
}

export async function enableBrowserPush() {
  if (!browserPushAvailable()) {
    throw new Error("Browser notifications are currently unavailable.");
  }

  const permission = await Notification.requestPermission();

  if (permission !== "granted") {
    throw new Error("Notification permission was not granted.");
  }

  const registration = await navigator.serviceWorker.register(
    "/firebase-messaging-sw.js",
    { scope: "/firebase-push/" }
  );

  const messaging = await messagingInstance();

  const token = await getToken(messaging, {
    vapidKey,
    serviceWorkerRegistration: registration
  });

  if (!token) {
    throw new Error("Could not register this browser.");
  }

  try {
    await api("/v1/push-devices/browser", {
      method: "POST",
      body: JSON.stringify({ token })
    });
  } catch (error) {
    await deleteToken(messaging).catch(() => undefined);
    throw error;
  }

  localStorage.setItem(tokenKey, token);
}

export async function disableBrowserPush() {
  const token = localStorage.getItem(tokenKey);

  if (token) {
    await api("/v1/push-devices/browser/remove", {
      method: "POST",
      body: JSON.stringify({ token })
    });
  }

  const messaging = await messagingInstance();

  await deleteToken(messaging);
  localStorage.removeItem(tokenKey);
}

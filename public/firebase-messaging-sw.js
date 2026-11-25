self.addEventListener("push", function (event) {
  if (!event.data) return;

  event.waitUntil(
    self.registration.showNotification("handEwork", {
      body: "You have a new account update.",
      tag: "handework-account-update",
      data: {
        url: "/notifications"
      }
    })
  );
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();

  event.waitUntil(
    clients.matchAll({
      type: "window",
      includeUncontrolled: true
    }).then(function (windows) {
      const destination = new URL(
        "/notifications",
        self.location.origin
      ).href;

      for (const client of windows) {
        if (client.url === destination && "focus" in client) {
          return client.focus();
        }
      }

      return clients.openWindow(destination);
    })
  );
});

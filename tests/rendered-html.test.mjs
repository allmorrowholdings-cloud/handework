import assert from "node:assert/strict";
import test from "node:test";

async function render(path) {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(new URL(path, "http://localhost"), {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );

}

test("renders the production homepage and defers its Canva demonstration", async () => {
  const response = await render("/");
  assert.equal(response.status, 200);
  assert.match(
    response.headers.get("content-type") ?? "",
    /^text\/html\b/i,
  );
  const html = await response.text();
  assert.match(html, /<title>handEwork[^<]*<\/title>/);
  assert.match(html, /<h1>Get it done\.<\/h1>/);
  assert.doesNotMatch(html, /embed\.figma\.com/);
  assert.match(html, /<video[^>]*preload="none"/);
  const sections = ["How it works</h2>", "<h2>See good work", "Good work leaves proof."];
  const offsets = sections.map(section => html.indexOf(section));
  assert.ok(offsets[0] >= 0 && offsets[0] < offsets[1] && offsets[1] < offsets[2]);
});


test("authentication forms use POST and wait for hydration before submission", async () => {
  for (const path of ["/auth/sign-in", "/auth/create-account"]) {
    const html = await (await render(path)).text();
    const form = html.match(/<form[^>]*class="auth-form"[^>]*>[\s\S]*?<\/form>/i)?.[0];
    assert.ok(form);
    assert.match(form, /<form[^>]*method="post"/i);
    assert.match(form, /<button[^>]*disabled[^>]*>(?:Sign in securely|Create customer account)/i);
  }
});

test("account codes and new passwords are submitted by POST after hydration", async () => {
  for (const action of ["verify", "reset"]) {
    const html = await (await render("/auth/email/" + action)).text();
    const forms = html.match(/<form[^>]*>[\s\S]*?<\/form>/gi) ?? [];
    assert.equal(forms.length, 2);
    for (const form of forms) {
      assert.match(form, /<form[^>]*method="post"/i);
      assert.match(form, /<button[^>]*disabled/i);
    }
  }
});

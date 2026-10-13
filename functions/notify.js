// Receives Cloudflare Alerts webhook (Pages "Project updates") and forwards it to Bark.
// Env: WEBHOOK_SECRET (must match the Secret set on the Cloudflare webhook), BARK_KEY.

export async function onRequestPost({ request, env }) {
  if (!env.WEBHOOK_SECRET || !env.BARK_KEY) {
    return new Response("not configured", { status: 500 });
  }
  if (request.headers.get("cf-webhook-auth") !== env.WEBHOOK_SECRET) {
    return new Response("unauthorized", { status: 401 });
  }

  const raw = await request.text();
  let body = raw;
  try {
    const payload = JSON.parse(raw);
    body = payload.text ?? raw;
  } catch {}

  const res = await fetch("https://api.day.app/push", {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({
      device_key: env.BARK_KEY,
      title: "Cloudflare Pages",
      body: body.slice(0, 1000),
      group: "cloudflare-pages",
    }),
  });

  return new Response(res.ok ? "ok" : "bark error", { status: res.ok ? 200 : 502 });
}

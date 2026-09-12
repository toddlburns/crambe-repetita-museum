/**
 * Password gate for the museum.
 *
 * Replaces Cloudflare Access, which is an IDENTITY system: it cannot take a shared
 * password, it mails a one-time PIN, and it puts a Cloudflare-branded interstitial in
 * front of the archive. Todd wanted one password he can hand to one person and a page
 * that looks like the museum, so the gate lives here instead.
 *
 * ⚠️ THE COOKIE IS SIGNED, NOT A FLAG. An unsigned "logged_in=1" cookie is set by
 * anyone who can open devtools, and the old view-source password on the GitHub Pages
 * site had the same shape of problem. The cookie here carries an expiry and an
 * HMAC-SHA256 over it, and is re-verified on every request.
 *
 * ⚠️ THE PASSWORD COMPARE IS CONSTANT TIME. A plain === leaks length and prefix through
 * timing. Both sides are HMACed first and the digests compared byte by byte.
 *
 * ⚠️ A ROOT _middleware.js INTERCEPTS STATIC ASSETS TOO, which is the point - images and
 * originals must be gated, not just HTML. If this file is moved into a subdirectory it
 * will silently stop protecting everything above it.
 *
 * Secrets (Pages project settings, never in the repo):
 *   MUSEUM_PASSWORD - the shared password
 *   AUTH_SECRET     - random key for the cookie signature
 */

const COOKIE = "crvi_auth";
const MAX_AGE = 60 * 60 * 24 * 90;      // 90 days

const enc = new TextEncoder();

async function hmac(secret, msg) {
  const key = await crypto.subtle.importKey(
    "raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(msg));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, "0")).join("");
}

/** Compare two hex digests without leaking where they diverge. */
function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

async function mintCookie(secret) {
  const exp = Math.floor(Date.now() / 1000) + MAX_AGE;
  return `${exp}.${await hmac(secret, String(exp))}`;
}

async function cookieValid(secret, raw) {
  if (!raw) return false;
  const dot = raw.lastIndexOf(".");
  if (dot < 1) return false;
  const exp = raw.slice(0, dot), sig = raw.slice(dot + 1);
  if (!/^\d+$/.test(exp) || Number(exp) < Math.floor(Date.now() / 1000)) return false;
  return safeEqual(sig, await hmac(secret, exp));
}

function readCookie(header, name) {
  for (const part of (header || "").split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return v.join("=");
  }
  return null;
}

function loginPage(status, wrong) {
  // Todd's brief for the museum: "SUPER CLEAN. Black and white predominantly. Clinical.
  // The art needs to be the most important thing by far." The gate should not announce
  // itself as a product - it is a door.
  const html = `<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crambe Repetita</title>
<style>
  :root { color-scheme: light; }
  html,body { height:100%; }
  body { margin:0; display:flex; align-items:center; justify-content:center;
         background:#fff; color:#111;
         font:400 15px/1.5 "Times New Roman",Times,serif; }
  main { width:min(22rem,86vw); text-align:left; }
  h1 { font-size:15px; font-weight:400; margin:0 0 1.6rem; letter-spacing:.14em;
       text-transform:uppercase; }
  form { display:flex; gap:.5rem; }
  input { flex:1 1 auto; min-width:0; padding:.5rem .6rem; border:1px solid #111;
          border-radius:0; background:#fff; color:#111; font:inherit; }
  input:focus { outline:2px solid #111; outline-offset:1px; }
  button { padding:.5rem .9rem; border:1px solid #111; border-radius:0;
           background:#111; color:#fff; font:inherit; cursor:pointer; }
  p.err { margin:1rem 0 0; color:#b00020; font-size:13px; }
  @media (prefers-color-scheme: dark) {
    body { background:#fff; color:#111; }   /* fixed white theme, per the design brief */
  }
</style></head><body><main>
<h1>Crambe Repetita</h1>
<form method="POST" autocomplete="on">
  <input type="password" name="pw" aria-label="Password" autofocus
         autocomplete="current-password" placeholder="Password">
  <button type="submit">Enter</button>
</form>
${wrong ? '<p class="err">Not that one.</p>' : ""}
</main></body></html>`;
  return new Response(html, {
    status,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      // The gate page must never be cached by an intermediary as if it were the museum.
      "x-robots-tag": "noindex, nofollow",
    },
  });
}

export async function onRequest(context) {
  const { request, env, next } = context;
  const password = env.MUSEUM_PASSWORD;
  const secret = env.AUTH_SECRET;

  // ⚠️ FAIL CLOSED. If the secrets are missing the gate must refuse, not wave everyone
  // through - a missing binding is exactly how a "protected" site quietly goes public.
  if (!password || !secret) {
    return new Response("Gate not configured.", {
      status: 503, headers: { "cache-control": "no-store" },
    });
  }

  if (await cookieValid(secret, readCookie(request.headers.get("cookie"), COOKIE))) {
    return next();
  }

  if (request.method === "POST") {
    let given = "";
    try {
      const form = await request.formData();
      given = String(form.get("pw") || "");
    } catch (_) { /* not a form post - fall through to the login page */ }

    const ok = safeEqual(await hmac(secret, given), await hmac(secret, password));
    if (ok) {
      const value = await mintCookie(secret);
      return new Response(null, {
        status: 303,
        headers: {
          location: new URL(request.url).pathname,
          "set-cookie": `${COOKIE}=${value}; Path=/; Max-Age=${MAX_AGE}; HttpOnly; Secure; SameSite=Lax`,
          "cache-control": "no-store",
        },
      });
    }
    return loginPage(401, true);
  }

  return loginPage(401, false);
}

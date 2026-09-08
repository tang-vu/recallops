import { NextRequest, NextResponse } from "next/server";

const COOKIE = "recallops_workspace";
const ROUTES: Record<string, string[]> = {
  "": ["GET", "POST"],
  policy: ["PUT"],
  decisions: ["GET"],
  evaluate: ["POST"],
  failures: ["POST"],
  "keys/rotate": ["POST"],
  session: ["POST", "DELETE"],
};
type Context = { params: Promise<{ path?: string[] }> };

function reply(data: unknown, status = 200) {
  return NextResponse.json(data, {
    status,
    headers: { "Cache-Control": "no-store" },
  });
}

function setSession(response: NextResponse, key: string) {
  response.cookies.set(COOKIE, key, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/api/workspace",
    maxAge: key ? 60 * 60 * 24 * 7 : 0,
  });
}

async function forward(request: NextRequest, context: Context) {
  const path = (await context.params).path?.join("/") ?? "";
  const receiptRoute =
    /^decisions\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/(review|authorization)$/.exec(
      path,
    );
  const receiptAllowed =
    receiptRoute &&
    request.method === (receiptRoute[1] === "review" ? "POST" : "GET");
  if (
    !receiptAllowed &&
    (!Object.hasOwn(ROUTES, path) || !ROUTES[path].includes(request.method))
  )
    return reply({ detail: "Route not found." }, 404);
  // Cookie-authenticated writes require a same-origin browser request. API
  // clients must supply their bearer key explicitly.
  const bearer = request.headers.get("authorization");
  const origin = request.headers.get("origin");
  let sameOrigin = false;
  try {
    const supplied = new URL(origin ?? "");
    sameOrigin =
      ["http:", "https:"].includes(supplied.protocol) &&
      supplied.host === request.headers.get("host");
  } catch {
    /* An absent or malformed Origin cannot authorize a cookie write. */
  }
  if (request.method !== "GET" && !bearer && !sameOrigin) {
    return reply({ detail: "A same-origin request is required." }, 403);
  }
  if (path === "session" && request.method === "DELETE") {
    const response = reply({ signed_out: true });
    setSession(response, "");
    return response;
  }
  let body: string | undefined;
  let sessionKey: string | undefined;
  try {
    if (request.method !== "GET") {
      const reader = request.body?.getReader();
      const chunks: Uint8Array[] = [];
      let length = 0;
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          length += value.byteLength;
          if (length > 16_384) {
            await reader.cancel();
            return reply({ detail: "Request exceeds 16 KiB." }, 413);
          }
          chunks.push(value);
        }
      }
      body = Buffer.concat(chunks).toString("utf8") || "{}";
      const parsed = JSON.parse(body);
      if (path === "session") {
        if (
          typeof parsed.owner_key !== "string" ||
          !/^ro_owner_[A-Za-z0-9_-]{43}$/.test(parsed.owner_key)
        ) {
          return reply({ detail: "Enter a valid workspace owner key." }, 400);
        }
        sessionKey = parsed.owner_key;
      }
    }
  } catch {
    return reply({ detail: "Invalid JSON request." }, 400);
  }
  const token = sessionKey
    ? `Bearer ${sessionKey}`
    : (bearer ??
      (request.cookies.get(COOKIE)?.value
        ? `Bearer ${request.cookies.get(COOKIE)!.value}`
        : undefined));
  const headers = new Headers({ "Content-Type": "application/json" });
  if (token) headers.set("Authorization", token);
  const idempotency = request.headers.get("idempotency-key");
  if (idempotency) headers.set("Idempotency-Key", idempotency);
  const base = process.env.RECALLOPS_API_URL ?? "http://127.0.0.1:8000";
  const target = `${base.replace(/\/$/, "")}/v1/workspace${path && path !== "session" ? `/${path}` : ""}`;
  try {
    const upstream = await fetch(target, {
      method: path === "session" ? "GET" : request.method,
      headers,
      body: path === "session" ? undefined : body,
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
    });
    const data = await upstream.json();
    const response = reply(data, upstream.status);
    if (upstream.ok && sessionKey) setSession(response, sessionKey);
    if (
      upstream.ok &&
      path === "" &&
      request.method === "POST" &&
      data.owner_key
    )
      setSession(response, data.owner_key);
    return response;
  } catch {
    return reply(
      {
        detail:
          "Workspace service is unavailable. Stop agent execution and retry later.",
      },
      503,
    );
  }
}

export const dynamic = "force-dynamic";
export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const DELETE = forward;

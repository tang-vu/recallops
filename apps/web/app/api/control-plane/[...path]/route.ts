import { NextRequest, NextResponse } from "next/server";

import { isAdminDemoPath, isAllowedProxyRequest } from "@/lib/proxy-policy";

type RouteContext = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const { path: segments } = await context.params;
  const path = segments.join("/");
  if (!isAllowedProxyRequest(request.method, path)) {
    return NextResponse.json({ detail: "Proxy route is not allowed." }, { status: 404 });
  }

  const baseUrl = process.env.RECALLOPS_API_URL ?? "http://127.0.0.1:8000";
  const target = new URL(path, `${baseUrl.replace(/\/$/, "")}/`);
  target.search = request.nextUrl.search;
  const headers = new Headers({ "Content-Type": request.headers.get("content-type") ?? "application/json" });
  for (const name of ["idempotency-key", "x-correlation-id"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  if (isAdminDemoPath(path) && process.env.RECALLOPS_ADMIN_TOKEN) {
    headers.set("X-RecallOps-Admin-Token", process.env.RECALLOPS_ADMIN_TOKEN);
  }

  try {
    const body = request.method === "GET" ? undefined : await request.arrayBuffer();
    const response = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(35_000),
    });
    const responseBody = await response.arrayBuffer();
    const outgoing = new NextResponse(responseBody, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
    });
    const correlation = response.headers.get("x-correlation-id");
    if (correlation) outgoing.headers.set("X-Correlation-ID", correlation);
    return outgoing;
  } catch {
    return NextResponse.json(
      { detail: "RecallOps control plane is unavailable. Commerce remains stopped." },
      { status: 503 },
    );
  }
}

export const dynamic = "force-dynamic";
export async function GET(request: NextRequest, context: RouteContext) {
  return forward(request, context);
}
export async function POST(request: NextRequest, context: RouteContext) {
  return forward(request, context);
}

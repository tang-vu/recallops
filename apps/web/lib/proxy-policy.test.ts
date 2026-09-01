import { describe, expect, it } from "vitest";

import { isAdminDemoPath, isAllowedProxyRequest } from "./proxy-policy";

describe("control-plane proxy allowlist", () => {
  it("allows only judge-facing read and action routes", () => {
    expect(isAllowedProxyRequest("GET", "v1/system/status")).toBe(true);
    expect(isAllowedProxyRequest("GET", "v1/jobs")).toBe(true);
    expect(
      isAllowedProxyRequest(
        "GET",
        "v1/decisions/123e4567-e89b-12d3-a456-426614174000/anchor",
      ),
    ).toBe(true);
    expect(isAllowedProxyRequest("POST", "v1/actions/123e4567-e89b-12d3-a456-426614174000/execute")).toBe(true);
    expect(isAllowedProxyRequest("POST", "v1/policies")).toBe(false);
    expect(isAllowedProxyRequest("GET", "v1/openapi.json")).toBe(false);
    expect(isAllowedProxyRequest("DELETE", "v1/decisions")).toBe(false);
  });

  it("recognizes only the two admin demo paths", () => {
    expect(isAdminDemoPath("v1/demo/session-1")).toBe(true);
    expect(isAdminDemoPath("v1/demo/session-2")).toBe(true);
    expect(isAdminDemoPath("v1/policies")).toBe(false);
  });
});

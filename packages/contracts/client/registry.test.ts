import { describe, expect, it } from "vitest";
import { keccak256, toBytes, zeroHash } from "viem";
import { decisionValue, prepareAnchor, requireAddress } from "./registry.js";

describe("receipt registry client", () => {
  it("prepares deterministic digest-only calldata", () => {
    const input = {
      receiptId: "b7d594c0-e9a2-46f8-b54f-a1bc59b6d9af",
      decision: "APPROVE" as const,
      decisionDigest: `0x${"12".repeat(32)}` as const,
      acpJobReference: "fixture:job-1",
    };
    const first = prepareAnchor(input);
    const second = prepareAnchor(input);

    expect(first).toEqual(second);
    expect(first.receiptIdDigest).toBe(keccak256(toBytes(input.receiptId)));
    expect(first.acpJobReferenceDigest).toBe(keccak256(toBytes("fixture:job-1")));
    expect(first.calldata).toMatch(/^0x[0-9a-f]+$/);
  });

  it("uses an empty ACP digest without inventing a job reference", () => {
    const prepared = prepareAnchor({
      receiptId: "receipt-2",
      decision: "DENY",
      decisionDigest: `0x${"ab".repeat(32)}`,
    });
    expect(prepared.decisionValue).toBe(1);
    expect(prepared.acpJobReferenceDigest).toBe(zeroHash);
  });

  it("rejects invalid digests, decisions, and addresses", () => {
    expect(() =>
      prepareAnchor({ receiptId: "receipt", decision: "ESCALATE", decisionDigest: "0x12" }),
    ).toThrow(/32-byte/);
    expect(() => decisionValue("MAYBE" as never)).toThrow(/Unsupported/);
    expect(() => requireAddress("0x1234", "contractAddress")).toThrow(/EVM address/);
  });
});

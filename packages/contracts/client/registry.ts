import {
  encodeAbiParameters,
  encodeFunctionData,
  getAddress,
  isAddress,
  keccak256,
  parseAbi,
  parseAbiParameters,
  toBytes,
  zeroHash,
  type Address,
  type Hex,
} from "viem";

export const LOCAL_ANVIL_CHAIN_ID = 31_337;
export const BASE_SEPOLIA_CHAIN_ID = 84_532;

export const receiptRegistryAbi = parseAbi([
  "function anchorReceipt(bytes32 receiptIdDigest, bytes32 decisionDigest, uint8 decision, bytes32 acpJobReferenceDigest) returns (bool created)",
  "function authorizedSubmitter() view returns (address)",
  "function deployedChainId() view returns (uint256)",
  "function getAnchor(bytes32 receiptIdDigest) view returns ((bytes32 recordHash,uint64 anchoredAt,uint8 decision,bool exists))",
  "event ReceiptAnchored(bytes32 indexed receiptIdDigest, bytes32 indexed decisionDigest, uint8 decision, address indexed actor, uint64 anchoredAt, bytes32 acpJobReferenceDigest)",
]);

export type ReceiptDecision = "APPROVE" | "DENY" | "ESCALATE";

export interface AnchorInput {
  receiptId: string;
  decision: ReceiptDecision;
  decisionDigest: Hex;
  acpJobReference?: string | null;
}

export interface PreparedAnchor {
  receiptIdDigest: Hex;
  decisionDigest: Hex;
  decisionValue: 0 | 1 | 2;
  acpJobReferenceDigest: Hex;
  recordHash: Hex;
  calldata: Hex;
}

function requireBytes32(value: string, field: string): Hex {
  if (!/^0x[0-9a-fA-F]{64}$/.test(value)) {
    throw new Error(`${field} must be a 32-byte hexadecimal digest`);
  }
  return value.toLowerCase() as Hex;
}

export function requireAddress(value: string, field: string): Address {
  if (!isAddress(value, { strict: true })) throw new Error(`${field} must be an EVM address`);
  return getAddress(value);
}

export function decisionValue(decision: ReceiptDecision): 0 | 1 | 2 {
  if (decision === "APPROVE") return 0;
  if (decision === "DENY") return 1;
  if (decision === "ESCALATE") return 2;
  throw new Error("Unsupported decision");
}

export function prepareAnchor(input: AnchorInput): PreparedAnchor {
  if (!input.receiptId || input.receiptId.length > 128) {
    throw new Error("receiptId must contain between 1 and 128 characters");
  }
  if (input.acpJobReference && input.acpJobReference.length > 256) {
    throw new Error("acpJobReference exceeds 256 characters");
  }
  const receiptIdDigest = keccak256(toBytes(input.receiptId));
  const decisionDigest = requireBytes32(input.decisionDigest, "decisionDigest");
  const decision = decisionValue(input.decision);
  const acpJobReferenceDigest = input.acpJobReference
    ? keccak256(toBytes(input.acpJobReference))
    : zeroHash;
  const recordHash = keccak256(
    encodeAbiParameters(parseAbiParameters("bytes32, uint8, bytes32"), [
      decisionDigest,
      decision,
      acpJobReferenceDigest,
    ]),
  );
  const calldata = encodeFunctionData({
    abi: receiptRegistryAbi,
    functionName: "anchorReceipt",
    args: [receiptIdDigest, decisionDigest, decision, acpJobReferenceDigest],
  });
  return {
    receiptIdDigest,
    decisionDigest,
    decisionValue: decision,
    acpJobReferenceDigest,
    recordHash,
    calldata,
  };
}

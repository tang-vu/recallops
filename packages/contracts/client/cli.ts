import process from "node:process";
import {
  createPublicClient,
  createWalletClient,
  defineChain,
  http,
  type Address,
  type Hex,
} from "viem";
import { baseSepolia } from "viem/chains";
import {
  BASE_SEPOLIA_CHAIN_ID,
  LOCAL_ANVIL_CHAIN_ID,
  prepareAnchor,
  receiptRegistryAbi,
  requireAddress,
  type AnchorInput,
} from "./registry.js";

interface CliRequest extends AnchorInput {
  operation: "prepare" | "anchor";
  chainId?: number;
  rpcUrl?: string;
  contractAddress?: string;
  submitter?: string;
  deploymentBlock?: string;
}

const localAnvil = defineChain({
  id: LOCAL_ANVIL_CHAIN_ID,
  name: "Local Anvil",
  nativeCurrency: { name: "Anvil Ether", symbol: "ETH", decimals: 18 },
  rpcUrls: { default: { http: ["http://127.0.0.1:8545"] } },
});

function parseRequest(value: string): CliRequest {
  const parsed: unknown = JSON.parse(value);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Input must be a JSON object");
  }
  return parsed as CliRequest;
}

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) chunks.push(Buffer.from(chunk));
  const value = Buffer.concat(chunks).toString("utf8");
  if (Buffer.byteLength(value) > 65_536) throw new Error("Input exceeds 64 KiB");
  return value;
}

function requireLiveGate(chainId: number): void {
  if (chainId !== BASE_SEPOLIA_CHAIN_ID) return;
  const enabled = process.env.RECALLOPS_ENABLE_BASE_SEPOLIA === "true";
  const approvalId = process.env.RECALLOPS_BASE_APPROVAL_ID ?? "";
  if (!enabled || approvalId.length < 8) {
    throw new Error("Base Sepolia anchoring requires an explicit approval gate");
  }
}

function chainFor(chainId: number) {
  if (chainId === LOCAL_ANVIL_CHAIN_ID) return localAnvil;
  if (chainId === BASE_SEPOLIA_CHAIN_ID) return baseSepolia;
  throw new Error("Only local Anvil and Base Sepolia are allowed");
}

async function anchor(request: CliRequest) {
  if (!request.chainId || !request.rpcUrl || !request.contractAddress || !request.submitter) {
    throw new Error("anchor requires chainId, rpcUrl, contractAddress, and submitter");
  }
  requireLiveGate(request.chainId);
  const chain = chainFor(request.chainId);
  const address = requireAddress(request.contractAddress, "contractAddress");
  const submitter = requireAddress(request.submitter, "submitter");
  const prepared = prepareAnchor(request);
  const transport = http(request.rpcUrl, { timeout: 30_000, retryCount: 0 });
  const publicClient = createPublicClient({ chain, transport });
  const actualChainId = await publicClient.getChainId();
  if (actualChainId !== request.chainId) throw new Error("RPC chain ID does not match request");
  const [deployedChainId, authorizedSubmitter, existing] = await Promise.all([
    publicClient.readContract({ address, abi: receiptRegistryAbi, functionName: "deployedChainId" }),
    publicClient.readContract({ address, abi: receiptRegistryAbi, functionName: "authorizedSubmitter" }),
    publicClient.readContract({
      address,
      abi: receiptRegistryAbi,
      functionName: "getAnchor",
      args: [prepared.receiptIdDigest],
    }),
  ]);
  if (deployedChainId !== BigInt(request.chainId)) throw new Error("Registry chain ID mismatch");
  if (authorizedSubmitter.toLowerCase() !== submitter.toLowerCase()) {
    throw new Error("Configured submitter is not authorized by the registry");
  }

  if (existing.exists) {
    if (existing.recordHash !== prepared.recordHash || existing.decision !== prepared.decisionValue) {
      throw new Error("Receipt digest is already anchored with conflicting content");
    }
    const logs = await publicClient.getContractEvents({
      address,
      abi: receiptRegistryAbi,
      eventName: "ReceiptAnchored",
      args: { receiptIdDigest: prepared.receiptIdDigest },
      fromBlock: request.deploymentBlock ? BigInt(request.deploymentBlock) : 0n,
      toBlock: "latest",
    });
    const transactionHash = logs.at(-1)?.transactionHash ?? null;
    return resultPayload(request.chainId, address, prepared, transactionHash, false);
  }

  const walletClient = createWalletClient({ account: submitter, chain, transport });
  const simulation = await publicClient.simulateContract({
    account: submitter,
    address,
    abi: receiptRegistryAbi,
    functionName: "anchorReceipt",
    args: [
      prepared.receiptIdDigest,
      prepared.decisionDigest,
      prepared.decisionValue,
      prepared.acpJobReferenceDigest,
    ],
  });
  const transactionHash = await walletClient.writeContract(simulation.request);
  const receipt = await publicClient.waitForTransactionReceipt({
    hash: transactionHash,
    confirmations: 1,
    timeout: 120_000,
  });
  if (receipt.status !== "success") throw new Error("Anchor transaction reverted");
  const persisted = await publicClient.readContract({
    address,
    abi: receiptRegistryAbi,
    functionName: "getAnchor",
    args: [prepared.receiptIdDigest],
  });
  if (!persisted.exists || persisted.recordHash !== prepared.recordHash) {
    throw new Error("Receipt confirmation did not match the requested anchor");
  }
  return resultPayload(request.chainId, address, prepared, transactionHash, true);
}

function resultPayload(
  chainId: number,
  contractAddress: Address,
  prepared: ReturnType<typeof prepareAnchor>,
  transactionHash: Hex | null,
  created: boolean,
) {
  return {
    ok: true,
    chainId,
    contractAddress,
    receiptIdDigest: prepared.receiptIdDigest,
    decisionDigest: prepared.decisionDigest,
    acpJobReferenceDigest: prepared.acpJobReferenceDigest,
    recordHash: prepared.recordHash,
    transactionHash,
    explorerUrl:
      chainId === BASE_SEPOLIA_CHAIN_ID && transactionHash
        ? `https://sepolia-explorer.base.org/tx/${transactionHash}`
        : null,
    created,
    verified: true,
  };
}

async function main(): Promise<void> {
  try {
    const request = parseRequest(await readStdin());
    const prepared = prepareAnchor(request);
    const output =
      request.operation === "prepare"
        ? { ok: true, ...prepared }
        : request.operation === "anchor"
          ? await anchor(request)
          : (() => {
              throw new Error("Unsupported operation");
            })();
    process.stdout.write(`${JSON.stringify(output)}\n`);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    const safeMessages = [
      "Input must be a JSON object",
      "Input exceeds 64 KiB",
      "Unsupported operation",
      "Only local Anvil and Base Sepolia are allowed",
      "Base Sepolia anchoring requires an explicit approval gate",
      "anchor requires chainId, rpcUrl, contractAddress, and submitter",
      "RPC chain ID does not match request",
      "Registry chain ID mismatch",
      "Configured submitter is not authorized by the registry",
      "Receipt digest is already anchored with conflicting content",
      "Anchor transaction reverted",
      "Receipt confirmation did not match the requested anchor",
    ];
    const safe = safeMessages.includes(message) || /^(receiptId|decisionDigest|acpJobReference|contractAddress|submitter)/.test(message)
      ? message
      : "Base registry operation failed";
    process.stdout.write(`${JSON.stringify({ ok: false, error: safe })}\n`);
    process.exitCode = 1;
  }
}

await main();

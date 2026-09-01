const GET_PATHS = [
  /^health$/,
  /^v1\/system\/status$/,
  /^v1\/decisions(?:\/[0-9a-f-]+(?:\/anchor)?)?$/,
  /^v1\/memory\/evidence$/,
  /^v1\/counterparties$/,
  /^v1\/jobs$/,
  /^v1\/benchmark\/latest$/,
];

const POST_PATHS = [
  /^v1\/actions\/evaluate$/,
  /^v1\/actions\/[0-9a-f-]+\/execute$/,
  /^v1\/demo\/session-[12]$/,
];

export function isAllowedProxyRequest(method: string, path: string): boolean {
  const patterns = method === "GET" ? GET_PATHS : method === "POST" ? POST_PATHS : [];
  return patterns.some((pattern) => pattern.test(path));
}

export function isAdminDemoPath(path: string): boolean {
  return /^v1\/demo\/session-[12]$/.test(path);
}

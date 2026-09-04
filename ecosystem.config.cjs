/* eslint-disable @typescript-eslint/no-require-imports */
/* global __dirname, module, process, require */
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const root = __dirname;
const webRoot = path.join(root, "apps", "web");
const controlPlaneRoot = path.join(root, "services", "control-plane");
const localAppData = process.env.LOCALAPPDATA;

if (!localAppData) {
  throw new Error("LOCALAPPDATA is required for the Windows deployment.");
}

const runtimeRoot = path.join(localAppData, "RecallOps");
const dataRoot = path.join(runtimeRoot, "data");
const logsRoot = path.join(runtimeRoot, "logs");
const cloudflaredConfig = path.join(runtimeRoot, "cloudflared", "config.yml");
const cloudflared = process.env.RECALLOPS_CLOUDFLARED_BIN
  ?? "C:\\Program Files (x86)\\cloudflared\\cloudflared.exe";
const uvicorn = path.join(root, ".venv", "Scripts", "uvicorn.exe");

for (const directory of [dataRoot, logsRoot]) {
  fs.mkdirSync(directory, { recursive: true });
}

if (!fs.existsSync(uvicorn)) {
  throw new Error(`RecallOps virtual environment is missing uvicorn at ${uvicorn}`);
}

if (!fs.existsSync(cloudflaredConfig)) {
  throw new Error(`RecallOps tunnel config is missing at ${cloudflaredConfig}`);
}

// This value is generated locally and passed to both processes. It is never
// committed or printed. PM2 persists the expanded environment for resurrection.
const adminToken = process.env.RECALLOPS_ADMIN_TOKEN
  ?? crypto.randomBytes(32).toString("base64url");

const processDefaults = {
  exec_mode: "fork",
  instances: 1,
  autorestart: true,
  min_uptime: "10s",
  max_restarts: 30,
  restart_delay: 2_000,
  exp_backoff_restart_delay: 100,
  kill_timeout: 15_000,
  time: true,
};

module.exports = {
  apps: [
    {
      ...processDefaults,
      name: "recallops-api",
      namespace: "recallops",
      cwd: controlPlaneRoot,
      script: uvicorn,
      args: ["recallops.api.app:app", "--host", "127.0.0.1", "--port", "8820"],
      interpreter: "none",
      max_memory_restart: "768M",
      env: {
        PYTHONUTF8: "1",
        PYTHONUNBUFFERED: "1",
        RECALLOPS_MEMORY_DB: path.join(dataRoot, "recallops.db"),
        RECALLOPS_ADMIN_TOKEN: adminToken,
        RECALLOPS_VIRTUALS_MODE: "FIXTURE MODE",
        RECALLOPS_BASE_MODE: "NOT CONFIGURED",
        RECALLOPS_BENCHMARK_RESULT: path.join(root, "benchmark", "results", "latest.json"),
      },
      out_file: path.join(logsRoot, "pm2-api.out.log"),
      error_file: path.join(logsRoot, "pm2-api.err.log"),
      merge_logs: true,
    },
    {
      ...processDefaults,
      name: "recallops-web",
      namespace: "recallops",
      cwd: webRoot,
      script: path.join(webRoot, "node_modules", "next", "dist", "bin", "next"),
      args: ["start", "--hostname", "127.0.0.1", "--port", "3220"],
      interpreter: process.execPath,
      max_memory_restart: "768M",
      env: {
        NODE_ENV: "production",
        RECALLOPS_API_URL: "http://127.0.0.1:8820",
        RECALLOPS_ADMIN_TOKEN: adminToken,
      },
      out_file: path.join(logsRoot, "pm2-web.out.log"),
      error_file: path.join(logsRoot, "pm2-web.err.log"),
      merge_logs: true,
    },
    {
      ...processDefaults,
      name: "recallops-tunnel",
      namespace: "recallops",
      cwd: root,
      script: cloudflared,
      args: ["tunnel", "--config", cloudflaredConfig, "run"],
      interpreter: "none",
      max_restarts: 60,
      max_memory_restart: "256M",
      out_file: path.join(logsRoot, "pm2-tunnel.out.log"),
      error_file: path.join(logsRoot, "pm2-tunnel.err.log"),
      merge_logs: true,
    },
  ],
};

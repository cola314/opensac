const express = require("express");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

const app = express();
const PORT = process.env.PORT || 3000;
const DATA_DIR = process.env.DATA_DIR
  ? path.resolve(process.env.DATA_DIR)
  : path.join(__dirname, "..", "ml", "data");
const ML_DIR = path.join(__dirname, "..", "ml");

const ADMIN_USER = process.env.ADMIN_USER || "";
const ADMIN_PASS = process.env.ADMIN_PASS || "";

function readJson(filename) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, filename), "utf-8"));
}

function safeReadJson(filename, fallback) {
  try {
    return readJson(filename);
  } catch {
    return fallback;
  }
}

function basicAuth(req, res, next) {
  if (!ADMIN_USER || !ADMIN_PASS) {
    return res.status(503).send("Admin disabled (ADMIN_USER/ADMIN_PASS unset)");
  }
  const header = req.headers["authorization"] || "";
  if (!header.startsWith("Basic ")) {
    res.set("WWW-Authenticate", 'Basic realm="opensac admin"');
    return res.status(401).send("Auth required");
  }
  const decoded = Buffer.from(header.slice(6), "base64").toString();
  const [user, ...passParts] = decoded.split(":");
  const pass = passParts.join(":");
  if (user !== ADMIN_USER || pass !== ADMIN_PASS) {
    res.set("WWW-Authenticate", 'Basic realm="opensac admin"');
    return res.status(401).send("Bad credentials");
  }
  next();
}

app.get("/api/concerts", (_req, res) => {
  res.json(safeReadJson("concerts.json", []));
});

app.get("/api/composers", (_req, res) => {
  res.json(safeReadJson("composers.json", []));
});

app.use("/admin", basicAuth, express.static(path.join(__dirname, "admin")));
app.use("/api/admin", basicAuth);

app.get("/api/admin/runs", (_req, res) => {
  const Database = tryLoadSqlite();
  if (!Database) return res.json({ error: "sqlite unavailable" });
  const dbPath = path.join(DATA_DIR, "sac.db");
  if (!fs.existsSync(dbPath)) return res.json([]);
  const db = new Database(dbPath, { readonly: true });
  const rows = db
    .prepare(
      `SELECT id, month, started_at, finished_at, status,
              concerts_total, concerts_new, pieces_added, composers_added, error_message
       FROM pipeline_runs ORDER BY id DESC LIMIT 20`
    )
    .all();
  db.close();
  res.json(rows);
});

app.post("/api/admin/pipeline/run", (req, res) => {
  const month = (req.query.month || "").toString().trim();
  if (!/^\d{4}-\d{2}$/.test(month)) {
    return res.status(400).send("month query param required (YYYY-MM)");
  }
  const force = req.query.force === "1";

  const args = ["run_pipeline.py", "--month", month];
  if (force) args.push("--force");

  res.set({
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });
  res.flushHeaders();

  const env = { ...process.env, PYTHONIOENCODING: "utf-8" };
  const child = spawn("python", args, { cwd: ML_DIR, env });

  const send = (event, data) => res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);

  child.stdout.on("data", (chunk) => {
    chunk.toString().split(/\r?\n/).filter(Boolean).forEach((line) => send("log", line));
  });
  child.stderr.on("data", (chunk) => {
    chunk.toString().split(/\r?\n/).filter(Boolean).forEach((line) => send("err", line));
  });
  child.on("close", (code) => {
    send("done", { code });
    res.end();
  });
  child.on("error", (e) => {
    send("err", `spawn error: ${e.message}`);
    res.end();
  });

  req.on("close", () => child.kill());
});

app.use(express.static(path.join(__dirname, "public")));

function tryLoadSqlite() {
  try {
    return require("better-sqlite3");
  } catch {
    return null;
  }
}

app.listen(PORT, () => {
  console.log(`SAC Classical Finder running at http://localhost:${PORT}`);
  console.log(`  data dir: ${DATA_DIR}`);
  console.log(`  admin: ${ADMIN_USER ? "enabled" : "disabled (set ADMIN_USER/ADMIN_PASS)"}`);
});

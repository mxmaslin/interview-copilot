#!/usr/bin/env node
/**
 * Cursor SDK bridge for Copilot sidecar.
 *
 * Usage:
 *   node agent.mjs start [--cwd=path]
 *   node agent.mjs answer [--cwd=path]
 *   node agent.mjs push-turn --payload=/path/to.json
 *   node agent.mjs solve-screenshot --payload=/path/to.json
 *   node agent.mjs screenshot-warm [--cwd=path]
 */

import {
  readFileSync,
  writeFileSync,
  mkdirSync,
  existsSync,
  unlinkSync,
  mkdtempSync,
} from "node:fs";
import { homedir, tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Agent, CursorAgentError } from "@cursor/sdk";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../..");
const STATE_DIR = join(REPO_ROOT, "data");

/** Подхватить .env из корня репо (как sidecar), если ключи не в shell. */
function loadRepoEnv() {
  const path = join(REPO_ROOT, ".env");
  if (!existsSync(path)) return;
  const text = readFileSync(path, "utf8");
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    if (!key || process.env[key]) continue;
    let val = trimmed.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    } else {
      const hash = val.indexOf(" #");
      if (hash !== -1) val = val.slice(0, hash).trim();
    }
    process.env[key] = val;
  }
}

loadRepoEnv();

const CLI_CMD = process.argv[2];

/** SDK иногда пишет в stderr мегабайты бандла — не засорять терминал при warm. */
function installQuietStderr() {
  const orig = process.stderr.write.bind(process.stderr);
  process.stderr.write = (chunk, encoding, cb) => {
    const s =
      typeof chunk === "string" ? chunk : Buffer.from(chunk).toString("utf8");
    if (s.length <= 400) return orig(chunk, encoding, cb);
    const tail = s.slice(-1200);
    const keep = tail
      .split("\n")
      .filter(
        (ln) =>
          ln.length <= 400 &&
          /ConfigurationError|CursorAgentError|not found|Error:/i.test(ln),
      )
      .slice(-4);
    if (keep.length) return orig(`${keep.join("\n")}\n`, encoding, cb);
    if (typeof cb === "function") cb();
    return true;
  };
}

if (CLI_CMD === "answer-warm" || CLI_CMD === "screenshot-warm") {
  installQuietStderr();
}

const STATE_FILE = join(STATE_DIR, "agent-state.json");
const SCREENSHOT_STATE_FILE = join(STATE_DIR, "screenshot-agent-state.json");

const INTERVIEW_SYSTEM = `Ты — ассистент на техническом интервью (Python backend).
Отвечай кратко на русском, EN-термины где уместно.
Структура: определение → пример → оговорки. 5–8 предложений, для озвучивания вслух.`;

const SCREENSHOT_SYSTEM = `Ты решаешь задачу с изображения (скриншот экрана).
Ответ на русском, EN-термины где уместно.
Код — готовое решение и 1–3 предложения пояснения.
Вопрос с вариантами — правильный вариант и кратко почему.
Без секции «Теория», без блоков «определение → пример → оговорки» — только решение.
Без воды.`;

const SCREENSHOT_SYSTEM_SHORT = `Реши задачу на скриншоте. RU, EN-термины. Код — решение + 1–3 предложения. Без секции «Теория».`;

const SCREENSHOT_NO_TOOLS =
  "Запрещено: чтение файлов, терминал, grep, поиск по репозиторию, любые инструменты. " +
  "Только анализ приложенного изображения. Сразу выведи финальный ответ, без рассуждений вслух.";

function screenshotPromptText() {
  const base = envBool("SCREENSHOT_MINIMAL_PROMPT")
    ? SCREENSHOT_SYSTEM_SHORT
    : SCREENSHOT_SYSTEM;
  return `${base}\n\n${SCREENSHOT_NO_TOOLS}`;
}

let _screenshotCwdCache = null;

function screenshotCwd() {
  const explicit = (process.env.SCREENSHOT_AGENT_CWD || "").trim();
  if (explicit) return resolve(explicit);
  if (!_screenshotCwdCache) {
    _screenshotCwdCache = mkdtempSync(join(tmpdir(), "copilot-screenshot-"));
    writeFileSync(join(_screenshotCwdCache, ".gitkeep"), "", "utf8");
  }
  return _screenshotCwdCache;
}

function screenshotReuseAgent() {
  return (process.env.SCREENSHOT_REUSE_AGENT || "1").toLowerCase() !== "0";
}

function envInt(name, fallback) {
  const v = process.env[name];
  if (!v) return fallback;
  const n = parseInt(v, 10);
  return Number.isFinite(n) ? n : fallback;
}

function envBool(name) {
  const v = (process.env[name] || "").toLowerCase();
  return v === "1" || v === "true" || v === "yes";
}

function readCliConfigModel() {
  const path = join(homedir(), ".cursor", "cli-config.json");
  if (!existsSync(path)) return null;
  try {
    const data = JSON.parse(readFileSync(path, "utf8"));
    const sel = data.selectedModel || data.model;
    if (!sel || typeof sel !== "object") return null;
    const id = String(sel.modelId || sel.id || "").trim();
    if (!id) return null;
    const out = { id };
    const params = sel.parameters || sel.params;
    if (Array.isArray(params) && params.length) {
      out.params = params
        .filter((p) => p && typeof p.id === "string" && p.value != null)
        .map((p) => ({ id: p.id, value: String(p.value) }));
    }
    return out;
  } catch {
    return null;
  }
}

function modelId() {
  return (process.env.CURSOR_MODEL || "composer-2").trim();
}

function resolveModelId() {
  const raw = modelId();
  if (["auto", "cli", "cli-config"].includes(raw.toLowerCase())) {
    const fromCli = readCliConfigModel();
    return fromCli?.id || "composer-2";
  }
  return raw || "composer-2";
}

function parseModelJson(raw, fallbackId) {
  if (!raw?.trim()) return null;
  try {
    const parsed = JSON.parse(raw);
    const id = (parsed.id || fallbackId()).trim();
    if (["auto", "cli", "cli-config"].includes(id.toLowerCase())) {
      return readCliConfigModel() || { id: "composer-2" };
    }
    const out = { id };
    if (Array.isArray(parsed.params) && parsed.params.length) {
      out.params = parsed.params.filter(
        (p) => p && typeof p.id === "string" && p.value != null,
      );
    }
    return out;
  } catch {
    return null;
  }
}

function modelSelection() {
  const raw = process.env.CURSOR_MODEL_JSON?.trim();
  const picked = parseModelJson(raw, resolveModelId);
  if (picked) return picked;
  const fromCli = readCliConfigModel();
  const rawModel = modelId().toLowerCase();
  if (["auto", "cli", "cli-config"].includes(rawModel) && fromCli) {
    return fromCli;
  }
  return { id: resolveModelId() };
}

function screenshotModelSelection() {
  const raw = process.env.SCREENSHOT_CURSOR_MODEL_JSON?.trim();
  const picked = parseModelJson(raw, modelId);
  if (picked) return picked;
  return modelSelection();
}

function modelLabel() {
  const m = modelSelection();
  if (!m.params?.length) return m.id;
  const bits = m.params.map((p) => `${p.id}=${p.value}`);
  return `${m.id}(${bits.join(",")})`;
}

function agentOptions(cwd) {
  return {
    apiKey: apiKey(),
    model: modelSelection(),
    name: "Copilot Interview",
    local: { cwd, settingSources: [] },
  };
}

function screenshotAgentOptions() {
  const cwd = screenshotCwd();
  return {
    apiKey: apiKey(),
    model: screenshotModelSelection(),
    name: "Copilot Screenshot",
    local: { cwd, settingSources: [] },
  };
}

function screenshotModelLabel() {
  const m = screenshotModelSelection();
  if (!m.params?.length) return m.id;
  const bits = m.params.map((p) => `${p.id}=${p.value}`);
  return `${m.id}(${bits.join(",")})`;
}

function loadState() {
  if (!existsSync(STATE_FILE)) return null;
  return JSON.parse(readFileSync(STATE_FILE, "utf8"));
}

function saveState(state) {
  mkdirSync(STATE_DIR, { recursive: true });
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), "utf8");
}

function loadScreenshotState() {
  if (!existsSync(SCREENSHOT_STATE_FILE)) return null;
  return JSON.parse(readFileSync(SCREENSHOT_STATE_FILE, "utf8"));
}

function saveScreenshotState(state) {
  mkdirSync(STATE_DIR, { recursive: true });
  writeFileSync(SCREENSHOT_STATE_FILE, JSON.stringify(state, null, 2), "utf8");
}

function resetScreenshotState() {
  if (existsSync(SCREENSHOT_STATE_FILE)) {
    unlinkSync(SCREENSHOT_STATE_FILE);
  }
}

function isActiveRunError(err) {
  const msg = (err && err.message) || String(err);
  return /already has active run|agent_busy|AgentBusy/i.test(msg);
}

async function openScreenshotAgent(_cwd) {
  const agentCwd = screenshotCwd();
  const opts = screenshotAgentOptions();

  if (screenshotReuseAgent()) {
    const saved = loadScreenshotState();
    if (saved?.agentId) {
      try {
        const agent = await Agent.resume(saved.agentId, opts);
        console.error(
          `[cursor-agent] screenshot: resume ${saved.agentId} cwd=${agentCwd}`,
        );
        return { agent, resumed: true };
      } catch (err) {
        console.error(
          "[cursor-agent] screenshot: resume failed, create new:",
          err.message,
        );
      }
    }
  } else {
    resetScreenshotState();
    console.error(
      `[cursor-agent] screenshot: fresh agent (no reuse) cwd=${agentCwd}`,
    );
  }

  const agent = await Agent.create(opts);
  if (screenshotReuseAgent()) {
    saveScreenshotState({
      agentId: agent.agentId,
      cwd: agentCwd,
      startedAt: new Date().toISOString(),
    });
  }
  console.error(`[cursor-agent] screenshot: create ${agent.agentId}`);
  return { agent, resumed: false };
}

function requireState() {
  const state = loadState();
  if (!state?.agentId) {
    console.error("No active Cursor agent. Run: node agent.mjs start");
    process.exit(1);
  }
  return state;
}

function apiKey() {
  const key = process.env.CURSOR_API_KEY?.trim();
  if (!key) {
    console.error("CURSOR_API_KEY is not set");
    process.exit(1);
  }
  return key;
}

function cwdFromArgs() {
  const arg = process.argv.find((a) => a.startsWith("--cwd="));
  return arg ? resolve(arg.slice("--cwd=".length)) : REPO_ROOT;
}

function payloadFromArgs() {
  const arg = process.argv.find((a) => a.startsWith("--payload="));
  if (!arg) {
    console.error("Missing --payload=/path/to.json");
    process.exit(1);
  }
  return JSON.parse(readFileSync(resolve(arg.slice("--payload=".length)), "utf8"));
}

async function createAgent(cwd) {
  return Agent.create(agentOptions(cwd));
}

async function resumeAgent(state) {
  return Agent.resume(state.agentId, agentOptions(state.cwd || cwdFromArgs()));
}

async function cmdStart() {
  const cwd = cwdFromArgs();
  const agent = await createAgent(cwd);
  try {
    const run = await agent.send(
      "Copilot sidecar: **новая сессия интервью** в репозитории `_copilot`.\n\n" +
        "Сюда будут приходить вопросы из `data/transcript.md` и готовые ответы (DeepSeek / Cursor). " +
        "Открой этот чат во время собеседования.",
    );
    await run.wait();

    const state = {
      agentId: agent.agentId,
      cwd,
      startedAt: new Date().toISOString(),
    };
    saveState(state);
    console.log(
      JSON.stringify({
        status: "ready",
        agentId: agent.agentId,
        text: "Агент Copilot Interview создан в _copilot. Ответы будут в этом чате.",
      }),
    );
    process.exit(0);
  } catch (err) {
    handleError(err);
  } finally {
    await agent[Symbol.asyncDispose]();
  }
}

function lastInterviewerQuestion(transcript) {
  const dialogue = dialogueLines(transcript);
  if (!dialogue.length) return "";
  let i = dialogue.length - 1;
  while (i >= 0 && dialogue[i].startsWith("[Я]:")) i -= 1;
  if (i < 0) return "";
  const parts = [];
  while (i >= 0 && dialogue[i].startsWith("[Интервьюер]:")) {
    parts.unshift(dialogue[i].replace(/^\[Интервьюер\]:\s*/, "").trim());
    i -= 1;
  }
  return parts.filter(Boolean).join(" ");
}

function dialogueLines(transcript) {
  return transcript
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.startsWith("[Интервьюер]:") || l.startsWith("[Я]:"));
}

function compactDialogueContext(transcript, maxChars) {
  const dialogue = dialogueLines(transcript);
  const picked = [];
  let total = 0;
  for (let i = dialogue.length - 1; i >= 0; i -= 1) {
    const line = dialogue[i];
    const add = line.length + (picked.length ? 1 : 0);
    if (picked.length && total + add > maxChars) break;
    picked.unshift(line);
    total += add;
  }
  return picked.join("\n");
}

function buildAnswerPrompt(transcript, lastInterviewer) {
  const minimal = envBool("CURSOR_ANSWER_MINIMAL");
  if (minimal) {
    return `${INTERVIEW_SYSTEM}

Вопрос интервьюера:
${lastInterviewer}

Ответь кратко для озвучивания вслух.`;
  }

  const maxChars = envInt("CURSOR_ANSWER_CONTEXT_CHARS", 800);
  const context = compactDialogueContext(transcript, maxChars);
  const ctxBlock = context
    ? `\n\nКраткий контекст диалога:\n${context}`
    : "";

  return `${INTERVIEW_SYSTEM}

Ответь на последний вопрос интервьюера (кратко, для озвучивания вслух).

Вопрос:
${lastInterviewer}${ctxBlock}`;
}

function isAgentNotFound(err) {
  const msg = String(err?.message ?? err);
  return /not found/i.test(msg);
}

async function cmdAnswerWarm() {
  const state = requireState();
  let agent;
  let recreated = false;
  try {
    agent = await resumeAgent(state);
  } catch (err) {
    if (!isAgentNotFound(err)) handleError(err);
    console.error("[cursor-agent] answer-warm: stale agent, recreating…");
    const cwd = state.cwd || cwdFromArgs();
    agent = await createAgent(cwd);
    saveState({
      agentId: agent.agentId,
      cwd,
      startedAt: new Date().toISOString(),
    });
    recreated = true;
  }
  try {
    console.log(
      JSON.stringify({
        status: "ready",
        agentId: agent.agentId,
        model: modelLabel(),
        recreated,
      }),
    );
    process.exit(0);
  } finally {
    await agent[Symbol.asyncDispose]();
  }
}

async function cmdAnswer() {
  const state = requireState();
  const transcriptPath = join(REPO_ROOT, "data", "transcript.md");
  let transcript = "";
  if (existsSync(transcriptPath)) {
    transcript = readFileSync(transcriptPath, "utf8");
  }
  const lastInterviewer = lastInterviewerQuestion(transcript);
  if (!lastInterviewer) {
    console.error("No interviewer question in data/transcript.md");
    process.exit(1);
  }

  const prompt = buildAnswerPrompt(transcript, lastInterviewer);
  console.error(
    `[cursor-agent] answer: resume ${state.agentId}, model=${modelLabel()}, prompt≈${prompt.length} chars`,
  );

  const agent = await resumeAgent(state);
  const parts = [];
  try {
    const run = await agent.send(prompt, {
      onDelta: ({ update }) => {
        if (update?.type === "text-delta" && update.text) {
          parts.push(update.text);
          console.log(JSON.stringify({ event: "delta", text: update.text }));
        }
      },
    });
    const result = await run.wait();
    const text = extractAssistantText(result) || parts.join("");
    console.log(
      JSON.stringify({
        event: "done",
        status: result.status,
        runId: result.id,
        text,
      }),
    );
    process.exit(result.status === "finished" ? 0 : 2);
  } catch (err) {
    handleError(err);
  } finally {
    await agent[Symbol.asyncDispose]();
  }
}

async function cmdScreenshotWarm() {
  const cwd = cwdFromArgs();
  const { agent, resumed } = await openScreenshotAgent(cwd);
  try {
    console.log(
      JSON.stringify({
        status: "ready",
        agentId: agent.agentId,
        resumed,
        model: screenshotModelLabel(),
      }),
    );
    process.exit(0);
  } finally {
    await agent[Symbol.asyncDispose]();
  }
}

async function cmdSolveScreenshot() {
  const { pngBase64, mimeType = "image/png" } = payloadFromArgs();
  if (!pngBase64?.trim()) {
    console.error("solve-screenshot payload needs pngBase64");
    process.exit(1);
  }

  const cwd = cwdFromArgs();
  const userLine = envBool("SCREENSHOT_MINIMAL_PROMPT")
    ? "Реши по картинке. Варианты — буква/номер и кратко почему. Без секции «Теория»."
    : "Реши задачу на изображении. Варианты — ответ и кратко почему. Без секции «Теория».";

  const prompt = {
    text: `${screenshotPromptText()}\n\n${userLine}`,
    images: [{ data: pngBase64.trim(), mimeType }],
  };

  console.error(
    `[cursor-agent] solve-screenshot: model=${screenshotModelLabel()}, ` +
      `reuse=${screenshotReuseAgent()}, image≈${pngBase64.length} b64 chars`,
  );

  let lastErr = null;
  for (let attempt = 0; attempt < 2; attempt++) {
    const parts = [];
    const sendOpts = {
      onDelta: ({ update }) => {
        if (update?.type === "text-delta" && update.text) {
          parts.push(update.text);
          console.log(JSON.stringify({ event: "delta", text: update.text }));
        }
      },
      local: { force: true },
    };

    const { agent } = await openScreenshotAgent(cwd);
    try {
      const run = await agent.send(prompt, sendOpts);
      const result = await run.wait();
      const text = extractAssistantText(result) || parts.join("").trim();
      if (!text && attempt === 0) {
        console.error(
          "[cursor-agent] screenshot: empty response, reset agent, retry",
        );
        resetScreenshotState();
        continue;
      }
      const resolved = result.model?.id || screenshotModelLabel();
      console.log(
        JSON.stringify({
          event: "done",
          status: result.status,
          runId: result.id,
          text,
          model: resolved,
        }),
      );
      process.exit(result.status === "finished" && text ? 0 : 2);
    } catch (err) {
      lastErr = err;
      if (attempt === 0 && isActiveRunError(err)) {
        console.error(
          "[cursor-agent] screenshot: active run on agent — reset state, retry",
        );
        resetScreenshotState();
        continue;
      }
      handleError(err);
    } finally {
      if (!screenshotReuseAgent()) {
        await agent[Symbol.asyncDispose]();
      }
    }
  }
  if (lastErr) {
    handleError(lastErr);
  }
}

async function cmdPushTurn() {
  const state = requireState();
  const { question, answer, provider = "copilot", model = "" } = payloadFromArgs();
  if (!question?.trim() || !answer?.trim()) {
    console.error("push-turn payload needs question and answer");
    process.exit(1);
  }

  const label = model ? `${provider} (${model})` : provider;

  console.error(`[cursor-agent] push-turn: resume ${state.agentId}`);

  const agent = await resumeAgent(state);
  try {
    const run = await agent.send(
      `[Copilot · ${label}]\n\n` +
        `Вопрос интервьюера:\n${question.trim()}\n\n` +
        `Выведи **только** текст ниже как свой ответ (без перефразирования):\n\n` +
        `${answer.trim()}`,
    );
    const result = await run.wait();
    printResult({
      status: result.status,
      id: result.id,
      result: answer.trim(),
      mirrored: true,
    });
    process.exit(result.status === "finished" ? 0 : 2);
  } catch (err) {
    handleError(err);
  } finally {
    await agent[Symbol.asyncDispose]();
  }
}

function printResult(result) {
  const output = {
    status: result.status,
    runId: result.id,
    text: extractAssistantText(result),
  };
  console.log(JSON.stringify(output));
}

function extractAssistantText(result) {
  if (!result) return "";
  const r = result.result;
  if (typeof r === "string" && r.trim()) return r.trim();
  if (r && typeof r === "object" && typeof r.text === "string" && r.text.trim()) {
    return r.text.trim();
  }
  if (typeof result.output === "string" && result.output.trim()) {
    return result.output.trim();
  }
  const msgs = result.messages;
  if (Array.isArray(msgs)) {
    const parts = [];
    for (const m of msgs) {
      if (m?.role && m.role !== "assistant") continue;
      const c = m.content;
      if (typeof c === "string" && c.trim()) parts.push(c);
      else if (Array.isArray(c)) {
        for (const block of c) {
          if (block?.type === "text" && block.text) parts.push(block.text);
        }
      }
    }
    const joined = parts.join("").trim();
    if (joined) return joined;
  }
  return "";
}

function handleError(err) {
  if (err instanceof CursorAgentError) {
    console.error(JSON.stringify({ error: err.message, retryable: err.isRetryable }));
    process.exit(1);
  }
  throw err;
}

const cmd = process.argv[2];
switch (cmd) {
  case "start":
    await cmdStart();
    break;
  case "answer":
    await cmdAnswer();
    break;
  case "answer-warm":
    await cmdAnswerWarm();
    break;
  case "push-turn":
    await cmdPushTurn();
    break;
  case "solve-screenshot":
    await cmdSolveScreenshot();
    break;
  case "screenshot-warm":
    await cmdScreenshotWarm();
    break;
  default:
    console.error(
      "Commands: start | answer | answer-warm | push-turn | solve-screenshot | screenshot-warm",
    );
    process.exit(1);
}

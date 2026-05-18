#!/usr/bin/env node
/**
 * Cursor SDK bridge for Copilot sidecar.
 *
 * Usage:
 *   node agent.mjs start [--cwd=path]
 *   node agent.mjs answer [--cwd=path]
 *   node agent.mjs push-turn --payload=/path/to.json
 *   node agent.mjs solve-screenshot --payload=/path/to.json
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Agent, CursorAgentError } from "@cursor/sdk";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../..");
const STATE_DIR = join(REPO_ROOT, "data");
const STATE_FILE = join(STATE_DIR, "agent-state.json");

const INTERVIEW_SYSTEM = `Ты — ассистент на техническом интервью (Python backend).
Отвечай кратко на русском, EN-термины где уместно.
Структура: определение → пример → оговорки. 5–8 предложений, для озвучивания вслух.`;

const SCREENSHOT_SYSTEM = `Ты решаешь задачу с изображения (скриншот экрана).
Ответ на русском, EN-термины где уместно.
Если на картинке задача на код — дай готовое решение (код + краткое пояснение).
Если теория — структура: определение → пример → оговорки.
Без воды, сразу к решению.`;

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

function modelId() {
  return (process.env.CURSOR_MODEL || "composer-2").trim();
}

function modelSelection() {
  const raw = process.env.CURSOR_MODEL_JSON?.trim();
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      const id = (parsed.id || modelId()).trim();
      const out = { id };
      if (Array.isArray(parsed.params) && parsed.params.length) {
        out.params = parsed.params.filter(
          (p) => p && typeof p.id === "string" && p.value != null,
        );
      }
      return out;
    } catch {
      /* fall through */
    }
  }
  return { id: modelId() };
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

function loadState() {
  if (!existsSync(STATE_FILE)) return null;
  return JSON.parse(readFileSync(STATE_FILE, "utf8"));
}

function saveState(state) {
  mkdirSync(STATE_DIR, { recursive: true });
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), "utf8");
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

function extractLastInterviewer(transcript) {
  const lines = transcript.split("\n").filter((l) => l.startsWith("[Интервьюер]:"));
  if (!lines.length) return "";
  return lines[lines.length - 1].replace(/^\[Интервьюер\]:\s*/, "");
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

async function cmdAnswer() {
  const state = requireState();
  const transcriptPath = join(REPO_ROOT, "data", "transcript.md");
  let transcript = "";
  if (existsSync(transcriptPath)) {
    transcript = readFileSync(transcriptPath, "utf8");
  }
  const lastInterviewer = extractLastInterviewer(transcript);
  if (!lastInterviewer) {
    console.error("No [Интервьюер] lines in data/transcript.md");
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

async function cmdSolveScreenshot() {
  const { pngBase64, mimeType = "image/png" } = payloadFromArgs();
  if (!pngBase64?.trim()) {
    console.error("solve-screenshot payload needs pngBase64");
    process.exit(1);
  }

  const cwd = cwdFromArgs();
  const prompt = {
    text:
      `${SCREENSHOT_SYSTEM}\n\n` +
      "Реши задачу на изображении. " +
      "Если это вопрос с вариантами — укажи правильный ответ и почему.",
    images: [{ data: pngBase64.trim(), mimeType }],
  };

  console.error(
    `[cursor-agent] solve-screenshot: model=${modelLabel()}, image≈${pngBase64.length} b64 chars`,
  );

  const agent = await createAgent(cwd);
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
    const resolved = result.model?.id || modelLabel();
    console.log(
      JSON.stringify({
        event: "done",
        status: result.status,
        runId: result.id,
        text,
        model: resolved,
      }),
    );
    process.exit(result.status === "finished" ? 0 : 2);
  } catch (err) {
    handleError(err);
  } finally {
    await agent[Symbol.asyncDispose]();
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
  if (result?.result && typeof result.result === "string") return result.result;
  if (result?.output && typeof result.output === "string") return result.output;
  return JSON.stringify(result);
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
  case "push-turn":
    await cmdPushTurn();
    break;
  case "solve-screenshot":
    await cmdSolveScreenshot();
    break;
  default:
    console.error("Commands: start | answer | push-turn | solve-screenshot");
    process.exit(1);
}

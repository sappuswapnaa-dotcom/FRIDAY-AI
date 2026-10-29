# FRIDAY AI — Intelligence in Motion

A real, local-first assistant foundation: Ollama inference, streamed chat, guarded workspace tools, a WebGL intelligence core, voice-input hooks, local document generation, and a small approval-gated Windows app launcher. This is runnable software, not a mock API. It is **an early, deliberately scoped build**, not the fully autonomous OS described in the master brief; the incomplete integrations are listed below.

## Quick start (Windows 10/11)

1. Install Python 3.11+ and [Ollama](https://ollama.com/download).
2. Open PowerShell and install a local model, for example:
   ```powershell
   ollama pull qwen2.5:7b
   ```
   Keep Ollama running. Pick a smaller model if your hardware is constrained.
3. Double-click `install_windows.bat` once, then `run_friday.bat`.
4. Open **http://127.0.0.1:8765**. Select the detected model in the chat header and send a prompt.

The app binds to loopback by default. The backend stores conversations in `data/friday.sqlite3` and restricts file operations to `user_files/`. Ollama URL, model default, workspace, and data paths can be overridden in `.env` (copy `.env.example` to `.env`). The launch scripts intentionally bind to loopback; this build has no user authentication or remote-access security layer.

## macOS / Linux / development

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
ollama pull qwen2.5:7b
uvicorn friday.app:app --app-dir backend --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`. Interactive API documentation is at `/docs`. Run tests with `pytest -q` from the project root.

## What's real in this build

- **Ollama only for LLM inference.** Discovers `/api/tags` models, allows model selection, streams `/api/chat` output, stores local conversation history, and reports actual connection/model errors. No response is fabricated when Ollama is down.
- **Guarded agent tools.** Ollama tool calls can list/read files in the private workspace. Creating files/folders requires the explicit “ALLOW FILE CREATION” checkbox for that request. Existing files are never overwritten by the tool. Path traversal is rejected.
- **Local artifacts.** Document Studio creates actual `.docx`, `.pptx`, `.xlsx`, `.pdf`, and `.md` files in `user_files/generated/`, checks that each output is non-empty, and offers a download. For PPTX, separate slide bodies with blank lines; first line is used as a heading. XLSX content lines are tab-separated.
- **Interactive WebGL core.** An original shader-driven, displaced 3D sphere and three animated orbit rings respond to genuine assistant states. It uses native WebGL to avoid a CDN/build dependency. A restrained dashboard remains usable if WebGL is unavailable.
- **Voice input (optional browser feature).** The UI uses the browser's `SpeechRecognition` implementation when available. Browser support and privacy behavior vary; some browsers may use remote speech services. Microphone access starts only after a user click. This build does not claim local speech recognition or provide speech synthesis/wake-word detection.
- **Windows launcher companion.** `windows_companion/friday_companion.py list` discovers Start Menu shortcuts and a short safe built-in app list. `python windows_companion\\friday_companion.py launch notepad` asks you to type `LAUNCH` before starting. It is a local CLI, not exposed as a network endpoint.

## Security boundaries

- Keep the browser app and Ollama bound to localhost. Do not port-forward either service or place this API on a public host. There is no authentication, TLS, multi-user isolation, CSRF defense, or remote pairing in this version.
- The agent cannot run shell commands, access arbitrary paths, or automate the desktop through its HTTP API. Its file scope is `FRIDAY_WORKSPACE` (default `user_files/`).
- The checkbox authorizes new workspace file/folder creation for one chat request; it does not approve external, financial, destructive, or system-level actions.
- The Windows launcher is a separately invoked CLI and prompts for confirmation. It does not inject keyboard/mouse input or elevate privileges.
- Generated code and documents are untrusted output. Inspect before running or sharing.

## Current limitations / not implemented yet

This build is a functional foundation, **not** the complete autonomous product. The following requested capabilities are not currently wired up: Windows accessibility/UIA automation, screenshot understanding, general mouse/keyboard control, browser automation, workflow planning with reliable rollback, task cancellation/progress ledger, full project-from-prompt generator and ZIP packaging UI, direct AI-to-document orchestration, local STT/TTS and wake word, image generation backend, auth/remote deployment, Three.js/React/GLSL/GSAP stack, and cross-device secure pairing. The Windows app launcher is a small CLI rather than the full companion. Ollama models differ in tool-call support; use a tool-capable model and check errors. No generated project is represented as production-ready.

## Layout

```text
backend/friday/       FastAPI, Ollama streaming, local SQLite, safe tools
frontend/             Offline-friendly browser UI, native WebGL core
windows_companion/    Opt-in confirmation-gated Windows app launcher
user_files/            FRIDAY's confined workspace (created at runtime)
data/                  Local SQLite store (created at runtime)
tests/                 Path-safety, API, and artifact smoke tests
```

## API

- `GET /api/health` — Ollama connectivity, available models, workspace
- `GET /api/models` — installed Ollama models
- `POST /api/chat` — SSE conversation stream; accepts `conversation_id`, `message`, optional `model`, `approve_workspace_writes`
- `GET /api/conversations` and `/api/conversations/{id}` — local history
- `GET /api/files?path=...` — confined workspace listing
- `POST /api/documents` — create and verify a local artifact
- `GET /api/download/{path}` — download a workspace file
- `GET /api/zip/{folder}` — create a transient download ZIP of a workspace folder

The ZIP endpoint does not save a second ZIP copy; it streams a ZIP response. The `/api/chat` endpoint streams model text and tool events as SSE.

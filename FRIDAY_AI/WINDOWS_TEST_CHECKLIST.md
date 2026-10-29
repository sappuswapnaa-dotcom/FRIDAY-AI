# Windows acceptance checklist

## Build-time verification

The build environment was Linux, with **no local Ollama installation or Windows desktop**. The following were verified here:

- Automated Python tests passed for path/URL restrictions, credential-like memory rejection, real DOCX/PPTX/XLSX creation, safe file operations, native and structured agent orchestration using **test doubles**, approval denial/cancellation, streamed event delivery with a **test double**, API Host/Origin checks and SQLite chat history. These tests do **not** demonstrate that any particular Ollama model can call tools.
- React/TypeScript production build succeeded. The dashboard was opened in a headless Chromium browser; navigation and local memory UI were exercised. The preview telemetry was read from the Linux sandbox, not a Windows PC.
- The real Playwright browser manager opened and read `https://example.com/` in headless Linux Chromium. Google search reached a CAPTCHA and was correctly reported unverified. YouTube did not produce verified results in that environment. No access control was bypassed.
- **Not verified here:** a live Ollama server/model, Windows application discovery/launch, Windows volume and UI Automation, real screenshot/OCR/vision, microphone/faster-whisper, Piper audio, a visible Windows Playwright session, and execution of the Windows batch files. Complete the checklist below on your own machine.

## On-device checks

Use a non-administrator Windows account and a disposable test folder. Start Ollama and the selected model before the tests. Confirm that any potentially sensitive approval shows the exact action before clicking **Approve**.

1. **Startup:** extract the ZIP, double-click `START_FRIDAY.bat`, explicitly approve any local dependency downloads, and verify the dashboard opens on `127.0.0.1:8765`. Stop Ollama and confirm the dashboard says it is offline with recovery instructions; restart it and check automatic recovery.
2. **Model detection:** pull at least one model in Ollama, refresh Settings, select it, and verify the selected name. Try a tool-capable model and, if available, a model without native tool support to exercise the validated fallback.
3. **Chat/context:** ask a question, send a follow-up that relies on it, and verify the actual answer is streamed. Restart and reopen the saved conversation. No response should appear if Ollama is unavailable.
4. **Notepad:** ask `Open Notepad`. Confirm a real Notepad process/window appears and compare the log's exact verification wording.
5. **Chrome:** ask `Open Chrome`. Verify a Chrome process/window appears. Test an uninstalled app and confirm a clear not-found or unverified result rather than a fake success.
6. **YouTube/open website:** ask FRIDAY to open YouTube in Playwright. Check the visible separate browser, URL and page. Resolve any normal consent/login page yourself.
7. **Search:** request Google and YouTube searches. Confirm actual query entry and result titles/links. If a CAPTCHA or consent screen occurs, confirm FRIDAY reports the result unverified and does not bypass it.
8. **Text file:** request creation of a small text file in the workspace and inspect its contents and verified receipt. Ask to create it again; deny overwrite and confirm the original is unchanged. Approve it on a second attempt and confirm the correct contents.
9. **Folder:** request a new `Projects` folder in the workspace and check it exists. Try an out-of-root path and confirm it is blocked.
10. **Voice input:** install the optional faster-whisper package and local model as documented. Grant microphone permission, record a short command, check the transcript, and send it. Test opt-in auto-submit and the one-command “Hey Friday” session separately. Stop the microphone and confirm listening ceases.
11. **Voice output:** install a Piper executable plus matching ONNX/JSON voice, select it, enable responses and hear a generated reply. Test mute, speed and interruption. Browser default voices may not be offline.
12. **History/memory:** create a conversation, restart FRIDAY, reopen it. Add, edit and delete a non-secret memory. Confirm an obvious `password=...` memory is rejected; do not use a real secret.
13. **Task plan:** request a harmless multi-step task, such as create a folder and a text file inside it. Review the plan and live receipts. Confirm the model handles errors instead of inventing success.
14. **Task execution:** ask for a research-to-PowerPoint workflow, review any outbound-navigation approvals, inspect collected content and open the generated `.pptx`. If research is blocked, confirm it does not claim the presentation contains verified research.
15. **Approvals:** attempt a screenshot, overwrite, move, browser form/click, upload or download. Confirm each is blocked pending approval. Deny one and verify no corresponding action. If the target page/element changes after approval, confirm the click is rejected.
16. **Screen capture/OCR/vision:** explicitly approve a screenshot and inspect the saved PNG. If Tesseract is installed, test OCR. If an image-capable Ollama model is installed, test vision and treat the description as fallible. With components missing, expect an informative error.
17. **System monitoring:** compare CPU/RAM/battery values against Windows Task Manager and battery settings. Network indicates an interface, not tested internet connectivity.
18. **Cancellation and pause:** start a long workflow, pause and resume between steps, then stop one while awaiting approval. Verify no denied/pending action runs. An operation already dispatched may finish; inspect the log and machine.
19. **Error recovery:** unplug the network for a web search, request a nonexistent file, and stop Ollama during a request. Confirm clear errors, bounded behavior, no fabricated completion, and a usable dashboard after restoring prerequisites.
20. **Stop/start:** double-click `STOP_FRIDAY.bat`; verify the dashboard server and its separate Playwright browser close while unrelated applications/Ollama remain. Restart FRIDAY and inspect persisted logs and schedules.

Also verify a reminder while FRIDAY is open, optional browser notification permission, daily schedule pause/resume, and behavior after an offline period. Schedules are not a Windows service. Do not use real payments, accounts or confidential files in the initial tests.

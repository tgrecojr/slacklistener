# Remaining Improvements

Items identified during code review that can be addressed iteratively.

## Security

### Prompt Injection Guardrails
- **File:** `src/handlers/message_handler.py`, `src/handlers/command_handler.py`
- **Issue:** User-supplied Slack messages are passed directly to the LLM with no sanitization. Malicious users could craft messages that attempt to override the system prompt.
- **Suggestion:** Add basic guardrails such as logging/flagging messages that contain phrases like "ignore previous instructions" or similar injection patterns.

### Broad Exception Catching
- **Files:** `src/app.py:42`, `src/handlers/message_handler.py:134`, `src/llm/openrouter.py:145`
- **Issue:** Multiple `except Exception` blocks catch all exceptions broadly, including `SystemExit` and `KeyboardInterrupt`.
- **Suggestion:** Catch more specific exceptions, or at minimum re-raise `SystemExit` and `KeyboardInterrupt`.

## Performance

### Linear Channel Config Lookup
- **File:** `src/handlers/message_handler.py:_get_channel_config`
- **Issue:** Iterates through all channels for every message. Fine for small configs but O(n).
- **Suggestion:** Build a dict keyed by `channel_id` at init time for O(1) lookup.

### Import Inside Loop
- **File:** `src/tools/implementations/openweathermap.py:154`
- **Issue:** `from datetime import datetime` is inside the for loop in `_format_weather_data`.
- **Suggestion:** Move the import to the top of the file.

## Error Handling

### Silent Failure on Image Download
- **File:** `src/utils/slack_helpers.py:56-58`
- **Issue:** When image downloads fail, the bot proceeds without the image. Users get no indication their image was not processed.
- **Suggestion:** Consider adding a reaction or brief message indicating image download failure when `require_image=false`.

### Unused Closure Variable
- **File:** `src/app.py:97-103`
- **Issue:** `_cmd` is captured in the `make_handler()` closure but never used inside `handler()`. The closure capture is dead code.
- **Suggestion:** Remove the unused `_cmd` variable.

### Text Truncation at Hard Boundary
- **File:** `src/utils/slack_helpers.py:162`
- **Issue:** `format_slack_text` truncates at a hard character offset, potentially mid-word.
- **Suggestion:** Find the last space or newline before the cutoff point to truncate at a word boundary.

## Infrastructure

### No Rate Limiting
- **Issue:** The bot processes all matching messages without any rate limiting. A busy channel could generate many concurrent LLM calls.
- **Suggestion:** Add per-channel or global rate limiting (e.g., max N requests per minute).

### Docker Compose Version Deprecated
- **File:** `docker-compose.yml:1`
- **Issue:** `version: '3.8'` is deprecated in modern Docker Compose. The `version` key is now ignored.
- **Suggestion:** Remove the `version` key.

### Health Check is a No-Op
- **File:** `Dockerfile:42-43`
- **Issue:** The health check (`python -c "import sys; sys.exit(0)"`) only checks if Python is available, not if the app is actually running and connected to Slack.
- **Suggestion:** Implement a health check that verifies the Slack connection is active (e.g., write a PID file or check socket mode status).

### Bad Exception Order in OpenRouter Client
- **File:** `src/llm/openrouter.py`
- **Issue:** pylint reports `bad-except-order` -- `APIConnectionError` is an ancestor of `APITimeoutError`, so the timeout handler is unreachable.
- **Suggestion:** Swap the order so `APITimeoutError` is caught before `APIConnectionError`.

# AgentCore Gateway — OpenAPI targets (Phase P4.2)

Expose Google Sheets and Twilio as MCP tools via AgentCore Gateway. Spec: `IMPLEMENTATION_PLAN.md` §8.7.

## Requirements for each OpenAPI target
- Every operation to expose needs an `operationId` (becomes the MCP tool name).
- `servers` must be the real endpoint (`https://sheets.googleapis.com/...`, `https://api.twilio.com/...`).
- JSON only; `oneOf`/`anyOf`/`allOf` are NOT supported.
- Auth is configured OUTSIDE the spec via **AgentCore Identity**:
  - Google Sheets → built-in **Google OAuth 2.0** provider (3-legged).
  - Twilio → **API-key** credential provider.

## Files to add here in P4.2
- `sheets_openapi.json` — trimmed Sheets API spec (only the operations Steward uses: read range, update range, append).
- `twilio_openapi.json` — trimmed Twilio spec (send SMS).
- `create_gateway.py` — creates the Gateway + targets + attaches Identity providers.

## MVP note (§16 D1)
Until P4, Sheets/Twilio run as local Strands `@tool`s (`app/tools/`). Migrate to Gateway for the depth story.
Skip semantic tool search for MVP (only ~a dozen tools; it costs 5× a normal invocation — §12).

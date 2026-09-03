# Patches we carry on our LiteLLM fork

Everything below lives only on our fork; none of it is in the upstream open source release we build from. It is now collapsed into a single commit on `main-pitchbook` so the whole delta replays as one unit each time we pull a new upstream version

| | |
| --- | --- |
| Upstream base | v1.100.0 |
| Fork commits | 3 |
| Files touched | 108 |
| Lines changed | 8,075 (43% tests) |

## Agentic coding clients on the proxy

The largest group. Upstream's Anthropic-compatible `/v1/messages` endpoint is good enough for simple chat, but it falls over on the traffic that agentic coding clients actually send, which is what our developers point at the proxy. Each of these was a hard failure for a real user before the patch

**Web search.** Requests carrying Anthropic's hosted `web_search` tool were rejected with a 400. We now route those requests to the provider's Responses API, translate the results back into Anthropic-native `web_search_tool_result` content blocks, and assemble the block from the completed search event so the citations and result URLs the client renders are the real ones

**Hosted tool and tool-result handling.** Anthropic-only server tools and their metadata were being forwarded verbatim into OpenAI-shaped requests, which the backends reject. We strip them at the bridge, drop a dangling `tool_choice` that would otherwise name a removed tool, and guarantee one tool message per tool result so multi-tool turns stay aligned

**Empty streaming chunks.** A stream whose first chunk carried no choices (Azure's content-filter annotation and usage chunks) raised an IndexError and killed the request while the provider had already billed the tokens. Guarded in the stream wrapper and the chunk builder. The sibling fix for truncated non-streaming responses went home in v1.99.0, which now maps `incomplete` responses to a `length` finish reason itself

**Reasoning passthrough for OpenAI-compatible backends.** Backends that stream `reasoning_content` deltas (Model Garden's OpenAI-compatible route) had them dropped on the floor, and in-band errors mid-stream were silently swallowed; both now surface to the client

Touches `litellm/llms/anthropic/**`, `litellm/llms/openai_like/**` and `litellm/litellm_core_utils/streaming_*`

## GPT-5.6 family enablement

The upstream release predates the model family we run in production, so the proxy neither priced it nor routed it correctly

**Pricing entries.** Added the full GPT-5.6 set, including the three named variants and their regional Azure deployments, plus the dated aliases clients pin to. Without these the proxy prices requests at zero and our spend dashboards under-report

**Tool calls routed to the Responses API.** This family rejects tool definitions on the older chat endpoint because the provider applies a reasoning default server side. Upstream now bridges these requests itself, scoped a little differently: it fires for gpt-5.4 and up whenever reasoning is active and the endpoint is one that enforces the constraint, and it leaves custom (grammar) tools on chat. We kept only the version detection, which matches a version anywhere in a deployment name so our custom Azure deployment names are recognized

**Availability probes on Azure.** Coding clients probe a deployment with a one-token request. Azure answers that with a 400 rather than an empty response, which made every Azure GPT-5 deployment look unreachable and broke model pickers. We floor the budget at the smallest value Azure accepts

## Spend accuracy

Three separate ways the proxy was reporting the wrong number. All of them affect chargeback, so they matter beyond the proxy itself

**Cache writes billed at zero.** When a model declares no explicit cache-write price, upstream charged nothing for those tokens. Providers charge for them. We now fall back to the input rate, and we declared the correct 1.25x cache-write price on the Azure GPT-5.6 entries

**Faked Responses streams billed zero.** A Responses API terminal event coming out of an iterator that fakes a stream never set the `stream` flag, so the cost block skipped it and logged spend=0. Terminal events now unwrap and cost regardless of the flag

**Failed requests missing their model.** Budget rejections happen before routing, so neither the error message nor the Logs UI told anyone which model was refused. Both are now filled in from the same resolver the budget check itself uses, including routes that carry the model in the URL path

Touches `litellm/cost_calculator.py`, `llm_cost_calc/utils.py`, `hooks/proxy_track_cost_callback.py`

## Budget controls

**Per-model budget exemption.** Admins can mark a model so that requests to it are admitted even when the caller is over budget; spend is still tracked, only the pre-call gate is relaxed. This is how we keep zero-cost and internally subsidised models usable when a team has exhausted its allowance. The exemption resolves through team aliases, wildcard routes and configured fallbacks, so it holds for the model the request will actually land on, and it is honoured in both the auth path and the budget hook that runs after it

**Team member spend reset.** A per-team member budget could only be cleared by waiting out the cycle or raising the limit. Upstream now owns the endpoint itself, so what we carry is the validation, the guard against an admin resetting their own spend, the cross-pod cache invalidation and the Members-tab button that calls it

## Vertex Model Garden coding models

Self-deployed Qwen, GLM and Gemma endpoints served through Vertex's OpenAI-compatible surface, pointed at by coding clients over /v1/messages

**System message merging.** These deployments reject any request with more than one system message, or one that is not first, with "System message must be at the beginning", and Claude Code sends hook output as a mid-turn `system` entry. Every system message is folded into a single leading one, on both the partner-models dispatch and the model garden route

**Template thinking off by default.** Qwen chat templates think unless told otherwise, burning tokens on requests where the client never asked for reasoning. When a request reaches a Qwen deployment without thinking or reasoning_effort enabled, the bridge sets `chat_template_kwargs.enable_thinking: false` in extra_body. Verified straight against the model server, no gateway in the path: on the Qwen 3.8 endpoint in pb-ai-enablement-dev (vLLM, `--reasoning-parser=qwen3`) that kwarg takes a one-word answer from 59 completion tokens down to 2, and the top-level `enable_thinking` copy we used to send alongside it changes nothing, so it is gone

GLM is deliberately excluded, because no working switch exists for it. Against the GLM 5.3 Flash endpoint (SGLang, `--reasoning-parser=glm45`, `zai-org/GLM-5.3-Flash`), `chat_template_kwargs.thinking: false` is inert, reasoning still runs and is still separated. `enable_thinking: false` is worse than inert: the model reasons regardless, but the template stops emitting the `<think>` prefill the parser keys on, so the reasoning lands in `content` with a stray `</think>` and `reasoning_content` comes back empty. The bridge then has no reasoning to map and returns one text block holding reasoning, the stray tag and the answer. Clients reading that block under a tight max_tokens, Claude Code auto mode's classifier among them, truncate mid-reasoning and fail closed. Sending GLM nothing keeps reasoning separated and lets the bridge emit a proper thinking block

## Model discovery and access groups

Which models a caller sees from `/v1/models` drives what appears in every client's model picker, and it was not matching what access groups actually grant

Access groups gained a separate list of models to advertise, so a group can grant access to a model without cluttering every user's picker with it. Upstream has since wired team access groups into the listing itself, but only to widen a restriction that already exists, so we still carry the rule that a team with an access group and an empty model list is bounded by what that group advertises rather than falling through to every proxy model. We also stopped a sentinel value used to mean "no defaults" from leaking into the response as if it were a real model, and deduplicated entries that arrived through both a wildcard and a concrete name. Ships with a `schema.prisma` migration and the matching dashboard changes to the access group create/edit forms and model info view

## Hardening and platform

**Key generation exemption.** Following an upstream advisory, the session-token exemption during key generation keys off what the caller explicitly requested. We extended that to the team field as well, so a personal key whose team was auto-filled from config defaults cannot slip through the exemption

**Streaming parser guards.** Two providers can emit chunks with no choices; both paths raised an index error and dropped the stream. Guarded, with regression tests

**Build and operations.** A GitHub Actions workflow builds and publishes our fork image from this branch with datetime-stamped tags, a Grafana dashboard covers background-job health so a stalled budget reset is visible, and there are local container definitions for pointing the two agentic CLIs at a dev proxy

## Where this leaves us

Roughly 40% of the delta is tests, which is what makes the rebase tractable: after each upstream pull the suite tells us immediately if a patch has been made redundant or has broken against new code

Most of these are general bug fixes rather than anything specific to us, so they are candidates to send upstream; every patch that lands upstream is one we stop carrying. The exceptions likely to stay local are the fork build workflow, the local dev containers, and the model pricing entries, which upstream will publish on its own schedule

The main standing risk is drift in the Anthropic pass-through layer, where our changes are deepest and upstream is most active. That is the area to watch on each version bump

## Rebase notes, v1.99.1 to v1.100.0

Upstream took over the Responses API retrieval billing question and did it more carefully than we did. Our patch zeroed every `get_responses` / `aget_responses` call outright; upstream now zeroes reads and management calls by default but still prices the two cases that carry the only billable usage a job ever has, a background poll and a read of a finished background response. Our blanket zero broke both, so the patch and its regression test are gone and upstream's gate stands

The team member spend reset endpoint came home in shape but not in substance. Upstream ships `POST /team/{team_id}/member/{user_id}/reset_spend`, so our `POST /team/member_reset_spend` route and its request and response models were dropped and the dashboard now calls the upstream path. The validation, the guard against an admin resetting their own spend and the cross-pod cache invalidation stayed ours, re-seated on upstream's handler signature

The rest was conflict reconciliation in the usual places. The Anthropic pass-through chat adapter took upstream's `_tool_result_content` helpers, which cover text, image and document, retiring ours; the Responses-to-Anthropic streaming iterator and the messages handler absorbed upstream's rewrites around our routing hook; and pricing was merged field by field again, defaulting to upstream on genuine conflicts so its corrected priority-tier costs on the regional GPT-5.6 entries survived alongside our fork-only aliases

## Rebase notes, v1.96.0 to v1.97.0

Upstream rewrote large parts of the Anthropic pass-through adapters, the `/v1/models` listing path and the gpt-5 bridge in this release, so most of the conflict work was reconciling our patches with those rewrites rather than replaying them

Three patches came home. Upstream now bridges gpt-5.4+ tool calls to the Responses API on its own, with a tighter rule than ours, so we dropped our bridge condition and the test that pinned the older families to chat; it also feeds team access groups into the model listing, so we kept only the `listed_model_names` override on top of its structure; and it took over the zero-cost budget skip inline in the auth path, which our budget-exemption helper already subsumed

Two of ours had to absorb upstream changes rather than replace them. Upstream started carrying a `snippet` alongside each synthesized web search result, so the shared result block builder we introduced now carries one too; and upstream corrected the terra and luna price entries downward, so the cache-write prices we derive at 1.25x input were recomputed off the corrected numbers instead of being replayed at the old ones

## Rebase notes, v1.97.0 to v1.98.0

Conflicts were again concentrated in the Anthropic pass-through adapters, plus the access group create flow and the budget reset job, all of which upstream rewrote

Two patches came home. Upstream replaced the nightly reset job with a transactional cascade that already advances `budget_reset_at` only after the linked spend is zeroed, so our ordering fix and its tests are gone; and upstream added its own image handling to the chat adapter's tool_result path, which we took in place of ours, keeping only the guarantee that every tool result still emits exactly one tool message

One patch had to be re-seated. Upstream replaced the access group create modal with a new dialog, so the `listed_model_names` field was ported onto its form, schema and request mapper rather than replayed on the deleted file. Our cache-write fallback was also narrowed to fire only when no write price resolves at all, since upstream now carries cache-creation prices inside tiered pricing entries where the top-level field is absent by design

## Rebase notes, v1.99.0 to v1.99.1

Nothing to re-seat. The upstream release was a backport of OTel cache payload changes plus a lock refresh, touching only `litellm/integrations/otel/**`, `pyproject.toml` and `uv.lock`, none of which our patches go near, so the whole delta replayed clean

## Rebase notes, v1.98.0 to v1.99.0

The big upstream event this cycle was the dashboard moving from antd to shadcn and react-hook-form, which deleted every antd surface our UI patches sat on. The `listed_model_names` field was re-seated onto the new access group base form and edit modal (upstream ships the create dialog and the details page tab with the field already wired), the skip-budget-checks switch onto the new add-model advanced settings and the extracted `ModelInfoEditForm`, and the team member spend reset onto the rewritten `TeamInfo` with a shadcn dialog in place of the antd modal

One patch came home. Upstream now maps incomplete Responses API responses to a `length`/`content_filter` finish reason itself, as a superset of ours: it also keys off `status == "incomplete"` and overrides the finish reason on partial content, so `_choices_for_empty_output` and its call site are gone. The streaming empty-choices guards stay ours

Two patches were reconciled against upstream rewrites of the same file. Upstream restructured the Responses-to-Anthropic streaming iterator around an `_open_block` helper that opens thinking blocks lazily on the first non-empty reasoning delta; the web search machinery was re-seated on that structure and our eager thinking-block-open was dropped in its favor, since it emitted empty thinking blocks upstream now deliberately avoids. Upstream also added document support to the chat adapter's tool_result path, which our always-emit helpers absorbed by treating `document` like `image`, retiring the regression params that pinned documents as unrenderable

Pricing was merged field by field. Upstream corrected `max_input_tokens` on the azure GPT-5.6 entries and cut the OpenAI GPT-5.6 prices while leaving azure at the old rates, so the dated aliases were rebuilt from the corrected entries with our cache-write prices on top, and the test asserting azure bills identically to OpenAI became one asserting azure resolves its declared 1.25x write price. Upstream now also ships cache-creation prices on the OpenAI GPT-5.6 entries, vindicating the 1.25x approach but keeping the azure declarations ours to carry

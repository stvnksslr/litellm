# Fork patch manifest (delta vs upstream v1.106.6, `v1.106.6..HEAD`)

Line numbers are as of the current `main-fork` tip. For modified files they are diff-hunk ranges (`git diff v1.106.6..HEAD --unified=0`); for added files `L1-L<n>` is the full file. 115 files, +8,768 / -211, roughly 63% tests

## Agentic coding clients on the proxy (/v1/messages bridge)

- `litellm/llms/anthropic/pass_through/adapters/transformation.py` L11, L123, L140-L148, L240-L254: import upstream `drop_non_python_regex_patterns` and the tool_search helpers; `_model_supports_web_search_options` gates web_search_options reduction
- `litellm/llms/anthropic/pass_through/adapters/transformation.py` L827-L840, L870: pass `defer_loading` through tool translation; drop hosted tools; sanitize tool input_schema via upstream `drop_non_python_regex_patterns` (upstream only applies it inside `OpenAIGPTConfig` for provider `openai`, so hosted_vllm / Model Garden targets of the bridge need this call)
- `litellm/llms/anthropic/pass_through/adapters/transformation.py` L1105-L1125: forward deferred tools only when a tool_reference names them (or server-side search requested); web_search tool becomes `web_search_options` when model supports it
- `litellm/llms/anthropic/pass_through/adapters/transformation.py` L491-L492, L559, L1274-L1296, L1345-L1357: tool_reference blocks in messages expand to `<functions>` via `_tool_result_content`
- `litellm/llms/anthropic/pass_through/adapters/transformation.py` L307, L1257-L1264, L1290-L1292, L1366, L1377: expansion is opt-in via `emulate_tool_search`, set only by the bridge; write-back callers (guardrails, shadow eval) keep upstream's `tool_reference` passthrough
- `litellm/llms/anthropic/pass_through/adapters/transformation.py` L1462-L1492: `_count_openai_tool_calls`; one tool message per tool result
- `litellm/llms/anthropic/pass_through/adapters/transformation.py` L1626-L1641: compaction-block insertion; truncated tool calls map to `max_tokens` finish reason
- `litellm/llms/anthropic/pass_through/adapters/tool_search.py` L1-L79: new, tool-search emulation; reference extraction, `forwards_tool`, `expand_tool_references` building the `<functions>` block
- `litellm/llms/anthropic/pass_through/adapters/handler.py` L14-L33: import classifier + reasoning overrides and hosted-tool filter
- `litellm/llms/anthropic/pass_through/adapters/handler.py` L554-L570: strip Anthropic hosted tools from forwarded tools; drop dangling `tool_choice`/`parallel_tool_calls` when tools emptied. This is the only hosted-tool filter on the chat path, so the Responses bridge in `completion_extras` never sees them
- `litellm/llms/anthropic/pass_through/adapters/handler.py` L612-L617: apply model-garden reasoning overrides then GLM classifier overrides before routing
- `litellm/llms/anthropic/pass_through/messages/handler.py` L10-L40, L77-L114, L124-L147: `_declares_responses_endpoint` / `_deployment_supports_responses_api` from model_info, base_model or model cost
- `litellm/llms/anthropic/pass_through/messages/handler.py` L117-L119, L611-L649: thread `model_info` into `_should_route_to_responses_api` routing hook
- `litellm/llms/anthropic/pass_through/responses_adapters/transformation.py` L9-L117, L713-L745, L764-L846: hosted web-search helpers (`as_responses_item_mapping`, `web_search_call_query`, `_url_citations`); `translate_response` keeps upstream's output loop and adds a `web_search_call` branch emitting server_tool_use -> web_search_tool_result, with url citations from the final message attached to the last search result
- `litellm/llms/anthropic/pass_through/responses_adapters/transformation.py` L457-L496, L648-L659: translate web_search tool to Responses `web_search`; Responses-API `tool_choice` conversion using translated tool list
- `litellm/llms/anthropic/pass_through/responses_adapters/streaming_iterator.py` L18-L40, L146-L149: web-search imports and state on the wrapper
- `litellm/llms/anthropic/pass_through/responses_adapters/streaming_iterator.py` L198-L249, L322-L325, L431-L433, L497: record search sources from citations; queue `server_tool_use` + paired `web_search_tool_result` blocks, the latter at response completion
- `litellm/llms/anthropic/common_utils.py` L8-L9, L54, L56: imports for web-search result types
- `litellm/llms/anthropic/common_utils.py` L108-L165: new `AnthropicWebSearchResult`, `web_search_result_from_source`, `build_anthropic_web_search_tool_result_block` shared by interception callback and Responses bridge
- `litellm/types/llms/anthropic.py` L1, L5, L659-L688: new `AnthropicResponseContentBlockServerToolUse`, `AnthropicWebSearchResultBlock`, `AnthropicResponseContentBlockWebSearchToolResult` models
- `litellm/types/llms/anthropic.py` L786-L810: `is_anthropic_hosted_tool_type` and `is_anthropic_web_search_tool` predicates, used by the bridge handlers, the Responses adapter and shadow eval (the chat adapter keeps upstream's `_is_web_search_tool`)
- `litellm/integrations/shadow_eval_logger.py` L43, L407-L409: hosted web search detection also matches the raw Anthropic tool via `is_anthropic_web_search_tool`, since the bridge only emits `web_search_options` for models that support it and shadow eval would otherwise sample and bill those requests
- `litellm/litellm_core_utils/streaming_handler.py` L2107-L2112: guard choice-less chunks in `response_uptil_now` accumulation on the non-aiohttp async path. No fork test covers it
- `litellm/llms/anthropic/pass_through/adapters/streaming_iterator.py` L598-L601, L837-L840, L1144, L1156-L1157: while a tool_use block is open, skip whitespace-only text chunks. Qwen streams `"\n"` between parallel tool calls before the previous call's closing `}`, which used to open a nameless tool_use that every later Claude turn on that history rejects
- `litellm/llms/anthropic/common_utils.py` L1939-L2025: `repair_nameless_tool_use_blocks_in_anthropic_messages` heals histories already poisoned by that bug. A nameless tool_use is dropped with its tool_result in the next user turn, or renamed `unknown_tool` when dropping would empty either message
- `litellm/llms/anthropic/pass_through/messages/utils.py` L10, L147-L149: `prepare_native_messages` runs the repair after tool_use id normalization. Upstream v1.106.0 consolidated both sanitize pipelines of `messages/handler.py` into that function, so native Vertex/Anthropic pass-through and the bridges all get it
- `litellm/litellm_core_utils/prompt_templates/factory.py` L2877-L2881: `anthropic_messages_pt` runs the same repair, covering OpenAI-format clients replaying a tool call with an empty `function.name`
- `litellm/llms/openai_like/chat/handler.py` L19-L22, L70-L72, L110-L112: stream via `OpenAIChatCompletionStreamingHandler` so `reasoning_content` deltas and mid-stream errors surface

## GPT-5.6 family enablement

- `litellm/llms/openai/chat/gpt_5_transformation.py` L15, L118, L123, L127: upstream's `_GPT_SERIES_VERSION` unanchored and applied with `search`, so `gpt-<major>.<minor>` is found anywhere in a custom deployment name; `is_model_gpt_5_2/5_4` reuse `_gpt_series_version`
- `litellm/llms/azure/chat/gpt_5_transformation.py` L14-L22, L99, L107-L119: floor `max_completion_tokens` at 3 (`AZURE_GPT5_MIN_COMPLETION_TOKENS`) so one-token availability probes get empty-with-`length` instead of 400

## Spend accuracy

- `litellm/proxy/hooks/proxy_track_cost_callback.py` L30, L265-L279, L369-L374: `_resolve_failure_log_model` fills model on failed spend logs from `get_model_from_request` route resolver
- `litellm/proxy/auth/auth_exception_handler.py` L25-L35, L133-L161, L217-L219: `_append_requested_model_to_budget_error` appends requested model to BudgetExceededError message

## Budget controls

- `litellm/proxy/auth/auth_checks.py` L156, L631-L645, L689-L864: `_get_deployments_for_model` (aliases, wildcard routes), `_is_model_budget_exempt` (`model_info.skip_budget_checks` on all deployments), request-model resolution, fallback-target reachability, `should_skip_budget_checks_for_model`
- `litellm/proxy/auth/auth_checks.py` L4679-L4736: `_get_listed_models_from_access_groups` (see Model discovery)
- `litellm/proxy/auth/user_api_key_auth.py` L80, L1882-L1887, L2374-L2380, L3106, L3924-L3929: call `_should_skip_budget_checks` with `valid_token` in the JWT, virtual-key, centralized common-checks and custom-auth paths, replacing the inline zero-cost checks
- `litellm/proxy/auth/user_api_key_auth.py` L3282-L3302: `_should_skip_budget_checks` derives `team_id` from `valid_token` for upstream's team-scoped model resolution and passes request `fallbacks` (validated list only) into `should_skip_budget_checks_for_model`
- `litellm/proxy/auth/fallback_budget.py` L43, L114-L116: upstream's router-time fallback budget check also admits `skip_budget_checks` targets, so an exempt fallback is not refused for an over-budget caller

## Vertex Model Garden coding models

- `litellm/litellm_core_utils/prompt_templates/common_utils.py` L14, L1968-L2003: `merge_system_messages_to_front` folds all system messages into one leading message
- `litellm/llms/vertex_ai/vertex_ai_partner_models/main.py` L6-L15, L224-L226: merge system messages on partner-models dispatch
- `litellm/llms/vertex_ai/vertex_model_garden/main.py` L20-L28, L128-L130: merge system messages on model garden route
- `litellm/llms/vertex_ai/vertex_model_garden/transformation.py` L1-L13: new `VertexAIModelGardenOpenAIConfig`, declares `reasoning_effort` on top of `VertexAILlama3Config`
- `litellm/utils.py` L4495-L4507: drop `stream_options` in `pre_process_non_default_params` unless `stream is True`; keeps only what upstream's `normalize_responses_api_stream_options` forwards so the Responses bridge contract holds
- `litellm/utils.py` L8902-L8907: `ProviderConfigManager` returns model-garden config for `openai/` Vertex prefix, which `get_supported_openai_params` picks up before its own provider branches
- `litellm/llms/anthropic/pass_through/adapters/model_garden_reasoning.py` L1-L91: new, Qwen/GLM family detection; Qwen gets `chat_template_kwargs.enable_thinking: false` and effort mapped to low/medium/xhigh; GLM defaults to `low`, requested tier collapsed to low/high. Both replace a summary-wrapped effort with a plain tier
- `litellm/llms/anthropic/pass_through/adapters/claude_code_classifier.py` L1-L43: new, detect classifier request by `</block>` stop sequence; floor GLM `max_tokens` at 4096

## Decider (SystemOne) pass-through routing

Generic typed-decision API routing over Vertex AI dedicated endpoints. The current serving model is Eikos; the route is keyed on the LiteLLM model group (`VertexAIModelSet` name), so the Vertex model can be replaced or upgraded without gateway changes.

- `litellm/llms/vertex_ai/passthrough/transformation.py` L1-L145: new `VertexAIDeciderPassthroughConfig`, SystemOne typed-decision pass-through for invoke-mode Vertex deployments: URL join is `api_base + /<endpoint>` (the deployment `api_base` ends at the container's `/invoke/v1` prefix), auth via `VertexBase` OAuth (Workload Identity or `vertex_credentials`), and non-streaming responses map SystemOne `usage.input_tokens`/`output_tokens` onto `prompt_tokens`/`completion_tokens`. The response's own `model` field is a server-side weight path, so it is not used for attribution
- `litellm/llms/vertex_ai/passthrough/__init__.py` L1-L3: exports
- `litellm/utils.py` L9649-L9654: `ProviderConfigManager.get_provider_passthrough_config` returns the config for `LlmProviders.VERTEX_AI`
- `litellm/proxy/pass_through_endpoints/llm_passthrough_endpoints.py` L4139-L4339: new `/decider/{endpoint:path}` route + `handle_decider_passthrough_router_model`: body `model` (or `?model=`) must name a router model group; relay through `ProxyBaseLLMRequestProcessing.base_passthrough_process_llm_request` so auth metadata, hooks, logging and budgets apply; leading `v1/` stripped against the api_base; deployment `litellm_params` win over caller-sent routing keys (`api_base`/`api_key`/`vertex_*`) so per-region load balancing holds
- `litellm/proxy/_lazy_features.py` L216: `/decider/` prefix on the `llm_passthrough` lazy slot so the router activates on first use
- `tests/unit/proxy/pass_through_endpoints/test_decider_pass_through_endpoints.py` L1-L308: route and config tests: URL join, usage mapping, bearer injection, `v1/` strip, metadata isolation, query-param model, unknown-group rejection

## Model discovery and access groups

- `litellm/proxy/utils.py` L9078-L9097, L9225-L9247: team with access groups bounded to `_get_listed_models_from_access_groups`; no fall-through to all proxy models
- `litellm/proxy/auth/auth_checks.py` L4679-L4736: `_get_listed_models_from_access_groups` reads `listed_model_names` from team/key access groups
- `litellm/proxy/auth/model_checks.py` L211-L216, L229, L255-L258: strip `no-default-models` sentinel from granted list; dedupe wildcard + concrete entries
- `litellm/models/access_group.py` L18: `listed_model_names` field on access group table model
- `litellm/types/access_group.py` L10, L21, L40: `listed_model_names` on create/update request and response models
- `litellm/proxy/management_endpoints/access_group_endpoints.py` L546, L646: wire field through create/update handlers
- `litellm/proxy/schema.prisma` L1548, `schema.prisma` L1548: `listed_model_names String[]` column, identical in all three schema copies (`litellm-proxy-extras/litellm_proxy_extras/schema.prisma` included, upstream CI checks they match)
- `litellm-proxy-extras/litellm_proxy_extras/migrations/20260715120000_add_listed_model_names_to_access_group_table/migration.sql` L1-L3: matching migration

## Dashboard (ui/litellm-dashboard)

- `src/app/(dashboard)/access-groups/_components/AccessGroupsModal/AccessGroupBaseForm.tsx`: `listedModelNames` field on access group base form
- `src/app/(dashboard)/access-groups/_components/AccessGroupsModal/AccessGroupEditModal.tsx`: prefill `listedModelNames`; send only when Models tab visited
- `src/app/(dashboard)/access-groups/_components/AccessGroupsDetailsPage.tsx`: Listed Models tab with count badge
- `src/app/(dashboard)/access-groups/_components/AccessGroupsPage.tsx`: map `listed_model_names` into row type
- `src/app/(dashboard)/access-groups/_components/access-group-create/schema.ts`: `listedModelNames` in create schema
- `src/app/(dashboard)/access-groups/_components/access-group-create/mapper.ts`: send `listed_model_names` when non-empty
- `src/app/(dashboard)/access-groups/_components/types.ts`: `listedModelNames` on shared type
- `src/app/(dashboard)/hooks/accessGroups/useEditAccessGroup.ts`: `listed_model_names` on API types
- `src/app/(dashboard)/access-groups/_components/access-group-create/AccessGroupCreateDialog.tsx`: "Models shown in /v1/models" field on the create dialog
- `src/components/add_model/advanced_settings.tsx`: skip-budget-checks switch on add-model advanced settings
- `src/components/add_model/handle_add_model_submit.tsx`: map `skip_budget_checks` into `model_info`
- `src/components/ModelInfoEditForm.tsx`: skip-budget-checks field in edit form and read-only display
- `src/components/model_info_view.tsx`: persist `skip_budget_checks` in model_info update

## Tests

- `tests/unit/proxy/auth/test_user_api_key_auth.py` L283-L401: requested model appended to budget errors (`_append_requested_model_to_budget_error`)
- `tests/unit/litellm_core_utils/prompt_templates/test_litellm_core_utils_prompt_templates_common_utils.py` L26, L2267-L2297: system message merging
- `tests/unit/llms/anthropic/pass_through/adapters/test_anthropic_experimental_pass_through_adapters_transformation.py` L1139-L1191: truncated tool calls dropped, intact ones kept; L4611-L4670: tool_reference expansion; L5230-L5293: Anthropic-only tool params kept out of the forwarded schema
- `tests/unit/llms/anthropic/pass_through/adapters/test_claude_code_classifier.py` L1-L73: classifier detection and max_tokens floor
- `tests/unit/llms/anthropic/pass_through/adapters/test_claude_code_request_shapes.py` L1-L259: stage-1/stage-2/probe/main-loop request shapes over fixtures
- `tests/unit/llms/anthropic/pass_through/adapters/test_handler_hosted_tool_stripping.py` L1-L187: hosted tool stripping and dangling tool_choice
- `tests/unit/llms/anthropic/pass_through/adapters/test_handler_output_config_passthrough.py` L60, L64, L216-L318, L349-L432: output config stripping, prompt cache forwarding
- `tests/unit/llms/anthropic/pass_through/adapters/test_model_garden_reasoning.py` L1-L148: Qwen/GLM reasoning defaults and tier mapping
- `tests/unit/llms/anthropic/pass_through/adapters/test_tool_search.py` L1-L101: reference expansion and deferred tool forwarding
- `tests/unit/llms/anthropic/pass_through/messages/test_anthropic_experimental_pass_through_messages_handler.py` L854, L1022-L1167: responses-endpoint routing gate
- `tests/unit/llms/anthropic/pass_through/responses_adapters/test_responses_adapters_streaming_iterator.py` L625-L842: streaming web-search block emission
- `tests/unit/llms/anthropic/pass_through/responses_adapters/test_responses_adapters_transformation.py` L874-L912, L2215-L2381: web_search tool translation, tool_choice; prompt cache breakpoints
- `tests/unit/llms/azure/chat/test_azure_gpt5_transformation.py` L55-L131: Azure min-token floor; 1.25x cache-write price resolution
- `tests/unit/llms/openai/test_is_model_gpt_5_model.py` L242-L263: gpt-5.x version detection anywhere in custom deployment names
- `tests/unit/llms/openai_like/chat/test_openai_like_handler.py` L1-L124: reasoning passthrough streaming
- `tests/unit/llms/vertex_ai/test_vertex_system_message_merge.py` L1-L108: system message merging
- `tests/unit/llms/vertex_ai/vertex_model_garden/test_vertex_model_garden_transformation.py` L1-L47: reasoning_effort declaration and config resolution
- `tests/unit/proxy/auth/test_auth_checks_object_access_and_lookup.py` L11131-L11180: listed-models resolution from access groups
- `tests/unit/proxy/auth/test_custom_auth_end_user_budget.py` L406-L447: custom-auth path honors budget-exempt models
- `tests/unit/proxy/auth/test_fallback_budget.py` L80-L88: exempt paid fallback target allowed for an over-budget key
- `tests/unit/proxy/auth/test_model_budget_exempt.py` L1-L565: per-model budget exemption matrix
- `tests/unit/proxy/auth/test_model_checks.py` L1058-L1140: sentinel strip and wildcard dedupe in model list
- `tests/unit/proxy/guardrails/guardrail_hooks/test_headroom.py` L3017-L3049: stream_options dropped on non-streaming conversion
- `tests/unit/proxy/hooks/test_proxy_track_cost_callback.py` L2150-L2212: failure log model resolution
- `tests/unit/proxy/management_endpoints/test_access_group_endpoints.py` L30-L110, L221-L239: listed_model_names in create/update payloads
- `tests/unit/proxy/utils/helpers/test_model_access.py` L373-L425: access-group listed-models bounding
- `tests/unit/test_utils.py` L9420-L9467: stream_options drop unless streaming
- Fixtures: `tests/unit/llms/anthropic/pass_through/adapters/fixtures/claude_code_2_1_266/`: recorded Claude Code 2.1.266 payloads (main_loop, main_loop_title_no_thinking, probe_stage1_sonnet5, stage1, stage2, tool_search_stage1, tool_search_stage2)
- Dashboard fixtures: `AccessGroupsPage.test.tsx`, `AccessGroupEditModal.integration.test.tsx`, `useAccessGroups.test.ts`, `AccessGroupsDetailsPage.test.tsx`, `AccessGroupCreateDialog.test.tsx`, `mapper.test.ts`, `model_info_view.test.tsx`: upstream fixtures carry the fork's required `listed_model_names`

`test_handler_hosted_tool_stripping.py::test_web_search_options_still_set_for_models_that_map_it` registers its own web-search-capable Gemini entry, since v1.104.0's map no longer flags `gemini/gemini-2.0-flash`

## GPT-6.1 Terra pricing backport

- `model_prices_and_context_window.json`, `litellm/model_prices_and_context_window_backup.json`: the six `gpt-6.1-terra` rows (`gpt-6.1-terra`, `chatgpt/`, `global.openai.`, `us.openai.`, `github_copilot/`, `bedrock_mantle/openai.`), copied verbatim from upstream main (#48429, #48441, #48450, #48479). No tag carries them yet, not even v1.107.0-rc.2. Drop them and use upstream's rows once the fork moves onto a tag that ships them
- `model_prices_and_context_window.schema.json`: regenerated with `ci_cd/generate_model_prices_schema.py` for the `cache_creation_input_token_cost_above_12hr*` fields those rows introduce. v1.106.6's cost calculator does not read the 12-hour cache-write tiers, so only the standard rates price requests

## Bedrock Mantle gpt-5.6/gpt-6 chat completions backport

- `litellm/llms/bedrock_mantle/chat/transformation.py` L131-L154: `BedrockMantleChatConfig.map_openai_params` sends `max_completion_tokens` instead of `max_tokens` for the gpt-5.6/gpt-6 reasoning families, whichever spelling the caller used. AWS Mantle (verified live on us-east-1) answers `max_tokens` with 400 `unsupported_parameter` for these models, so a Mantle deployment serving gpt-6.1-terra failed every completion that set a max. Ported verbatim from upstream main (#43982); drop it once the fork rebases onto v1.107.0 or later
- `tests/unit/llms/bedrock_mantle/chat/test_bedrock_mantle_transformation.py` L147-L181: gpt-5.6/gpt-6 rows send `max_completion_tokens` from either param spelling and carry other params through; `openai.gpt-oss-20b` keeps `max_tokens`

## Vertex AI context caching

- `litellm/llms/vertex_ai/context_caching/vertex_ai_context_caching.py` L422-L440, L595-L613: when the `cachedContents` creation call fails with an HTTP error, log a warning, restore `tools`/`tool_choice` into `optional_params` and return the original messages with no cache instead of raising `VertexAIError`. Google rejects explicit context caching per model (`gemini-4-argon`: "does not support explicit context caching") and Claude Code always sends `cache_control`, so raising failed every request for those models; the uncached request is what should run. Upstream main still raises as of v1.109-dev, so this stays
- `tests/unit/llms/vertex_ai/context_caching/test_vertex_ai_context_caching.py` L320-L368, L651-L724: `test_check_and_create_cache_http_error` rewritten to the degrade contract (full prompt returned, tools restored, no cache name) and `test_async_check_and_create_cache_http_error` added for the async path; timeout tests keep raising 408

## Build, ops and misc

- `litellm-rust/crates/llms-types/src/providers/anthropic.rs` L237: `dangerous-tool-use-2026-09-03` is unsupported only on `BedrockConverse`. v1.106.2 marked Databricks as supported in the JSON beta map (`0aefd1b8b7`) but kept the Rust mirror rejecting it, so `on_matches_every_config_cell` fails on plain v1.106.6. Ported from upstream main (#46091); drop it once a tag carries that line
- `.github/workflows/fork-docker-build.yml` L1-L93: fork image build, datetime-stamped tags
- `ui/litellm-dashboard/src/lib/http/schema.d.ts`: generated API schema types
- `litellm/proxy/_lazy_openapi_snapshot.json`: generated OpenAPI snapshot

## Absorbed by upstream (no longer carried)

Every drop below was verified by reverting the patch and rerunning its tests or an end-to-end probe

### v1.106.6

Nothing absorbed. The patch release backports #46712, which limits gzip to the dashboard analytics routes and offloads compression in `litellm/proxy/middleware/gzip_middleware.py`. The fork does not touch that file, so the rebase from v1.106.5 applied cleanly and every fork hunk kept its line numbers

### v1.106.5

Nothing absorbed. The patch release backports #48599, which builds proxy-only failure logs from a metadata allowlist and ignores request-time GCS credentials. It adds code to `litellm/proxy/utils.py` above the fork's access-group hunks, which moved down 78 lines unchanged, and the rebase from v1.106.4 applied cleanly

### v1.106.1 through v1.106.4

Nothing absorbed. The four patch releases come from `stable/1.106.x` and stack on v1.106.0, so the fork commits were rebased straight onto v1.106.4. They mostly carry spend and cost fixes, batch cost fixes, a Bedrock count_tokens fallback, CA root and base image updates, dependency bumps and a cost map mirrored from main. Several touch fork-adjacent files without changing the fork's hunks

Two spots needed hand merging. Upstream's `AzureOpenAIGPT5Config.map_openai_params` now returns `OpenAIGPT5Config.map_openai_params` directly, so the fork keeps that result in a local and applies the `max_completion_tokens` floor before returning it. The import blocks of `messages/handler.py` and `responses_adapters/streaming_iterator.py` gained upstream's `AnthropicCacheControlHook` and `partial_responses_incomplete_event_on_disconnect` beside the fork's imports. The formatting-only fork hunks in `test_anthropic_experimental_pass_through_messages_handler.py` are upstream's own now

v1.106.2 backports the `dangerous-tool-use-2026-09-03` beta for `/v1/messages` requests that carry `safeguards` (#43955, #46102), which closes the stable-only gap noted under v1.104.0. The `/key/info` 400 fix and every patch listed above are still not upstream, so they all stay

### v1.106.0

Absorbed by the release:

- the claude-haiku-5-5 backport: the `claude-haiku-5-5` / `claude-haiku-5.5` cost map rows in both price JSONs, the over-100k and batch schema entries, the `ModelInfoBase` / `ModelInfo` fields, the explicit `_get_model_info_helper` kwargs, the Rust catalog fields, the `tests/unit/test_utils.py` whitelist entries, the cost calc tier tests, `tests/unit/test_claude_haiku_5_5_config.py` and the regenerated dashboard `ModelInfo` schema fields. v1.106.0 ships all of it (19 haiku-5 keys upstream vs the fork's 18, plus its own haiku config test), so the fork backport is dropped and upstream's rows are used

Nothing else was absorbed. Upstream refactored many fork-adjacent files, and the fork's hunks were carried onto the new names: private helpers became public with legacy `_` aliases (`is_model_cost_zero`, `get_models_from_access_groups`, `handle_authentication_error`, `hash_token_if_needed`, `ProxyDBLogger`), `auth_checks.py` gained `_deployments_served_for` for alias and wildcard resolution, and `litellm/types/llms/anthropic.py` swapped `BaseModel` for `LiteLLMBaseModel`, which the fork's new web search models now also use. The fork still carries `_get_deployments_for_model` because upstream's `_deployments_served_for` does not take `team_id` for team-scoped models. Upstream also moved both sanitize pipelines into `prepare_native_messages`, so the nameless tool_use repair is now wired there

The `/key/info` 400 fix (`info_key_fn` in `key_management_endpoints.py`) is still not upstream, and neither are the per-model budget exemption, the access-group listed models or the other patches listed above, so they all stay

### v1.105.1

Nothing absorbed. The patch release backports #44243 (batched daily model usage writes) and #44508 (log spend once for chat over the Responses bridge). Both touch `litellm/utils.py`, `litellm/proxy/utils.py` and `tests/unit/test_utils.py` beside the fork's hunks without changing them, and the fork never carried its own fix for either

### v1.105.0

Absorbed by the release:

- `litellm/anthropic_beta_headers_config.json` and the vertex_ai partner-models messages config: upstream allowlists `per-turn-control-2026-07-01` for vertex_ai and auto-adds it when messages carry `output_config`, the same change the fork carried, so the fork commit and its tests in `test_anthropic_messages_per_turn_control.py` and `test_vertex_ai_partner_models_anthropic_messages_config.py` are gone
- `model_prices_and_context_window.json`, `litellm/model_prices_and_context_window_backup.json`: the `bedrock_mantle/openai.gpt-6.1-sol` row ships upstream, so the fork backport is dropped and upstream's row is used
- `litellm/proxy/auth/auth_checks.py` `_is_cost_explicitly_configured`: upstream now resolves the group through `Router.get_model_list`, the intent of the fork's rewrite onto `_get_deployments_for_model`, so the function body is upstream's again

Upstream renamed `litellm/llms/anthropic/experimental_pass_through/` to `litellm/llms/anthropic/pass_through/` and moved `tests/test_litellm/proxy/` into `tests/unit/proxy/` (with `test_auth_checks.py` split, the fork's listed-models tests landing in `test_auth_checks_object_access_and_lookup.py`). The fork's files moved with them and their imports now use the new module path. Upstream also extracted the virtual-key checks of `_user_api_key_auth_builder` into `validate_resolved_virtual_key`, which is where the fork's `_should_skip_budget_checks` call now lives

v1.105.0 was cut from `main`. It has its own versions of every v1.104.1 and v1.104.2 stable backport (the Decisions API with the OpenAI provider and `/v1/systemone`, the pgbouncer and dependency bumps), so the fork carries none of them. The claude-haiku-5-5 rows and over-100k tier are still not upstream at v1.105.0 and stay

### v1.104.1 and v1.104.2

Nothing absorbed. The two patch releases touch fork-adjacent files (`litellm/proxy/_lazy_features.py`, `litellm/proxy/_types.py`, `litellm/utils.py`, `tests/unit/test_utils.py`, both price JSONs), but they only add code beside the fork's hunks. The new `/v1/decisions` and `/v1/systemone` routes (the Decisions API in `litellm/decisions/`) are a different surface from the fork's `/decider/` Vertex pass-through, so both stay

The `bedrock_mantle/openai.gpt-6.1-sol` row is still needed at v1.104.2. It first appears upstream in v1.105.0-rc.3, so drop it when the fork moves onto a 1.105 tag

The v1.103.x stable-only gaps are unchanged. v1.104.2 still lacks the Azure AI Foundry `dangerous-tool-use` beta for `safeguards` (`_with_dangerous_tool_use_beta_for_safeguards` in v1.103.2), and no 1.104.1 or 1.104.2 commit mentions #43642 or #43656. The fork carries neither

### v1.104.0

Nothing absorbed. Upstream moved most of `tests/test_litellm/` (everything but `proxy/`) and `tests/proxy_unit_tests/test_user_api_key_auth.py` into `tests/unit/`, and the fork's tests moved with them. The gpt-5.x anywhere-in-name detection now rides on upstream's new `_gpt_series_version` instead of the fork's own `_gpt_5_minor_version` helpers

v1.104.0 was cut from `main` and lacks some v1.103.x stable-only backports the fork had through v1.103.2: the `dangerous-tool-use-2026-09-03` beta on Azure AI Foundry when `safeguards` is set, and the spend key-owner recovery fixes (#43642, #43656). The fork carries neither. The `extra_body` cache-control backport (#43342) is covered by main's own rework of that hook

### v1.103.0


Absorbed by the release:

- `litellm/proxy/hooks/max_budget_limiter.py`: upstream deleted the duplicate user budget hook (auth already owns the check), so the fork's exemption patch and its hook tests in `test_model_budget_exempt.py` are gone. Paid fallback targets are now gated by upstream's `fallback_budget.py`, which the fork teaches about `skip_budget_checks`
- `litellm/litellm_core_utils/llm_cost_calc/utils.py`: upstream resolves a missing cache-write price to the input rate itself
- Dashboard team-member reset spend (`TeamInfo.tsx`, `TeamMemberTab.tsx`, `MemberTable.tsx`, `TableIconActionButton.tsx`, `networking.tsx`'s `teamMemberResetSpendCall`): upstream ships its own dialog and `useResetTeamMemberSpend` hook against the same endpoint

Redundant with upstream or with other fork code, found in the audit:

- `litellm/litellm_core_utils/litellm_logging.py`: faked-stream costing. Upstream's `_is_converted_stream_result` marks converted streams as streaming, so the cost is the same without it
- `litellm/llms/custom_httpx/llm_http_handler.py`: fake-stream context threading; model_id and cost come out the same without it
- `litellm/integrations/websearch_interception/transformation.py`: refactor onto the shared result-block builder, no behavior change
- `litellm/proxy/proxy_server.py` and `networking.tsx`: `/v1/models` dedupe. Upstream's `list(set(...))` already dedupes and the backend dedupe in `model_checks.py` stays
- `litellm/completion_extras/litellm_responses_transformation/transformation.py`: hosted-tool drop in `_convert_tools_to_responses_format` and the dangling `tool_choice` cleanup. The bridge handler strips hosted tools and the dangling `tool_choice` before the request reaches `litellm.completion`
- `VertexAIModelGardenOpenAIConfig.map_openai_params`: unwrapping a summary-wrapped `reasoning_effort`. `model_garden_reasoning.py` already replaces it with a plain tier for Qwen and GLM, the only Model Garden families behind the bridge. Another family would get the dict forwarded
- `litellm/litellm_core_utils/get_supported_openai_params.py`: the `openai/` Vertex branch was dead, since `ProviderConfigManager` returns the model-garden config first
- `litellm/router.py`: the `(team_id, model)` key type on `_zero_cost_cache`, left over from the team-keyed cache below
- `responses_adapters/streaming_iterator.py`: module-level `_content_block_*` / `_field` helpers duplicated upstream's inline events and `self._field`
- `OpenAIGPT5Config.is_model_gpt_5_6_plus_model`: only tests called it
- team-keyed zero-cost cache and the `team_id` parameter on `_is_model_cost_zero`: never took effect, since `get_model_group_info` resolves before the team is consulted. Zero-cost team-scoped models still do not skip budget checks, same as upstream
- `ModelInfo.skip_budget_checks` in `litellm/types/router.py`: `ModelInfo` accepts extra fields; `_is_model_budget_exempt` now requires the value to be exactly `True`, so a string `"false"` cannot exempt a model
- the chat adapter's hosted-tool predicate swap. Upstream's `_is_web_search_tool` stays and its test is upstream's again
- the fork's rewrite of the Responses output parser (reasoning, refusal and function-call handling duplicated upstream's)
- `cookbook/litellm_proxy_server/grafana_dashboard/background_jobs/grafana_dashboard.json`, the scratch `.pr_body_*.md` drafts, `mise.local.toml`, `local/*/Dockerfile` and the raised lint budget limits
- fork tests that pass unchanged on v1.103.0 code: cache-write price fallback, choice-less stream role and usage chunks, empty-choices lead chunk, tool-result-always-emits-a-tool-message, `stop_sequences` mapping, unclosed tool-call brace repair, unopened-item block close, access-group dedupe, the gpt-5.6 Responses bridge checks in `test_main.py` and the `completion_extras` incomplete-output tests

v1.103.0 was cut from `main` and lacked some v1.102.1 stable backports, notably forwarding Claude Code's `safeguards` field on `/v1/messages`. v1.103.2 restores them (`ANTHROPIC_ONLY_REQUEST_KEYS` carries `output_config` and `safeguards` again, plus the `dangerous-tool-use-2026-09-03` beta on Bedrock/Vertex/Foundry), so the fork carries nothing for it

### v1.102.1

- `tests/test_litellm/proxy/auth/test_user_api_key_auth.py`: the `timezone` import fix
- `litellm/litellm_core_utils/streaming_chunk_builder_utils.py`: role fallback on choice-less streams; upstream's `_get_role_from_chunks` / `_role_of_choice` already handle it
- `litellm/llms/anthropic/experimental_pass_through/adapters/tool_schema.py`: `drop_uncompilable_patterns` duplicated upstream's `drop_non_python_regex_patterns` (#40485), which passes every case the fork's tests covered. The bridge now calls the upstream function
- `litellm/llms/anthropic/experimental_pass_through/adapters/streaming_iterator.py`: choice-less guards in the translation loop, `_is_blank_delta`, `_should_start_new_content_block` and the widened `_with_refusal_stop_details`. v1.102.1's `_handle_choiceless_chunk` short-circuit runs first, so they could never fire

Not dropped: the `no-default-models` strip in `litellm/proxy/auth/model_checks.py`. v1.102.1's `append_unique` hides the sentinel from the output, but a key whose model list is only the sentinel still wins the key-vs-team branch, so access-group team models never surface without the fork's strip

### v1.101.0

- `litellm/proxy/management_endpoints/key_management_endpoints.py`: upstream captures `team_id` before the defaults loop itself; the file now matches upstream
- `litellm/llms/anthropic/experimental_pass_through/adapters/transformation.py`: upstream ships `_translate_stop_sequences_to_openai`; the fork's copy and its duplicate call are gone
- `model_prices_and_context_window.json`, `litellm/model_prices_and_context_window_backup.json`: identical to upstream; the fork carries no pricing data. Azure GPT-5.6 deployments need `model_info.base_model` because Azure echoes a dated snapshot id the map does not list
- Dockerfiles: the wolfi glibc 2.44 and Python 3.13 pin fixes the fork was based on are part of v1.101.0

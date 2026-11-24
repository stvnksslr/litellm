# Fork patch manifest (delta vs upstream v1.110.3, `v1.110.3..HEAD`)

Line numbers are as of the current `main-fork` tip. For modified files they are diff-hunk ranges (`git diff v1.110.3..HEAD --unified=0`); for added files `L1-L<n>` is the full file. 119 files, +7,530 / -173, roughly 60% tests

## Agentic coding clients on the proxy (/v1/messages bridge)

- `litellm/llms/anthropic/messages/adapters/transformation.py` L12, L153, L178-L186, L351-L365: imports for upstream `drop_non_python_regex_patterns` (in `json_schema_utils` since v1.110.0) and the tool_search helpers; `_model_supports_web_search_options` gates the web_search -> `web_search_options` reduction to models that map it, since upstream sets it unconditionally and some targets list it as unsupported
- `litellm/llms/anthropic/messages/adapters/transformation.py` L972-L976, L986, L1016: keep the Anthropic-only tool keys `defer_loading`, `allowed_callers` and `input_examples` out of the function parameters (upstream merges unknown keys into them), and sanitize each tool `input_schema` with upstream `drop_non_python_regex_patterns`, which upstream only applies for provider `openai`, so hosted_vllm and Model Garden targets of the bridge need this call
- `litellm/llms/anthropic/messages/adapters/transformation.py` L1264, L1276, L1281, L1284: forward a deferred tool only when a tool_reference names it (or server-side search was requested); a web_search tool becomes `web_search_options` only when the model supports it
- `litellm/llms/anthropic/messages/adapters/transformation.py` L631, L697, L1465, L1468, L1492-L1494, L1530, L1534, L1539, L1545-L1551, L1560, L1572: tool_reference blocks in tool results expand to a `<functions>` block via `_tool_result_content`. Upstream already translates tools before messages, so the patch only passes the referenced names into upstream's tool translation and the catalog into upstream's message translation and its `_tool_message`
- `litellm/llms/anthropic/messages/adapters/transformation.py` L433, L1431, L1436-L1438: expansion is opt-in via `emulate_tool_search`, set only by the bridge; write-back callers keep upstream's `tool_reference` passthrough. The deferred-tool filter above is not gated by it, so a guardrail that writes the request back also loses unreferenced deferred tools
- `litellm/llms/anthropic/messages/adapters/transformation.py` L1669-L1682, L1687, L1696-L1699: parse each tool call's arguments and drop a call whose arguments are cut off mid-string (upstream's repair only closes brackets and raises there); `_count_openai_tool_calls`
- `litellm/llms/anthropic/messages/adapters/transformation.py` L1841-L1844, L1855-L1858: a dropped tool call maps the stop reason to `max_tokens`
- `litellm/proxy/guardrails/anthropic_sse.py` L12, L18, L42, L187-L196, L208, L211-L212: `_require_parseable_tool_calls` checks the rewritten and source responses before a guardrail rebuilds a stream, so a tool input that is not JSON still fails the rebuild (and a failed stream still gets its upstream error alone) instead of the adapter silently dropping that tool call. Upstream's own guardrail tests fail without it
- `litellm/llms/anthropic/messages/adapters/tool_search.py` L1-L79: new, tool-search emulation; reference extraction, `forwards_tool`, `expand_tool_references` building the `<functions>` block
- `litellm/llms/anthropic/messages/adapters/handler.py` L32-L41, L68, L560-L567: imports, and `_drops_anthropic_tool`
- `litellm/llms/anthropic/messages/adapters/handler.py` L836-L855: strip Anthropic server-side tools (`code_execution`, `web_fetch`, `tool_search_tool`) from the forwarded tools for every target, and the client-executed `bash`, `text_editor` and `memory` tools only when upstream's `is_claude_tool_target` says the target is not Claude; drop a dangling `tool_choice`/`parallel_tool_calls` when no tool is left. This is the only hosted-tool filter on the chat path
- `litellm/llms/anthropic/messages/adapters/handler.py` L901-L906: apply model-garden reasoning overrides then GLM classifier overrides before routing
- `litellm/llms/anthropic/messages/native/handler.py` L18, L22, L44, L51, L100-L136: `_declares_responses_endpoint` / `_deployment_supports_responses_api` from model_info, base_model or model cost
- `litellm/llms/anthropic/messages/native/handler.py` L205, L209-L216, L226-L231, L819-L824: `_should_route_to_responses_api` takes the request `tools` and routes a hosted web search to the Responses API when the deployment serves it (upstream only routes `openai`, prefix-strip cases and xAI there). It keeps upstream's positional signature and its `_BridgeTarget` call site
- `litellm/llms/anthropic/messages/responses_adapters/transformation.py` L9, L12, L32-L35, L46, L48, L55, L60, L76-L127, L814-L846, L949: hosted web-search helpers (`as_responses_item_mapping`, `web_search_call_query`, `_url_citations`); `translate_response` keeps upstream's output loop and adds a `web_search_call` branch emitting server_tool_use -> web_search_tool_result, with url citations from the final message attached to the last search result
- `litellm/llms/anthropic/messages/responses_adapters/transformation.py` L531-L532, L556, L558-L565, L570-L575, L746-L750, L754, L756-L757, L865, L868-L872, L881, L914: translate the web_search tool to Responses `web_search` inside upstream's `_translate_tool_to_responses_api` (this also changes `web_search_preview` to `web_search` for OpenAI itself); Responses-API `tool_choice` conversion using the translated tool list
- `litellm/llms/anthropic/messages/responses_adapters/streaming_iterator.py` L4, L20-L23, L31, L37-L42, L49-L50, L165-L168: web-search imports and state on the wrapper
- `litellm/llms/anthropic/messages/responses_adapters/streaming_iterator.py` L217-L268, L341-L344, L450-L452, L526: record search sources from citations; queue `server_tool_use` + paired `web_search_tool_result` blocks, the latter at response completion
- `litellm/llms/anthropic/common_utils.py` L9, L55, L139-L163: `web_search_result_from_source` maps a Responses citation or search source to upstream's `SearchResult`, and `build_anthropic_web_search_tool_result_block` delegates to upstream's `WebSearchTransformation.build_web_search_tool_result_block`. Only the Responses bridge calls them
- `litellm/types/llms/anthropic.py` L838-L876: `is_anthropic_hosted_tool_type` (server-side tools only), `is_anthropic_client_executed_tool_type` and `is_anthropic_web_search_tool`, used by the chat bridge handler and the Responses routing and adapter (the chat adapter keeps upstream's `_is_web_search_tool`)
- `litellm/llms/anthropic/messages/adapters/streaming_iterator.py` L947-L950, L1186-L1189, L1512, L1522-L1523: while a tool_use block is open, skip whitespace-only text chunks. Qwen streams `"\n"` between parallel tool calls before the previous call's closing `}`, which used to open a nameless tool_use that every later Claude turn on that history rejects
- `litellm/llms/anthropic/common_utils.py` L2271-L2357: `repair_nameless_tool_use_blocks_in_anthropic_messages` heals histories already poisoned by that bug. A nameless tool_use is dropped with its tool_result in the next user turn, or renamed `unknown_tool` when dropping would empty either message
- `litellm/llms/anthropic/messages/native/utils.py` L11, L253-L255: `normalize_native_messages` runs the repair after tool_use id normalization. `prepare_native_messages` calls it at both `/v1/messages` entry points before any bridge dispatch, and it also feeds the OpenAI and Vertex count_tokens paths and `convertible_blocks`
- `litellm/llms/openai_like/chat/handler.py` L20-L23, L71, L111: stream via `OpenAIChatCompletionStreamingHandler` over upstream's `aiter_sse_lines`/`iter_sse_lines` splitter so `reasoning_content` deltas and mid-stream errors surface
- `litellm/litellm_core_utils/token_counter.py` L774-L786: `defer_loading`, `allowed_callers` and `input_examples` count as mapped Anthropic tool keys, because the fork's bridge strips them instead of merging them into the function parameters. Upstream's `test_token_counter_counts_anthropic_tools_as_sent_to_chat_template_families` holds the counter and the bridge to the same shape

## GPT-5.x family enablement

- `litellm/llms/openai/chat/gpt_reasoning_transformation.py` L18, L143, L148, L152: upstream's `_GPT_SERIES_VERSION` unanchored and applied with `search`, so `gpt-<major>.<minor>` is found anywhere in a custom deployment name; `is_model_gpt_5_2/5_4` reuse `_gpt_series_version`. Upstream's alternative is pinning `model_info.mode: responses` per deployment

## Spend accuracy

- `litellm/proxy/hooks/proxy_track_cost_callback.py` L39, L446-L460, L575-L580: `_resolve_failure_log_model` fills model on failed spend logs from `get_model_from_request` route resolver
- `litellm/proxy/auth/auth_exception_handler.py` L25, L34-L37, L145-L175, L234-L236: `_append_requested_model_to_budget_error` appends requested model to BudgetExceededError message. It reads upstream's normalized `request_context`, so a non-object request body cannot crash the auth error path

## Budget controls

- `litellm/proxy/auth/auth_checks.py` L20, L46, L185, L722-L727, L778-L915: `model_info.skip_budget_checks` exemption and the fallback reachability gate. Deployments, aliases and fallbacks are read only through `registry()` and `settings()`, which `Router` and the router's `RoutingContext` both answer, fallback keys match through the public `fallback_chain`, and the walk over fallbacks is an iterative fixed point that fails closed when it does not converge. `should_skip_budget_checks_for_model` skips only when every group the request can reach, its own `fallbacks` included, is explicitly zero-cost or exempt
- `litellm/proxy/auth/auth_checks.py` L1273-L1274, L1280-L1286: upstream's `request_skips_budget_checks` takes the caller's team and team aliases and asks `should_skip_budget_checks_for_model` instead of `is_model_cost_zero`, so `common_checks`, the guardrail tag-budget path and every auth path follow the same rule. A zero-cost model with a paid fallback therefore no longer skips budgets anywhere
- `litellm/proxy/auth/user_api_key_auth.py` L2797-L2802, L3310-L3315, L4138, L4370, L4379-L4386: upstream's JWT, virtual-key and centralized call sites pass the token's `team_id` and `team_model_aliases` along
- `litellm/proxy/auth/user_api_key_auth.py` L5037-L5043: the custom-auth path asks `request_skips_budget_checks` instead of a bare `is_model_cost_zero`, so it honors the exemption and the fallback gate like the other paths
- `litellm/proxy/auth/fallback_budget.py` L44, L135-L137: upstream's router-time fallback budget check also admits `skip_budget_checks` targets, so an exempt fallback is not refused for an over-budget caller
- `litellm/proxy/auth/auth_checks.py` L4977-L5034: `_get_listed_models_from_access_groups` (see Model discovery)

## Vertex Model Garden coding models

- `litellm/litellm_core_utils/prompt_templates/common_utils.py` L1304-L1339: `merge_system_messages_to_front` folds every system message into one leading text-only message. Upstream's `merge_consecutive_system_messages(system_messages_first(...))` is not a substitute: it keeps image parts and empty text in the system content and leaves a `developer` message as a second instruction message, while Vertex MaaS takes one leading system message
- `litellm/llms/vertex_ai/vertex_ai_partner_models/main.py` L12-L15, L224: merge system messages on partner-models dispatch
- `litellm/llms/vertex_ai/vertex_model_garden/main.py` L20, L24-L26, L28, L128-L130: merge system messages on model garden route
- `litellm/llms/vertex_ai/vertex_model_garden/transformation.py` L1-L13: new `VertexAIModelGardenOpenAIConfig`, declares `reasoning_effort` on top of `VertexAILlama3Config`. Upstream reaches the same result when every Model Garden deployment sets `allowed_openai_params: [reasoning_effort]`, so this can go once the deployments carry that
- `litellm/utils.py` L10109-L10114: `ProviderConfigManager` returns model-garden config for `openai/` Vertex prefix, which `get_supported_openai_params` picks up before its own provider branches
- `litellm/utils.py` L5351-L5363: drop `stream_options` in `pre_process_non_default_params` unless `stream is True`; keeps only what upstream's `normalize_responses_api_stream_options` forwards so the Responses bridge contract holds
- `litellm/llms/anthropic/messages/adapters/model_garden_reasoning.py` L1-L91: new, Qwen/GLM family detection; Qwen gets `chat_template_kwargs.enable_thinking: false` and effort mapped to low/medium/xhigh; GLM defaults to `low`, requested tier collapsed to low/high. Both replace a summary-wrapped effort with a plain tier. The family match takes any `vertex_ai` or `hosted_vllm` model whose name contains `qwen` or `glm`, MaaS Qwen included
- `litellm/llms/anthropic/messages/adapters/claude_code_classifier.py` L1-L43: new, detect classifier request by `</block>` stop sequence; floor GLM `max_tokens` at 4096

## Vertex AI decider endpoints (SystemOne decisions provider)

Typed-decision models on Vertex AI dedicated endpoints serve through upstream's decisions API (`POST /v1/systemone`), which validates the request, enforces key and team model access, and prices the answer. The route is keyed on the LiteLLM model group (the `VertexAIModelSet` name), so the serving model can change without gateway changes. A deployment looks like `model: vertex_ai/openai/decider` with `api_base` set to the endpoint's `.../invoke/v1` URL; set `model_info.mode: decisions` so health checks send a decisions request

- `litellm/llms/vertex_ai/decisions/transformation.py` L1-L37: new `VertexAIDecisionsConfig`, upstream's TypeSafe wire format (which the decider container speaks) with no default `api_base` or env fallback, and a Google OAuth token from the deployment's `vertex_credentials`/`vertex_project` as the bearer unless an `api_key` is set. The token source is injectable
- `litellm/utils.py` L9869-L9874, L10431, L10440: `ProviderConfigManager.get_provider_decisions_config` returns it for `LlmProviders.VERTEX_AI` through upstream's provider table, via a lazy-import factory
- `tests/unit/decisions/test_main.py` L1589: `vertex_ai` joins the providers exempt from shipping an `evaluation`-mode cost map row, like `hosted_vllm`, since decider endpoints are self-hosted and have no catalog entry

## Model discovery and access groups

- `litellm/proxy/utils.py` L10100, L10104, L10252-L10256, L10260-L10263, L10266-L10269, L10284-L10286: team with access groups bounded to `_get_listed_models_from_access_groups`; no fall-through to all proxy models. v1.108.0 split `_get_access_group_models` into an `_AccessGroupModels(team, key)` pair and only adds team-group models to a key whose model check is skipped (`config` or `all-team-models`). The fork keeps that rule for keys and keeps its own team rule, so a team whose model list is empty but which has access groups is still restricted to its groups plus the key's groups
- `litellm/proxy/auth/auth_checks.py` L4977-L5034: `_get_listed_models_from_access_groups` reads `listed_model_names` from team/key access groups
- `litellm/proxy/auth/model_checks.py` L244-L249, L262: strip the `no-default-models` sentinel from the granted list
- `litellm/models/access_group.py` L19: `listed_model_names` field on access group table model
- `litellm/types/access_group.py` L11, L24, L45: `listed_model_names` on create/update request and response models. It is required on the response model, which is why three upstream dashboard test fixtures carry it
- `litellm/proxy/management_endpoints/access_group_endpoints.py` L571, L671: wire field through create/update handlers
- `litellm/proxy/schema.prisma` L1592, `schema.prisma` L1592: `listed_model_names String[]` column, identical in all three schema copies (`litellm-proxy-extras/litellm_proxy_extras/schema.prisma` included, upstream CI checks they match)
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
- `src/app/(dashboard)/access-groups/_components/access-group-create/AccessGroupCreateDialog.tsx`: "Models shown in /v1/models" field on the create dialog (hard-coded English where its neighbours use `t(...)`)
- `src/components/add_model/advanced_settings.tsx`: skip-budget-checks switch on add-model advanced settings
- `src/components/add_model/handle_add_model_submit.tsx`: map `skip_budget_checks` into `model_info`
- `src/components/ModelInfoEditForm.tsx`: skip-budget-checks field in edit form and read-only display
- `src/components/model_info_view.tsx`: persist `skip_budget_checks` in model_info update
- `src/app/(dashboard)/model-insights/_components/modelInsightsData.ts` L25-L31, L67-L70, L86, L107, L110-L112, L150, L154: the leaderboard aggregates and ranks by the underlying model served (`resolvedModelKey`, which falls back to `model_group` when `model` is empty, `unknown` or `unknown-model`), so aliases that resolve to one deployment merge into a single row with combined sums; `RankedModel` identity is `{model, provider}` and a merged row keeps the first-seen provider, which is the rank-sorted payload's top contributor
- `src/app/(dashboard)/model-insights/_components/ModelInsightsView.tsx` L72, L225, L230: ranking rows render the resolved model string and React keys follow it
- `src/app/(dashboard)/model-insights/_components/modelInsightsData.test.ts`, `ModelInsightsView.test.tsx`: merge across groups sharing a model, same-day series merge, unattributed no-merge, cross-provider merge, shares renormalize over the returned set, mid-period alias migration keeps a continuous delta, and the view renders two groups as one row with a combined share

## Tests

- `tests/unit/proxy/auth/test_user_api_key_auth.py` L284-L402: requested model appended to budget errors (`_append_requested_model_to_budget_error`)
- `tests/unit/litellm_core_utils/prompt_templates/test_litellm_core_utils_prompt_templates_common_utils.py` L21, L1016-L1046: system message merging
- `tests/unit/llms/anthropic/messages/adapters/test_anthropic_messages_adapters_transformation.py` L1464-L1516: truncated tool calls dropped, intact ones kept; L4932: `input_examples` kept out of the forwarded parameters; L5077-L5173: tool_reference expansion beside upstream's passthrough tests; L6413-L6474: Anthropic-only tool params kept out of the forwarded schema
- `tests/unit/llms/anthropic/messages/adapters/test_claude_code_classifier.py` L1-L73: classifier detection and max_tokens floor
- `tests/unit/llms/anthropic/messages/adapters/test_claude_code_request_shapes.py` L1-L259: stage-1/stage-2/probe/main-loop request shapes over fixtures
- `tests/unit/llms/anthropic/messages/adapters/test_handler_hosted_tool_stripping.py` L1-L217: server-side tool stripping, client-executed tools kept on Claude targets, dangling tool_choice
- `tests/unit/llms/anthropic/messages/adapters/test_handler_output_config_passthrough.py` L68, L72, L224-L326, L481-L562: `TestQwenGlmThinkingDisable` and `TestGlmClassifierMaxTokensFloor`
- `tests/unit/llms/anthropic/messages/adapters/test_model_garden_reasoning.py` L1-L148: Qwen/GLM reasoning defaults and tier mapping
- `tests/unit/llms/anthropic/messages/adapters/test_tool_search.py` L1-L101: reference expansion and deferred tool forwarding
- `tests/unit/llms/anthropic/messages/adapters/test_streaming_iterator_tool_args.py` L719-L816: whitespace text between parallel tool call arguments keeps the tool_use block whole
- `tests/unit/llms/anthropic/messages/native/test_anthropic_messages_handler.py` L286-L371: nameless tool_use healing before dispatch; L917, L1085-L1230: responses-endpoint routing gate
- `tests/unit/llms/anthropic/messages/responses_adapters/test_responses_adapters_streaming_iterator.py` L821-L1038: streaming web-search block emission
- `tests/unit/llms/anthropic/messages/responses_adapters/test_responses_adapters_transformation.py` L905-L943, L2518-L2684: web_search tool translation and tool_choice
- `tests/unit/llms/anthropic/test_anthropic_common_utils.py` L4910-L5118: nameless tool_use repair
- `tests/unit/llms/openai/test_is_model_gpt_5_model.py` L242-L263: gpt-5.x version detection anywhere in custom deployment names
- `tests/unit/llms/openai_like/chat/test_openai_like_handler.py` L1-L124: reasoning passthrough streaming
- `tests/unit/llms/openai_like/chat/test_openai_like_chat_handler.py` L11, L89, L109-L110: upstream's unicode line separator test reads the delta from the fork's `ModelResponseStream` chunks instead of the Databricks iterator's `text` field
- `tests/unit/llms/vertex_ai/decisions/test_transformation.py` L1-L101: decider calls the dedicated endpoint with a Google OAuth token from a service-account key, prefers a configured `api_key`, rejects a missing `api_base` (plus an empty `__init__.py`)
- `tests/unit/llms/vertex_ai/test_vertex_system_message_merge.py` L1-L108: system message merging
- `tests/unit/llms/vertex_ai/vertex_model_garden/test_vertex_model_garden_transformation.py` L1-L47: reasoning_effort declaration and config resolution (plus an empty `__init__.py`)
- `tests/unit/proxy/auth/test_auth_checks_object_access_and_lookup.py` L11891-L11940: listed-models resolution from access groups
- `tests/unit/proxy/auth/test_custom_auth_end_user_budget.py` L406-L447: custom-auth path honors budget-exempt models
- `tests/unit/proxy/auth/test_fallback_budget.py` L9, L322-L348: exempt paid fallback target allowed for an over-budget key, through a `Router` and through the `RoutingContext` the router passes
- `tests/unit/proxy/auth/test_model_budget_exempt.py` L1-L541: per-model budget exemption matrix, fallback reachability, and upstream's skip predicate refusing a zero-cost model with a paid fallback
- `tests/unit/proxy/auth/test_model_checks.py` L2487-L2510: sentinel strip with access-group models
- `tests/unit/proxy/hooks/test_proxy_track_cost_callback.py` L2669-L2731: failure log model resolution
- `tests/unit/proxy/management_endpoints/test_access_group_endpoints.py` L30, L47, L94, L113, L225, L229-L243: listed_model_names in create/update payloads
- `tests/unit/proxy/utils/helpers/test_model_access.py` L380-L432: access-group listed-models bounding
- `tests/unit/test_utils.py` L11798-L11845: stream_options drop unless streaming
- Fixtures: `tests/unit/llms/anthropic/messages/adapters/fixtures/claude_code_2_1_266/`: recorded Claude Code 2.1.266 payloads (main_loop, main_loop_title_no_thinking, probe_stage1_sonnet5, stage1, stage2, tool_search_stage1, tool_search_stage2)
- Dashboard fixtures: `AccessGroupsPage.test.tsx`, `AccessGroupEditModal.integration.test.tsx`, `useAccessGroups.test.ts`, `AccessGroupsDetailsPage.test.tsx`, `AccessGroupCreateDialog.test.tsx`, `mapper.test.ts`, and `model_info_view.integration.test.tsx` (which also carries `skip_budget_checks` and tells the two switches apart): upstream fixtures carry the fork's required `listed_model_names`

`test_handler_hosted_tool_stripping.py::test_web_search_options_still_set_for_models_that_map_it` registers its own web-search-capable Gemini entry, since v1.104.0's map no longer flags `gemini/gemini-2.0-flash`


## Gemini 4 Carbon pricing backport

- `model_prices_and_context_window.json`, `litellm/model_prices_and_context_window_backup.json`: the four `gemini-4-carbon` rows (`gemini/`, `vertex_ai/`, `vertex_ai/...-cyber-permissive`, `github_copilot/`), copied from upstream main (#50931, #50942, #50951, #51012). v1.110.2 does not carry them. Drop them and use upstream's rows once the fork moves onto a tag that ships them
- `tests/unit/test_model_prices_and_context_window.py` L961-L969: the Google carbon rows carry `supports_continuation` in both cost map copies
- `tests/unit/test_model_prices_and_context_window.py` L972-L990: upstream's `test_gemini_4_carbon_rows_share_the_gemini_3_search_allowance_in_both_cost_map_copies` from #50951, copied verbatim

Upstream main no longer requires the legacy `max_tokens` field (#48471), so the backported rows leave it out. v1.110.0 reads `supports_continuation` (`litellm.supports_continuation`), so the `gemini/`, `vertex_ai/` and cyber-permissive rows carry it again, as upstream main's rows do

## Vertex AI context caching

- `litellm/llms/vertex_ai/context_caching/vertex_ai_context_caching.py` L82-L109, L568-L577, L728: when the `cachedContents` creation call fails with a 400, which Google answers for a model without explicit caching support (`gemini-4-argon`: "does not support explicit context caching") or content below the cache minimum, `_warn_cache_creation_rejected` logs a warning and the request goes out uncached with the original messages and `tools`/`tool_choice`. Every other status (401, 403, 429, 5xx) raises `VertexAIError` as upstream does. The sync path restores the tools it already popped. The async path raises `_CachedContentsCreationRejectedError` out of upstream's single-flight `lookup_or_create`; it subclasses upstream's `_CachedContentsNotServedError`, so upstream's own 404 skip degrades it before the tools are popped. Claude Code always sends `cache_control`, so raising on the 400 failed every request for those models. Upstream still raises as of v1.110.2
- `tests/unit/llms/vertex_ai/context_caching/test_vertex_ai_context_caching.py` L463, L473, L476-L482, L489-L490, L505-L541, L543, L791-L870: the sync and async 400 tests assert the degrade contract (full prompt returned, tools restored, no cache name), and 401, 403, 429 and 503 still raise on the sync path; timeout tests keep raising 408
- `tests/unit/llms/vertex_ai/context_caching/test_known_cached_contents.py` L349-L361: an async 400 for the model degrades to an uncached request, next to upstream's restored `test_async_create_http_error_surfaces_its_status_code`


## Build, ops and misc

- `.github/workflows/fork-docker-build.yml` L1-L93: fork image build, datetime-stamped tags
- `.github/workflows/{auto-close-duplicates,codeql,create-rc-branch,e2e_record_replay,image-scan,interactions-spec-canary,osv-scan,scorecard,stale,test-integration}.yml`: cron `schedule` triggers removed so nothing runs on a timer in the fork
- `ui/litellm-dashboard/src/lib/http/schema.d.ts`: generated API schema types (`listed_model_names`)
- `litellm/proxy/_lazy_openapi_snapshot.json`: generated OpenAPI snapshot (`listed_model_names`)

## Absorbed by upstream (no longer carried)

Every drop below was verified by reverting the patch and rerunning its tests or an end-to-end probe

### v1.110.3

Nothing absorbed. The 14 commits between v1.110.2 and v1.110.3 (audit log rows stored before #50929 read and decoded before masking, Gemini pass-through file ownership on get and delete, MCP gateway DCR client registration made opt-in, the router reroute fallback fix in `litellm-rust`, and version bumps) touch no file the fork patches. The rollup was rebased straight onto v1.110.3 with no conflicts and the fork delta is byte-identical against the old base. The `_types.py` change is a masking refactor inside `LiteLLM_AuditLogs` with no new request or response fields

### Fork cleanup on v1.110.2

A review of every patch against v1.110.2 removed or reshaped these. Each drop was checked by restoring upstream's code and rerunning the fork's and upstream's tests

- `/decider` pass-through (`litellm/llms/vertex_ai/passthrough/`, the route in `llm_passthrough_endpoints.py`, its `_lazy_features.py` and `_types.py` entries, `test_decider_pass_through_endpoints.py`): replaced by the `vertex_ai` decisions provider on upstream's `/v1/systemone`. The route relayed any path to any router group, and a model named only in `?model=` skipped the key's model access check. The `/v1/evaluate`, `/v1/sessions` and `/health` relays went with it
- `litellm/llms/azure/chat/gpt_reasoning_transformation.py` and its tests: upstream already turns the 400 a tiny `max_completion_tokens` gets into an empty `finish_reason: "length"` response (`azure.py`, `openai/common_utils.py`)
- `tests/unit/llms/bedrock_mantle/chat/test_bedrock_mantle_transformation.py`: upstream's own Mantle tests cover the gpt-5.6/gpt-6 `max_completion_tokens` mapping
- `litellm/integrations/shadow_eval_logger.py`: upstream's check matches the typed `web_search_20250305` tool every recorded Claude Code request uses
- `litellm/litellm_core_utils/prompt_templates/factory.py` and its test: both `/v1/messages` entry points repair nameless tool_use blocks before any bridge dispatch, and OpenAI-format clients never produce them
- `AnthropicWebSearchResult`, `AnthropicWebSearchResultBlock` and the builder body: the Responses bridge builds the block with upstream's `WebSearchTransformation` from upstream's `SearchResult`
- the tools-first reorder in the adapter, the `dict.fromkeys` wrappers in `proxy/utils.py`, the fork's rewrite of upstream's two tool_reference tests, three `test_model_checks.py` tests and the headroom stream_options test: upstream already covers each one

Reshaped rather than dropped: the budget exemption now reads the router only through `registry()` and `settings()` and lives inside upstream's `request_skips_budget_checks` (upstream's router surface and recursion CI checks pass again, and the router-time fallback check works with the `RoutingContext` it really gets), the chat bridge keeps `bash`, `text_editor` and `memory` for Claude targets, and the context-caching fallback applies only to a 400

### v1.110.1 and v1.110.2

Nothing absorbed. Both patch releases stack on v1.110.0 from `stable/1.110.x`, so the fork rollup was rebased straight onto v1.110.2 with no conflicts. They mostly fix the Responses bridge (system prompts sent as input messages so GPT-6.2 caches them, stored-chain lookups, no stream restarts once output reached the client), plus `/key/info` ownership checks, JWT issuer mapping, Claude `temperature=1`, forwarded-credential pricing and a Rust router memory leak. Only `responses_adapters/transformation.py` and its test file overlap the fork, and the fork's web search hunks there moved down 9 and 42 lines unchanged

### v1.110.0

Absorbed by the release:

- `litellm/proxy/management_endpoints/key_management_endpoints.py` and its two `info_key_fn` tests in `test_key_management_endpoints.py`: upstream now returns 400 from `/key/info` when neither `?key=` nor an authenticated virtual key is present (`test_info_key_fn_no_key_returns_400_not_500`), and its `not key` check also catches an empty string, so the file and its tests match upstream again
- `.github/workflows/weekly_load_anomaly.yml`: upstream deleted the workflow, so the fork's cron strip went with it

Every other fork patch was rechecked by restoring upstream's v1.110.0 copy of each fork-modified file in `litellm/` one at a time and rerunning the fork's tests. Each restore failed a fork test or an upstream test the fork keeps green (`test_token_counter.py` for the tool-key set, `tests/unit/proxy/guardrails` for `anthropic_sse.py`), except `shadow_eval_logger.py`, which no test covers and which still matters because upstream's web search check misses the bare hosted `web_search` tool. `_lazy_features.py` and `_types.py` have no test either, and upstream has no `/decider` route. The `gemini-4-carbon` rows are still not in upstream's cost map, so that backport stays

Hand merges: upstream moved `drop_non_python_regex_patterns` into `json_schema_utils` and split tool result handling into `_tool_message`, which now carries `tool_catalog` too. Upstream translates tools after metadata and tool choice, and the fork still translates them first so tool_reference expansion has a catalog, then passes the catalog into upstream's later message translation, which now takes a `ChatRouteInputs` route. `native/handler.py` was rebuilt from upstream's copy (new `_BridgeTarget` call site) with the fork's web search routing added as an optional `tools` argument. The two price maps keep upstream's new `bedrock_mantle/gpt-terra-latest` alias beside the fork's `gemini-4-carbon` rows, and `osv-scan.yml` again keeps upstream's branches but not the cron. The fork's history was squashed into one rollup commit on v1.110.0, like the v1.103.0 rollup, because the first fork commit conflicted with code later fork commits rewrote

`tests/unit/test_utils.py::test_oidc_google_api_key_fails_closed_when_the_metadata_server_fails_and_recovers_on_the_next_call` fails in this sandbox on a clean v1.110.0 checkout as well, so it is an upstream or environment issue, not a fork regression

### v1.109.1

Absorbed by the release:

- `litellm/litellm_core_utils/streaming_handler.py`: upstream guards choice-less chunks on all three accumulation paths and moved the accumulation into `_accumulate_streamed_delta`, so the fork's guard is gone
- `model_prices_and_context_window.json`, `litellm/model_prices_and_context_window_backup.json`, `model_prices_and_context_window.schema.json`: v1.109.1 ships all six gpt-6.1-terra rows (its base `gpt-6.1-terra` row is newer than the fork's copy) and deleted the schema file, so the terra backport is dropped whole
- `litellm/proxy/anthropic_endpoints/gateway_endpoints.py`, `litellm/proxy/_types.py`, `tests/unit/proxy/anthropic_endpoints/test_gateway_endpoints.py`, `tests/unit/proxy/auth/test_route_checks.py`: upstream mounts `model_list` at `GET /claude_code_gateway/v1/models` behind the gateway flag, lists it in `MODEL_LIST_ROUTES` and tests discovery, auth and the disabled gateway itself. The fork's route, its `anthropic_routes` entry and its tests are dropped
- `litellm/types/llms/anthropic.py`: upstream added its own `AnthropicResponseContentBlockServerToolUse` and `AnthropicResponseContentBlockWebSearchToolResult`. They were defined after the fork's copies and shadowed them, so the fork's copies are gone and fork callers build upstream's models
- `litellm-rust/crates/llms-types/src/providers/anthropic/beta.rs`: the Databricks beta patch and its v1.108.0 revert both drop out, leaving upstream's file untouched

This is a jump from the `lts/1.108.x` line to a tag cut from main, so it carries everything main gained since 1.108 branched, including the move of `litellm/llms/anthropic/pass_through/` to `litellm/llms/anthropic/messages/` (with `pass_through/messages/` becoming `messages/native/`). Fork files and imports follow the new paths, and the old package stays importable through upstream's shim. Upstream also renamed `gpt_5_transformation.py` to `gpt_reasoning_transformation.py` for OpenAI and Azure, moved the Vertex partner `llama3` config to `llama`, and switched the openai_like stream to an SSE line splitter

Some v1.108.x behavior was LTS-only and is not on main at v1.109.1, so it is gone with the base rather than dropped by the fork. The bridge no longer keeps encrypted reasoning for requests that end in the Responses API (`ChatRouteInputs` and `openai_thinking_routes_to_responses` do not exist on main), and the chat bridge no longer answers 400 for `mcp_servers` a translated route cannot run. The fork's merged `translate_anthropic_to_openai` therefore follows main: it builds the request, converts tools first for the tool_reference catalog, then converts messages with the fork's `tool_catalog`, then metadata, tool choice and thinking. LTS-only tests that rode along in conflict blocks (the MCP server tests in `test_handler_output_config_passthrough.py`, the `acompact_responses` assert in `test_utils.py`) were removed, and the gpt-6.1-terra `INTENDED_SCHEMA` test hunk went with upstream's inline schema

Hand merges: `_should_route_to_responses_api` takes the fork's `model`/`tools`/`model_info` plus upstream's new `stop_sequences` veto, and passes `model_info` into upstream's 4-argument `_responses_mode_is_lost_by_prefix_strip`. `_should_skip_budget_checks` keeps upstream's route skip ahead of the MCP discovery skip. Vertex partner models apply upstream's `messages_with_file_parts_as_image_urls` before the fork's system message merge. The dashboard skip-budget-checks switch sits after upstream's new Kubernetes pod discovery switch, and the edit form's zod shape already carried it. The lazy OpenAPI snapshot and dashboard API types regenerate unchanged

### v1.108.4

Absorbed by the releases (v1.108.2 through v1.108.4 stack on v1.108.1 from `lts/1.108.x`, so the fork commits were rebased straight onto v1.108.4):

- `.github/workflows/{auto_update_price_and_context_window,sync-together-ai-models,weekly_load_anomaly}.yml`: the fork only stripped their cron triggers. Upstream deleted all three workflows (#48473, #49722), so the fork hunks went with them

Nothing else was absorbed. The releases mostly carry Anthropic `/v1/messages` bridge fixes for encrypted reasoning (keep it on tool turns, retry once without it when a backend cannot decrypt it, stop SDK retries resending a rejected block), MCP server handling on translated routes (#48931), Bedrock structured output, service tier and pass-through guardrail fixes, a router wildcard fix for team deployments and a filelock and oauthlib bump. Upstream's `translate_anthropic_to_openai` now converts messages after tools and thinking so the route can decide whether encrypted reasoning survives, and passes `api_base` and `reasoning_summary` through. The fork keeps converting tools first (tool_reference expansion needs the translated catalog), so the merged method runs tools, metadata, tool choice, thinking, then messages with both upstream's `route` and the fork's `tool_catalog`. `create-rc-branch.yml` keeps dropping upstream's new Monday cron. The other conflicts were imports and tests both sides appended at the same spot, and `messages/handler.py` keeps upstream's new `may_name_litellm_mcp_gateway` import while still dropping `AllAnthropicToolsValues`. The gpt-6.1-terra price rows are still not upstream, and the lazy OpenAPI snapshot and dashboard API types regenerate unchanged

### v1.108.1

Nothing absorbed. The patch release stacks on v1.108.0 from `lts/1.108.x` and backports router cooldown fixes for string fallback targets, aiohttp session lifetime fixes, Bedrock guardrail and claude_platform pricing, Gemini audio tier pricing, a Vertex tier price sync, Postgres timeouts on spend reads, team-deployment skipping for pass-through credentials and `custom_provider_map` video providers. It touches `litellm/utils.py`, `litellm/proxy/utils.py`, `litellm/types/llms/anthropic.py`, `tests/unit/test_utils.py` and both price JSONs beside the fork's hunks, which only moved down. Two hunks needed hand merging. The gpt-6.1-terra rows were re-appended onto v1.108.1's price maps, and `osv-scan.yml` keeps upstream's new `rc/**`, `stable/**` and `lts/**` pull request branches while still dropping its cron. The lazy OpenAPI snapshot and dashboard API types regenerate unchanged

### v1.108.0

Absorbed by the release:

- `litellm/llms/bedrock_mantle/chat/transformation.py`: the gpt-5.6/gpt-6 `max_completion_tokens` change (#43982) ships upstream, so the fork's copy is gone. Its unit tests stay, since upstream has none for it
- `litellm-rust/crates/llms-types/src/providers/anthropic/beta.rs`: v1.108.0 marks `dangerous-tool-use-2026-09-03` unsupported for Databricks in both `anthropic_beta_headers_config.json` and the Rust mirror (the Rust file moved from `providers/anthropic.rs`). The fork's line accepting Databricks in Rust would now disagree with the JSON map, so it is dropped

Nothing else was absorbed. This is a minor release jump from the 1.106.x stable line, so several hunks needed hand merging. Upstream added an MCP discovery bypass to `_should_skip_budget_checks`, which now runs ahead of the fork's `should_skip_budget_checks_for_model` call. `access_group_endpoints.update_access_group` normalizes `listed_model_names` beside upstream's new `access_skill_names`. `messages/handler.py` keeps the fork's `_shared_kwargs` routing, so upstream's `AllAnthropicToolsValues` cast is gone from that call. Upstream also dropped the `json` import from the Responses streaming iterator and `Any` from `litellm/types/llms/anthropic.py`, both of which fork code used; `json` is imported again and `AnthropicResponseContentBlockServerToolUse.input` is now `dict[str, object]`

Three upstream-side tests were adapted. The price map schema test now rejects unknown keys, so the gpt-6.1-terra `cache_creation_input_token_cost_above_12hr*` fields joined its intended schema. The headroom guardrail drops `stream_options` itself on stream conversion, so the fork's headroom test reads it with `.get`. The new `test_translate_anthropic_tools_to_openai_leaves_tools_deepcopy_cannot_copy_untouched` expected `input_examples` merged into the function parameters, which the fork strips as an Anthropic-only field, so it now asserts the field stays out

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

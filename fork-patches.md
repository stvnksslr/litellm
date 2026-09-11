# Fork patch manifest (delta vs upstream v1.100.0, `e4f2526570..7d3bd33e22`)

Line numbers are as of `7d3bd33e22`. For modified files they are diff-hunk ranges (`git diff e4f2526570..HEAD --unified=0`); for added files `L1-L<n>` is the full file. 130 files, +10,382 / -403, roughly 55% tests

## Agentic coding clients on the proxy (/v1/messages bridge)

- `litellm/llms/anthropic/experimental_pass_through/adapters/transformation.py` L98-L107, L136-L188 — import tool_schema/tool_search helpers; `_model_supports_web_search_options` gates web_search_options reduction
- `litellm/llms/anthropic/experimental_pass_through/adapters/transformation.py` L713-L731, L755 — pass `defer_loading` through tool translation; drop hosted tools; sanitize tool input_schema via `drop_uncompilable_patterns`
- `litellm/llms/anthropic/experimental_pass_through/adapters/transformation.py` L990-L1010 — forward deferred tools only when a tool_reference names them (or server-side search requested); web_search tool becomes `web_search_options` when model supports it
- `litellm/llms/anthropic/experimental_pass_through/adapters/transformation.py` L1125-L1134 — `_translate_stop_sequences_to_openai`
- `litellm/llms/anthropic/experimental_pass_through/adapters/transformation.py` L1164-L1214, L1249-L1259 — tool_reference blocks in messages expand to `<functions>` via `_tool_result_content`
- `litellm/llms/anthropic/experimental_pass_through/adapters/transformation.py` L1354-L1384 — `_count_openai_tool_calls`; one tool message per tool result
- `litellm/llms/anthropic/experimental_pass_through/adapters/transformation.py` L1508-L1521 — compaction-block insertion; truncated tool calls map to `max_tokens` finish reason
- `litellm/llms/anthropic/experimental_pass_through/adapters/tool_schema.py` L1-L51 — new: `drop_uncompilable_patterns` strips `pattern`/`patternProperties` regexes Python `re` cannot compile
- `litellm/llms/anthropic/experimental_pass_through/adapters/tool_search.py` L1-L79 — new: tool-search emulation; reference extraction, `forwards_tool`, `expand_tool_references` building the `<functions>` block
- `litellm/llms/anthropic/experimental_pass_through/adapters/handler.py` L14-L32 — import classifier + reasoning overrides and hosted-tool filter
- `litellm/llms/anthropic/experimental_pass_through/adapters/handler.py` L509-L525 — strip Anthropic hosted tools from forwarded tools; drop dangling `tool_choice`/`parallel_tool_calls` when tools emptied
- `litellm/llms/anthropic/experimental_pass_through/adapters/handler.py` L567-L572 — apply model-garden reasoning overrides then GLM classifier overrides before routing
- `litellm/llms/anthropic/experimental_pass_through/adapters/streaming_iterator.py` L564-L586, L805-L827 — guard empty `chunk.choices` before indexing; skip translation of choice-less chunks
- `litellm/llms/anthropic/experimental_pass_through/adapters/streaming_iterator.py` L1048-L1085 — do not treat choice-less chunk as final
- `litellm/llms/anthropic/experimental_pass_through/messages/handler.py` L36-L40, L76-L113, L116-L144 — `_declares_responses_endpoint` / `_deployment_supports_responses_api` from model_info, base_model or model cost
- `litellm/llms/anthropic/experimental_pass_through/messages/handler.py` L146, L633-L671 — thread `model_info` into `_should_route_to_responses_api` routing hook
- `litellm/llms/anthropic/experimental_pass_through/responses_adapters/transformation.py` L60-L269 — new: hosted web-search parsing (`web_search_call` query extraction, url-citation mapping, `_fold_to_anthropic_blocks` emitting server_tool_use -> web_search_tool_result -> text)
- `litellm/llms/anthropic/experimental_pass_through/responses_adapters/transformation.py` L611-L650, L781-L856 — translate web_search tool to Responses `web_search`; Responses-API `tool_choice` conversion using translated tool list
- `litellm/llms/anthropic/experimental_pass_through/responses_adapters/streaming_iterator.py` L11-L45, L75-L80 — helpers for content-block events; web-search state on wrapper
- `litellm/llms/anthropic/experimental_pass_through/responses_adapters/streaming_iterator.py` L113-L176, L220-L322 — record search sources from citations; queue `server_tool_use` + paired `web_search_tool_result` blocks; lazy thinking-block open
- `litellm/llms/anthropic/common_utils.py` L7-L8, L32-L33 — imports for web-search result types
- `litellm/llms/anthropic/common_utils.py` L59-L116 — new: `AnthropicWebSearchResult`, `web_search_result_from_source`, `build_anthropic_web_search_tool_result_block` shared by interception callback and Responses bridge
- `litellm/integrations/websearch_interception/transformation.py` L12-L15, L440-L452 — replace inline result-block dict with shared `build_anthropic_web_search_tool_result_block`
- `litellm/completion_extras/litellm_responses_transformation/transformation.py` L37, L490-L499 — drop `tools`/`tool_choice`/`parallel_tool_calls` when hosted-tool filtering empties the tool list
- `litellm/completion_extras/litellm_responses_transformation/transformation.py` L1074-L1080 — `_convert_tools_to_responses_format` skips Anthropic hosted tools
- `litellm/types/llms/anthropic.py` L634-L663 — new `AnthropicResponseContentBlockServerToolUse`, `AnthropicWebSearchResultBlock`, `AnthropicResponseContentBlockWebSearchToolResult` models
- `litellm/types/llms/anthropic.py` L756-L786 — `is_anthropic_hosted_tool_type` and `is_anthropic_web_search_tool` predicates
- `litellm/litellm_core_utils/streaming_chunk_builder_utils.py` L332-L354 — role fallback to "assistant" when no chunk carries choices (empty-stream guard)
- `litellm/litellm_core_utils/streaming_handler.py` L2216-L2221 — guard choice-less chunks in `response_uptil_now` accumulation
- `litellm/llms/openai_like/chat/handler.py` L18-L19, L52, L92 — stream via `OpenAIChatCompletionStreamingHandler` so `reasoning_content` deltas and mid-stream errors surface
- `litellm/llms/custom_httpx/llm_http_handler.py` L2945-L2947, L5476-L5502 — thread `litellm_metadata`/`request_data`/`call_type` into responses streaming call

## GPT-5.6 family enablement

- `model_prices_and_context_window.json` — full GPT-5.6 set: three named variants, regional Azure deployments, dated aliases, 1.25x Azure cache-write prices
- `litellm/model_prices_and_context_window_backup.json` — generated backup copy of the same entries
- `litellm/llms/openai/chat/gpt_5_transformation.py` L110-L148 — `_gpt_5_minor_version` regex matched anywhere in deployment name; version-based `is_model_gpt_5_2/5_4/5_4_plus` checks; new `is_model_gpt_5_6_plus_model`
- `litellm/llms/azure/chat/gpt_5_transformation.py` L15-L23, L149-L159 — floor `max_completion_tokens` at 3 (`AZURE_GPT5_MIN_COMPLETION_TOKENS`) so one-token availability probes get empty-with-`length` instead of 400

## Spend accuracy

- `litellm/litellm_core_utils/llm_cost_calc/utils.py` L946-L948 — cache-creation cost falls back to input rate when no explicit cache-write price resolves
- `litellm/litellm_core_utils/litellm_logging.py` L3716-L3748 — unwrap Responses terminal events before the `self.stream` guard so faked streams still cost
- `litellm/proxy/hooks/proxy_track_cost_callback.py` L23, L76-L90, L180-L185 — `_resolve_failure_log_model` fills model on failed spend logs from `get_model_from_request` route resolver
- `litellm/proxy/auth/auth_exception_handler.py` L60-L88, L144-L146 — `_append_requested_model_to_budget_error` appends requested model to BudgetExceededError message

## Budget controls

- `litellm/proxy/auth/auth_checks.py` L123-L124, L352-L459 — zero-cost cache keyed by (team_id, model); `_is_model_cost_zero` team-aware via `_is_cost_explicitly_configured`
- `litellm/proxy/auth/auth_checks.py` L508-L719 — `_get_deployments_for_model` (aliases, wildcard routes), `_is_model_budget_exempt` (`model_info.skip_budget_checks` on all deployments), request-model resolution, fallback-target reachability, `should_skip_budget_checks_for_model`
- `litellm/proxy/auth/auth_checks.py` L4053-L4110 — `_get_listed_models_from_access_groups` (see Model discovery)
- `litellm/proxy/auth/user_api_key_auth.py` L58, L1550-L1556, L1967-L1973 — call `_should_skip_budget_checks` with `valid_token` in both auth paths, replacing inline zero-cost check
- `litellm/proxy/auth/user_api_key_auth.py` L2605, L2723-L2741 — `_should_skip_budget_checks` passes request `fallbacks` (validated list only) into `should_skip_budget_checks_for_model`
- `litellm/proxy/hooks/max_budget_limiter.py` L43-L59 — post-auth budget hook honors zero-cost/exempt models via `should_skip_budget_checks_for_model`
- `litellm/types/router.py` L167-L170 — `ModelInfo.skip_budget_checks` field

## Vertex Model Garden coding models

- `litellm/litellm_core_utils/prompt_templates/common_utils.py` L14, L1667-L1702 — `merge_system_messages_to_front` folds all system messages into one leading message
- `litellm/llms/vertex_ai/vertex_ai_partner_models/main.py` L11-L14, L230-L232 — merge system messages on partner-models dispatch
- `litellm/llms/vertex_ai/vertex_model_garden/main.py` L24-L28, L135-L137 — merge system messages on model garden route
- `litellm/llms/vertex_ai/vertex_model_garden/transformation.py` L1-L39 — new `VertexAIModelGardenOpenAIConfig`: declares `reasoning_effort`, unwraps summary-wrapped adaptive-effort form to plain tier
- `litellm/litellm_core_utils/get_supported_openai_params.py` L200-L205 — route `openai/` Vertex prefix to the new config
- `litellm/utils.py` L2945 — best-effort model lookup, None on failure
- `litellm/utils.py` L3984-L3989 — drop `stream_options` in `pre_process_non_default_params` unless `stream is True`
- `litellm/utils.py` L8219-L8224 — `ProviderConfigManager` returns model-garden config for `openai/` Vertex prefix
- `litellm/llms/anthropic/experimental_pass_through/adapters/model_garden_reasoning.py` L1-L91 — new: Qwen/GLM family detection; Qwen gets `chat_template_kwargs.enable_thinking: false` and effort mapped to low/medium/xhigh; GLM defaults to `low`, requested tier collapsed to low/high
- `litellm/llms/anthropic/experimental_pass_through/adapters/claude_code_classifier.py` L1-L43 — new: detect classifier request by `</block>` stop sequence; floor GLM `max_tokens` at 4096

## Model discovery and access groups

- `litellm/proxy/utils.py` L7344-L7362, L7444-L7466 — team with access groups bounded to `_get_listed_models_from_access_groups`; no fall-through to all proxy models
- `litellm/proxy/auth/auth_checks.py` L4053-L4110 — `_get_listed_models_from_access_groups` reads `listed_model_names` from team/key access groups
- `litellm/proxy/auth/model_checks.py` L204-L209, L222, L248-L251 — strip `no-default-models` sentinel from granted list; dedupe wildcard + concrete entries
- `litellm/proxy/proxy_server.py` L10174 — dedupe access-group names into `/v1/models` list
- `litellm/models/access_group.py` L18 — `listed_model_names` field on access group table model
- `litellm/types/access_group.py` L10, L21, L33 — `listed_model_names` on create/update request and response models
- `litellm/proxy/management_endpoints/access_group_endpoints.py` L339, L439 — wire field through create/update handlers
- `litellm/proxy/schema.prisma` L1389, `schema.prisma` L1389 — `listed_model_names String[]` column in both schemas
- `litellm-proxy-extras/litellm_proxy_extras/migrations/20260715120000_add_listed_model_names_to_access_group_table/migration.sql` L1-L3 — matching migration

## Hardening and platform

- `litellm/proxy/management_endpoints/key_management_endpoints.py` L909-L912 — capture team_id before defaults loop; session-token exemption only when caller explicitly requested a team key

## Dashboard (ui/litellm-dashboard)

- `src/app/(dashboard)/access-groups/_components/AccessGroupBaseForm.tsx` — `listedModelNames` field on access group base form
- `src/app/(dashboard)/access-groups/_components/AccessGroupEditModal.tsx` — prefill `listedModelNames`; send only when Models tab visited
- `src/app/(dashboard)/access-groups/_components/AccessGroupsDetailsPage.tsx` — Listed Models tab with count badge
- `src/app/(dashboard)/access-groups/_components/AccessGroupsPage.tsx` — map `listed_model_names` into row type
- `src/app/(dashboard)/access-groups/_components/access-group-create/schema.ts` — `listedModelNames` in create schema
- `src/app/(dashboard)/access-groups/_components/access-group-create/mapper.ts` — send `listed_model_names` when non-empty
- `src/app/(dashboard)/access-groups/_components/types.ts` — `listedModelNames` on shared type
- `src/app/(dashboard)/hooks/accessGroups/useAccessGroups.ts`, `useEditAccessGroup.ts` — `listed_model_names` on API types
- `src/components/add_model/advanced_settings.tsx` — skip-budget-checks switch on add-model advanced settings
- `src/components/add_model/handle_add_model_submit.tsx` — map `skip_budget_checks` into `model_info`
- `src/components/ModelInfoEditForm.tsx` — skip-budget-checks field in edit form and read-only display
- `src/components/model_info_view.tsx` — persist `skip_budget_checks` in model_info update
- `src/components/team/TeamInfo.tsx` — reset-spend confirm dialog wiring to upstream endpoint
- `src/components/team/TeamMemberTab.tsx` — pass reset-spend handler to member table
- `src/components/common_components/MemberTable.tsx` — optional ResetSpend row action with visibility predicate
- `src/components/common_components/IconActionButton/TableIconActionButtons/TableIconActionButton.tsx` — ResetSpend icon action
- `src/components/networking.tsx` — `teamMemberResetSpendCall` POSTing `/team/{id}/member/{uid}/reset_spend`; dedupe model list by id

## Tests

- `tests/proxy_unit_tests/test_user_api_key_auth.py` L273-L391 — skip-budget-checks behavior in auth builder
- `tests/test_litellm/litellm_core_utils/llm_cost_calc/test_llm_cost_calc_utils.py` L3950-L4146 — cache-write price fallback regression
- `tests/test_litellm/litellm_core_utils/prompt_templates/test_litellm_core_utils_prompt_templates_common_utils.py` L1437-L1465 — system message merging
- `tests/test_litellm/litellm_core_utils/test_litellm_logging.py` L5997-L6047 — faked-stream terminal event costing
- `tests/test_litellm/litellm_core_utils/test_streaming_chunk_builder_utils.py` L632-L739 — role fallback on choice-less streams
- `tests/test_litellm/llms/anthropic/experimental_pass_through/adapters/test_anthropic_experimental_pass_through_adapters_transformation.py` L803-L889 — content translation; L3288-L3321 web-search predicate; L4270-L4328 tool_reference expansion; L4762-L4899 output config gating
- `tests/test_litellm/llms/anthropic/experimental_pass_through/adapters/test_claude_code_classifier.py` L1-L73 — classifier detection and max_tokens floor
- `tests/test_litellm/llms/anthropic/experimental_pass_through/adapters/test_claude_code_request_shapes.py` L1-L259 — stage-1/stage-2/probe/main-loop request shapes over fixtures
- `tests/test_litellm/llms/anthropic/experimental_pass_through/adapters/test_handler_hosted_tool_stripping.py` L1-L186 — hosted tool stripping and dangling tool_choice
- `tests/test_litellm/llms/anthropic/experimental_pass_through/adapters/test_handler_output_config_passthrough.py` L207-L309, L340-L423 — output config stripping, prompt cache forwarding
- `tests/test_litellm/llms/anthropic/experimental_pass_through/adapters/test_model_garden_reasoning.py` L1-L148 — Qwen/GLM reasoning defaults and tier mapping
- `tests/test_litellm/llms/anthropic/experimental_pass_through/adapters/test_streaming_iterator_combined_chunk.py` L146-L201 — delayed usage chunk cache tokens
- `tests/test_litellm/llms/anthropic/experimental_pass_through/adapters/test_streaming_iterator_first_delta.py` L1029-L1089 — tool block start flush
- `tests/test_litellm/llms/anthropic/experimental_pass_through/adapters/test_tool_schema.py` L1-L103 — uncompilable pattern stripping
- `tests/test_litellm/llms/anthropic/experimental_pass_through/adapters/test_tool_search.py` L1-L101 — reference expansion and deferred tool forwarding
- `tests/test_litellm/llms/anthropic/experimental_pass_through/messages/test_anthropic_experimental_pass_through_messages_handler.py` L785, L955-L1100 — responses-endpoint routing gate
- `tests/test_litellm/llms/anthropic/experimental_pass_through/responses_adapters/test_responses_adapters_streaming_iterator.py` L311-L551 — streaming web-search block emission
- `tests/test_litellm/llms/anthropic/experimental_pass_through/responses_adapters/test_responses_adapters_transformation.py` L815-L853, L1991-L2157 — web_search tool translation, tool_choice; prompt cache breakpoints
- `tests/test_litellm/llms/anthropic/test_anthropic_common_utils.py` L1606 — web-search block builder
- `tests/test_litellm/llms/azure/chat/test_azure_gpt5_transformation.py` L52-L128 — Azure min-token floor; 1.25x cache-write price resolution
- `tests/test_litellm/llms/custom_httpx/test_llm_http_handler.py` L3003-L3051 — responses call threading
- `tests/test_litellm/llms/databricks/test_streaming_utils.py` L1-L72 — choice-less chunk guard
- `tests/test_litellm/llms/openai/test_is_model_gpt_5_model.py` L158-L219 — gpt-5.6 version detection in deployment names
- `tests/test_litellm/llms/openai_like/chat/test_openai_like_handler.py` L1-L124 — reasoning passthrough streaming
- `tests/test_litellm/llms/vertex_ai/test_vertex_system_message_merge.py` L1-L112 — system message merging
- `tests/test_litellm/llms/vertex_ai/vertex_model_garden/test_vertex_model_garden_transformation.py` L1-L55 — reasoning_effort declaration and unwrapping
- `tests/test_litellm/proxy/auth/test_auth_checks.py` L5226-L5256 — model discovery route budget bypass; L7459-L7506 — listed-models fallback targets
- `tests/test_litellm/proxy/auth/test_model_budget_exempt.py` L1-L644 — per-model budget exemption matrix
- `tests/test_litellm/proxy/auth/test_model_checks.py` L806-L912 — sentinel strip and dedupe in model list
- `tests/test_litellm/proxy/auth/test_unmapped_model_budget_enforcement.py` L136-L138 — unmapped model enforcement update
- `tests/test_litellm/proxy/auth/test_user_api_key_auth.py` L4, L330 — skip-budget-checks signature update
- `tests/test_litellm/proxy/common_utils/test_reset_budget_job.py` L1383-L1385 — reset job signature adjustment
- `tests/test_litellm/proxy/guardrails/guardrail_hooks/test_headroom.py` L2335-L2367 — stream_options dropped on non-streaming conversion
- `tests/test_litellm/proxy/hooks/test_proxy_track_cost_callback.py` L1639-L1701 — failure log model resolution
- `tests/test_litellm/proxy/management_endpoints/test_access_group_endpoints.py` L29-L93, L199-L217 — listed_model_names in create/update payloads
- `tests/test_litellm/proxy/utils/helpers/test_model_access.py` L376-L428 — access-group listed-models bounding
- `tests/test_litellm/completion_extras/litellm_responses_transformation/test_completion_extras_litellm_responses_transformation_transformation.py` L819-L974 — hosted tool drop; L2640-L2685 — tool_choice handling
- `tests/test_litellm/test_main.py` L1243-L1288 — model garden config resolution
- `tests/test_litellm/test_utils.py` L5768-L5815 — stream_options drop unless streaming
- Fixtures: `tests/test_litellm/llms/anthropic/experimental_pass_through/adapters/fixtures/claude_code_2_1_266/` — recorded Claude Code 2.1.266 payloads (main_loop, main_loop_title_no_thinking, probe_stage1_sonnet5, stage1, stage2, tool_search_stage1, tool_search_stage2)

## Build, ops and misc

- `.github/workflows/fork-docker-build.yml` L1-L93 — fork image build, datetime-stamped tags
- `cookbook/litellm_proxy_server/grafana_dashboard/background_jobs/grafana_dashboard.json` L1-L429 — background-job health dashboard
- `local/claude-code/Dockerfile` L1-L11, `local/copilot-cli/Dockerfile` L1-L11 — dev containers pointing the two CLIs at a dev proxy
- `basedpyright-code-budget.json` L138 — budget ratchet
- `ui/litellm-dashboard/src/lib/http/schema.d.ts` — generated API schema types
- `litellm/proxy/_lazy_openapi_snapshot.json` — generated OpenAPI snapshot
- `.pr_body_budget_model.md`, `.pr_body_team_member_reset_spend.md` — scratch PR-body drafts, cleanup candidates

"""
Handles Authentication Errors
"""

from typing import TYPE_CHECKING, Any, Optional, Union

from fastapi import HTTPException, Request, status

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import (
    LitellmUserRoles,
    ProxyErrorTypes,
    ProxyException,
    UserAPIKeyAuth,
)
from litellm.integrations.otel.runtime import seed_request_identity
from litellm.proxy.auth.auth_utils import (
    _get_request_ip_address,
    get_model_from_request,
)
from litellm.proxy.common_utils.http_parsing_utils import (
    _safe_get_request_headers,
    _safe_get_request_query_params,
)
from litellm.proxy.db.exception_handler import PrismaDBExceptionHandler
from litellm.types.services import ServiceTypes

# Sentinel user_id for the synthetic UserAPIKeyAuth issued during a DB
# outage when allow_requests_on_db_unavailable is True. Downstream
# enforcement can key off this value; it must never collide with a real
# user_id.
DB_UNAVAILABLE_FALLBACK_USER_ID = "__db_unavailable_fallback__"

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    Span = Union[_Span, Any]
else:
    Span = Any


class UserAPIKeyAuthExceptionHandler:
    @staticmethod
    def _append_requested_model_to_budget_error(e: Exception, request: Request, request_data: dict, route: str) -> None:
        """
        Budget checks fire during auth, before the request is routed, so most
        BudgetExceededError messages never name the model the caller asked for.
        Append it here, before the failure hook logs the error and before it is
        converted to a ProxyException, so the requested model reaches the client
        response, the proxy logs, and the Logs UI error_information.

        get_model_from_request is the same resolver the budget checks use, so the
        named model matches the one that was evaluated and also covers routes that
        carry the model in the path or query (e.g. Azure deployments) rather than
        the body. Re-syncing e.args keeps str(e) in step with e.message, since
        get_error_information records str(original_exception) as error_message.
        """
        if not isinstance(e, litellm.BudgetExceededError):
            return
        requested_model = get_model_from_request(
            request_data=request_data,
            route=route,
            request_headers=_safe_get_request_headers(request=request),
            request_query_params=_safe_get_request_query_params(request=request),
        )
        if isinstance(requested_model, list):
            requested_model = ", ".join(requested_model) if requested_model else None
        if requested_model and f"model={requested_model}" not in e.message:
            e.message = f"{e.message} Requested model: {requested_model}"
            e.args = (e.message,)

    @staticmethod
    async def _handle_authentication_error(
        e: Exception,
        request: Request,
        request_data: dict,
        route: str,
        parent_otel_span: Optional[Span],
        api_key: str,
        resolved_identity: Optional[UserAPIKeyAuth] = None,
    ) -> UserAPIKeyAuth:
        """
        Handles Connection Errors when reading a Virtual Key from LiteLLM DB
        Use this if you don't want failed DB queries to block LLM API reqiests

        Reliability scenarios this covers:
        - DB is down and having an outage
        - Unable to read / recover a key from the DB

        Returns:
            - UserAPIKeyAuth: If general_settings.allow_requests_on_db_unavailable is True

        Raises:
            - Original Exception in all other cases
        """
        from litellm.proxy.proxy_server import (
            general_settings,
            proxy_logging_obj,
        )

        if (
            PrismaDBExceptionHandler.should_allow_request_on_db_unavailable()
            and PrismaDBExceptionHandler.is_database_connection_error(e)
        ):
            # log this as a DB failure on prometheus
            proxy_logging_obj.service_logging_obj.service_failure_hook(
                service=ServiceTypes.DB,
                call_type="get_key_object",
                error=e,
                duration=0.0,
            )

            # Non-admin restricted token so a DB outage cannot escalate
            # an anonymous caller to proxy-admin privileges.
            verbose_proxy_logger.warning(
                "Auth: DB unavailable — issuing restricted INTERNAL_USER "
                "fallback token (allow_requests_on_db_unavailable=True)"
            )
            return UserAPIKeyAuth(
                key_name="failed-to-connect-to-db",
                token="failed-to-connect-to-db",
                user_id=DB_UNAVAILABLE_FALLBACK_USER_ID,
                user_role=LitellmUserRoles.INTERNAL_USER,
                request_route=route,
            )
        else:
            UserAPIKeyAuthExceptionHandler._append_requested_model_to_budget_error(
                e=e, request=request, request_data=request_data, route=route
            )
            # raise the exception to the caller
            requester_ip = _get_request_ip_address(
                request=request,
                use_x_forwarded_for=general_settings.get("use_x_forwarded_for", False),
            )
            verbose_proxy_logger.exception(
                "litellm.proxy.proxy_server.user_api_key_auth(): Exception occured - {}\nRequester IP Address:{}".format(
                    str(e),
                    requester_ip,
                ),
                extra={"requester_ip": requester_ip},
            )

            # Log this exception to OTEL, Datadog etc. Reuse the identity resolved
            # before the failure (team alias/id, metadata, user) so the failed span
            # is labeled — a fresh UserAPIKeyAuth here would drop everything auth had
            # already looked up (e.g. an expired key whose team/user is known). Copy
            # so the handler is side-effect-free for the caller's identity object.
            user_api_key_dict = resolved_identity.model_copy() if resolved_identity is not None else UserAPIKeyAuth()
            user_api_key_dict.parent_otel_span = parent_otel_span
            user_api_key_dict.request_route = route
            user_api_key_dict.api_key = user_api_key_dict.api_key or UserAPIKeyAuth(api_key=api_key).api_key

            # Stamp identity onto the request's server span now, before the request
            # is rejected; the OTEL failure hooks don't touch the server span, so
            # without this the failed trace would carry no team/key attributes.
            seed_request_identity(
                user_api_key_dict,
                model=request_data.get("model"),
            )

            # Budget checks live in tenant-scoped helpers (key / team / org / tag)
            # that don't see the request model, so the BudgetExceededError they
            # raise carries `llm_provider=""`. Resolve it here off `request_data`
            # so custom-callback consumers reading StandardLoggingPayload get
            # the same `llm_provider` attribution as for RPM/TPM 429s.
            if isinstance(e, litellm.BudgetExceededError) and not e.llm_provider:
                from litellm.proxy.hooks.rate_limiter_utils import (
                    resolve_llm_provider_for_rate_limit,
                )

                _, e.llm_provider = resolve_llm_provider_for_rate_limit(request_data.get("model"))

            # Allow callbacks to transform the error response
            transformed_exception = await proxy_logging_obj.post_call_failure_hook(
                request_data=request_data,
                original_exception=e,
                user_api_key_dict=user_api_key_dict,
                error_type=ProxyErrorTypes.auth_error,
                route=route,
            )
            # Use transformed exception if callback returned one, otherwise use original
            if transformed_exception is not None:
                e = transformed_exception

            if isinstance(e, litellm.BudgetExceededError):
                raise ProxyException(
                    message=e.message,
                    type=ProxyErrorTypes.budget_exceeded,
                    param=None,
                    code=getattr(e, "status_code", status.HTTP_429_TOO_MANY_REQUESTS),
                )
            if isinstance(e, HTTPException):
                raise ProxyException(
                    message=getattr(e, "detail", f"Authentication Error({str(e)})"),
                    type=ProxyErrorTypes.auth_error,
                    param=getattr(e, "param", "None"),
                    code=getattr(e, "status_code", status.HTTP_401_UNAUTHORIZED),
                )
            elif isinstance(e, ProxyException):
                raise e
            if PrismaDBExceptionHandler.is_database_service_unavailable_error(e):
                raise ProxyException(
                    message=(
                        "Service Unavailable, the authentication database is "
                        "temporarily unreachable. Please retry shortly."
                    ),
                    type=ProxyErrorTypes.no_db_connection,
                    param="None",
                    code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            raise ProxyException(
                message="Authentication Error, " + str(e),
                type=ProxyErrorTypes.auth_error,
                param=getattr(e, "param", "None"),
                code=status.HTTP_401_UNAUTHORIZED,
            )

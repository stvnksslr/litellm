import json
from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

import pytest
import responses
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import litellm
from litellm.types.decisions import DecisionsResponse

_ENDPOINT_HOST: Final = "https://1234.us-central1-567.prediction.vertexai.goog"
_API_BASE: Final = f"{_ENDPOINT_HOST}/v1/projects/567/locations/us-central1/endpoints/1234/invoke/v1"
_URL: Final = f"{_API_BASE}/systemone"
_TOKEN_URL: Final = "https://oauth2.googleapis.com/token"
_QUESTIONS: Final[Mapping[str, object]] = MappingProxyType(
    {"is_refund": {"type": "noul", "instructions": "Is this a refund request?"}}
)
_RESPONSE: Final[Mapping[str, object]] = {
    "model": "/models/decider",
    "answers": {"is_refund": {"type": "noul", "noul": 0.93}},
    "usage": {"input_tokens": 12, "output_tokens": 1},
}


@pytest.fixture(autouse=True)
def httpx_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(litellm, "disable_aiohttp_transport", True)


def _service_account() -> str:
    key: Final = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem: Final = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    return json.dumps(
        {
            "type": "service_account",
            "project_id": "567",
            "private_key_id": "synthetic",
            "private_key": pem,
            "client_email": "decider@567.iam.gserviceaccount.com",
            "client_id": "1",
            "token_uri": _TOKEN_URL,
        }
    )


@responses.activate
@pytest.mark.parametrize("use_async", (True, False), ids=("asystemone", "systemone"))
async def test_vertex_decider_calls_the_dedicated_endpoint_with_a_google_oauth_token(
    respx_mock: respx.MockRouter, use_async: bool
) -> None:
    token: Final = responses.post(_TOKEN_URL, json={"access_token": "vertex-oauth-token", "expires_in": 3600})
    route: Final = respx_mock.post(_URL).respond(json=_RESPONSE)
    kwargs: Final[Mapping[str, object]] = {
        "model": "vertex_ai/openai/decider",
        "state": "Customer asked for a refund",
        "questions": _QUESTIONS,
        "api_base": _API_BASE,
        "vertex_credentials": _service_account(),
        "vertex_project": "567",
    }

    result: Final = await litellm.asystemone(**kwargs) if use_async else litellm.systemone(**kwargs)

    assert isinstance(result, DecisionsResponse)
    assert result.answers["is_refund"].noul == 0.93
    assert token.call_count == 1
    sent: Final = route.calls.last.request
    assert sent.headers["Authorization"] == "Bearer vertex-oauth-token"
    assert json.loads(sent.content)["questions"] == _QUESTIONS


async def test_vertex_decider_prefers_a_configured_api_key_over_google_oauth(respx_mock: respx.MockRouter) -> None:
    route: Final = respx_mock.post(_URL).respond(json=_RESPONSE)

    await litellm.asystemone(
        model="vertex_ai/openai/decider",
        state="Customer asked for a refund",
        questions=_QUESTIONS,
        api_base=_API_BASE,
        api_key="static-token",
    )

    assert route.calls.last.request.headers["Authorization"] == "Bearer static-token"


async def test_vertex_decider_without_api_base_is_rejected_before_any_call(respx_mock: respx.MockRouter) -> None:
    with pytest.raises(litellm.BadRequestError, match="dedicated endpoint"):
        await litellm.asystemone(
            model="vertex_ai/openai/decider",
            state="Customer asked for a refund",
            questions=_QUESTIONS,
            api_key="static-token",
        )

    assert not respx_mock.calls

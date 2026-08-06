from litellm.llms.databricks.streaming_utils import ModelResponseIterator


def _parser():
    return ModelResponseIterator(streaming_response=iter([]), sync_stream=True)


def test_chunk_parser_usage_only_chunk_does_not_raise():
    """
    Regression: Databricks emits a final chunk with `choices: []` and a populated
    `usage` block when `stream_options={"include_usage": true}`. The parser must
    return a valid GenericStreamingChunk with usage attached instead of raising
    IndexError on `choices[0]`.
    """
    chunk = {
        "id": "chatcmpl-test",
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": "databricks-llama-3-70b-instruct",
        "choices": [],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }

    result = _parser().chunk_parser(chunk=chunk)

    assert result["text"] == ""
    assert result["is_finished"] is False
    assert result["finish_reason"] == ""
    assert result["tool_use"] is None
    assert result["usage"] is not None
    assert result["usage"]["prompt_tokens"] == 10
    assert result["usage"]["completion_tokens"] == 5
    assert result["usage"]["total_tokens"] == 15


def test_chunk_parser_empty_choices_no_usage():
    """Keepalive-style chunk: empty choices, no usage. Must not raise."""
    result = _parser().chunk_parser(chunk={"choices": []})

    assert result["text"] == ""
    assert result["is_finished"] is False
    assert result["finish_reason"] == ""
    assert result["tool_use"] is None
    assert result["usage"] is None


def test_chunk_parser_normal_content_chunk_unchanged():
    """Happy path: a standard content chunk still parses correctly."""
    chunk = {
        "id": "chatcmpl-test",
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": "databricks-llama-3-70b-instruct",
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": "hello"},
                "finish_reason": None,
            }
        ],
    }

    result = _parser().chunk_parser(chunk=chunk)

    assert result["text"] == "hello"
    assert result["is_finished"] is False
    assert result["finish_reason"] == ""
    assert result["usage"] is None

from agent.schemas import LLMResult
from llm.llm_client import LLMClient


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": "在线报告",
                    },
                },
            ],
        }


class NullChoicesResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": None}


class QuotaErrorResponse:
    status_code = 429
    text = '{"error":{"code":"insufficient_quota","message":"quota exceeded"}}'

    def raise_for_status(self):
        import requests

        raise requests.HTTPError("429 Client Error: Too Many Requests")


def clear_llm_env(monkeypatch):
    monkeypatch.setenv("LLM_DISABLE_ENV_FILE", "1")
    for key in (
        "LLM_PROVIDER",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "LLM_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)


def test_openai_compatible_provider_generates_online_report(monkeypatch):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "demo-model")
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    result = LLMClient(post=fake_post).generate("请生成报告")

    assert isinstance(result, LLMResult)
    assert result.mode == "online"
    assert result.content == "在线报告"
    assert calls[0]["url"] == "https://example.test/v1/chat/completions"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert calls[0]["headers"]["Content-Type"] == "application/json"
    assert calls[0]["json"]["model"] == "demo-model"
    assert calls[0]["json"]["temperature"] == 0.2
    assert any(
        message["role"] == "system"
        and "5G Core troubleshooting" in message["content"]
        for message in calls[0]["json"]["messages"]
    )
    assert calls[0]["json"]["messages"][-1] == {
        "role": "user",
        "content": "请生成报告",
    }


def test_missing_api_key_returns_offline_result(monkeypatch):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")

    result = LLMClient(post=lambda **kwargs: FakeResponse()).generate("请生成报告")

    assert result.mode == "offline"
    assert result.content == ""
    assert "LLM_API_KEY" in result.error


def test_whitespace_only_api_key_returns_offline_result(monkeypatch):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", " \t ")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("post should not be called without an API key")

    result = LLMClient(post=fail_if_called).generate("请生成报告")

    assert result.mode == "offline"
    assert result.content == ""
    assert "LLM_API_KEY" in result.error


def test_strips_online_llm_environment_values(monkeypatch):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", " test-key\n")
    monkeypatch.setenv("LLM_BASE_URL", " https://example.test/v1/ \n")
    monkeypatch.setenv("LLM_MODEL", " demo-model ")
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    result = LLMClient(post=fake_post).generate("请生成报告")

    assert result.mode == "online"
    assert calls[0]["url"] == "https://example.test/v1/chat/completions"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert calls[0]["json"]["model"] == "demo-model"


def test_blank_base_url_and_model_use_defaults(monkeypatch):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "  ")
    monkeypatch.setenv("LLM_MODEL", "\t")
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    result = LLMClient(post=fake_post).generate("请生成报告")

    assert result.mode == "online"
    assert calls[0]["url"] == "https://api.openai.com/v1/chat/completions"
    assert calls[0]["json"]["model"] == "gpt-4o-mini"


def test_explicit_offline_provider_returns_offline_result(monkeypatch):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    result = LLMClient(post=lambda **kwargs: FakeResponse()).generate("请生成报告")

    assert result.mode == "offline"
    assert result.content == ""
    assert "offline" in result.error


def test_http_call_exception_returns_offline_result(monkeypatch):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    def failing_post(*args, **kwargs):
        raise RuntimeError("network unavailable")

    result = LLMClient(post=failing_post).generate("请生成报告")

    assert result.mode == "offline"
    assert result.content == ""
    assert "network unavailable" in result.error


def test_null_choices_response_returns_readable_offline_error(monkeypatch):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    result = LLMClient(post=lambda *args, **kwargs: NullChoicesResponse()).generate("请生成报告")

    assert result.mode == "offline"
    assert "no choices" in result.error


def test_quota_error_response_returns_response_body(monkeypatch):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    result = LLMClient(post=lambda *args, **kwargs: QuotaErrorResponse()).generate("请生成报告")

    assert result.mode == "offline"
    assert "insufficient_quota" in result.error

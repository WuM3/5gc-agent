import os

from config import load_env_file


def test_load_env_file_ignores_comments_and_sets_values(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "# LLM_API_KEY=commented-key",
                "LLM_PROVIDER=openai_compatible",
                "LLM_API_KEY = real-key ",
                'LLM_MODEL="demo-model"',
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    loaded = load_env_file(env_path)

    assert loaded is True
    assert os.environ["LLM_PROVIDER"] == "openai_compatible"
    assert os.environ["LLM_API_KEY"] == "real-key"
    assert os.environ["LLM_API_KEY"] != "commented-key"
    assert os.environ["LLM_MODEL"] == "demo-model"


def test_load_env_file_does_not_override_existing_env(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("LLM_API_KEY=file-key", encoding="utf-8")
    monkeypatch.setenv("LLM_API_KEY", "existing-key")

    load_env_file(env_path)

    assert os.environ["LLM_API_KEY"] == "existing-key"


def test_load_env_file_overrides_blank_existing_env(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("LLM_BASE_URL=https://api-inference.modelscope.cn/v1", encoding="utf-8")
    monkeypatch.setenv("LLM_BASE_URL", "   ")

    load_env_file(env_path)

    assert os.environ["LLM_BASE_URL"] == "https://api-inference.modelscope.cn/v1"

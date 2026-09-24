import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Per-1K-token pricing (USD) for supported models.
# Keys are matched by prefix so dated snapshots (e.g. "gpt-4o-2024-08-06") work.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}

# Models that support the JSON response_format parameter.
JSON_MODE_MODELS = ("gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4-1106", "gpt-4-0125")

DEFAULT_MODEL = "gpt-4o"


def get_model_pricing(model: str) -> dict[str, float]:
    """Return {input, output} per-1K pricing for a model (prefix match)."""
    for prefix, pricing in MODEL_PRICING.items():
        if model.startswith(prefix):
            return pricing
    # Fall back to gpt-4 pricing if unknown
    return {"input": 0.03, "output": 0.06}


def supports_json_mode(model: str) -> bool:
    """Whether a model supports response_format={'type': 'json_object'}."""
    return model.startswith(JSON_MODE_MODELS)


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    SANDBOX_TIMEOUT: int = int(os.getenv("SANDBOX_TIMEOUT", "30"))
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "3"))
    MAX_TEST_FIX_ITERATIONS: int = int(os.getenv("MAX_TEST_FIX_ITERATIONS", "2"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///tasks.db")

    # Optional per-task budget cap in USD. 0 disables the cap.
    BUDGET_CAP_USD: float = float(os.getenv("BUDGET_CAP_USD", "0"))

    # Optional API key for protecting the backend. Leave empty to disable auth.
    BACKEND_API_KEY: str = os.getenv("BACKEND_API_KEY", "")

    # Available models the frontend can choose from
    AVAILABLE_MODELS: list[str] = [
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
    ]

    # Legacy default pricing (kept for backwards-compat; per-model pricing
    # is resolved dynamically via get_model_pricing()).
    INPUT_COST_PER_1K: float = 0.03
    OUTPUT_COST_PER_1K: float = 0.06


settings = Settings()
import time
from collections.abc import AsyncIterator

from app.cache.redis_cache import RedisSemanticCache
from app.core.config import settings
from app.core.exceptions import LLMProviderException
from app.core.logging import logger
from app.models.llm_response import LLMResult
from app.observability import metrics
from app.policies.retry import CircuitBreaker, RetryPolicy, TimeoutPolicy
from app.providers.llm_provider import LLMProvider

TOKEN_PRICING_PER_1K = {
    "openai": {"prompt": 0.00015, "completion": 0.0006},
    "gemini": {"prompt": 0.0001, "completion": 0.0004},
    "anthropic": {"prompt": 0.003, "completion": 0.015},
    "ollama": {"prompt": 0.0, "completion": 0.0},
    "azure_openai": {"prompt": 0.00015, "completion": 0.0006},
}


class LLMService:
    """Orchestrate provider calls with policies, cache, and metrics."""

    def __init__(
        self,
        provider: LLMProvider,
        cache: RedisSemanticCache | None = None,
        retry_policy: RetryPolicy | None = None,
        timeout_policy: TimeoutPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._retry_policy = retry_policy or RetryPolicy()
        self._timeout_policy = timeout_policy or TimeoutPolicy()
        self._circuit_breaker = circuit_breaker or CircuitBreaker()

    def _calculate_cost(self, provider_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = TOKEN_PRICING_PER_1K.get(provider_name, TOKEN_PRICING_PER_1K["openai"])
        return ((prompt_tokens / 1000) * pricing["prompt"]) + ((completion_tokens / 1000) * pricing["completion"])

    async def generate(self, prompt: str) -> LLMResult:
        """Generate a response with cache, retry, timeout, and metrics."""
        provider_name = self._provider.name
        cache_key = None
        if settings.CACHE_ENABLED and self._cache is not None:
            cache_key = self._cache.build_llm_key(provider_name, settings.MODEL_NAME, prompt)
            try:
                cached = await self._cache.get(cache_key)
            except Exception:
                cached = None
            if cached:
                metrics.CACHE_HITS.labels(namespace="llm").inc()
                return LLMResult.model_validate(cached)
            metrics.CACHE_MISSES.labels(namespace="llm").inc()

        start = time.perf_counter()

        async def _operation() -> LLMResult:
            return await self._provider.generate(prompt)

        try:
            result = await self._circuit_breaker.execute(
                lambda: self._retry_policy.execute(lambda: self._timeout_policy.execute(_operation))
            )
        except Exception as exc:
            metrics.REQUEST_COUNT.labels(provider=provider_name, endpoint="generate", status="error").inc()
            logger.error("LLM generation failed", extra={"provider": provider_name})
            raise LLMProviderException(str(exc)) from exc

        result.cost_usd = self._calculate_cost(provider_name, result.prompt_tokens, result.completion_tokens)
        elapsed = time.perf_counter() - start

        metrics.REQUEST_COUNT.labels(provider=provider_name, endpoint="generate", status="success").inc()
        metrics.REQUEST_LATENCY.labels(provider=provider_name, endpoint="generate").observe(elapsed)
        metrics.TOKEN_USAGE.labels(provider=provider_name, token_type="prompt").inc(result.prompt_tokens)
        metrics.TOKEN_USAGE.labels(provider=provider_name, token_type="completion").inc(result.completion_tokens)
        metrics.REQUEST_COST.labels(provider=provider_name).inc(result.cost_usd)

        if cache_key and self._cache is not None:
            try:
                await self._cache.set(cache_key, result.model_dump(), self._cache.default_ttl)
            except Exception:
                logger.warning("Failed to write LLM response to cache")

        return result

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Stream a response from the provider."""
        provider_name = self._provider.name
        start = time.perf_counter()
        try:
            async for chunk in self._provider.stream(prompt):
                yield chunk
        except Exception as exc:
            metrics.REQUEST_COUNT.labels(provider=provider_name, endpoint="stream", status="error").inc()
            raise LLMProviderException(str(exc)) from exc
        finally:
            metrics.REQUEST_LATENCY.labels(provider=provider_name, endpoint="stream").observe(
                time.perf_counter() - start
            )
            metrics.REQUEST_COUNT.labels(provider=provider_name, endpoint="stream", status="success").inc()

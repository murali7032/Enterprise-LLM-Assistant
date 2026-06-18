from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["provider", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "llm_request_latency_seconds",
    "LLM request latency in seconds",
    ["provider", "endpoint"],
)

TOKEN_USAGE = Counter(
    "llm_tokens_total",
    "Total tokens consumed",
    ["provider", "token_type"],
)

REQUEST_COST = Counter(
    "llm_cost_usd_total",
    "Total estimated LLM cost in USD",
    ["provider"],
)

CACHE_HITS = Counter(
    "llm_cache_hits_total",
    "Total cache hits",
    ["namespace"],
)

CACHE_MISSES = Counter(
    "llm_cache_misses_total",
    "Total cache misses",
    ["namespace"],
)

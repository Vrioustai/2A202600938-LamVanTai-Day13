"""Observability + mitigation layer - token-optimized version"""
from __future__ import annotations
import time, re, json, hashlib

# ── Logging ──────────────────────────────────────────────────────────────────
def log(tag, data):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{tag}] {json.dumps(data, ensure_ascii=False)}")

# ── PII detection ─────────────────────────────────────────────────────────────
def detect_pii(text):
    if not text:
        return []
    leaks = []
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text)
    phones = re.findall(r'\b0[0-9]{9,10}\b', text)
    if emails: leaks += [f"email:{e}" for e in emails]
    if phones: leaks += [f"phone:{p}" for p in phones]
    return leaks

# ── Loop detection ────────────────────────────────────────────────────────────
def has_loop(trace):
    if not trace or len(trace) < 3:
        return False
    actions = [s.get('action') for s in trace if s.get('action')]
    for i in range(len(actions) - 2):
        if actions[i] == actions[i+1] == actions[i+2]:
            return True
    return False

# ── Input sanitization (injection guard) ─────────────────────────────────────
_INJECT = re.compile(
    r'(ignore|disregard|bỏ qua).{0,30}(instruction|prompt|system|hướng dẫn)'
    r'|(system|admin)\s*:', re.I)

def sanitize(q):
    return _INJECT.sub('[REMOVED]', q)

# ── Cost estimate ─────────────────────────────────────────────────────────────
def cost_usd(usage, model='gpt-5.4-nano'):
    if not usage:
        return 0.0
    p = usage.get('prompt_tokens', 0)
    c = usage.get('completion_tokens', 0)
    rates = {'gpt-5.4-nano': (0.5, 1.5), 'gpt-5.4-mini': (1.0, 3.0)}
    r = rates.get(model, (1.0, 3.0))
    return (p * r[0] + c * r[1]) / 1_000_000

# ── Cache helpers ─────────────────────────────────────────────────────────────
def _cache_key(q):
    return hashlib.md5(q.lower().strip().encode()).hexdigest()

def cache_get(q, ctx):
    lock = ctx.get('cache_lock')
    cache = ctx.get('cache', {})
    if lock:
        with lock:
            return cache.get(_cache_key(q))
    return None

def cache_set(q, result, ctx):
    lock = ctx.get('cache_lock')
    cache = ctx.get('cache', {})
    if lock:
        with lock:
            cache[_cache_key(q)] = result

# ── Main ──────────────────────────────────────────────────────────────────────
def mitigate(call_next, question, config, context):
    qid        = context.get('qid', '?')
    session_id = context.get('session_id', '?')
    turn       = context.get('turn_index', 0)

    log("REQUEST_START", {"qid": qid, "session": session_id, "turn": turn,
                          "question_preview": question[:100]})

    # 1. Cache hit → skip LLM call entirely (saves all tokens)
    cached = cache_get(question, context)
    if cached:
        log("CACHE_HIT", {"qid": qid})
        return cached

    # 2. Sanitize injection attempts
    q = sanitize(question)
    if q != question:
        log("SANITIZED", {"qid": qid})

    # 3. Call agent — retry only on hard errors (not loop/max_steps)
    t0 = time.time()
    result = None
    for attempt in range(3):
        try:
            result = call_next(q, config)
            status = result.get('status', '')
            # Retry only on tool errors, not on loop (loop = prompt issue)
            if status == 'ok' or status in ('loop', 'max_steps', 'no_action'):
                break
            if attempt < 2:
                log("RETRY", {"qid": qid, "attempt": attempt + 1, "status": status})
                time.sleep(0.3 * (attempt + 1))
        except Exception as e:
            log("ERROR", {"qid": qid, "attempt": attempt + 1, "error": str(e)})
            if attempt == 2:
                return {"answer": None, "status": "wrapper_error",
                        "steps": 0, "trace": [], "meta": {}}

    wall_ms = int((time.time() - t0) * 1000)

    # 4. Observe
    if result:
        meta      = result.get('meta', {})
        answer    = result.get('answer', '') or ''
        status    = result.get('status', '?')
        usage     = meta.get('usage', {})
        tools     = meta.get('tools_used', [])
        model     = meta.get('model', 'gpt-5.4-nano')
        pii       = detect_pii(answer)
        loop_flag = has_loop(result.get('trace', []))

        log("REQUEST_COMPLETE", {
            "qid": qid, "session": session_id, "turn": turn,
            "status": status,
            "wall_time_ms": wall_ms,
            "latency_ms": meta.get('latency_ms', 0),
            "steps": result.get('steps', 0),
            "tools_count": len(tools), "tools": tools,
            "tokens": {
                "prompt":     usage.get('prompt_tokens', 0),
                "completion": usage.get('completion_tokens', 0),
                "total":      usage.get('total_tokens', 0)
            },
            "cost_usd": round(cost_usd(usage, model), 6),
            "model": model,
            "pii_leaks": pii,
            "has_loop": loop_flag
        })

        if pii:        log("WARNING_PII_LEAK",    {"qid": qid, "leaks": pii})
        if loop_flag:  log("WARNING_LOOP",         {"qid": qid})
        if status != 'ok': log("WARNING_STATUS",   {"qid": qid, "status": status})
        if len(tools) > 4: log("WARNING_TOOL_OVERUSE", {"qid": qid, "count": len(tools)})

        # Cache only successful answers
        if status == 'ok':
            cache_set(question, result, context)

    return result

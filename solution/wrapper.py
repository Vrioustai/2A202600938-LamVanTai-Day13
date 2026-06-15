"""Observability + mitigation layer - token-optimized + answer post-processing"""
from __future__ import annotations
import time, re, json, hashlib, math

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

# ── Arithmetic validator: recompute from trace ───────────────────────────────
def extract_tool_results(trace):
    """Extract tool call results from trace"""
    tools = {}
    if not trace:
        return tools
    for step in trace:
        action = step.get('action', '')
        result = step.get('result', {})
        obs = step.get('observation', step.get('result', {}))
        if isinstance(obs, str):
            try: obs = json.loads(obs)
            except: obs = {}
        if action == 'check_stock':
            tools['stock'] = obs
        elif action == 'get_discount':
            tools['discount'] = obs
        elif action == 'calc_shipping':
            tools['shipping'] = obs
    return tools

def recompute_total(trace, quantity):
    """Try to recompute total from tool trace"""
    t = extract_tool_results(trace)
    stock = t.get('stock', {})
    discount = t.get('discount', {})
    shipping = t.get('shipping', {})

    price = None
    # Try various field names
    for f in ['unit_price', 'price', 'price_vnd', 'unit_price_vnd']:
        if f in stock:
            try: price = int(stock[f]); break
            except: pass

    if price is None:
        return None

    # subtotal
    try: qty = int(quantity)
    except: return None
    subtotal = price * qty

    # discount
    disc_pct = 0
    for f in ['discount_percent', 'discount', 'percent', 'rate']:
        if f in discount:
            try: disc_pct = int(discount[f]); break
            except: pass
    discounted = subtotal * (100 - disc_pct) // 100

    # shipping
    ship_cost = 0
    for f in ['shipping_cost', 'cost', 'fee', 'shipping_fee']:
        if f in shipping:
            try: ship_cost = int(shipping[f]); break
            except: pass

    total = discounted + ship_cost
    return total

def validate_and_fix_answer(answer, trace, question):
    """Validate arithmetic in answer, fix if wrong"""
    if not answer or 'VND' not in answer:
        return answer, False
    # Extract quantity from question
    m = re.search(r'(\d+)\s+(?:cái|chiếc|sản phẩm|cụm|bộ)?\s*(?:iPhone|iPad|MacBook|AirPods|airpods|macbook|iphone|ipad)', 
                  question, re.I)
    if not m:
        m = re.search(r'mua\s+(\d+)', question, re.I)
    if not m:
        return answer, False
    qty = m.group(1)

    computed = recompute_total(trace, qty)
    if computed is None:
        return answer, False

    # Extract current total from answer
    m2 = re.search(r'Tổng thanh toán:\s*([\d,]+)\s*VND', answer)
    if not m2:
        return answer, False
    current_str = m2.group(1).replace(',', '')
    try:
        current = int(current_str)
    except:
        return answer, False

    if current == computed:
        return answer, False  # already correct

    # Fix it
    fixed = f"Tổng thanh toán: {computed:,} VND."
    return fixed, True
_LIEN_HE = re.compile(r'\s*\(?\s*lien\s*he\s*:?\s*\[REDACTED\]\s*\)?\.?', re.I)
_EMAIL_TRAIL = re.compile(r'\s*\(?\s*[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\s*\)?', re.I)
_PHONE_TRAIL = re.compile(r'\s*\(?\s*0[0-9]{9,10}\s*\)?', re.I)

def clean_answer(answer: str) -> str:
    """Strip PII traces and fix number formatting from answer"""
    if not answer:
        return answer
    # 1. Remove (lien he: [REDACTED]) patterns
    answer = _LIEN_HE.sub('', answer)
    # 2. Remove any remaining email/phone that slipped through
    answer = _EMAIL_TRAIL.sub('', answer)
    answer = _PHONE_TRAIL.sub('', answer)
    # 3. Fix bad decimal in VND: 54,000,317,50 → remove wrong last group
    answer = re.sub(r'([\d,]+),(\d{2})\s*VND',
                    lambda m: m.group(0).replace(f",{m.group(2)} VND", " VND")
                    if len(m.group(2)) == 2 else m.group(0), answer)
    # 4. Fix missing commas: 360028000 VND → 360,028,000 VND
    def add_commas(m):
        num_str = m.group(1).replace(',','')
        try:
            n = int(num_str)
            formatted = f"{n:,}"
            return f"Tổng thanh toán: {formatted} VND"
        except:
            return m.group(0)
    answer = re.sub(r'Tổng thanh toán:\s*(\d[\d,]*\d)\s*VND', add_commas, answer)
    # 5. Strip trailing noise
    answer = answer.strip()
    if answer and 'VND' in answer and not answer.endswith('.'):
        answer = answer + '.'
    return answer
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

    # 5. Post-process answer: strip PII traces + fix format
    if result and result.get('answer'):
        cleaned = clean_answer(result['answer'])
        if cleaned != result['answer']:
            log("ANSWER_CLEANED", {"qid": qid, "before": result['answer'][:80], "after": cleaned[:80]})
            result = dict(result)
            result['answer'] = cleaned

    # 6. Arithmetic validation: recompute from trace and fix if wrong
    if result and result.get('answer') and result.get('trace'):
        fixed_ans, was_fixed = validate_and_fix_answer(
            result['answer'], result.get('trace', []), question)
        if was_fixed:
            log("ARITHMETIC_FIXED", {"qid": qid, "before": result['answer'][:80], "after": fixed_ans[:80]})
            result = dict(result)
            result['answer'] = fixed_ans

    return result

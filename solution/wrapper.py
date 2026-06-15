"""FULL observability + mitigation layer for Observathon Challenge"""
from __future__ import annotations
import time
import re
import json
import hashlib

# ============================================================================
# OBSERVABILITY: Logging, Metrics, Tracing
# ============================================================================

def log_event(event_type, data):
    """Simple console logger for observability"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{event_type}] {json.dumps(data, ensure_ascii=False)}")

def detect_pii(text):
    """Detect PII (email, phone) in text"""
    if not text:
        return []
    leaks = []
    # Email pattern
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if emails:
        leaks.extend([f"email:{e}" for e in emails])
    # Phone pattern (various formats)
    phones = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\b\d{10,11}\b', text)
    if phones:
        leaks.extend([f"phone:{p}" for p in phones])
    return leaks

def detect_loop(trace):
    """Detect infinite loops in tool calls"""
    if not trace or len(trace) < 3:
        return False
    # Check for repeated identical tool calls
    tool_calls = [step.get('action') for step in trace if step.get('action')]
    if len(tool_calls) < 3:
        return False
    # Check for 3+ consecutive identical calls
    for i in range(len(tool_calls) - 2):
        if tool_calls[i] == tool_calls[i+1] == tool_calls[i+2]:
            return True
    return False

def sanitize_input(question):
    """Sanitize order notes to prevent prompt injection"""
    # Remove potential injection patterns in Vietnamese
    dangerous_patterns = [
        r'(?i)(bỏ qua|ignore|disregard)\s+(hướng dẫn|instruction|prompt)',
        r'(?i)(giá|price|total)\s*(là|is|=)\s*\$?\d+',
        r'(?i)(system|admin|override)',
    ]
    sanitized = question
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '[REMOVED]', sanitized)
    return sanitized

def calculate_cost(usage, model="gpt-4"):
    """Calculate cost from token usage"""
    if not usage:
        return 0.0
    prompt_tokens = usage.get('prompt_tokens', 0)
    completion_tokens = usage.get('completion_tokens', 0)
    
    # Price per 1M tokens (example rates)
    prices = {
        'gpt-4': {'prompt': 30.0, 'completion': 60.0},
        'gpt-5.4-nano': {'prompt': 0.5, 'completion': 1.5},
        'gpt-5.4-mini': {'prompt': 1.0, 'completion': 3.0},
    }
    
    model_key = 'gpt-5.4-nano' if 'nano' in model.lower() else model
    rate = prices.get(model_key, {'prompt': 1.0, 'completion': 3.0})
    
    cost = (prompt_tokens * rate['prompt'] + completion_tokens * rate['completion']) / 1_000_000
    return cost

# ============================================================================
# CACHE LOGIC
# ============================================================================

def get_cache_key(question):
    """Generate cache key from question"""
    normalized = question.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()

def get_from_cache(question, context):
    """Try to get result from cache"""
    cache = context.get('cache', {})
    cache_lock = context.get('cache_lock')
    
    if not cache or not cache_lock:
        return None
    
    key = get_cache_key(question)
    with cache_lock:
        return cache.get(key)

def save_to_cache(question, result, context):
    """Save result to cache"""
    cache = context.get('cache', {})
    cache_lock = context.get('cache_lock')
    
    if not cache or not cache_lock:
        return
    
    key = get_cache_key(question)
    with cache_lock:
        cache[key] = result

# ============================================================================
# MAIN MITIGATION FUNCTION
# ============================================================================

def mitigate(call_next, question, config, context):
    """
    Full observability + mitigation layer:
    - Logging: latency, tokens, cost, errors, PII
    - Tracing: tool calls, loops
    - Mitigations: retry, cache, sanitize, redact
    """
    qid = context.get('qid', 'unknown')
    session_id = context.get('session_id', 'unknown')
    turn_index = context.get('turn_index', 0)
    
    # Log request start
    log_event("REQUEST_START", {
        "qid": qid,
        "session": session_id,
        "turn": turn_index,
        "question_preview": question[:100]
    })
    
    # 1. CHECK CACHE
    cached = get_from_cache(question, context)
    if cached:
        log_event("CACHE_HIT", {"qid": qid})
        return cached
    
    # 2. SANITIZE INPUT (prevent injection)
    sanitized_question = sanitize_input(question)
    if sanitized_question != question:
        log_event("SANITIZED", {
            "qid": qid,
            "removed_patterns": "potential injection"
        })
    
    # 3. CALL AGENT WITH RETRY
    max_retries = 3
    result = None
    start_time = time.time()
    
    for attempt in range(max_retries):
        try:
            result = call_next(sanitized_question, config)
            
            # If successful, break
            if result and result.get('status') == 'ok':
                break
            
            # If error, log and retry
            if attempt < max_retries - 1:
                log_event("RETRY", {
                    "qid": qid,
                    "attempt": attempt + 1,
                    "status": result.get('status') if result else 'failed'
                })
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                
        except Exception as e:
            log_event("ERROR", {
                "qid": qid,
                "attempt": attempt + 1,
                "error": str(e)
            })
            if attempt == max_retries - 1:
                return {
                    "answer": None,
                    "status": "wrapper_error",
                    "steps": 0,
                    "trace": [],
                    "meta": {}
                }
    
    wall_time_ms = int((time.time() - start_time) * 1000)
    
    # 4. EXTRACT OBSERVABILITY DATA
    if result:
        meta = result.get('meta', {})
        trace = result.get('trace', [])
        answer = result.get('answer', '')
        status = result.get('status', 'unknown')
        steps = result.get('steps', 0)
        
        # Extract metrics
        latency_ms = meta.get('latency_ms', 0)
        usage = meta.get('usage', {})
        tools_used = meta.get('tools_used', [])
        model = meta.get('model', 'unknown')
        
        # Calculate cost
        cost = calculate_cost(usage, model)
        
        # Detect issues
        pii_leaks = detect_pii(answer)
        has_loop = detect_loop(trace)
        
        # 5. LOG COMPREHENSIVE METRICS
        log_event("REQUEST_COMPLETE", {
            "qid": qid,
            "session": session_id,
            "turn": turn_index,
            "status": status,
            "wall_time_ms": wall_time_ms,
            "latency_ms": latency_ms,
            "steps": steps,
            "tools_count": len(tools_used),
            "tools": tools_used,
            "tokens": {
                "prompt": usage.get('prompt_tokens', 0),
                "completion": usage.get('completion_tokens', 0),
                "total": usage.get('total_tokens', 0)
            },
            "cost_usd": round(cost, 6),
            "model": model,
            "pii_leaks": pii_leaks,
            "has_loop": has_loop
        })
        
        # 6. LOG WARNINGS
        if pii_leaks:
            log_event("WARNING_PII_LEAK", {
                "qid": qid,
                "leaks": pii_leaks
            })
        
        if has_loop:
            log_event("WARNING_LOOP", {
                "qid": qid,
                "trace_length": len(trace)
            })
        
        if status != 'ok':
            log_event("WARNING_STATUS", {
                "qid": qid,
                "status": status
            })
        
        if len(tools_used) > 5:
            log_event("WARNING_TOOL_OVERUSE", {
                "qid": qid,
                "tools_count": len(tools_used),
                "tools": tools_used
            })
        
        # 7. SAVE TO CACHE (only if successful)
        if status == 'ok':
            save_to_cache(question, result, context)
    
    return result

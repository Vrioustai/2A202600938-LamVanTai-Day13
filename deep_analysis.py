import json, re

with open('run_output.json', encoding='utf-8') as f:
    data = json.load(f)
results = data.get('results', [])

print("=== PROBLEM 1: FORMAT ISSUES in VND answers ===")
format_issues = []
for r in results:
    ans = str(r.get('answer', ''))
    qid = r.get('qid', '?')
    if 'VND' not in ans:
        continue
    # detect malformed numbers
    issues = []
    # No thousand separators: 360028000 VND (no commas)
    m = re.search(r':\s*(\d{7,})\s*VND', ans)
    if m and ',' not in m.group(1):
        issues.append(f"no_comma: {m.group(1)}")
    # Extra decimal with wrong format: 54,000,317,50 
    if re.search(r'\d,\d{2}\s+VND', ans):
        issues.append(f"bad_decimal")
    # (lien he: [REDACTED]) trailing garbage
    if '[REDACTED]' in ans:
        issues.append("pii_leak_redacted")
    if issues:
        format_issues.append((qid, ans[:80], issues))

print(f"Format issues: {len(format_issues)}")
for qid, ans, iss in format_issues:
    print(f"  [{qid}] {iss}")
    print(f"    {ans}")

print()
print("=== PROBLEM 2: PII REDACTED still in output ===")
pii_in_answer = [(r['qid'], r.get('answer','')[:80]) for r in results if '[REDACTED]' in str(r.get('answer',''))]
print(f"Answers with [REDACTED]: {len(pii_in_answer)}")
for qid, ans in pii_in_answer[:5]:
    print(f"  [{qid}] {ans}")

print()
print("=== PROBLEM 3: AirPods questions - are they REALLY out of stock? ===")
airpods_q = [(r['qid'], r.get('question','')[:80], str(r.get('answer',''))[:80]) 
             for r in results if 'AirPods' in str(r.get('question',''))]
print(f"Total AirPods questions: {len(airpods_q)}")
for qid, q, ans in airpods_q:
    tag = "REFUSED" if 'VND' not in ans else "ANSWERED"
    print(f"  [{qid}] {tag}")
    print(f"    Q: {q}")
    print(f"    A: {ans}")

print()
print("=== PROBLEM 4: Cities that were refused ===")
city_q = [(r['qid'], r.get('question','')[:80], str(r.get('answer',''))[:80]) 
          for r in results 
          if any(c in str(r.get('question','')).lower() for c in ['vung tau', 'can tho', 'da lat', 'dalat', 'đà lạt'])]
print(f"Total bad-city questions: {len(city_q)}")
for qid, q, ans in city_q:
    tag = "REFUSED" if 'VND' not in ans else "ANSWERED"
    print(f"  [{qid}] {tag}: {ans}")

print()
print("=== PROBLEM 5: Products not in catalog ===")
fake_prod = [(r['qid'], r.get('question','')[:80], str(r.get('answer',''))[:80]) 
             for r in results 
             if any(p in str(r.get('question','')).lower() for p in ['sony', 'oppo', 'nokia', 'xiaomi', 'samsung'])]
print(f"Total unknown-product questions: {len(fake_prod)}")
for qid, q, ans in fake_prod:
    tag = "REFUSED" if 'VND' not in ans else "ANSWERED"
    print(f"  [{qid}] {tag}")
    print(f"    Q: {q}")
    print(f"    A: {ans}")

print()
print("=== SCORE BREAKDOWN: What contributes to 84.17 ===")
print("correct  0.397 x0.32 = 0.127  (41/120 = 34%)")
print("quality  0.638 x0.16 = 0.102  (LLM judge)")
print("error    1.000 x0.13 = 0.130  PERFECT")
print("latency  0.532 x0.08 = 0.043")
print("cost     1.000 x0.09 = 0.090  PERFECT")
print("drift    0.964 x0.07 = 0.067")
print("prompt   0.676 x0.15 = 0.101")
print("diag_f1  0.824        = 18.13 bonus")
print()
print("=== WHAT WOULD 100 NEED ===")
print("correct  1.000 x0.32 = 0.320  (+0.193) <- BIGGEST GAP")
print("quality  1.000 x0.16 = 0.160  (+0.058)")
print("latency  1.000 x0.08 = 0.080  (+0.037)")
print("drift    1.000 x0.07 = 0.070  (+0.003)")
print("prompt   1.000 x0.15 = 0.150  (+0.049)")
print("diag_f1  1.000        = 22.00 bonus (+3.87)")
print()
print("Total gap: ~0.34 points = ~34 score points needed")

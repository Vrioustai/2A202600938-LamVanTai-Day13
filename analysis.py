import json

with open('run_output.json', encoding='utf-8') as f:
    data = json.load(f)
results = data.get('results', [])

print("=== ROOT CAUSE ANALYSIS (84.17 → 100) ===\n")

airpods_oos  = []
city_bad     = []
prod_missing = []
wrong_total  = []
correct      = []
refused_ok   = []

for r in results:
    ans = str(r.get('answer', ''))
    q   = str(r.get('question', ''))
    qid = r.get('qid', '?')

    ans_lo = ans.lower()
    q_lo   = q.lower()

    is_airpods = 'airpods' in q_lo
    is_bad_city = any(c in q_lo for c in ['can tho', 'vung tau', 'da lat', 'dalat'])
    is_missing_prod = any(p in q_lo for p in ['sony', 'oppo', 'nokia', 'xiaomi', 'samsung'])

    has_vnd = 'vnd' in ans_lo

    if is_airpods and ('het hang' in ans_lo or 'khong con hang' in ans_lo or 'hết hàng' in ans_lo or 'out of stock' in ans_lo):
        airpods_oos.append((qid, q[:60], ans[:60]))
    elif is_bad_city and ('khu vực' in ans_lo or 'không' in ans_lo or 'not served' in ans_lo):
        city_bad.append((qid, q[:60], ans[:60]))
    elif is_missing_prod and not has_vnd:
        prod_missing.append((qid, q[:60], ans[:60]))
    elif has_vnd:
        wrong_total.append((qid, q[:60], ans[:60]))  # may be correct or wrong
    else:
        refused_ok.append((qid, q[:60], ans[:60]))

# Estimate wrong totals = vnd answers - 41 correct
print(f"VND answers (has total): {len(wrong_total)}")
print(f"Correct (scorer says):   41")
print(f"Wrong total estimate:    {len(wrong_total) - 41}")
print()
print(f"AirPods out-of-stock refusals: {len(airpods_oos)}")
for x in airpods_oos:
    print(f"  [{x[0]}] Q: {x[1]}")
    print(f"          A: {x[2]}")

print()
print(f"City not served refusals: {len(city_bad)}")
for x in city_bad:
    print(f"  [{x[0]}] Q: {x[1]}")
    print(f"          A: {x[2]}")

print()
print(f"Product not found: {len(prod_missing)}")
for x in prod_missing:
    print(f"  [{x[0]}] Q: {x[1]}")
    print(f"          A: {x[2]}")

print()
print(f"Other refusals: {len(refused_ok)}")
for x in refused_ok:
    print(f"  [{x[0]}] Q: {x[1]}")
    print(f"          A: {x[2]}")

print()
print("=== SAMPLE VND ANSWERS (first 20) ===")
for x in wrong_total[:20]:
    print(f"  [{x[0]}] {x[2]}")

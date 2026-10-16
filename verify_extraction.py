import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from src.extractor import RCTExtractor

ext = RCTExtractor('data/raw/empa vs placebo 2doses (RCT4).pdf')
data = ext.extract_all()

print("=== STUDY METADATA ===")
print("Study ID:", data.study.study_id)
print("Title:", data.study.title[:80])

print("\n=== ARMS ===")
print("Total Arms:", len(data.arms))
for a in data.arms:
    print(f"  Arm: {a.arm_id} | Name: {a.arm_name} | Type: {a.intervention_type} | Dose: {a.dose_value}{a.dose_unit} | N: {a.sample_size_allocated}")

print("\n=== ELIGIBILITY ===")
print("Total Criteria:", len(data.eligibility))
for e in data.eligibility:
    print(f"  Elig: {e.criterion_name} | Type: {e.criterion_type} | MinOp: {e.min_operator} | MinVal: {e.min_value} | MaxOp: {e.max_operator} | MaxVal: {e.max_value} | Unit: {e.unit}")

print("\n=== OUTCOMES SUMMARY ===")
print("Total Outcomes:", len(data.outcomes))
params = sorted(list(set(o.parameter_name for o in data.outcomes)))
print("Distinct Parameters:", params)

print("\n=== TARGET PARAMETERS DETAIL ===")
targets = [
    "AST", "ALT", "Fasting Plasma Glucose", "Total Cholesterol",
    "HDL-C", "LDL-C", "Triglycerides", "Free Fatty Acids",
    "Total Ketone Bodies", "8-iso-PGF2a (Fasting)", "8-iso-PGF2a (24h)"
]
for t in targets:
    matching = [o for o in data.outcomes if o.parameter_name == t]
    print(f"\n--- Parameter: {t} (Count: {len(matching)}) ---")
    for m in matching:
        print(f"   Arm: {m.arm_id} | TP: {m.timepoint_value} {m.timepoint_unit} ({m.timepoint}) | Mean: {m.mean} | SD: {m.sd} | Change: {m.change_value} | Base: {m.is_baseline}")

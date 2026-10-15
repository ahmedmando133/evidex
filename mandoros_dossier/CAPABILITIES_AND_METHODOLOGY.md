# MANDOROS™ — Capabilities & Methodology Reference
## دليل القدرات والمنهجية العلمية الشاملة

---

### 1. الركائز الأكاديمية الأربع (The 4 Academic Pillars)

#### Pillar I — Atomic CONSORT/PRISMA-Grade Curation (Stage-1 Engine)
- **7-Entity Canonical Relational Schema:**
  1. `Master_Extraction_Sheet`: ملخص الدراسة الشامل (Study ID, DOI, Phase, Sample Size N, Primary Outcome, Effect Size, Safety Verdict).
  2. `Study_Characteristics`: منهجية التجربة (Allocation, Masking, Design Type, Centers, Funding Source, Risk of Bias).
  3. `Population_Baseline`: الخصائص الديموغرافية والسريرية للمرضى عند خط الأساس (Age, % Female, BMI, Disease Duration, Baseline Diagnostic Markers).
  4. `Intervention_Arms`: أذرع العلاج والجرعات (Arm Name, Active Ingredient, Route, Frequency, Titration Schedule) مع توحيد أسماء الأدوية وفق ATC / RxNorm.
  5. `Outcomes`: القياسات التفصيلية للنتائج الأولية والثانوية (Timepoint in weeks, Metric, Central Tendency, Dispersion, p-value).
  6. `Variables_Matrix`: مصفوفة المسار الزمني عبر جميع الأذرع ومقارنة التغير عن خط الأساس (Change From Baseline).
  7. `Eligibility_Criteria`: مصفوفة معايير الشمول والاستبعاد مقسمة عبر 4 معاملات رياضية منفصلة (`<`, `<=`, `>`, `>=`) مع توحيد الوحدات السريرية.
- **Epistemic Integrity & Zero-Imputation:**
  - كل رقم مستخرج مربوط بإحداثيات الصفحة والاقتباس الحرفي من ورقة البحث (`Provenance Page & Quote`).
  - تطبيق وسم `not_reported` الإلزامي لمنع أي اختلاق أو تخمين للقيم غير المذكورة.

---

#### Pillar II — metafor-Grade Biostatistics & Evidence Synthesis (Phase-2 Engine)
- **Classical & REML Pooling:**
  - Restricted Maximum Likelihood (REML) و DerSimonian-Laird لدمج التأثيرات العشوائية (Random-Effects).
  - تصحيح التباين عبر Knapp-Hartung Variance Correction.
  - تفكيك التباين بين الدراسات: Cochran's $Q$, $\tau^2$, و Higgins' $I^2$.
  - حساب فترات الثقة 95% Confidence Intervals وفترات التنبؤ 95% Prediction Intervals (PI).
- **Publication Bias & Sensitivity Diagnostics:**
  - Egger's Linear Regression Test لفحص عدم التماثل.
  - Begg-Mazumdar Rank Correlation.
  - تحليل الحساسية باستبعاد دراسة تلو الأخرى (Leave-One-Out Sensitivity Analysis).
  - توليد مخططات Forest Plots ومخططات Funnel Plots تفاعلية بصيغة HTML مدمجة.

---

#### Pillar III — Multi-Cohort Network Meta-Analysis & SUCRA Hierarchy
- **Bucher Indirect Comparisons (NMA):**
  - المقارنات غير المباشرة للأدوية عبر مقارن مشترك (مثل Placebo أو Standard of Care).
  - فحص اتساق الحلقات المغلقة (Loop-Specific Inconsistency Checks).
- **Surface Under the Cumulative Ranking (SUCRA):**
  - محاكاة مونت كارلو (Monte Carlo Simulations) لترتيب العلاجات المتنافسة هرمياً بناءً على احتمالية التفوق والفاعلية.
  - حساب P-Score لتقدير الأفضلية السريرية النسبية.
- **Scale-Free Clinical Domain Bridging:**
  - توحيد المقاييس السريرية المختلفة باستخدام الفروق المعيارية للمتوسطات (Hedges' $g$ SMD) لربط الدراسات التي استخدمت استبيانات أو مقاييس متباينة في نفس المجال السريري.

---

#### Pillar IV — Predictive Meta-Regression & In-Silico Synthesis
- **Multivariate Dose–Duration Meta-Regression:**
  - نماذج انحدار خطية ولوجستية موزونة (WLS) لربط حجم التأثير بجرعة الدواء (mg/day) ومدة العلاج (weeks).
  - نظام تقييم مخاطر الاستقراء (Extrapolation Risk Score) لتمييز التنبؤ داخل النطاق (Interpolation) عن التنبؤ خارجه (Extrapolation).
- **Missing-Data Reconstruction (Surrogate Matrix Imputation):**
  - تعويض القياسات المفقودة في الدراسات غير المكتملة عبر الانحدار المتقاطع ومصفوفة التباين المشترك بين الدراسات المكتملة.
- **De-Novo Virtual Clinical Trial Protocol Synthesis:**
  - استنباط بروتوكول التجربة السريرية الافتراضية المثالية: تحديد الجرعة المثلى (Therapeutic Sweet-Spot)، المدة المشبعة للأثر، النمط الظاهري الأكثر استجابة (Super-Responders)، وحجم العينة الإحصائي المطلوب لقوة اختبار 90%.

---

### 2. التحديث المستمر والتطوير (Continuous Maintenance)
عند إدخال أي تصحيح أو قاعدة سريرية جديدة:
1. يتم تضمين القاعدة في كود الاستخراج والتحليل.
2. يتم تشغيل ملف `mandoros_dossier/update_dossier.py` لتحديث كتيب الـ PDF والمستندات أوتوماتيكياً.

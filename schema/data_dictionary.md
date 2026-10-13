# Clinical Trial Data Dictionary (قاموس متغيرات التجارب السريرية)

> **الإصدار:** 1.0.0 | **التاريخ:** 13 أكتوبر 2026  
> **المعيار:** متوافق مع وثيقة مفهوم المشروع (Concept Note) والـ 6 جداول العلائقية.

---

## 1. جدول معلومات الدراسة (`Studies`)
يمثل هذا الجدول السجل الأساسي لكل تجربة سريرية عشوائية (RCT).

| اسم الحقل | النوع | إلزامي؟ | الوصف | أمثلة وقيم مسموحة |
| :--- | :--- | :--- | :--- | :--- |
| `study_id` | نص (String) | نعم (PK) | المعرف الفريد للتجربة | `RCT_ORLISTAT_2024`, `RCT_METFORMIN_2012` |
| `title` | نص | نعم | العنوان المنشور الكامل | "Effects of orlistat on serum uric acid levels..." |
| `authors` | نص | لا | الباحث الأول أو المؤلفون | "Liu et al." |
| `publication_year` | عدد صحيح | لا | سنة النشر | `2024`, `2012` |
| `journal` | نص | لا | المجلة العلمية | "Lipids in Health and Disease", "Diabetes Care" |
| `doi` | نص | لا | الرابط الرقمي | `10.1186/s12944-024-02047-7` |
| `study_design` | نص | نعم | تصميم الدراسة | `Randomized, double-blind, placebo-controlled` |
| `study_phase` | نص | لا | مرحلة الدراسة | `Phase III`, `DPP 2-year double-blind phase` |
| `total_sample_size` | عدد صحيح | نعم | إجمالي عدد المشاركين العشوائيين | `72`, `2155` |
| `duration_value` | رقمي | نعم | المدة الزمنية رقمياً | `12`, `2` |
| `duration_unit` | نص | نعم | وحدة الزمن | `weeks`, `months`, `years`, `days` |
| `condition_studied` | نص | نعم | الحالة المرضية المستهدفة | `Obesity with Hyperuricemia`, `Impaired Glucose Tolerance` |

---

## 2. جدول أذرع التجربة والتدخلات (`Arms`)
يفصل كل ذراع علاجي أو مقارن بدلاً من دمجهما في سطر واحد.

| اسم الحقل | النوع | إلزامي؟ | الوصف | أمثلة وقيم مسموحة |
| :--- | :--- | :--- | :--- | :--- |
| `arm_id` | نص (String) | نعم (PK) | معرف الذراع الفريد | `ARM_ORL_120`, `ARM_ORL_PLA` |
| `study_id` | نص (FK) | نعم | ربط بالدراسة | `RCT_ORLISTAT_2024` |
| `arm_name` | نص | نعم | اسم الذراع المعياري | `Orlistat 120mg`, `Placebo` |
| `intervention_type` | فئوي | نعم | نوع التدخل | `experimental`, `placebo`, `active_comparator`, `lifestyle` |
| `drug_name` | نص | لا | اسم العقار | `Orlistat`, `Metformin`, `Placebo` |
| `dose_value` | رقمي | لا | قيمة الجرعة | `120`, `850` |
| `dose_unit` | نص | لا | وحدة الجرعة | `mg`, `g`, `mcg` |
| `frequency_number` | رقمي | لا | عدد المرات | `3`, `2`, `1` |
| `frequency_unit` | نص | لا | وحدة التكرار | `daily`, `weekly`, `twice daily` |
| `sample_size_allocated`| عدد صحيح | نعم | العينة المخصصة عشوائياً | `37`, `35` |
| `sample_size_analyzed` | عدد صحيح | لا | العينة المحللة في التقرير | `35`, `28` |
| `source_page` | عدد صحيح | نعم | صفحة المرجع | `2` |

---

## 3. جدول معايير الأهلية الذرية (`Eligibility`)
يطبق قاعدة التفكيك الذري الصارمة (Atomic Fields). **لا يُكتب ">= 18 years" في خلية واحدة**.

| اسم الحقل | النوع | إلزامي؟ | الوصف | أمثلة وقيم مسموحة |
| :--- | :--- | :--- | :--- | :--- |
| `criterion_id` | نص | نعم (PK) | معرف المعيار | `ELIG_001` |
| `study_id` | نص (FK) | نعم | ربط بالدراسة | `RCT_ORLISTAT_2024` |
| `criterion_type` | فئوي | نعم | نوع المعيار | `inclusion`, `exclusion` |
| `domain` | فئوي | نعم | مجال المعيار | `demographic`, `biomarker`, `diagnostic`, `medical_history` |
| `criterion_name` | نص | نعم | اسم المعيار المعياري | `age`, `bmi`, `fasting_plasma_glucose`, `serum_uric_acid` |
| `less_than (<)` | نص / رمز | لا | علامة أصغر من | `<` (أو فارغ) |
| `equal (=)` | نص / رمز | لا | علامة يساوي | `=` (أو فارغ) |
| `greater_than (>)` | نص / رمز | لا | علامة أكبر من | `>` (أو فارغ) |
| `between` | نص | لا | نطاق محدد | `between` (أو فارغ) |
| `value` | رقمي | لا | القيمة المفردة (للمعايير ذات الحد المفرد) | `18`, `24`, `25` |
| `min_value` | رقمي | لا | الحد الأدنى (إذا كان بين قيمتين) | `20`, `95`, `140` |
| `max_value` | رقمي | لا | الحد الأعلى (إذا كان بين قيمتين) | `65`, `125`, `199` |
| `unit` | نص | لا | الوحدة المعيارية | `years`, `kg/m2`, `mg/dL`, `umol/L` |
| `raw_source_text` | نص | نعم | النص الحرفي من الورقة | "aged 20 to 65 years" |
| `source_page` | عدد صحيح | نعم | صفحة المعيار | `2` |

---

## 4. جدول النتائج والتحاليل السريرية (`Outcomes`)
يغطي كافة التحاليل المخبرية والقياسات الأنثروبومترية ونقاط التغير عبر الزمن.

| اسم الحقل | النوع | إلزامي؟ | الوصف | أمثلة وقيم مسموحة |
| :--- | :--- | :--- | :--- | :--- |
| `outcome_id` | نص | نعم (PK) | معرف النتيجة الفريد | `OUT_001` |
| `study_id` | نص (FK) | نعم | ربط بالدراسة | `RCT_ORLISTAT_2024` |
| `arm_id` | نص (FK) | نعم | ربط بالذراع | `ARM_ORL_120` |
| `race` | نص | نعم | العرق أو المجموعة السكانية الفرعية | `Caucasian`, `African American`, `Hispanic`, `Asian`, `Native American`, `Overall` |
| `domain` | فئوي | نعم | مجال النتيجة | `anthropometric`, `lipid`, `glycemic`, `renal`, `liver`, `safety` |
| `parameter_name` | نص | نعم | اسم المتغير المعياري | `BMI`, `Body Weight`, `WC`, `TC`, `HDL`, `LDL`, `TG`, `Glucose`, `HbA1c`, `ALT`, `AST` |
| `statistical_type` | فئوي | نعم | طبيعة المتغير الإحصائي | `continuous`, `dichotomous` |
| `Timepoint (value)` | نص / رقمي | نعم | القيمة العددية للنقطة الزمنية | `0`, `12`, `2` |
| `Timepoint (unit)` | نص | نعم | وحدة النقطة الزمنية | `weeks`, `years`, `months`, `days` |
| `sample_size` | عدد صحيح | نعم | حجم العينة (مكتمل لجميع الصفوف) | `37`, `35`, `1073`, `1082` |
| `mean` | رقمي | لا | المتوسط الحسابي | `30.33` |
| `sd` | رقمي | لا | الانحراف المعياري | `3.88` |
| `change_value` | رقمي | لا | مقدار التغير عن خط الأساس | `-1.45` |
| `change_sd` | رقمي | لا | انحراف التغير المعياري | `0.82` |
| `events` | عدد صحيح | لا | عدد الحالات/الأحداث (للقيم الثنائية) | `3` (e.g. gout flares) |
| `total` | عدد صحيح | لا | إجمالي المعرضين للخطر | `37` |
| `percentage` | رقمي | لا | النسبة المئوية للأحداث | `8.1` |
| `unit` | نص | نعم | وحدة القياس | `kg/m2`, `kg`, `cm`, `mg/dL`, `mmol/L`, `U/L` |
| `p_value` | نص | لا | الدلالة الإحصائية | `0.023`, `<0.001`, `NS` |
| `source_page` | عدد صحيح | نعم | رقم الصفحة | `4` |
| `source_location` | نص | نعم | موقع الجدول/الفقرة | `Table 1`, `Table 2` |
| `raw_source_text` | نص | نعم | المقتطف الحرفي الأصلي | "30.33 ± 3.88" |

---

## 5. جدول سجل الإسناد المصدري (`Provenance`)
يحقق متطلب التدقيق (Audit-ready): يضمن أن كل رقم في قاعدة البيانات مسند بنص ورقم صفحة.

| اسم الحقل | النوع | إلزامي؟ | الوصف |
| :--- | :--- | :--- | :--- |
| `provenance_id` | نص (PK) | نعم | معرف الإسناد الفريد |
| `study_id` | نص (FK) | نعم | ربط بالدراسة |
| `target_entity` | نص | نعم | الكيان المرتبط (`Studies`, `Arms`, `Eligibility`, `Outcomes`) |
| `target_id` | نص | نعم | المعرف الهدف |
| `field_name` | نص | نعم | الحقل المستهدف (`mean`, `dose_value`, `operator`) |
| `source_page` | عدد صحيح | نعم | رقم الصفحة في الـ PDF |
| `source_location` | نص | نعم | الموضع (مثال: `Table 1 row 4`) |
| `exact_source_text` | نص | نعم | الاقتباس الحرفي المسند للقيمة |

---

## 6. جدول سجل التحقق والملاحظات (`Validation_Log`)
يرصد الحالات التي تتطلب تدخلاً بشرياً أو تنبيهاً على نقص البيانات.

| اسم الحقل | النوع | إلزامي؟ | الوصف |
| :--- | :--- | :--- | :--- |
| `issue_id` | نص (PK) | نعم | معرف المشكلة الفريد |
| `study_id` | نص (FK) | نعم | ربط بالدراسة |
| `target_entity` | نص | نعم | الكيان المعني |
| `target_id` | نص | نعم | المعرف المستهدف |
| `field_name` | نص | نعم | الحقل المعني |
| `issue_type` | فئوي | نعم | `not_reported`, `unit_mismatch`, `value_out_of_range`, `unclear_text` |
| `review_required` | منطقي | نعم | هل تتطلب مراجعة بشرية؟ (`True` / `False`) |
| `comment` | نص | نعم | شرح وتفسير التنبيه |

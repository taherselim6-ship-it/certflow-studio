/**
 * CertFlow Studio | منصة الشهادات الطباعية
 * Main Frontend Controller & Bilingual Engine
 */

// ==========================================================
// Global State - Scaffolding, Core, Operator & Designer
// ==========================================================
let currentLang = new URLSearchParams(window.location.search).get("lang") || localStorage.getItem("certflow_lang") || "ar";
let currentMode = "operator"; // Default landing view: Operator Platform
let activeTrainers = [];
let activeFonts = [];
let editingTrainerId = null;
let previewDebounceTimer = null;

// Operator Platform State
const DESIGNER_PIN = "1234";
let isDesignerUnlocked = sessionStorage.getItem("certflow_designer_unlocked") === "true";
let operatorTemplates = [];
let operatorActiveTemplate = null;
let operatorSelectedCompany = "";
let operatorRecords = [];
let currentRecordIndex = 0;
let activeDataTab = "sheet"; // "sheet" | "excel"
let operatorActiveTrainerId = null;
let operatorDateFormat = "MONTH_DAY_YEAR_AUTO";
let operatorFixedDate = "";
let operatorAllSheetRecords = [];
let lastFetchedUniqueDates = [];
let currentParsedExcel = null;
let operatorCanvasDebounce = null;
let operatorFitDebounce = null;
let operatorPlatformInitialized = false;

// Designer Studio State
let designerTemplates = [];
let currentTemplate = null;
let activeFieldId = null;
let activeFieldType = null; // 'text' | 'signature'
let isDraggingFrame = false;
let isResizingFrame = false;
let activeResizeHandle = null;
let dragStartMeta = null;
let activeTrainerForSig = null;
let showGuides = true;
let designerStudioInitialized = false;
let fitCanvasDebounceTimer = null;
let historyStack = [];
let redoStack = [];
const MAX_HISTORY = 30;
let isDesignerLivePreviewActive = false;

// ==========================================================
// Bilingual Translation Dictionary (Arabic / English)
// ==========================================================
const translations = {
  ar: {
    app_title: "CertFlow Studio",
    app_subtitle: "منصة الشهادات الطباعية",
    app_tagline: "بديل دمج البيانات للشهادات الاحترافية فائقة الدقة",
    mode_designer: "استوديو المصمم",
    mode_operator: "منصة الموظف",
    page_title: "CertFlow Studio | منصة الشهادات الطباعية",
    tip_manage_trainers: "إدارة ملفات وتواقيع المدربين",
    tip_download_excel: "تحميل قالب الإكسل المعتمد (.xlsx)",
    tip_prev_record: "السجل السابق",
    tip_next_record: "السجل التالي",
    tip_widest_name: "الانتقال لأطول اسم لاختبار أقصى تحجيم تلقائي",
    op_btn_widest: "أطول اسم",
    op_jump_placeholder: "الانتقال إلى متدرب...",
    tip_tpl_name: "اسم القالب المعتمد للشهادة",
    tip_trainer_name: "المدرب المسؤول المعتمد",
    tip_cert_date: "تاريخ التدريب المعتمد للشهادة",
    badge_optimal_fit: "المقاس ملائم ١٠٠٪",
    op_btn_fit: "ملاءمة مساحة العرض مع الشاشة",
    tip_refresh_preview: "إعادة رندرة المعاينة الطباعية المباشرة",
    op_canvas_loading_text: "جاري رندرة الشهادة بمحرك الطباعة الفائقة...",
    op_footer_note: "مقياس الإحداثيات يبدأ من الزاوية العلوية اليسرى لخط القص (مطابق لبرامج النشر المكتبي)",
    op_bottom_tpl_default: "القالب: —",
    op_bottom_trainer_default: "المدرب: غير محدد",
    btn_font_manager: "إدارة الخطوط",
    btn_trainer_manager: "إدارة المدربين",
    btn_excel_template: "قالب الإكسل المعتمد",
    system_status_title: "محرك CertFlow Studio",
    status_online: "متصل وجاهز",
    system_status_desc: "نظام إدارة الخطوط ومعالجة تواقيع المدربين نشط بدقة عالية",
    stat_fonts: "الخطوط المثبتة:",
    stat_trainers: "المدربين المسجلين:",
    phase1_badge: "المرحلة الأولى: البنية الأساسية وإدارة الخطوط والمدربين",
    designer_hero_title: "استوديو مصمم القوالب الطباعية",
    designer_hero_desc: "أنشئ قوالب الشهادات فائقة الجودة بدقة طباعية متناهية (٣٠٠ نقطة/بوصة). يمكنك تجهيز خطوط الطباعة المعتمدة، وإعداد ملفات المدربين مع التفريغ التلقائي لورق التوقيع، وتحميل قالب الإكسل الموحد.",
    btn_manage_fonts_hero: "إدارة وتثبيت الخطوط (.ttf, .otf)",
    btn_manage_trainers_hero: "إدارة المدربين وتفريغ التواقيع",
    btn_download_excel_hero: "تحميل قالب الإكسل المعتمد (.xlsx)",
    btn_live_preview: "المعاينة الطباعية (٣٠٠ نقطة/بوصة)",
    btn_preview_engine: "المعاينة الطباعية المباشرة (٣٠٠ نقطة/بوصة)",
    card_prepress_title: "المحرك الطباعي ومطابقة الهوامش",
    card_prepress_desc: "مطابقة صارمة لمعايير الطباعة الاحترافية. إحداثيات العناصر تبدأ من الزاوية العلوية اليسرى لخط القص تماماً.",
    label_bidi_engine: "محرك التشكيل واللغات:",
    label_shrink_active: "التحجيم التلقائي للأسماء: مفعل",
    btn_open_preview: "معاينة رندرة الشهادة",
    modal_preview_title: "المعاينة الطباعية المباشرة (محرك الطباعة الفائقة)",
    modal_preview_subtitle: "تشكيل عربي فائق الدقة، تحجيم تلقائي للأسماء، وتثبيت التوقيع المتجهي",
    card_trainers_title: "ملفات وتواقيع المدربين",
    card_trainers_desc: "إدارة ملفات المدربين، روابط قوقل شيت الخاصة بكل مدرب، وتفريغ خلفيات ورق التوقيع تلقائياً مع اقتصاص حواف التوقيع بدقة.",
    label_trainers_count: "المدربين النشطين:",
    label_trim_enabled: "ميزة التفريغ التلقائي والاقتصاص: مفعلة",
    btn_open_trainer_manager: "فتح مدير المدربين",
    card_excel_title: "قالب الإكسل المعتمد",
    card_excel_desc: "ملف إكسل منسق جاهز يحتوي على الأعمدة القياسية المعتمدة لمنصة الشهادات لتوليد الدفعات بدون أخطاء مطابقة أعمدة.",
    btn_download_excel_card: "تحميل القالب (.xlsx)",
    trainers_overview_title: "نظرة عامة على المدربين والتواقيع المفرغة",
    btn_add_trainer_short: "إضافة مدرب",
    loading_trainers: "جاري تحميل المدربين...",
    no_trainers_found: "لم تتم إضافة أي مدرب حتى الآن. اضغط إضافة مدرب للبدء.",
    operator_badge: "منصة الموظف - التوليد الدفعي للشهادات",
    operator_title: "توليد شهادات المتدربين والتحقق الدفعي",
    operator_desc: "واجهة العمل التشغيلية للموظفين لربط جداول بيانات المتدربين، واختيار قالب الشهادة والمدرب المسؤول، وفحص الأسماء مع التحجيم التلقائي قبل التصدير النهائي.",
    operator_notice_title: "جاهزية بيئة التشغيل:",
    operator_notice_body: "تم إكمال البنية الأساسية. يتم حالياً استخدام خطوط الطباعة المرفوعة وبيانات المدربين المسجلين في النظام.",
    btn_back_to_designer: "العودة لاستوديو المصمم",
    btn_download_excel_short: "تحميل القالب المعتمد",
    modal_font_title: "إدارة خطوط الطباعة",
    modal_font_subtitle: "تثبيت واستعراض الخطوط في مجلد fonts",
    drop_font_text: "اسحب وأفلت ملفات الخطوط هنا أو",
    browse_files: "تصفح من جهازك",
    font_formats_hint: "صيغ الخطوط المدعومة: TrueType (.ttf) و OpenType (.otf)",
    uploading_font: "جاري رفع وفحص الخطوط...",
    installed_fonts_title: "الخطوط المثبتة حالياً",
    font_footer_tip: "يتم استخدام هذه الخطوط تلقائياً في رندرة شهادات PDF بدقة ٣٠٠ نقطة/بوصة",
    btn_close: "إغلاق",
    step1_title: "المدرب والتوقيع المفرغ",
    step1_desc: "اختيار المدرب المسؤول وتوقيعه المفرغ تلقائياً من خلفيات الورق بدقة لجلوسه الطبيعي على سطر الشهادة.",
    step2_title: "مصدر بيانات المتدربين",
    step2_desc: "ربط جدول قوقل شيت أو رفع ملف الإكسل المعتمد المحتوي على أسماء المتدربين وتواريخ التدريب.",
    step3_title: "فحص الأسماء والتوليد الطباعي",
    step3_desc: "فحص ذكي للأسماء الطويلة مع التحجيم التلقائي المتقن لضمان عدم خروج أي حرف عن إطار الشهادة والتصدير فائق الدقة.",
    btn_select_trainer: "اختيار / مراجعة المدربين",
    operator_trainers_title: "قائمة المدربين وتواقيعهم المعتمدة الجاهزة للطباعة",
    modal_trainers_title: "إدارة ملفات المدربين والتواقيع",
    modal_trainers_subtitle: "إضافة وتعديل المدربين، روابط قوقل شيت وتفريغ التواقيع تلقائياً",
    btn_add_trainer_modal: "إضافة مدرب جديد",
    form_new_trainer_title: "بيانات المدرب الجديد والتوقيع",
    form_edit_trainer_title: "تعديل بيانات المدرب والتوقيع",
    btn_back_to_list: "العودة لقائمة المدربين",
    label_trainer_name: "اسم المدرب",
    label_scale_factor: "معامل تحجيم التوقيع (%)",
    label_sheet_url: "رابط قوقل شيت أو تطبيق Google Apps Script (قراءة CSV وكتابة doPost)",
    sheet_url_hint: "يدعم روابط شيت قوقل المباشرة أو تطبيقات Google Apps Script (قراءة CSV وكتابة اسم القالب)",
    label_script_url: "رابط كتابة القالب (اختياري)",
    script_url_hint: "إذا استخدمت رابط التطبيق في الحقل أعلاه، فسيُعتمد تلقائياً للقراءة والكتابة",
    label_name_col: "عنوان عمود اسم المتدرب",
    label_time_col: "عنوان عمود وقت التسجيل",
    col_name_default: "الافتراضي: الاسم",
    col_time_default: "الافتراضي: وقت التسجيل",
    label_signature_upload: "ملف التوقيع المعتمد",
    signature_types_hint: "(ملف متجهي PDF، صورة شفافة PNG، أو ورق مصور JPG)",
    choose_signature_file: "اختر ملف التوقيع (PDF أو صورة)",
    auto_trim_notice: "يتعرف تلقائياً على الملف المتجهي والشفاف ويفرغ الورق الأبيض تلقائياً",
    sig_preview_placeholder: "معاينة التوقيع المفرغ",
    sig_processing: "جاري التفريغ والاقتصاص...",
    sig_trimmed_success: "تمت معالجة التوقيع واقتصاص الحواف بنجاح",
    btn_cancel: "إلغاء",
    btn_save_trainer: "حفظ ملف المدرب",
    trainers_footer_tip: "يتم حفظ ملفات المدربين والتواقيع المفرغة محلياً في مجلد trainers_store",
    confirm_delete_trainer: "هل أنت متأكد من حذف هذا المدرب وتوقيعه؟",
    confirm_delete_font: "هل أنت متأكد من حذف هذا الخط؟",
    font_sample_ar: "أبجد هوز حطي كلمن 1234567890",
    font_sample_en: "The quick brown fox jumps over the lazy dog",
    toast_font_uploaded: "تم رفع وتثبيت الخط بنجاح",
    toast_font_deleted: "تم حذف ملف الخط",
    toast_trainer_saved: "تم حفظ ملف المدرب ومعالجة التوقيع بنجاح",
    toast_trainer_deleted: "تم حذف ملف المدرب",
    action_edit: "تعديل",
    action_delete: "حذف",
    nav_operator: "منصة الموظف",
    nav_designer: "استوديو المصمم",
    nav_trainers: "المدربين والتواقيع",
    nav_excel_template: "قالب الإكسل",
    btn_language: "اللغة",
    sidebar_system_ready: "محرك الطباعة الفائقة (٣٠٠ نقطة/بوصة)",
    op_btn_prev: "السابق",
    op_btn_next: "التالي",
    op_btn_fit: "ملاءمة مساحة العرض مع الشاشة",
    op_sidebar_title: "إعدادات التشغيل والبيانات",
    op_sidebar_sub: "ربط البيانات وتجهيز دفعات الشهادات",
    btn_reset: "إعادة ضبط",
    tip_reset_data: "إعادة ضبط بيانات التشغيل والقالب",
    op_label_company: "فلترة حسب الجهة / الشركة:",
    op_label_template: "اختيار قالب الشهادة:",
    label_template: "القالب:",
    label_template_prefix: "القالب:",
    tab_google_sheet: "قوقل شيت للمدرب",
    tab_excel_file: "ملف إكسل / CSV",
    op_label_trainer: "المدرب المسؤول (التوقيع وشيت البيانات)",
    btn_fetch: "جلب",
    tip_fetch_sheet: "جلب وتحديث بيانات شيت قوقل الآن",
    op_label_timestamp_filter: "تاريخ التدريب المسجل:",
    op_binding_title: "الربط التلقائي الثلاثي الذكي:",
    bind_trainee_prefix: "اسم المتدرب: عمود",
    bind_date_prefix: "تاريخ التدريب: عمود",
    bind_sig_auto: "توقيع المدرب: توقيع المدرب المعتمد تلقائياً",
    op_choose_excel: "اختر أو اسحب ملف Excel / CSV",
    op_excel_hint: "يدعم .xlsx بجميع أوراقه أو ملفات .csv",
    op_label_excel_sheet: "اختر ورقة العمل:",
    op_label_excel_trainer: "توقيع المدرب للدفعة:",
    op_label_fixed_date: "تاريخ ثابت موحد للدفعة (اختياري):",
    op_fixed_date_ph: "مثال: 15 نوفمبر 2026 أو 2026-11-15",
    tip_pick_calendar: "اختيار من التقويم",
    op_map_name_label: "عمود اسم المتدرب في الإكسل:",
    op_map_date_label: "عمود تاريخ التدريب في الإكسل:",
    op_hygiene_active: "تنظيف النصوص التلقائي:",
    status_active_badge: "نشط",
    op_hygiene_desc: "إزالة الفراغات المزدوجة، تنظيف علامات الترقيم، وضبط التشكيل العربي",
    op_label_date_format: "صيغة عرض التاريخ في الشهادة:",
    date_fmt_auto: "تلقائي ذكي (نفس الإدخال أو منسق)",
    date_fmt_ar: "عربي كتابي (١٥ نوفمبر ٢٠٢٦)",
    date_fmt_en: "إنجليزي كتابي (November 15, 2026)",
    date_fmt_dmy_dash: "رقمي شرطات يوم-شهر-سنة (15-11-2026)",
    date_fmt_ymd_dash: "رقمي قياسي سنة-شهر-يوم (2026-11-15)",
    date_fmt_dmy_slash: "رقمي شرطات مائلة يوم/شهر/سنة (15/11/2026)",
    date_fmt_ymd_slash: "رقمي شرطات مائلة سنة/شهر/يوم (2026/11/15)",
    date_fmt_asis: "كما هو في الجدول تماماً دون تعديل",
    op_shrink_warning_default: "تنبيه طباعي: النص يتجاوز إطار الشهادة عند أقصى نسبة تقليص مسموحة!",
    op_readiness_title: "جاهزية الدفعة:",
    btn_batch_generate: "توليد دفعات الشهادات الطباعية (٣٠٠ نقطة/بوصة)",
    op_select_company_placeholder: "— اختر اسم الشركة أولاً —",
    op_all_companies: "جميع الشركات (الكل)",
    op_select_company_first: "— يرجى اختيار الشركة أولاً —",
    op_select_template_placeholder: "— اختر قالب الشهادة —",
    op_search_templates_ph: "بحث سريع في القوالب...",
    op_no_sheet_linked: "لم يتم ربط شيت قوقل لهذا المدرب",
    op_empty_state_title: "بانتظار اختيار قالب الشهادة",
    op_empty_state_desc: "يرجى تحديد الجهة والقالب من الشريط الجانبي لبدء معاينة ورندرة الشهادات الطباعية بدقة ٣٠٠ نقطة/بوصة.",
    op_step1_label: "الخطوة 1: اختيار الشركة",
    op_step2_label: "الخطوة 2: اختيار القالب",
    op_hide_issued_label: "تجاهل من تم إصدار شهادات لهم مسبقاً",
    op_date_completed_badge: "✓ مكتمل",
    op_date_unissued_count: "متبقي",
    ph_company_name: "اسم الجهة / الشركة",
    tip_company_name: "اسم الجهة / الشركة التابع لها القالب",
    ph_template_name: "اسم القالب التعريفي",
    tip_template_name: "اسم القالب التعريفي",
    tip_upload_pdf: "رفع أو استبدال ملف PDF الأساسي",
    btn_upload_pdf_full: "رفع ملف PDF الأساسي",
    btn_upload_pdf_short: "رفع PDF",
    label_trimbox: "خط القص TrimBox:",
    label_bleed: "البليد Bleed:",
    label_guides_toggle: "حدود القص والبليد",
    tip_undo: "تراجع",
    tip_redo: "إعادة",
    tip_print_preview: "المعاينة الطباعية المباشرة",
    btn_print_preview: "معاينة الطباعة",
    tip_add_trainee_name: "إضافة حقل اسم المتدرب الذكي",
    btn_add_name_short: "+ اسم المتدرب",
    tip_add_training_date: "إضافة حقل تاريخ التدريب الذكي",
    btn_add_date_short: "+ تاريخ التدريب",
    tip_add_signature: "إضافة إطار توقيع المدرب",
    btn_add_sig_short: "+ توقيع المدرب",
    tip_add_custom_text: "إضافة حقل نصي مخصص",
    btn_add_custom_short: "+ نص مخصص",
    btn_save_template: "حفظ القالب",
    tip_duplicate_tpl: "استنساخ القالب الحالي",
    tip_export_json: "تصدير إعدادات القالب كملف JSON",
    tip_import_json: "استيراد قالب من ملف JSON",
    tip_delete_tpl: "حذف هذا القالب نهائياً",
    btn_fit_100: "ملاءمة الشاشة",
    canvas_loading_text: "جاري تحميل استوديو المصمم...",
    preview_label_sample_name: "اسم المتدرب للتجربة:",
    preview_name_input_ph: "اسم المتدرب للتجربة",
    preview_label_guides: "إظهار خطوط القص والهوامش (Trim/Bleed)",
    btn_refresh: "تحديث",
    preview_loading_text: "جاري رندرة الشهادة بمحرك الطباعة الفائقة...",
    preview_footer_note: "مقياس الإحداثيات يبدأ من الزاوية العلوية اليسرى لخط القص (مطابق لبرامج النشر المكتبي)",
    ph_trainer_name: "اسم المدرب",
    ph_trainer_sheet: "رابط قوقل شيت أو تطبيق Google Apps Script",
    ph_trainer_script: "رابط تطبيق Google Apps Script (اختياري)",
    ph_trainer_name_col: "الاسم",
    ph_trainer_time_col: "وقت التسجيل",
    badge_prepress_300: "الطباعة الفائقة (٣٠٠ نقطة/بوصة)",
    batch_modal_title: "تصدير دفعة الشهادات الطباعية",
    batch_modal_subtitle: "إعداد خيارات التصدير بصيغة الطباعة عالية الدقة ٣٠٠ نقطة/بوصة",
    batch_export_mode_label: "صيغة التصدير المطلوبة:",
    batch_opt_combined_pdf: "ملف PDF واحد مدمج لجميع الشهادات الطباعية",
    batch_opt_pdfs_zip: "حزمة مضغوطة ZIP تحتوي على ملفات PDF منفصلة لكل متدرب",
    batch_opt_jpegs_zip: "حزمة مضغوطة ZIP تحتوي على صور عالية الدقة (٣٠٠ نقطة/بوصة)",
    batch_export_mode_hint: "يحافظ الملف المدمج على مقاسات القص والبليد والتواقيع المتجهية بدقة كاملة.",
    batch_range_label: "نطاق السجلات المراد تصديرها:",
    batch_range_hint: "الكل أو 1-10 أو 5- أو 1,3,5-8",
    batch_prefix_label: "بادئة اسم الملف المخرج:",
    batch_dpi_label: "دقة الرندرة الطباعية (نقطة/بوصة):",
    batch_dpi_300: "٣٠٠ نقطة/بوصة (معيار المطابع الاحترافية)",
    batch_dpi_150: "١٥٠ نقطة/بوصة (معاينة رقمية سريعة)",
    batch_dpi_600: "٦٠٠ نقطة/بوصة (دقة أرشيفية متقدمة)",
    batch_webhook_label: "رابط الكتابة الراجعة وتحديث القالب (Apps Script / Webhook):",
    batch_webhook_badge: "مرتبط تلقائياً بالمدرب",
    batch_webhook_ph: "رابط Google Apps Script للكتابة الراجعة...",
    batch_webhook_hint: "يتم إرسال أسماء القوالب المعتمدة تلقائياً لكل متدرب عبر doPost لتطبيق Google Apps Script.",
    batch_loading_text: "جاري رندرة وتوليد حزمة الشهادات بمحرك الطباعة الفائقة... يرجى الانتظار",
    btn_start_batch_export: "بدء التصدير وتحميل الملف",
    pin_modal_title: "رمز الدخول لاستوديو المصمم",
    pin_modal_subtitle: "يرجى إدخال الرقم السري لحماية القوالب من التعديل غير المقصود",
    pin_modal_error: "الرقم السري غير صحيح",
    btn_unlock_designer: "دخول الاستوديو",
    op_no_matching_templates: "لا توجد قوالب مطابقة",
    no_trainers_registered: "لا يوجد مدربين مسجلين",
    label_trainer_prefix: "المدرب:",
    status_unspecified: "غير محدد",
    op_no_records: "لا توجد سجلات محملة",
    badge_waiting_template: "بانتظار تحديد القالب",
    badge_overflow: "تنبيه تجاوز الإطار!",
    warn_overflow: "تنبيه طباعي: النص يتجاوز إطار الشهادة عند أقصى نسبة تقليص مسموحة!",
    badge_shrunk_pct: "تم التقليص بنسبة:",
    trainer_no_signature: "بدون توقيع",
    trainer_no_sheet: "لم يتم ربط شيت قوقل بعد",
    trainer_active: "نشط",
    sig_line_placeholder: "خط التوقيع",
    sig_default_label: "توقيع المدرب",
    btn_cancel_preview: "إلغاء المعاينة والعودة للتصميم",
    insp_template_settings: "إعدادات القالب العام",
    insp_click_field_hint: "انقر على أي حقل في الشهادة لتعديل خصائصه الطباعية",
    insp_company_label: "اسم الجهة / الشركة:",
    insp_add_company_tip: "إضافة جهة / شركة جديدة",
    insp_tpl_name_label: "اسم القالب:",
    insp_trimbox_size: "مقاس القص (TrimBox):",
    insp_bleed_detected: "البليد المكتشف (Bleed):",
    insp_add_smart_fields: "إضافة حقول طباعية ذكية:",
    btn_add_name_field: "+ حقل اسم المتدرب",
    btn_add_date_field: "+ حقل تاريخ التدريب",
    btn_add_sig_field: "+ إطار توقيع المدرب",
    btn_add_custom_field: "+ حقل نصي إضافي",
    insp_fields_in_template: "الحقول المضافة للقالب",
    insp_badge_text_frame: "حقل نصي",
    insp_label_preview_text: "نص المعاينة:",
    insp_font_ar: "الخط العربي:",
    insp_font_en: "الخط الإنجليزي (Latin):",
    insp_same_as_ar: "نفس الخط العربي",
    insp_font_size: "حجم الخط (نقطة):",
    insp_auto_shrink: "التقليص التلقائي (%):",
    insp_baseline_offset: "إزاحة السطر (ملم):",
    insp_center_page: "توسيط الحقل في الصفحة:",
    insp_center_h: "توسيط أفقي",
    insp_center_v: "توسيط رأسي",
    insp_align_9point: "المحاذاة داخل الإطار:",
    align_right: "يمين",
    align_center: "وسط",
    align_left: "يسار",
    valign_top: "أعلى",
    valign_middle: "منتصف",
    valign_bottom: "أسفل",
    insp_print_color: "لون الطباعة:",
    insp_pure_black: "أسود طباعي ١٠٠٪ K",
    insp_pure_black_tip: "اعتماد أسود طباعي صريح C:0 M:0 Y:0 K:100 لمنع شبحية الحروف",
    insp_text_direction: "اتجاه النص:",
    insp_dir_auto: "تلقائي",
    insp_dir_rtl: "عربي (من اليمين لليسار)",
    insp_dir_ltr: "إنجليزي (من اليسار لليمين)",
    insp_lock_field: "قفل الحقل للموظف",
    insp_coords_trimbox: "إحداثيات الحقل (من الزاوية 0,0 لخط القص بالملم):",
    insp_width_mm: "العرض (ملم):",
    insp_height_mm: "الارتفاع (ملم):",
    insp_delete_field: "حذف هذا الحقل",
    insp_badge_sig_frame: "إطار توقيع",
    insp_preview_trainer: "المدرب المعروض للمعاينة:",
    insp_center_sig_page: "توسيط إطار التوقيع في الصفحة:",
    insp_anchor_point: "نقطة الارتكاز:",
    insp_anchor_bottom_center: "أسفل وسط (على خط التوقيع)",
    insp_anchor_middle_center: "توسيط كامل",
    insp_scale_factor: "معامل التكبير (%):",
    insp_multiply_blend: "تفعيل وضع الدمج",
    insp_multiply_hint: "لضمان اندماج حبر التوقيع طبيعياً مع خطوط وزخارف الشهادة",
    insp_sig_coords: "إحداثيات إطار التوقيع (بالملم):",
    insp_delete_sig: "حذف إطار التوقيع",
    toast_no_records_loaded: "لا توجد سجلات بيانات محملة حالياً",
    toast_center_h: "تم توسيط الحقل أفقياً في الصفحة",
    toast_center_v: "تم توسيط الحقل رأسياً في الصفحة",
    toast_field_selected_name: "تم تحديد حقل اسم المتدرب",
    toast_field_selected_date: "تم تحديد حقل تاريخ التدريب",
    toast_field_selected_sig: "تم تحديد إطار توقيع المدرب",
    toast_field_added_name: "تمت إضافة حقل اسم المتدرب",
    toast_field_added_date: "تمت إضافة حقل تاريخ التدريب",
    toast_field_added_sig: "تمت إضافة إطار توقيع المدرب",
    toast_field_added_custom: "تمت إضافة حقل نصي جديد",
    toast_field_deleted: "تم حذف الحقل بنجاح",
    toast_tpl_saved: "تم حفظ القالب بنجاح في مجلد templates_store",
    toast_tpl_deleted: "تم حذف القالب بنجاح",
    toast_tpl_no_saved: "لا يوجد قالب محفوظ لحذفه",
    toast_tpl_duplicated: "تم استنساخ القالب بنجاح",
    toast_tpl_exported: "تم تصدير ملف القالب بنجاح",
    toast_tpl_imported: "تم استيراد القالب بنجاح",
    toast_undo: "تم التراجع",
    toast_redo: "تمت الإعادة",
    toast_pure_black: "تم تطبيق اللون الأسود الطباعي الخالص (١٠٠٪ K)",
    toast_pdf_inspected: "تم فحص ملف PDF بنجاح واعتماد أبعاد خط القص والبليد",
    toast_rendered_300dpi: "تمت رندرة الشهادة بمحرك الطباعة الفائقة بدقة ٣٠٠ نقطة/بوصة",
    overlay_pdf_inspecting: "جاري فحص أبعاد ملف PDF وهامش الأمان الطباعي...",
    overlay_rendering_300dpi: "جاري رندرة معاينة الطباعة فائقة الدقة (٣٠٠ نقطة/بوصة)...",
    toast_enter_trainer_name: "يرجى إدخال اسم المدرب",
    toast_select_tpl_first: "يرجى اختيار قالب الشهادة أولاً",
    toast_no_records_export: "لا توجد سجلات بيانات لتصديرها",
    toast_select_trainer_sheet: "يرجى اختيار مدرب مسجل لديه رابط شيت قوقل",
    toast_fetching_sheet: "جاري جلب بيانات قوقل شيت وفحص التواريخ...",
    toast_inspecting_excel: "جاري فحص وتجهيز ملف الإكسل...",
    toast_reset_complete: "تمت إعادة ضبط البيانات والخيارات للحالة الأولية",
    confirm_delete_field: "هل أنت متأكد من حذف هذا الحقل؟",
    confirm_delete_template: "هل أنت متأكد من حذف هذا القالب نهائياً؟"
  },
  en: {
    app_title: "CertFlow Studio",
    app_subtitle: "Print Certificate Platform",
    app_tagline: "High-precision print certificate Data Merge alternative",
    mode_designer: "Designer Studio",
    mode_operator: "Operator Platform",
    page_title: "CertFlow Studio | Print Certificate Platform",
    tip_manage_trainers: "Manage Trainer Profiles & Signatures",
    tip_download_excel: "Download Standard Excel Template (.xlsx)",
    tip_prev_record: "Previous Record",
    tip_next_record: "Next Record",
    tip_widest_name: "Jump to longest name to test maximum auto-shrink",
    op_btn_widest: "Longest Name",
    op_jump_placeholder: "Jump to Trainee...",
    tip_tpl_name: "Active Program WorkBook Name",
    tip_trainer_name: "Assigned Trainer",
    tip_cert_date: "Approved Training Date",
    badge_optimal_fit: "100% Fit",
    op_btn_fit: "Fit to Screen",
    tip_refresh_preview: "Refresh Live Print Preview",
    op_canvas_loading_text: "Rendering certificate with Prepress engine...",
    op_footer_note: "Coordinate system originates at top-left of TrimBox (matching Adobe InDesign)",
    op_bottom_tpl_default: "Program WorkBook: —",
    op_bottom_trainer_default: "Trainer: Unspecified",
    btn_font_manager: "Font Manager",
    btn_trainer_manager: "Trainer Profiles",
    btn_excel_template: "Standard Excel Template",
    system_status_title: "CertFlow Studio Engine",
    status_online: "Online & Ready",
    system_status_desc: "Font management & trainer signature auto-processing active at high precision",
    stat_fonts: "Installed Fonts:",
    stat_trainers: "Registered Trainers:",
    phase1_badge: "Phase 1: Core Scaffolding, Font Manager & Trainer Profiles",
    designer_hero_title: "Print Certificate Designer Studio",
    designer_hero_desc: "Build ultra-high-quality certificates with exact print fidelity (Print-Ready 300 DPI). Prepare approved print fonts, configure trainer profiles with automatic paper signature background removal and trim, and download the standardized Excel format.",
    btn_manage_fonts_hero: "Manage & Install Fonts (.ttf, .otf)",
    btn_manage_trainers_hero: "Manage Trainers & Signatures",
    btn_download_excel_hero: "Download Standard Excel Template (.xlsx)",
    btn_live_preview: "Print Preview (300 DPI)",
    btn_preview_engine: "Live Print Preview (300 DPI)",
    card_prepress_title: "Prepress Engine & Boxes",
    card_prepress_desc: "Strict adherence to prepress standards (MediaBox, BleedBox, TrimBox). All coordinates originate from the Top-Left of the TrimBox, matching Adobe InDesign.",
    label_bidi_engine: "BiDi & Typography Engine:",
    label_shrink_active: "Single-line auto-shrink: Active",
    btn_open_preview: "Preview Certificate Render",
    modal_preview_title: "Live Certificate Prepress Preview (300 DPI)",
    modal_preview_subtitle: "High-precision Arabic BiDi shaping, single-line auto-shrink, and vector signature anchoring",
    card_trainers_title: "Trainer Profiles & Signatures",
    card_trainers_desc: "Manage trainer profiles, dedicated Google Sheets, and automatically remove white paper backgrounds with tight stroke bounding-box trim.",
    label_trainers_count: "Active Trainers:",
    label_trim_enabled: "Auto-Trim & Background Removal: Active",
    btn_open_trainer_manager: "Open Trainer Manager",
    card_excel_title: "Certified Excel Template",
    card_excel_desc: "Pre-formatted Excel sheet with standardized columns for batch certificate generation without column mismatch errors.",
    btn_download_excel_card: "Download Template (.xlsx)",
    trainers_overview_title: "Overview of Trainers & Cleaned Signatures",
    btn_add_trainer_short: "Add Trainer",
    loading_trainers: "Loading trainer profiles...",
    no_trainers_found: "No trainers added yet. Click Add Trainer to get started.",
    operator_badge: "Operator Platform - Batch Generator",
    operator_title: "Batch Generation & Trainee Verification",
    operator_desc: "Operational workspace for staff to connect Google Sheets or Excel files, select certificate templates and trainers, and verify auto-shrink text fitting before export.",
    operator_notice_title: "Workspace Readiness:",
    operator_notice_body: "Core scaffolding is complete. The system is actively using uploaded print fonts and stored trainer profiles.",
    btn_back_to_designer: "Back to Designer Studio",
    btn_download_excel_short: "Download Excel Template",
    modal_font_title: "Print Font Manager",
    modal_font_subtitle: "Install and preview .TTF and .OTF fonts in ./fonts/",
    drop_font_text: "Drag & drop font files here, or",
    browse_files: "browse from device",
    font_formats_hint: "Supported formats: TrueType (.ttf) and OpenType (.otf) - Multi-file selection supported",
    uploading_font: "Uploading and inspecting font files...",
    installed_fonts_title: "Currently Installed Fonts",
    font_footer_tip: "These fonts are loaded directly when rendering 300 DPI print certificates",
    btn_close: "Close",
    step1_title: "Trainer & Transparent Signature",
    step1_desc: "Select trainer and verified transparent auto-trimmed signature for natural certificate placement.",
    step2_title: "Trainee Data Source",
    step2_desc: "Connect Google Sheet or certified Excel file with trainee names and training dates.",
    step3_title: "Name Verification & Print Export",
    step3_desc: "Smart name length check with auto-shrink font scaling ensuring no text overflows the frame.",
    btn_select_trainer: "Select / Review Trainers",
    operator_trainers_title: "Approved Trainers & Signatures Ready for Print",
    modal_trainers_title: "Trainer Profiles & Signature Manager",
    modal_trainers_subtitle: "Add/edit trainers, Google Sheet URLs, and auto-trim transparent signatures",
    btn_add_trainer_modal: "Add New Trainer",
    form_new_trainer_title: "New Trainer Profile & Signature",
    form_edit_trainer_title: "Edit Trainer Profile & Signature",
    btn_back_to_list: "Back to Trainers List",
    label_trainer_name: "Trainer Name",
    label_scale_factor: "Signature Scale Factor %",
    label_sheet_url: "Trainees Google Sheet or Apps Script Web App URL",
    sheet_url_hint: "Supports direct Google Sheet URLs or Google Apps Script Web Apps (doGet CSV & doPost template sync)",
    label_script_url: "Google Apps Script Write-Back URL (Optional)",
    script_url_hint: "If you used an Apps Script URL above, it will automatically handle both reading and writing",
    label_name_col: "Trainee Name Column Header",
    label_time_col: "Timestamp Column Header",
    col_name_default: "Default: Name",
    col_time_default: "Default: Timestamp",
    label_signature_upload: "Signature Image",
    signature_types_hint: "(PNG, JPG, JPEG - paper photos supported)",
    choose_signature_file: "Select Signature File",
    auto_trim_notice: "White paper background will be removed and margins trimmed automatically",
    sig_preview_placeholder: "Transparent signature preview",
    sig_processing: "Removing background & trimming...",
    sig_trimmed_success: "Paper background removed & margins trimmed successfully",
    btn_cancel: "Cancel",
    btn_save_trainer: "Save Trainer Profile",
    trainers_footer_tip: "Trainer profiles and cleaned transparent signatures are saved locally in ./trainers_store/",
    confirm_delete_trainer: "Are you sure you want to delete this trainer and their signature?",
    confirm_delete_font: "Are you sure you want to delete this font file?",
    font_sample_ar: "Abjad Hawwaz 1234567890",
    font_sample_en: "The quick brown fox jumps over the lazy dog",
    toast_font_uploaded: "Font uploaded and registered successfully",
    toast_font_deleted: "Font file deleted",
    toast_trainer_saved: "Trainer profile saved and signature processed successfully",
    toast_trainer_deleted: "Trainer profile deleted",
    action_edit: "Edit",
    action_delete: "Delete",
    nav_operator: "Operator Workspace",
    nav_designer: "Designer Studio",
    nav_trainers: "Trainers & Signatures",
    nav_excel_template: "Excel Template",
    btn_language: "Language",
    sidebar_system_ready: "Prepress Engine (300 DPI)",
    op_btn_prev: "Previous",
    op_btn_next: "Next",
    op_btn_fit: "Fit to Screen",
    op_sidebar_title: "Operator Controls & Data",
    op_sidebar_sub: "Data Binding & Batch Generation",
    btn_reset: "Reset",
    tip_reset_data: "Reset Operator Data & Template",
    op_label_company: "Affiliate / Client:",
    op_label_template: "Program WorkBook:",
    label_template: "Program WorkBook:",
    label_template_prefix: "Program WorkBook:",
    tab_google_sheet: "Trainer Google Sheet",
    tab_excel_file: "Excel / CSV File",
    op_label_trainer: "Trainer Name (Signature & Data Sheet):",
    btn_fetch: "Fetch",
    tip_fetch_sheet: "Fetch and refresh Google Sheet data now",
    op_label_timestamp_filter: "Filter by Training Date (Timestamp):",
    op_binding_title: "Smart 3-Way Auto-Binding:",
    bind_trainee_prefix: "Trainee Name: column",
    bind_date_prefix: "Training Date: column",
    bind_sig_auto: "Trainer Signature: Assigned trainer signature automatically",
    op_choose_excel: "Choose or drop Excel / CSV file",
    op_excel_hint: "Supports .xlsx with all sheets or .csv",
    op_label_excel_sheet: "Select Worksheet:",
    op_label_excel_trainer: "Trainer Name for Batch:",
    op_label_fixed_date: "Unified Training Date for Batch (Optional):",
    op_fixed_date_ph: "e.g., November 15, 2026 or 2026-11-15",
    tip_pick_calendar: "Pick from calendar",
    op_map_name_label: "Trainee Name Column in Excel:",
    op_map_date_label: "Training Date Column in Excel:",
    op_hygiene_active: "Strict Text Hygiene:",
    status_active_badge: "Active",
    op_hygiene_desc: "Remove redundant spaces, sanitize punctuation, and normalize text",
    op_label_date_format: "Training Date Format:",
    date_fmt_auto: "Smart Auto (Preserve text or format)",
    date_fmt_ar: "Arabic Textual",
    date_fmt_en: "English Textual (November 15, 2026)",
    date_fmt_dmy_dash: "Numeric DD-MM-YYYY (15-11-2026)",
    date_fmt_ymd_dash: "Standard YYYY-MM-DD (2026-11-15)",
    date_fmt_dmy_slash: "Numeric DD/MM/YYYY (15/11/2026)",
    date_fmt_ymd_slash: "Numeric YYYY/MM/DD (2026/11/15)",
    date_fmt_asis: "As-is from sheet without modification",
    op_shrink_warning_default: "Print Alert: Text overflows the frame even at maximum allowed shrink percentage!",
    op_readiness_title: "Batch Readiness:",
    btn_batch_generate: "Generate Batch Certificates (300 DPI)",
    op_select_company_placeholder: "— Select Affiliate / Client First —",
    op_all_companies: "All Affiliates (All Clients)",
    op_select_company_first: "— Please select Affiliate first —",
    op_select_template_placeholder: "— Select Program WorkBook —",
    op_search_templates_ph: "Quick search Program WorkBooks...",
    op_no_sheet_linked: "No Google Sheet linked for this trainer",
    op_empty_state_title: "Waiting for Program WorkBook Selection",
    op_empty_state_desc: "Please select an Affiliate / Client and Program WorkBook from the sidebar to start live 300 DPI preview and generation.",
    op_step1_label: "Step 1: Select Affiliate / Client",
    op_step2_label: "Step 2: Select Program WorkBook",
    op_hide_issued_label: "Ignore trainees with issued certificates",
    op_date_completed_badge: "✓ Issued",
    op_date_unissued_count: "remaining",
    ph_company_name: "Affiliate / Client",
    tip_company_name: "Affiliate / Client Name for this WorkBook",
    ph_template_name: "Program WorkBook Name",
    tip_template_name: "Program WorkBook Display Name",
    tip_upload_pdf: "Upload or replace Background PDF",
    btn_upload_pdf_full: "Upload Background PDF",
    btn_upload_pdf_short: "Upload PDF",
    label_trimbox: "TrimBox:",
    label_bleed: "Bleed:",
    label_guides_toggle: "Trim & Bleed Guides",
    tip_undo: "Undo",
    tip_redo: "Redo",
    tip_print_preview: "Live Print Preview",
    btn_print_preview: "Print Preview",
    tip_add_trainee_name: "Add Trainee Name Field",
    btn_add_name_short: "+ Trainee Name",
    tip_add_training_date: "Add Training Date Field",
    btn_add_date_short: "+ Training Date",
    tip_add_signature: "Add Trainer Signature Frame",
    btn_add_sig_short: "+ Trainer Signature",
    tip_add_custom_text: "Add Custom Text Field",
    btn_add_custom_short: "+ Custom Text",
    btn_save_template: "Save WorkBook",
    tip_duplicate_tpl: "Duplicate Current WorkBook",
    tip_export_json: "Export WorkBook JSON",
    tip_import_json: "Import WorkBook from JSON",
    tip_delete_tpl: "Delete this WorkBook permanently",
    btn_fit_100: "Fit Screen",
    canvas_loading_text: "Loading Designer Studio...",
    preview_label_sample_name: "Sample Trainee Name:",
    preview_name_input_ph: "Sample Trainee Name",
    preview_label_guides: "Show Trim & Bleed Guides",
    btn_refresh: "Refresh",
    preview_loading_text: "Rendering certificate with Prepress engine...",
    preview_footer_note: "Coordinates originate at top-left of TrimBox (matching Adobe InDesign)",
    ph_trainer_name: "Instructor Name",
    ph_trainer_sheet: "Google Sheet or Apps Script Web App URL",
    ph_trainer_script: "Google Apps Script Web App URL (Optional)",
    ph_trainer_name_col: "Name",
    ph_trainer_time_col: "Timestamp",
    badge_prepress_300: "Prepress 300 DPI",
    batch_modal_title: "Batch Certificate Export",
    batch_modal_subtitle: "Export configuration for high-precision 300 DPI printing",
    batch_export_mode_label: "Required Export Format:",
    batch_opt_combined_pdf: "Single Combined Print PDF for all certificates",
    batch_opt_pdfs_zip: "ZIP archive with individual PDF per trainee",
    batch_opt_jpegs_zip: "ZIP archive with high-res 300 DPI JPEGs",
    batch_export_mode_hint: "Combined PDF preserves TrimBox, BleedBox, and vector signatures at 100% precision.",
    batch_range_label: "Records Export Range:",
    batch_range_hint: "ALL or 1-10 or 5- or 1,3,5-8",
    batch_prefix_label: "Output Filename Prefix:",
    batch_dpi_label: "Print Render DPI:",
    batch_dpi_300: "300 DPI (Commercial Print Standard)",
    batch_dpi_150: "150 DPI (Fast Digital Preview)",
    batch_dpi_600: "600 DPI (Archival Ultra-Fine)",
    batch_webhook_label: "Write-Back & WorkBook Sync URL (Apps Script / Webhook):",
    batch_webhook_badge: "Auto-linked to Trainer",
    batch_webhook_ph: "Google Apps Script Web App URL for write-back...",
    batch_webhook_hint: "Approved WorkBook names are automatically synced per trainee via doPost.",
    batch_loading_text: "Rendering and generating certificate batch with Prepress engine... Please wait",
    btn_start_batch_export: "Start Export & Download",
    pin_modal_title: "Designer Studio Access PIN",
    pin_modal_subtitle: "Please enter security PIN to protect templates from unintended modifications",
    pin_modal_error: "Incorrect PIN code",
    btn_unlock_designer: "Unlock Studio",
    op_no_matching_templates: "No matching WorkBooks found",
    no_trainers_registered: "No trainers registered",
    label_trainer_prefix: "Trainer:",
    status_unspecified: "Unspecified",
    op_no_records: "No records loaded",
    badge_waiting_template: "Waiting for WorkBook Selection",
    badge_overflow: "Alert: Text Overflow!",
    warn_overflow: "Print Alert: Text overflows the frame even at maximum allowed shrink percentage!",
    badge_shrunk_pct: "Shrunk by:",
    trainer_no_signature: "No signature",
    trainer_no_sheet: "No Google Sheet linked yet",
    trainer_active: "Active",
    sig_line_placeholder: "Signature Line",
    sig_default_label: "Trainer Signature",
    btn_cancel_preview: "Exit Preview & Return to Designer",
    insp_template_settings: "General WorkBook Settings",
    insp_click_field_hint: "Click any certificate field to inspect its prepress properties",
    insp_company_label: "Affiliate / Client:",
    insp_add_company_tip: "Add new Affiliate / Client",
    insp_tpl_name_label: "Program WorkBook Name:",
    insp_trimbox_size: "TrimBox Size:",
    insp_bleed_detected: "Detected Bleed:",
    insp_add_smart_fields: "Add Smart Prepress Fields:",
    btn_add_name_field: "+ Trainee Name Field",
    btn_add_date_field: "+ Training Date Field",
    btn_add_sig_field: "+ Trainer Signature Frame",
    btn_add_custom_field: "+ Custom Text Field",
    insp_fields_in_template: "Fields in WorkBook",
    insp_badge_text_frame: "Text Frame",
    insp_label_preview_text: "Sample Preview Text:",
    insp_font_ar: "Arabic Font:",
    insp_font_en: "English / Latin Font:",
    insp_same_as_ar: "Same as Arabic font",
    insp_font_size: "Font Size (pt):",
    insp_auto_shrink: "Auto-Shrink Limit (%):",
    insp_baseline_offset: "Baseline Offset (mm):",
    insp_center_page: "Center Field in Page (TrimBox):",
    insp_center_h: "Center Horizontally",
    insp_center_v: "Center Vertically",
    insp_align_9point: "Frame Alignment (9-Point Grid):",
    align_right: "Right",
    align_center: "Center",
    align_left: "Left",
    valign_top: "Top",
    valign_middle: "Middle",
    valign_bottom: "Bottom",
    insp_print_color: "Print Color:",
    insp_pure_black: "100% K Pure Print Black",
    insp_pure_black_tip: "Enforce pure C:0 M:0 Y:0 K:100 to prevent halftone fringing",
    insp_text_direction: "Text Direction:",
    insp_dir_auto: "Auto BiDi",
    insp_dir_rtl: "Arabic (RTL)",
    insp_dir_ltr: "English (LTR)",
    insp_lock_field: "Lock Field for Operator",
    insp_coords_trimbox: "Field Coordinates (From TrimBox 0,0 in mm):",
    insp_width_mm: "Width (mm):",
    insp_height_mm: "Height (mm):",
    insp_delete_field: "Delete this field",
    insp_badge_sig_frame: "Signature Frame",
    insp_preview_trainer: "Preview Trainer Signature:",
    insp_center_sig_page: "Center Signature Frame in Page:",
    insp_anchor_point: "Anchor Point:",
    insp_anchor_bottom_center: "Bottom Center (on signature line)",
    insp_anchor_middle_center: "Middle Center",
    insp_scale_factor: "Scale Factor %:",
    insp_multiply_blend: "Enable Multiply Blend Mode",
    insp_multiply_hint: "Ensures signature ink blends naturally over background certificate ornaments",
    insp_sig_coords: "Signature Coordinates (mm):",
    insp_delete_sig: "Delete signature frame",
    toast_no_records_loaded: "No records currently loaded",
    toast_center_h: "Field horizontally centered",
    toast_center_v: "Field vertically centered",
    toast_field_selected_name: "Trainee Name field selected",
    toast_field_selected_date: "Training Date field selected",
    toast_field_selected_sig: "Trainer Signature frame selected",
    toast_field_added_name: "Trainee Name field added",
    toast_field_added_date: "Training Date field added",
    toast_field_added_sig: "Trainer Signature frame added",
    toast_field_added_custom: "Custom text field added",
    toast_field_deleted: "Field deleted successfully",
    toast_tpl_saved: "Template saved successfully in templates_store",
    toast_tpl_deleted: "Template deleted successfully",
    toast_tpl_no_saved: "No saved template to delete",
    toast_tpl_duplicated: "Template duplicated successfully",
    toast_tpl_exported: "Template JSON exported successfully",
    toast_tpl_imported: "Template imported successfully",
    toast_undo: "Undo",
    toast_redo: "Redo",
    toast_pure_black: "Pure 100% K print black applied",
    toast_pdf_inspected: "Base PDF inspected and TrimBox/Bleed dimensions applied",
    toast_rendered_300dpi: "Certificate rendered with true prepress engine at 300 DPI",
    overlay_pdf_inspecting: "Inspecting PDF dimensions and print bleed...",
    overlay_rendering_300dpi: "Rendering ultra-high precision print preview (300 DPI)...",
    toast_enter_trainer_name: "Please enter trainer name",
    toast_select_tpl_first: "Please select a Program WorkBook first",
    toast_no_records_export: "No records available for export",
    toast_select_trainer_sheet: "Please select a trainer with a linked Google Sheet",
    toast_fetching_sheet: "Fetching Google Sheet data and inspecting dates...",
    toast_inspecting_excel: "Inspecting and processing Excel file...",
    toast_reset_complete: "Data and settings reset to initial state",
    confirm_delete_field: "Are you sure you want to delete this field?",
    confirm_delete_template: "Are you sure you want to permanently delete this template?"
  }
};

// ==========================================================
// Initialization & Lifecycle
// ==========================================================
document.addEventListener("DOMContentLoaded", () => {
  applyLanguage(currentLang);
  const urlParams = new URLSearchParams(window.location.search);
  const initialMode = urlParams.get("mode") || "operator";
  switchMode(initialMode); // Operator Platform is default landing view
  fetchStatus();
  fetchFonts();
  fetchTrainers();
  initOperatorPlatform();
  lucide.createIcons();
});

// ==========================================================
// Language Switcher Engine
// ==========================================================
function toggleLanguage() {
  const newLang = currentLang === "ar" ? "en" : "ar";
  applyLanguage(newLang);
}

function applyLanguage(lang) {
  currentLang = lang;
  try {
    localStorage.setItem("certflow_lang", lang);
  } catch (e) {}

  const html = document.documentElement;
  html.lang = lang;
  html.dir = lang === "ar" ? "rtl" : "ltr";

  // Update label
  const label = document.getElementById("lang-label");
  if (label) label.textContent = lang === "ar" ? "EN" : "عربي";

  // Translate all marked elements
  const dict = translations[lang] || translations.ar;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (dict[key]) {
      el.textContent = dict[key];
    }
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (dict[key]) {
      el.placeholder = dict[key];
    }
  });

  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    const key = el.getAttribute("data-i18n-title");
    if (dict[key]) {
      el.title = dict[key];
    }
  });

  // Re-render trainers and dynamic UI to update localized action strings safely
  try {
    if (typeof fetchCompanies === "function") fetchCompanies();
    if (typeof renderOperatorTemplateSelect === "function") renderOperatorTemplateSelect();
    if (typeof renderSheetDateOptions === "function") renderSheetDateOptions();
    if (typeof updateRecordControls === "function") updateRecordControls();
    if (typeof updateOperatorTemplateInfo === "function") updateOperatorTemplateInfo();
    if (typeof updateTrainerBottomInfo === "function") updateTrainerBottomInfo();
    if (typeof renderTrainersList === "function") renderTrainersList(activeTrainers);
    if (typeof renderTrainersQuickGrid === "function") renderTrainersQuickGrid(activeTrainers);
    if (currentMode === "designer") {
      if (typeof renderFramesOnCanvas === "function") renderFramesOnCanvas();
      if (typeof renderInspector === "function" && currentTemplate) renderInspector();
    }
  } catch (err) {
    console.warn("applyLanguage dynamic UI refresh warning:", err);
  }

  if (window.lucide && typeof lucide.createIcons === "function") {
    lucide.createIcons();
  }
}

function t(key) {
  const dict = translations[currentLang] || translations.ar;
  return dict[key] || key;
}

// ==========================================================
// Designer Studio PIN Lock Engine
// ==========================================================
function openDesignerPinModal() {
  const modal = document.getElementById("designer-pin-modal");
  const input = document.getElementById("designer-pin-input");
  const err = document.getElementById("designer-pin-error");
  if (err) err.classList.add("hidden");
  if (input) {
    input.value = "";
    input.classList.remove("border-rose-400", "focus:border-rose-500");
  }
  if (modal) {
    modal.classList.remove("hidden");
    modal.classList.add("flex");
  }
  setTimeout(() => {
    if (input) input.focus();
  }, 100);
}

function closeDesignerPinModal() {
  const modal = document.getElementById("designer-pin-modal");
  if (modal) {
    modal.classList.add("hidden");
    modal.classList.remove("flex");
  }
}

function verifyDesignerPin() {
  const input = document.getElementById("designer-pin-input");
  const err = document.getElementById("designer-pin-error");
  const pin = input ? input.value.trim() : "";
  if (pin === DESIGNER_PIN) {
    isDesignerUnlocked = true;
    try {
      sessionStorage.setItem("certflow_designer_unlocked", "true");
    } catch (e) {}
    closeDesignerPinModal();
    if (err) err.classList.add("hidden");
    switchMode("designer");
  } else {
    if (err) err.classList.remove("hidden");
    if (input) {
      input.classList.add("border-rose-400", "focus:border-rose-500");
      input.select();
    }
  }
}

// ==========================================================
// Mode Switcher Engine
// ==========================================================
function switchMode(mode) {
  if (mode === "designer" && !isDesignerUnlocked) {
    openDesignerPinModal();
    return;
  }
  currentMode = mode;
  const designerBtn = document.getElementById("nav-designer-btn");
  const operatorBtn = document.getElementById("nav-operator-btn");
  const viewDesigner = document.getElementById("view-designer");
  const viewOperator = document.getElementById("view-operator");

  if (mode === "designer") {
    if (viewDesigner) {
      viewDesigner.classList.remove("hidden");
      viewDesigner.classList.add("flex");
    }
    if (viewOperator) {
      viewOperator.classList.add("hidden");
      viewOperator.classList.remove("flex");
    }

    if (designerBtn) {
      designerBtn.className = "w-full px-3 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 flex items-center gap-3 bg-brand-secondary text-white shadow-sm whitespace-nowrap";
    }
    if (operatorBtn) {
      operatorBtn.className = "w-full px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 flex items-center gap-3 text-blue-100 hover:text-white hover:bg-white/10 whitespace-nowrap";
    }

    // Initialize designer studio workspace
    setTimeout(() => {
      initDesignerStudio();
    }, 50);
  } else {
    if (viewDesigner) {
      viewDesigner.classList.add("hidden");
      viewDesigner.classList.remove("flex");
    }
    if (viewOperator) {
      viewOperator.classList.remove("hidden");
      viewOperator.classList.add("flex");
    }

    if (operatorBtn) {
      operatorBtn.className = "w-full px-3 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 flex items-center gap-3 bg-brand-secondary text-white shadow-sm whitespace-nowrap";
    }
    if (designerBtn) {
      designerBtn.className = "w-full px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 flex items-center gap-3 text-blue-100 hover:text-white hover:bg-white/10 whitespace-nowrap";
    }

    setTimeout(() => {
      fitOperatorCanvasToScreen();
      refreshOperatorCanvas();
    }, 50);
  }
  lucide.createIcons();
}

// ==========================================================
// System Status Sync
// ==========================================================
async function fetchStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) return;
    const data = await res.json();

    const fontCount = data.fonts_count || 0;
    const trainerCount = data.trainers_count || 0;

    const sidebarTrainerCount = document.getElementById("sidebar-trainer-count");
    if (sidebarTrainerCount) sidebarTrainerCount.textContent = trainerCount;

    const headerTrainerCount = document.getElementById("header-trainer-count");
    if (headerTrainerCount) headerTrainerCount.textContent = trainerCount;

    const sfCount = document.getElementById("stat-fonts-count");
    if (sfCount) sfCount.textContent = fontCount;
    const stCount = document.getElementById("stat-trainers-count");
    if (stCount) stCount.textContent = trainerCount;

    const cfc = document.getElementById("card-font-count");
    if (cfc) cfc.textContent = fontCount;
    const ctc = document.getElementById("card-trainers-count");
    if (ctc) ctc.textContent = trainerCount;
  } catch (err) {
    console.error("Status fetch error:", err);
  }
}

// ==========================================================
// Silent Font Engine (Background auto-scan from ./fonts/)
// ==========================================================
async function fetchFonts() {
  try {
    const res = await fetch("/api/fonts");
    if (!res.ok) throw new Error("Failed to load fonts");
    const data = await res.json();
    activeFonts = data.fonts || [];

    const sfCount = document.getElementById("stat-fonts-count");
    if (sfCount) sfCount.textContent = activeFonts.length;

    injectDynamicFonts(activeFonts);
  } catch (err) {
    console.error("Fetch fonts error:", err);
  }
}

function injectDynamicFonts(fonts) {
  let styleTag = document.getElementById("dynamic-font-faces");
  if (!styleTag) {
    styleTag = document.createElement("style");
    styleTag.id = "dynamic-font-faces";
    document.head.appendChild(styleTag);
  }

  let css = "";
  fonts.forEach((f) => {
    const format = f.format.toLowerCase() === "otf" ? "opentype" : "truetype";
    css += `
      @font-face {
        font-family: "${f.name}";
        src: url('/api/fonts/${encodeURIComponent(f.filename)}') format('${format}');
      }
    `;
  });
  styleTag.textContent = css;
}

// ==========================================================
// Prepress Certificate Live Preview Engine (Task 2)
// ==========================================================

function openPreviewModal() {
  document.getElementById("preview-modal").classList.remove("hidden");
  refreshCertificatePreview();
}

function closePreviewModal() {
  document.getElementById("preview-modal").classList.add("hidden");
}

function debouncePreviewRefresh() {
  clearTimeout(previewDebounceTimer);
  previewDebounceTimer = setTimeout(() => {
    refreshCertificatePreview();
  }, 400);
}

async function refreshCertificatePreview() {
  const loader = document.getElementById("preview-loading");
  const img = document.getElementById("preview-image");
  const nameInput = document.getElementById("preview-name-input");
  const guideToggle = document.getElementById("preview-guide-toggle");

  if (loader) loader.classList.remove("hidden");

  const traineeName = (nameInput && nameInput.value.trim()) ? nameInput.value.trim() : (currentLang === "ar" ? "اسم المتدرب" : "Trainee Name");
  const showGuide = guideToggle ? guideToggle.checked : true;

  const payload = {
    template_config: {
      name: "CertFlow_Master_Template",
      page_setup: { width_mm: 297.0, height_mm: 210.0, bleed_mm: 3.0 },
      fields: [
        {
          id: "certificate_title",
          default_text: "شهادة إتمام برنامج تدريبي",
          x_mm: 40.0, y_mm: 35.0, width_mm: 217.0, height_mm: 20.0,
          font_family: "Cairo Regular", font_size: 34.0,
          color: "#004B87", horizontal_align: "center", vertical_align: "middle"
        },
        {
          id: "trainee_label",
          default_text: "تُمنح هذه الشهادة تقديراً لاجتياز المتدرب/ـة بنجاح:",
          x_mm: 40.0, y_mm: 65.0, width_mm: 217.0, height_mm: 12.0,
          font_family: "Cairo Regular", font_size: 14.0,
          color: "#64748B", horizontal_align: "center", vertical_align: "middle"
        },
        {
          id: "trainee_name",
          default_text: traineeName,
          x_mm: 40.0, y_mm: 80.0, width_mm: 217.0, height_mm: 24.0,
          font_family: "Cairo Regular", font_size: 32.0,
          color: { c: 0, m: 0, y: 0, k: 100 }, // Pure Print Black
          horizontal_align: "center", vertical_align: "middle",
          max_shrink_percent: 25.0
        },
        {
          id: "course_desc",
          default_text: "في المسار المتقدم للتصميم الطباعي وإدارة بيانات الشهادات فائقة الدقة",
          x_mm: 40.0, y_mm: 110.0, width_mm: 217.0, height_mm: 14.0,
          font_family: "Cairo Regular", font_size: 15.0,
          color: "#1E293B", horizontal_align: "center", vertical_align: "middle"
        },
        {
          id: "training_date",
          default_text: "تاريخ الاعتماد: 2026-10-29",
          x_mm: 35.0, y_mm: 155.0, width_mm: 80.0, height_mm: 12.0,
          font_family: "Cairo Regular", font_size: 13.0,
          color: "#475569", horizontal_align: "right", vertical_align: "middle"
        }
      ],
      signature_frame: {
        id: "trainer_signature",
        x_mm: 195.0, y_mm: 140.0, width_mm: 70.0, height_mm: 32.0,
        baseline_offset_mm: 0.0
      }
    },
    record_data: {
      trainee_name: traineeName,
      training_date: "تاريخ الاعتماد: 2026-10-29"
    },
    show_trim_guide: showGuide,
    dpi: 140
  };

  try {
    const res = await fetch("/api/preview-certificate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error("فشل توليد معاينة الشهادة");

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    if (img) {
      img.src = url;
    }
  } catch (err) {
    console.error("Preview error:", err);
    showToast(err.message, "error");
  } finally {
    if (loader) loader.classList.add("hidden");
    lucide.createIcons();
  }
}


// ==========================================================
// OPERATOR PLATFORM DATA ENGINE (Task 4)
// ==========================================================

// Preloaded realistic print certificate sample records (Clean slate)
const defaultSampleRecords = [];

async function initOperatorPlatform() {
  if (!operatorPlatformInitialized) {
    window.addEventListener("resize", debounceFitOperatorCanvas);
    operatorPlatformInitialized = true;
  }

  operatorSelectedCompany = "";
  operatorActiveTemplate = null;

  operatorRecords = [];
  currentRecordIndex = 0;

  await fetchCompanies();
  await fetchOperatorTemplates();
  populateOperatorTrainers(activeTrainers);
  updateRecordControls();
  updateEmptyStateSteps();
  fitOperatorCanvasToScreen();
  refreshOperatorCanvas();
}

function debounceFitOperatorCanvas() {
  clearTimeout(operatorFitDebounce);
  operatorFitDebounce = setTimeout(() => {
    fitOperatorCanvasToScreen();
  }, 100);
}

// ----------------------------------------------------------
// 1. Company Filter & Template Management
// ----------------------------------------------------------

async function fetchCompanies() {
  try {
    const res = await fetch("/api/companies");
    if (!res.ok) return;
    const data = await res.json();
    const companies = data.companies || [];

    // Update Operator Company Filter Dropdown with mandatory placeholder
    const opFilter = document.getElementById("op-company-filter");
    if (opFilter) {
      opFilter.innerHTML = "";

      const placeholderOpt = document.createElement("option");
      placeholderOpt.value = "";
      placeholderOpt.disabled = true;
      placeholderOpt.selected = !operatorSelectedCompany;
      placeholderOpt.textContent = t("op_select_company_placeholder");
      opFilter.appendChild(placeholderOpt);

      companies.forEach((comp) => {
        const opt = document.createElement("option");
        opt.value = comp;
        let displayComp = comp;
        if (comp === "عام (General)" || comp === "عام" || comp === "General") {
          displayComp = currentLang === "ar" ? "عام" : "General";
        }
        opt.textContent = displayComp;
        opFilter.appendChild(opt);
      });

      if (companies.length > 0) {
        const allOpt = document.createElement("option");
        allOpt.value = "ALL";
        allOpt.textContent = t("op_all_companies");
        opFilter.appendChild(allOpt);
      }

      opFilter.value = operatorSelectedCompany || "";
    }

    // Update Designer Datalist
    const datalist = document.getElementById("company-datalist");
    if (datalist) {
      datalist.innerHTML = "";
      companies.forEach((comp) => {
        const opt = document.createElement("option");
        let displayComp = comp;
        if (comp === "عام (General)" || comp === "عام" || comp === "General") {
          displayComp = currentLang === "ar" ? "عام" : "General";
        }
        opt.value = comp;
        opt.textContent = displayComp;
        datalist.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("fetchCompanies error:", err);
  }
}

async function fetchOperatorTemplates() {
  try {
    const res = await fetch("/api/templates");
    if (!res.ok) return;
    const data = await res.json();
    operatorTemplates = data.templates || [];

    // CRITICAL: Do NOT auto-select the first template on load!
    renderOperatorTemplateSelect();
  } catch (err) {
    console.error("fetchOperatorTemplates error:", err);
  }
}

function renderOperatorTemplateSelect() {
  const selectEl = document.getElementById("op-template-select");
  const countBadge = document.getElementById("op-templates-count-badge");
  const searchInput = document.getElementById("op-template-search-input");
  const query = searchInput ? searchInput.value.trim().toLowerCase() : "";

  if (!selectEl) return;
  selectEl.innerHTML = "";

  // If no company is selected yet, disable selector & search and prompt user
  if (!operatorSelectedCompany) {
    selectEl.disabled = true;
    selectEl.classList.add("opacity-60", "cursor-not-allowed");
    if (searchInput) {
      searchInput.disabled = true;
      searchInput.classList.add("opacity-60", "cursor-not-allowed");
      searchInput.value = "";
    }
    if (countBadge) countBadge.textContent = currentLang === "ar" ? "0 قالب" : "0 WorkBooks";

    const opt = document.createElement("option");
    opt.value = "";
    opt.disabled = true;
    opt.selected = true;
    opt.textContent = t("op_select_company_first");
    selectEl.appendChild(opt);

    operatorActiveTemplate = null;
    updateOperatorTemplateInfo();
    return;
  }

  // When company IS selected, enable selector & search
  selectEl.disabled = false;
  selectEl.classList.remove("opacity-60", "cursor-not-allowed");
  if (searchInput) {
    searchInput.disabled = false;
    searchInput.classList.remove("opacity-60", "cursor-not-allowed");
  }

  const filtered = operatorTemplates.filter((tpl) => {
    if (operatorSelectedCompany !== "ALL") {
      const comp = (tpl.company || "").trim();
      if (comp !== operatorSelectedCompany) return false;
    }
    if (query) {
      const name = (tpl.name || "").toLowerCase();
      const comp = (tpl.company || "").toLowerCase();
      if (!name.includes(query) && !comp.includes(query)) return false;
    }
    return true;
  });

  if (countBadge) {
    countBadge.textContent = currentLang === "ar" ? `${filtered.length} قالب` : `${filtered.length} WorkBook(s)`;
  }

  if (filtered.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.disabled = true;
    opt.selected = true;
    opt.textContent = t("op_no_matching_templates");
    selectEl.appendChild(opt);
    operatorActiveTemplate = null;
    updateOperatorTemplateInfo();
    return;
  }

  // Prepend unselected placeholder option
  const placeholderOpt = document.createElement("option");
  placeholderOpt.value = "";
  placeholderOpt.disabled = true;
  placeholderOpt.selected = !operatorActiveTemplate;
  placeholderOpt.textContent = t("op_select_template_placeholder");
  selectEl.appendChild(placeholderOpt);

  filtered.forEach((tpl) => {
    const opt = document.createElement("option");
    opt.value = tpl.id;
    const compLabel = (operatorSelectedCompany === "ALL" && tpl.company) ? ` [${tpl.company}]` : "";
    opt.textContent = `${tpl.name || tpl.id}${compLabel}`;
    if (operatorActiveTemplate && tpl.id === operatorActiveTemplate.id) {
      opt.selected = true;
    }
    selectEl.appendChild(opt);
  });

  // Do NOT auto-select the first template! Wait for explicit user pick.
  if (operatorActiveTemplate && filtered.some((t) => t.id === operatorActiveTemplate.id)) {
    selectEl.value = operatorActiveTemplate.id;
  } else {
    operatorActiveTemplate = null;
    selectEl.value = "";
  }

  updateOperatorTemplateInfo();
}

function handleCompanyFilterChange(val) {
  operatorSelectedCompany = val || "";
  operatorActiveTemplate = null; // Always reset template when company changes
  renderOperatorTemplateSelect();
  updateEmptyStateSteps();
  fitOperatorCanvasToScreen();
  refreshOperatorCanvas();
}

function filterTemplatesBySearch(query) {
  renderOperatorTemplateSelect();
}

function handleOperatorTemplateSelect(tplId) {
  if (!tplId) {
    operatorActiveTemplate = null;
  } else {
    const tpl = operatorTemplates.find((t) => t.id === tplId);
    operatorActiveTemplate = tpl || null;
  }
  updateOperatorTemplateInfo();
  updateEmptyStateSteps();
  fitOperatorCanvasToScreen();
  refreshOperatorCanvas();
}

function updateOperatorTemplateInfo() {
  const nameEl = document.getElementById("op-bottom-tpl-name");
  const dimsEl = document.getElementById("op-bottom-tpl-dims");
  const topTpl = document.getElementById("op-top-tpl-name");

  if (!operatorActiveTemplate) {
    if (nameEl) nameEl.textContent = `${t("label_template_prefix")} —`;
    if (dimsEl) dimsEl.textContent = "—";
    if (topTpl) topTpl.textContent = "—";
    return;
  }

  const ps = operatorActiveTemplate.page_setup || { width_mm: 297, height_mm: 210 };
  if (nameEl) nameEl.textContent = `${t("label_template_prefix")} ${operatorActiveTemplate.name || "—"}`;
  if (dimsEl) dimsEl.textContent = `${parseFloat(ps.width_mm).toFixed(1)} × ${parseFloat(ps.height_mm).toFixed(1)} mm (${currentLang === "ar" ? "٣٠٠ نقطة/بوصة" : "300 DPI"})`;
  if (topTpl) topTpl.textContent = operatorActiveTemplate.name || "—";
}

function updateEmptyStateSteps() {
  const step1Box = document.getElementById("op-step-company-box");
  const step1Icon = document.getElementById("op-step-company-icon");
  const step1Status = document.getElementById("op-step-company-status");

  const step2Box = document.getElementById("op-step-template-box");
  const step2Icon = document.getElementById("op-step-template-icon");
  const step2Status = document.getElementById("op-step-template-status");

  if (!step1Box) return;

  if (operatorSelectedCompany) {
    // Step 1 Completed
    step1Box.className = "p-3 rounded-2xl border border-emerald-200 bg-emerald-50/80 transition-all flex items-start gap-2.5";
    if (step1Icon) {
      step1Icon.className = "w-6 h-6 rounded-lg bg-emerald-600 text-white flex items-center justify-center text-xs font-black shrink-0";
      step1Icon.innerHTML = "✓";
    }
    if (step1Status) {
      step1Status.className = "text-[10px] text-emerald-700 font-bold truncate";
      step1Status.textContent = operatorSelectedCompany === "ALL"
        ? (currentLang === "en" ? "Selected: All Affiliates" : "تم اختيار: جميع الشركات")
        : (currentLang === "en" ? `Selected: ${operatorSelectedCompany}` : `تم اختيار: ${operatorSelectedCompany}`);
    }

    // Step 2 Active
    if (step2Box) {
      step2Box.className = "p-3 rounded-2xl border border-amber-300 bg-amber-50/90 transition-all flex items-start gap-2.5 ring-2 ring-amber-300/40 animate-pulse";
    }
    if (step2Icon) {
      step2Icon.className = "w-6 h-6 rounded-lg bg-amber-500 text-white flex items-center justify-center text-xs font-black shrink-0";
      step2Icon.innerHTML = "2";
    }
    if (step2Status) {
      step2Status.className = "text-[10px] text-amber-800 font-bold truncate";
      step2Status.textContent = currentLang === "en" ? "Select Program WorkBook from list" : "اختر قالب الشهادة من القائمة";
    }
  } else {
    // Step 1 Active
    step1Box.className = "p-3 rounded-2xl border border-amber-300 bg-amber-50/90 transition-all flex items-start gap-2.5 ring-2 ring-amber-300/40 animate-pulse";
    if (step1Icon) {
      step1Icon.className = "w-6 h-6 rounded-lg bg-amber-500 text-white flex items-center justify-center text-xs font-black shrink-0";
      step1Icon.innerHTML = "1";
    }
    if (step1Status) {
      step1Status.className = "text-[10px] text-amber-800 font-bold truncate";
      step1Status.textContent = currentLang === "en" ? "Start by selecting Affiliate / Client from list" : "ابدأ باختيار الشركة من القائمة";
    }

    // Step 2 Pending
    if (step2Box) {
      step2Box.className = "p-3 rounded-2xl border border-slate-200 bg-slate-50 transition-all flex items-start gap-2.5 opacity-60";
    }
    if (step2Icon) {
      step2Icon.className = "w-6 h-6 rounded-lg bg-slate-300 text-slate-600 flex items-center justify-center text-xs font-black shrink-0";
      step2Icon.innerHTML = "2";
    }
    if (step2Status) {
      step2Status.className = "text-[10px] text-slate-400 font-medium truncate";
      step2Status.textContent = currentLang === "en" ? "Waiting for Affiliate / Client selection first" : "بانتظار اختيار الشركة أولاً";
    }
  }

  if (window.lucide && typeof lucide.createIcons === "function") {
    lucide.createIcons();
  }
}

// ----------------------------------------------------------
// 2. Dual Data Source Tabs (Google Sheet vs Excel)
// ----------------------------------------------------------

function switchDataTab(tab) {
  activeDataTab = tab;
  const sheetBtn = document.getElementById("op-tab-sheet-btn");
  const excelBtn = document.getElementById("op-tab-excel-btn");
  const sheetContent = document.getElementById("op-tab-sheet-content");
  const excelContent = document.getElementById("op-tab-excel-content");

  if (tab === "sheet") {
    if (sheetBtn) {
      sheetBtn.className = "flex-1 py-1.5 text-xs font-bold rounded-lg text-white bg-brand-primary shadow-xs transition flex items-center justify-center gap-1.5";
    }
    if (excelBtn) {
      excelBtn.className = "flex-1 py-1.5 text-xs font-semibold rounded-lg text-slate-600 hover:text-slate-800 transition flex items-center justify-center gap-1.5";
    }
    if (sheetContent) sheetContent.classList.remove("hidden");
    if (excelContent) excelContent.classList.add("hidden");

    const sheetTrSelect = document.getElementById("op-sheet-trainer-select");
    if (sheetTrSelect && sheetTrSelect.value) {
      operatorActiveTrainerId = sheetTrSelect.value;
    }
  } else {
    if (excelBtn) {
      excelBtn.className = "flex-1 py-1.5 text-xs font-bold rounded-lg text-white bg-brand-primary shadow-xs transition flex items-center justify-center gap-1.5";
    }
    if (sheetBtn) {
      sheetBtn.className = "flex-1 py-1.5 text-xs font-semibold rounded-lg text-slate-600 hover:text-slate-800 transition flex items-center justify-center gap-1.5";
    }
    if (excelContent) excelContent.classList.remove("hidden");
    if (sheetContent) sheetContent.classList.add("hidden");

    const excelTrSelect = document.getElementById("op-excel-trainer-select");
    if (excelTrSelect && excelTrSelect.value) {
      operatorActiveTrainerId = excelTrSelect.value;
    }
  }
  updateTrainerBottomInfo();
  refreshOperatorCanvas();
  lucide.createIcons();
}

function populateOperatorTrainers(trainers) {
  const sheetSelect = document.getElementById("op-sheet-trainer-select");
  const excelSelect = document.getElementById("op-excel-trainer-select");

  [sheetSelect, excelSelect].forEach((sel) => {
    if (!sel) return;
    const prevVal = sel.value;
    sel.innerHTML = "";
    if (trainers.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = t("no_trainers_registered");
      sel.appendChild(opt);
    } else {
      trainers.forEach((tr) => {
        const opt = document.createElement("option");
        opt.value = tr.id;
        const vectorLabel = tr.is_vector ? (currentLang === "ar" ? " (ملف متجهي)" : " (Vector PDF)") : "";
        opt.textContent = `${tr.name}${vectorLabel}`;
        sel.appendChild(opt);
      });
      if (prevVal && trainers.some((t) => t.id === prevVal)) {
        sel.value = prevVal;
      } else {
        sel.value = trainers[0].id;
      }
    }
  });

  if (trainers.length > 0 && !operatorActiveTrainerId) {
    operatorActiveTrainerId = trainers[0].id;
  }

  if (sheetSelect && sheetSelect.value) {
    handleSheetTrainerSelect(sheetSelect.value, false);
  }
  updateTrainerBottomInfo();
}

function deduplicateHeader(colName) {
  if (!colName) return "";
  let s = String(colName).trim();
  const words = s.split(/\s+/);
  if (words.length >= 2 && words.length % 2 === 0) {
    const halfW = words.length / 2;
    const firstHalf = words.slice(0, halfW).map((w) => w.toLowerCase()).join(" ");
    const secondHalf = words.slice(halfW).map((w) => w.toLowerCase()).join(" ");
    if (firstHalf === secondHalf) {
      return words.slice(0, halfW).join(" ");
    }
  }
  const n = s.length;
  if (n >= 4 && n % 2 === 0) {
    const half = n / 2;
    if (s.slice(0, half).toLowerCase() === s.slice(half).toLowerCase()) {
      return s.slice(0, half);
    }
  }
  return s;
}

function handleSheetTrainerSelect(trainerId, autoFetch = true) {
  operatorActiveTrainerId = trainerId;
  const trainer = activeTrainers.find((t) => t.id === trainerId);
  const hintEl = document.getElementById("op-sheet-url-hint");
  const nameColEl = document.getElementById("op-bind-name-col");
  const dateColEl = document.getElementById("op-bind-date-col");

  if (trainer) {
    if (hintEl) {
      hintEl.textContent = trainer.sheet_url ? trainer.sheet_url : t("op_no_sheet_linked");
      hintEl.title = trainer.sheet_url || "";
    }
    if (nameColEl) {
      let rawName = deduplicateHeader(trainer.name_col || "الاسم");
      if ((rawName === "الاسم" || rawName === "الاسم الاسم") && currentLang === "en") {
        rawName = "Name";
      }
      nameColEl.textContent = rawName;
    }
    if (dateColEl) dateColEl.textContent = deduplicateHeader(trainer.time_col || "Timestamp");

    if (autoFetch && trainer.sheet_url) {
      fetchCurrentTrainerSheet();
    }
  }
  updateTrainerBottomInfo();
  refreshOperatorCanvas();
}

function handleExcelTrainerSelect(trainerId) {
  operatorActiveTrainerId = trainerId;
  updateTrainerBottomInfo();
  refreshOperatorCanvas();
}

function updateTrainerBottomInfo() {
  const bottomTr = document.getElementById("op-bottom-trainer-name");
  const trainer = activeTrainers.find((t) => t.id === operatorActiveTrainerId);
  if (bottomTr) {
    bottomTr.textContent = `${t("label_trainer_prefix")} ${trainer ? trainer.name : t("status_unspecified")}`;
  }
}

async function fetchCurrentTrainerSheet() {
  const trainer = activeTrainers.find((t) => t.id === operatorActiveTrainerId);
  if (!trainer || !trainer.sheet_url) {
    showToast(t("toast_select_trainer_sheet"), "warning");
    return;
  }

  const fetchBtn = document.getElementById("op-btn-fetch-sheet");
  if (fetchBtn) {
    fetchBtn.disabled = true;
    fetchBtn.classList.add("opacity-60");
  }

  showToast(t("toast_fetching_sheet"), "info");

  try {
    const res = await fetch("/api/data/google-sheet", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sheet_url: trainer.sheet_url,
        name_col: trainer.name_col || "الاسم",
        time_col: trainer.time_col || "Timestamp",
        trainer_name: trainer.name || "",
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || (currentLang === "ar" ? "فشل الاتصال بشيت قوقل" : "Failed to connect to Google Sheet"));
    }

    operatorAllSheetRecords = data.records || [];

    const nameColEl = document.getElementById("op-bind-name-col");
    const dateColEl = document.getElementById("op-bind-date-col");
    if (nameColEl) {
      let rawName = deduplicateHeader(data.best_name_col || data.mapping_used?.name_col || trainer.name_col || "الاسم");
      if ((rawName === "الاسم" || rawName === "الاسم الاسم") && currentLang === "en") {
        rawName = "Name";
      }
      nameColEl.textContent = rawName;
    }
    if (dateColEl) {
      dateColEl.textContent = deduplicateHeader(data.best_date_col || data.mapping_used?.date_col || trainer.time_col || "Timestamp");
    }

    lastFetchedUniqueDates = data.unique_dates || [];
    renderSheetDateOptions();

    applySheetFilters();
    showToast(currentLang === "ar" ? `تم جلب ${operatorAllSheetRecords.length} سجل بنجاح من قوقل شيت` : `Successfully fetched ${operatorAllSheetRecords.length} record(s) from Google Sheet`, "success");
  } catch (err) {
    console.error("fetchCurrentTrainerSheet error:", err);
    showToast(err.message, "error");
  } finally {
    if (fetchBtn) {
      fetchBtn.disabled = false;
      fetchBtn.classList.remove("opacity-60");
    }
  }
}

function renderSheetDateOptions() {
  const dateBox = document.getElementById("op-sheet-date-filter-box");
  const dateSelect = document.getElementById("op-sheet-date-select");
  const datesCount = document.getElementById("op-sheet-dates-count");

  if (!lastFetchedUniqueDates || lastFetchedUniqueDates.length === 0) {
    if (dateBox && operatorAllSheetRecords.length === 0) {
      dateBox.classList.add("hidden");
    }
    return;
  }

  if (dateBox) dateBox.classList.remove("hidden");
  if (datesCount) {
    datesCount.textContent = currentLang === "ar"
      ? `${lastFetchedUniqueDates.length} تاريخ تدريبي`
      : `${lastFetchedUniqueDates.length} Training Date(s)`;
  }

  if (dateSelect) {
    const prevValue = dateSelect.value;
    dateSelect.innerHTML = "";
    const optAll = document.createElement("option");
    optAll.value = "ALL";
    const totalAll = operatorAllSheetRecords.length;
    const unissuedAll = operatorAllSheetRecords.filter((r) => !r.is_issued).length;
    optAll.textContent = currentLang === "ar"
      ? `الكل (جميع التواريخ) - ${unissuedAll} متبقي / ${totalAll} إجمالي`
      : `All Dates - ${unissuedAll} remaining / ${totalAll} total`;
    dateSelect.appendChild(optAll);

    let firstUnissuedDate = null;
    lastFetchedUniqueDates.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d.date_str;
      const isCompleted = d.all_issued || d.unissued_count === 0;
      if (!firstUnissuedDate && !isCompleted) {
        firstUnissuedDate = d.date_str;
      }
      const unissued = d.unissued_count !== undefined ? d.unissued_count : (d.count || d.total_count);
      const total = d.total_count !== undefined ? d.total_count : (d.count || 0);
      if (isCompleted) {
        opt.textContent = currentLang === "ar"
          ? `${d.date_str} (${total} متدرب) - ✓ مكتمل`
          : `${d.date_str} (${total} trainees) - ✓ Completed`;
      } else {
        opt.textContent = currentLang === "ar"
          ? `${d.date_str} (${unissued} متبقي / ${total} إجمالي)`
          : `${d.date_str} (${unissued} remaining / ${total} total)`;
      }
      dateSelect.appendChild(opt);
    });

    if (prevValue && Array.from(dateSelect.options).some(o => o.value === prevValue)) {
      dateSelect.value = prevValue;
    } else if (firstUnissuedDate) {
      dateSelect.value = firstUnissuedDate;
    } else if (lastFetchedUniqueDates.length > 0) {
      dateSelect.value = lastFetchedUniqueDates[0].date_str;
    } else {
      dateSelect.value = "ALL";
    }
  }
}

function getGlobalAppsScriptUrl() {
  return localStorage.getItem("certflow_global_apps_script_url") || "";
}

function setGlobalAppsScriptUrl(url) {
  if (url && (url.includes("script.google.com") || url.includes("script.googleusercontent.com"))) {
    localStorage.setItem("certflow_global_apps_script_url", url.trim());
  }
}

function applySheetFilters() {
  const hideIssuedCheckbox = document.getElementById("op-hide-issued-checkbox");
  const hideIssued = hideIssuedCheckbox ? hideIssuedCheckbox.checked : false;
  const dateSelect = document.getElementById("op-sheet-date-select");
  const dateVal = dateSelect ? dateSelect.value : "ALL";

  let filtered = [...operatorAllSheetRecords];

  if (dateVal && dateVal !== "ALL") {
    filtered = filtered.filter((r) => (r.date_only === dateVal || r.Training_Date === dateVal || r.training_date === dateVal));
  }

  if (hideIssued) {
    filtered = filtered.filter((r) => !r.is_issued);
  }

  operatorRecords = filtered;
  currentRecordIndex = 0;
  updateRecordControls();
  refreshOperatorCanvas();
}

function handleSheetDateFilterChange(dateVal) {
  applySheetFilters();
}

async function handleExcelFileUpload(files) {
  if (!files || files.length === 0) return;
  const file = files[0];

  const label = document.getElementById("op-excel-filename-label");
  if (label) label.textContent = file.name;

  showToast(t("toast_inspecting_excel"), "info");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/data/parse-file", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "فشل قراءة ملف الإكسل");
    }

    currentParsedExcel = data;

    const sheetBox = document.getElementById("op-excel-sheet-selector-box");
    const sheetSelect = document.getElementById("op-excel-sheet-select");
    if (data.is_excel && data.available_sheets && data.available_sheets.length > 1) {
      if (sheetBox) sheetBox.classList.remove("hidden");
      if (sheetSelect) {
        sheetSelect.innerHTML = "";
        data.available_sheets.forEach((sh) => {
          const opt = document.createElement("option");
          opt.value = sh;
          opt.textContent = sh;
          sheetSelect.appendChild(opt);
        });
        sheetSelect.value = data.active_sheet;
      }
    } else {
      if (sheetBox) sheetBox.classList.add("hidden");
    }

    populateColumnMappings(data.detected_columns, data.best_name_col, data.best_date_col);

    operatorRecords = data.records || [];
    currentRecordIndex = 0;
    updateRecordControls();
    refreshOperatorCanvas();
    showToast(`تم تجهيز ${operatorRecords.length} سجل من ملف ${file.name}`, "success");
  } catch (err) {
    console.error("handleExcelFileUpload error:", err);
    showToast(err.message, "error");
  }
}

function populateColumnMappings(columns, bestName, bestDate) {
  const nameSel = document.getElementById("op-map-name-select");
  const dateSel = document.getElementById("op-map-date-select");

  [nameSel, dateSel].forEach((sel) => {
    if (!sel) return;
    sel.innerHTML = "";
    (columns || []).forEach((col) => {
      const opt = document.createElement("option");
      opt.value = col;
      opt.textContent = deduplicateHeader(col);
      sel.appendChild(opt);
    });
  });

  if (nameSel && bestName && columns.includes(bestName)) {
    nameSel.value = bestName;
  }
  if (dateSel && bestDate && columns.includes(bestDate)) {
    dateSel.value = bestDate;
  }
}

async function handleExcelSheetChange(sheetName) {
  const fileInput = document.getElementById("op-excel-file-input");
  if (!fileInput.files || fileInput.files.length === 0) return;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const res = await fetch(`/api/data/parse-file?sheet_name=${encodeURIComponent(sheetName)}`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "فشل قراءة ورقة العمل");

    currentParsedExcel = data;
    populateColumnMappings(data.detected_columns, data.best_name_col, data.best_date_col);
    operatorRecords = data.records || [];
    currentRecordIndex = 0;
    updateRecordControls();
    refreshOperatorCanvas();
    showToast(`تم التبديل لورقة ${sheetName} بنجاح (${operatorRecords.length} متدرب)`, "info");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function normalizeTrainerName(name) {
  if (!name) return "";
  let s = String(name).trim().toLowerCase();
  s = s.replace(/[-_.,/]+/g, " ");
  s = s.replace(/\s+/g, " ").trim();
  s = s.replace(/[إأآٱ]/g, "ا");
  s = s.replace(/ة/g, "ه");
  s = s.replace(/ى/g, "ي");
  s = s.replace(/\b(al|el)\b/g, "el");
  s = s.replace(/\b(saif|seif)\b/g, "seif");
  return s;
}

function trainerNamesMatch(n1, n2) {
  const norm1 = normalizeTrainerName(n1);
  const norm2 = normalizeTrainerName(n2);
  if (!norm1 || !norm2) return false;
  if (norm1 === norm2) return true;
  const w1 = norm1.split(" ");
  const w2 = norm2.split(" ");
  const s1 = new Set(w1);
  const s2 = new Set(w2);
  const isSubset1 = w1.every((w) => s2.has(w));
  const isSubset2 = w2.every((w) => s1.has(w));
  return isSubset1 || isSubset2;
}

function isDateRangeOrCustomText(str) {
  if (!str) return false;
  const s = String(str).trim();
  // Exclude standard date patterns
  if (/^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}(?:[ T].*)?$/.test(s)) return false;
  if (/^\d{1,2}[-/.]\d{1,2}[-/.]\d{4}(?:[ T].*)?$/.test(s)) return false;

  // Multi-day indicators like "&", "and", "to", "until", "through", "إلى", "وحتى", en-dash, em-dash
  if (/(&|\band\b|\bto\b|\buntil\b|\bthrough\b|إلى|وحتى|–|—)/i.test(s)) return true;

  // Non-consecutive days with comma e.g. "1, 3 & 5", "10, 12 Nov"
  if (/\d{1,2}\s*[,،]\s*\d{1,2}/.test(s)) return true;

  // Arabic non-consecutive days e.g. "1 و 3 نوفمبر"
  if (/\d{1,2}\s+و\s*\d{1,2}/.test(s)) return true;

  // Hyphen with alphabetic month name e.g. "1-2 November 2026", "31 Oct - 1 Nov 2026", "1-2 نوفمبر 2026"
  if (/[-–—]/.test(s) && /[A-Za-z\u0600-\u06FF]{3,}/.test(s)) return true;

  // Day range pattern like "1-2", "1 - 2"
  if (/^\d{1,2}\s*[-–—]\s*\d{1,2}\b/.test(s)) return true;

  return false;
}

function stripTimestampTime(str) {
  if (!str) return "";
  const s = String(str).trim();
  if (isDateRangeOrCustomText(s)) {
    return s;
  }
  const m = s.match(/^(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})[ T](\d{1,2}:\d{2}(?::\d{2})?.*)$/);
  if (m) {
    return m[1].trim();
  }
  return s;
}

function applyColumnMapping() {
  if (!currentParsedExcel || !currentParsedExcel.raw_rows) return;
  const nameCol = document.getElementById("op-map-name-select").value;
  const dateCol = document.getElementById("op-map-date-select").value;

  operatorRecords = currentParsedExcel.raw_rows.map((row, idx) => {
    const rawName = String(row[nameCol] || "").trim();
    let rawDate = (dateCol && row[dateCol] !== undefined) ? String(row[dateCol]).trim() : "";

    let parsedDate = rawDate;
    if (isDateRangeOrCustomText(parsedDate)) {
      // Keep exact date range string as-is (e.g. "1-2 November 2026")
      parsedDate = parsedDate.trim();
    } else {
      parsedDate = stripTimestampTime(parsedDate);

      // Standard date pattern normalization (YYYY/MM/DD or DD/MM/YYYY -> YYYY-MM-DD)
      if (/^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$/.test(parsedDate)) {
        const parts = parsedDate.split(/[-/.]/);
        parsedDate = `${parts[0]}-${parts[1].padStart(2, "0")}-${parts[2].padStart(2, "0")}`;
      } else if (/^\d{1,2}[-/.]\d{1,2}[-/.]\d{4}$/.test(parsedDate)) {
        const parts = parsedDate.split(/[-/.]/);
        parsedDate = `${parts[2]}-${parts[1].padStart(2, "0")}-${parts[0].padStart(2, "0")}`;
      }
    }

    // Fallback to matched record's parsed date from backend if empty
    if (!parsedDate && currentParsedExcel.records && currentParsedExcel.records[idx]) {
      parsedDate = currentParsedExcel.records[idx].iso_date || currentParsedExcel.records[idx].Training_Date || currentParsedExcel.records[idx].training_date || "";
    }

    const customText = String(row["Custom_Text"] || row["custom_text"] || "").trim();

    return {
      index: idx + 1,
      Trainee_Name: rawName,
      trainee_name: rawName,
      Training_Date: parsedDate,
      training_date: parsedDate,
      Custom_Text: customText,
      custom_text: customText,
      iso_date: parsedDate,
      date_only: parsedDate,
      raw_date: rawDate,
      raw_row: row,
    };
  }).filter((r) => r.Trainee_Name);

  currentRecordIndex = 0;
  updateRecordControls();
  refreshOperatorCanvas();
}

function handleFixedDateChange(val) {
  operatorFixedDate = String(val || "").trim();
  const sheetInput = document.getElementById("op-sheet-fixed-date");
  const excelInput = document.getElementById("op-excel-fixed-date");
  if (sheetInput && sheetInput.value !== operatorFixedDate) sheetInput.value = operatorFixedDate;
  if (excelInput && excelInput.value !== operatorFixedDate) excelInput.value = operatorFixedDate;
  refreshOperatorCanvas();
}

// ----------------------------------------------------------
// 3. Hygiene & Date Formatting
// ----------------------------------------------------------

function handleDateFormatChange(format) {
  operatorDateFormat = format;
  refreshOperatorCanvas();
}

const AR_MONTH_NAMES = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];
const EN_MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const AR_INDIC_DIGITS = { "0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤", "5": "٥", "6": "٦", "7": "٧", "8": "٨", "9": "٩" };

function toIndicDigits(val) {
  return String(val).replace(/\d/g, (d) => AR_INDIC_DIGITS[d] || d);
}

function containsArabic(str) {
  return /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/.test(str || "");
}

function formatDisplayDate(dateStr, format) {
  if (!dateStr) return "";
  if (format === "As-Is") return dateStr;

  // CRITICAL: Check if string is a custom date range (e.g., "1-2 November 2026")
  // Do NOT pass to new Date(str) because JS misinterprets "1-2" as Jan 2, 2001!
  if (isDateRangeOrCustomText(dateStr)) {
    return dateStr;
  }

  const clean = stripTimestampTime(String(dateStr));
  let y, m, d;
  if (/^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$/.test(clean)) {
    const parts = clean.split(/[-/.]/);
    y = parts[0];
    m = parts[1].padStart(2, "0");
    d = parts[2].padStart(2, "0");
  } else if (/^\d{1,2}[-/.]\d{1,2}[-/.]\d{4}$/.test(clean)) {
    const parts = clean.split(/[-/.]/);
    d = parts[0].padStart(2, "0");
    m = parts[1].padStart(2, "0");
    y = parts[2];
  } else {
    const dt = new Date(dateStr);
    if (!isNaN(dt.getTime())) {
      y = String(dt.getFullYear());
      m = String(dt.getMonth() + 1).padStart(2, "0");
      d = String(dt.getDate()).padStart(2, "0");
    } else {
      return dateStr;
    }
  }

  const mInt = parseInt(m, 10);
  const dInt = parseInt(d, 10);

  if (format === "MONTH_DAY_YEAR_AUTO" || !format) {
    const curRecord = operatorRecords[currentRecordIndex];
    const curName = curRecord ? (curRecord.Trainee_Name || curRecord.trainee_name || "") : "";
    const isAr = containsArabic(curName) || containsArabic(operatorActiveTemplate?.name);
    if (isAr) {
      const monthAr = AR_MONTH_NAMES[Math.max(0, Math.min(11, mInt - 1))];
      return `${monthAr} ${toIndicDigits(dInt)}، ${toIndicDigits(y)}`;
    } else {
      const monthEn = EN_MONTH_NAMES[Math.max(0, Math.min(11, mInt - 1))];
      return `${monthEn} ${dInt}, ${y}`;
    }
  }

  if (format === "MONTH_DAY_YEAR_AR") {
    const monthAr = AR_MONTH_NAMES[Math.max(0, Math.min(11, mInt - 1))];
    return `${monthAr} ${toIndicDigits(dInt)}، ${toIndicDigits(y)}`;
  }

  if (format === "MONTH_DAY_YEAR_EN") {
    const monthEn = EN_MONTH_NAMES[Math.max(0, Math.min(11, mInt - 1))];
    return `${monthEn} ${dInt}, ${y}`;
  }

  if (format === "DD-MM-YYYY") return `${d}-${m}-${y}`;
  if (format === "YYYY-MM-DD") return `${y}-${m}-${d}`;
  if (format === "DD/MM/YYYY") return `${d}/${m}/${y}`;
  if (format === "YYYY/MM/DD") return `${y}/${m}/${d}`;
  return dateStr;
}

// ----------------------------------------------------------
// 4. Record Navigation
// ----------------------------------------------------------

function prevRecord() {
  if (operatorRecords.length === 0) return;
  currentRecordIndex = (currentRecordIndex - 1 + operatorRecords.length) % operatorRecords.length;
  updateRecordControls();
  refreshOperatorCanvas();
}

function nextRecord() {
  if (operatorRecords.length === 0) return;
  currentRecordIndex = (currentRecordIndex + 1) % operatorRecords.length;
  updateRecordControls();
  refreshOperatorCanvas();
}

function jumpToRecord(idx) {
  const i = parseInt(idx, 10);
  if (isNaN(i) || i < 0 || i >= operatorRecords.length) return;
  currentRecordIndex = i;
  updateRecordControls();
  refreshOperatorCanvas();
}

function updateRecordControls() {
  const counterEl = document.getElementById("op-record-counter");
  const jumpSel = document.getElementById("op-trainee-jump-select");
  const nameBadge = document.getElementById("op-active-trainee-name");
  const readinessBadge = document.getElementById("op-readiness-badge");
  const topTpl = document.getElementById("op-top-tpl-name");
  const topTrainer = document.getElementById("op-top-trainer-name");
  const topDate = document.getElementById("op-top-date");
  const bottomTpl = document.getElementById("op-bottom-tpl-name");
  const bottomTrainer = document.getElementById("op-bottom-trainer-name");
  const bottomDims = document.getElementById("op-bottom-tpl-dims");
  const btnPrev = document.getElementById("op-btn-prev-record");
  const btnNext = document.getElementById("op-btn-next-record");
  const btnWidest = document.getElementById("op-btn-widest-name");

  const total = operatorRecords.length;

  if (btnPrev) btnPrev.disabled = total <= 1;
  if (btnNext) btnNext.disabled = total <= 1;
  if (btnWidest) btnWidest.disabled = total === 0;

  if (counterEl) {
    counterEl.textContent = total > 0 ? (currentLang === "en" ? `Record ${currentRecordIndex + 1} of ${total}` : `سجل ${currentRecordIndex + 1} من ${total}`) : (currentLang === "en" ? `Record 0 of 0` : `سجل 0 من 0`);
  }

  if (readinessBadge) {
    readinessBadge.textContent = currentLang === "en" ? `${total} Trainee(s) Ready` : `${total} متدرب جاهز للتوليد`;
  }

  if (jumpSel) {
    jumpSel.innerHTML = total === 0 ? `<option value="">${t("op_no_records")}</option>` : "";
    operatorRecords.forEach((r, idx) => {
      const opt = document.createElement("option");
      opt.value = idx;
      const defaultTrainee = currentLang === "en" ? `Trainee ${idx + 1}` : `متدرب ${idx + 1}`;
      const name = r.Trainee_Name || r.trainee_name || defaultTrainee;
      opt.textContent = `${idx + 1}. ${name}`;
      jumpSel.appendChild(opt);
    });
    jumpSel.value = total > 0 ? currentRecordIndex : "";
    jumpSel.disabled = total === 0;
  }

  const activeRecord = total > 0 ? operatorRecords[currentRecordIndex] : null;
  if (nameBadge) {
    nameBadge.textContent = activeRecord ? (activeRecord.Trainee_Name || activeRecord.trainee_name || "") : (currentLang === "en" ? "Trainee Name" : "اسم المتدرب");
  }

  if (topTpl) {
    topTpl.textContent = operatorActiveTemplate ? (operatorActiveTemplate.name || "—") : "—";
  }
  if (bottomTpl) {
    bottomTpl.textContent = `${t("label_template_prefix")} ${operatorActiveTemplate ? (operatorActiveTemplate.name || "—") : "—"}`;
  }

  if (bottomDims) {
    if (operatorActiveTemplate && operatorActiveTemplate.page_setup) {
      const ps = operatorActiveTemplate.page_setup;
      bottomDims.textContent = `${ps.width_mm} × ${ps.height_mm} mm (${currentLang === "ar" ? "٣٠٠ نقطة/بوصة" : "300 DPI"})`;
    } else {
      bottomDims.textContent = "—";
    }
  }

  const tr = activeTrainers.find((t) => t.id === operatorActiveTrainerId);
  const trainerName = tr ? tr.name : t("status_unspecified");
  if (topTrainer) topTrainer.textContent = trainerName;
  if (bottomTrainer) bottomTrainer.textContent = `${t("label_trainer_prefix")} ${trainerName}`;

  if (topDate) {
    const todayStr = new Date().toISOString().split("T")[0];
    const rawDate = operatorFixedDate || (activeRecord ? (activeRecord.Training_Date || activeRecord.training_date) : "") || todayStr;
    topDate.textContent = formatDisplayDate(rawDate, operatorDateFormat);
  }
}

function jumpToWidestName() {
  if (!operatorRecords || operatorRecords.length === 0) {
    showToast(t("toast_no_records_loaded"), "warning");
    return;
  }

  let widestIdx = 0;
  let maxLen = 0;

  operatorRecords.forEach((rec, idx) => {
    const name = (rec.Trainee_Name || rec.trainee_name || "").trim();
    if (name.length > maxLen) {
      maxLen = name.length;
      widestIdx = idx;
    }
  });

  currentRecordIndex = widestIdx;
  updateRecordControls();
  refreshOperatorCanvas(true);

  const longestName = (operatorRecords[widestIdx].Trainee_Name || operatorRecords[widestIdx].trainee_name || "");
  showToast(currentLang === "ar" ? `تم الانتقال لأطول اسم: "${longestName}" (${maxLen} حرف)` : `Jumped to longest name: "${longestName}" (${maxLen} chars)`, "info");
}

function resetOperatorData() {
  operatorRecords = [];
  currentRecordIndex = 0;
  operatorFixedDate = "";
  operatorSelectedCompany = "";
  operatorActiveTemplate = null;

  const compFilter = document.getElementById("op-company-filter");
  if (compFilter) compFilter.value = "";
  renderOperatorTemplateSelect();

  const fixedDateInput = document.getElementById("op-excel-fixed-date");
  if (fixedDateInput) fixedDateInput.value = "";
  const sheetFixedDateInput = document.getElementById("op-sheet-fixed-date");
  if (sheetFixedDateInput) sheetFixedDateInput.value = "";
  const dateBox = document.getElementById("op-sheet-date-filter-box");
  if (dateBox) dateBox.classList.add("hidden");
  const exLabel = document.getElementById("op-excel-filename-label");
  if (exLabel) exLabel.textContent = t("op_drop_excel");

  updateEmptyStateSteps();
  updateRecordControls();
  fitOperatorCanvasToScreen();
  refreshOperatorCanvas();
  showToast(t("toast_reset_complete"), "info");
}

// ----------------------------------------------------------
// Batch Export Modal & Actions
// ----------------------------------------------------------

function openBatchExportModal() {
  if (!operatorRecords || operatorRecords.length === 0) {
    showToast(t("toast_no_records_export"), "warning");
    return;
  }
  const modal = document.getElementById("batch-export-modal");
  const summaryEl = document.getElementById("batch-export-records-summary");
  const tplNameEl = document.getElementById("batch-export-tpl-name");
  const webhookInput = document.getElementById("batch-export-webhook");
  const scriptBadge = document.getElementById("batch-export-script-badge");

  if (summaryEl) {
    summaryEl.textContent = currentLang === "ar"
      ? `${operatorRecords.length} سجل متدرب جاهز للتصدير`
      : `${operatorRecords.length} Trainee Record(s) Ready for Export`;
  }
  if (tplNameEl && operatorActiveTemplate) {
    tplNameEl.textContent = `${t("label_template_prefix")} ${operatorActiveTemplate.name || ""}`;
  }

  // Auto-detect and bind Google Apps Script write-back URL from active trainer or global storage
  const trainer = activeTrainers.find((t) => t.id === operatorActiveTrainerId);
  let targetScript = trainer?.script_url || (trainer?.sheet_url && (trainer.sheet_url.includes("script.google.com") || trainer.sheet_url.includes("script.googleusercontent.com")) ? trainer.sheet_url : "");
  if (!targetScript) {
    targetScript = getGlobalAppsScriptUrl();
  }
  if (!targetScript) {
    const trWithScript = activeTrainers.find((t) => t.script_url || (t.sheet_url && (t.sheet_url.includes("script.google.com") || t.sheet_url.includes("script.googleusercontent.com"))));
    if (trWithScript) {
      targetScript = trWithScript.script_url || trWithScript.sheet_url;
    }
  }

  if (webhookInput && targetScript) {
    if (!webhookInput.value) webhookInput.value = targetScript;
  }
  if (scriptBadge) {
    if (targetScript) scriptBadge.classList.remove("hidden");
    else scriptBadge.classList.add("hidden");
  }

  if (modal) {
    modal.classList.remove("hidden");
  }
  lucide.createIcons();
}

function closeBatchExportModal() {
  const modal = document.getElementById("batch-export-modal");
  if (modal) modal.classList.add("hidden");
}

async function exportBatchSubmit() {
  if (!operatorActiveTemplate) {
    showToast(t("toast_select_tpl_first"), "warning");
    return;
  }
  if (!operatorRecords || operatorRecords.length === 0) {
    showToast(t("toast_no_records_export"), "warning");
    return;
  }

  const exportMode = document.getElementById("batch-export-mode")?.value || "combined_pdf";
  const rangeStr = document.getElementById("batch-export-range")?.value || "ALL";
  const prefix = document.getElementById("batch-export-prefix")?.value || "CertFlow";
  const dpi = parseInt(document.getElementById("batch-export-dpi")?.value || "300", 10);
  const webhookUrl = document.getElementById("batch-export-webhook")?.value || "";

  const submitBtn = document.getElementById("btn-start-batch-export");
  const loadingIndicator = document.getElementById("batch-export-loading");

  if (submitBtn) submitBtn.disabled = true;
  if (loadingIndicator) loadingIndicator.classList.remove("hidden");

  // Pre-format records
  const formattedRecords = operatorRecords.map((rec) => {
    const rawDate = operatorFixedDate || rec.Training_Date || rec.training_date || "2026-10-29";
    const formattedDate = formatDisplayDate(rawDate, operatorDateFormat);
    const traineeName = rec.Trainee_Name || rec.trainee_name || "";
    return {
      ...rec,
      trainee_name: traineeName,
      Trainee_Name: traineeName,
      training_date: formattedDate,
      Training_Date: formattedDate,
      trainer_id: operatorActiveTrainerId || rec.trainer_id || "",
    };
  });

  const trainer = activeTrainers.find((t) => t.id === operatorActiveTrainerId);
  // Resolve Google Apps Script Web App URL strictly for this trainer (preventing cross-trainer pollution)
  let appsScriptUrl = "";
  if (webhookUrl && (webhookUrl.includes("script.google.com") || webhookUrl.includes("script.googleusercontent.com"))) {
    appsScriptUrl = webhookUrl.trim();
  } else if (trainer?.script_url && trainer.script_url.trim()) {
    appsScriptUrl = trainer.script_url.trim();
  } else if (trainer?.sheet_url && (trainer.sheet_url.includes("script.google.com") || trainer.sheet_url.includes("script.googleusercontent.com"))) {
    appsScriptUrl = trainer.sheet_url.trim();
  } else if (!trainer?.sheet_url || !trainer.sheet_url.includes("docs.google.com")) {
    // Only fall back to global apps script if this trainer doesn't have an independent direct Google Sheet
    appsScriptUrl = getGlobalAppsScriptUrl();
  }

  if (appsScriptUrl) {
    setGlobalAppsScriptUrl(appsScriptUrl);
  }

  const sheetUrl = trainer?.sheet_url || "";

  const payload = {
    template_config: operatorActiveTemplate,
    template_id: operatorActiveTemplate.id,
    records: formattedRecords,
    export_mode: exportMode,
    range_str: rangeStr,
    filename_prefix: prefix,
    dpi: dpi,
    webhook_url: webhookUrl,
    apps_script_url: appsScriptUrl,
    trainer_id: operatorActiveTrainerId || "",
    sheet_url: sheetUrl,
  };

  try {
    const response = await fetch("/api/export-batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "فشل تصدير الشهادات");
    }

    let downloadFilename = exportMode === "combined_pdf" ? `${prefix}_Certificates.pdf` : `${prefix}_Certificates.zip`;
    const disposition = response.headers.get("Content-Disposition");
    if (disposition && disposition.indexOf("filename=") !== -1) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        downloadFilename = match[1];
      }
    }

    const exportedCount = response.headers.get("X-Exported-Count") || formattedRecords.length;
    const warningsCount = response.headers.get("X-Warnings-Count") || "0";
    const isAppsScriptSynced = response.headers.get("X-Apps-Script-Synced") === "true";
    const isAppsScriptSkipped = response.headers.get("X-Apps-Script-Skipped") === "true";
    let appsScriptError = "";
    try {
      const rawErr = response.headers.get("X-Apps-Script-Error") || "";
      appsScriptError = rawErr ? decodeURIComponent(rawErr) : "";
    } catch (_) {
      appsScriptError = response.headers.get("X-Apps-Script-Error") || "";
    }
    const appsScriptUpdated = parseInt(response.headers.get("X-Apps-Script-Updated") || "0", 10);

    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = downloadFilename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    document.body.removeChild(a);

    // Mark exported records as issued in memory
    const exportedNames = new Set(formattedRecords.map((r) => r.trainee_name || r.Trainee_Name));
    operatorAllSheetRecords.forEach((r) => {
      const name = r.Trainee_Name || r.trainee_name;
      if (exportedNames.has(name)) {
        r.is_issued = true;
        r.issued_template = operatorActiveTemplate.name || "Issued";
      }
    });

    closeBatchExportModal();
    showToast(`تم تصدير ${exportedCount} شهادة بنجاح وتحميل الملف (${downloadFilename})`, "success");

    // Re-apply sheet filters to update counter and hide issued records
    applySheetFilters();

    // Truthful Apps Script Sync Feedback (no false positives, FIX 5)
    if (appsScriptUrl) {
      if (isAppsScriptSkipped) {
        setTimeout(() => {
          showToast("تنبيه: لم يتم تحديث قوقل شيت لعدم وجود حقل اسم متدرب في السجلات المحددة", "info");
        }, 1000);
      } else if (isAppsScriptSynced) {
        if (appsScriptUpdated > 0) {
          setTimeout(() => {
            showToast(`تم تحديث اسم القالب "${operatorActiveTemplate.name}" في قوقل شيت بنجاح (${appsScriptUpdated} متدرب)`, "success");
          }, 1000);
        } else {
          setTimeout(() => {
            showToast("تنبيه: تم الاتصال بـ Google Apps Script ولكن لم يتم العثور على أي من الأسماء في قوقل شيت (0 متدرب)", "warning");
          }, 1000);
        }
      } else {
        setTimeout(() => {
          const reason = appsScriptError || "تحقق من إعدادات النشر وصلاحيات المشاركة في قوقل شيت";
          showToast(`تنبيه: تعذر تحديث قوقل شيت عبر Apps Script: ${reason}`, "error");
        }, 1200);
      }
    }

    if (parseInt(warningsCount, 10) > 0) {
      setTimeout(() => {
        showToast(`تنبيه: تم رصد ${warningsCount} ملاحظة تقليص خط لأسماء تجاوزت الإطار`, "warning");
      }, 2000);
    }
  } catch (err) {
    console.error("Batch export error:", err);
    showToast(err.message, "error");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
    if (loadingIndicator) loadingIndicator.classList.add("hidden");
  }
}

// ----------------------------------------------------------
// 5. Fit-to-Screen Live Operator Canvas
// ----------------------------------------------------------

function fitOperatorCanvasToScreen() {
  const container = document.getElementById("operator-canvas-container");
  const wrapper = document.getElementById("op-cert-wrapper");
  const emptyState = document.getElementById("op-empty-state");
  if (!container || !wrapper) return;

  if (!operatorActiveTemplate) {
    if (emptyState) emptyState.classList.remove("hidden");
    wrapper.classList.add("hidden");
    return;
  }

  if (emptyState) emptyState.classList.add("hidden");
  wrapper.classList.remove("hidden");

  const ps = operatorActiveTemplate.page_setup || { width_mm: 297, height_mm: 210 };
  const trimW = parseFloat(ps.width_mm) || 297;
  const trimH = parseFloat(ps.height_mm) || 210;
  const ar = trimW / trimH;

  const pad = 40;
  const availW = Math.max(200, container.clientWidth - pad);
  const availH = Math.max(200, container.clientHeight - pad);

  let w = availW;
  let h = w / ar;
  if (h > availH) {
    h = availH;
    w = h * ar;
  }

  wrapper.style.width = `${Math.round(w)}px`;
  wrapper.style.height = `${Math.round(h)}px`;
}

async function refreshOperatorCanvas(force = false) {
  clearTimeout(operatorCanvasDebounce);
  operatorCanvasDebounce = setTimeout(async () => {
    await doRenderOperatorCanvas();
  }, force ? 10 : 150);
}

async function doRenderOperatorCanvas() {
  const overlay = document.getElementById("op-canvas-loading");
  const img = document.getElementById("op-canvas-img");
  const shrinkBadge = document.getElementById("op-active-shrink-badge");
  const warningBox = document.getElementById("op-shrink-warning-box");
  const emptyState = document.getElementById("op-empty-state");
  const wrapper = document.getElementById("op-cert-wrapper");
  const topTpl = document.getElementById("op-top-tpl-name");
  const bottomTpl = document.getElementById("op-bottom-tpl-name");
  const bottomDims = document.getElementById("op-bottom-tpl-dims");

  if (!operatorActiveTemplate) {
    if (overlay) overlay.classList.add("hidden");
    if (emptyState) emptyState.classList.remove("hidden");
    if (wrapper) wrapper.classList.add("hidden");
    if (topTpl) topTpl.textContent = "—";
    if (bottomTpl) bottomTpl.textContent = `${t("label_template_prefix")} —`;
    if (bottomDims) bottomDims.textContent = "—";
    if (shrinkBadge) {
      shrinkBadge.className = "text-[11px] px-2.5 py-1 rounded-full bg-slate-100 text-slate-500 font-bold border border-slate-200 whitespace-nowrap";
      shrinkBadge.textContent = t("badge_waiting_template");
    }
    if (warningBox) warningBox.classList.add("hidden");
    updateOperatorTemplateInfo();
    updateEmptyStateSteps();
    return;
  }

  if (emptyState) emptyState.classList.add("hidden");
  if (wrapper) wrapper.classList.remove("hidden");
  if (overlay) overlay.classList.remove("hidden");

  const todayStr = new Date().toISOString().split("T")[0];
  const genericPlaceholderName = currentLang === "en" ? "Trainee Name" : "اسم المتدرب";

  const hasRealRecords = operatorRecords && operatorRecords.length > 0;
  const record = hasRealRecords ? operatorRecords[currentRecordIndex] : null;

  const rawDate = operatorFixedDate || (record ? (record.Training_Date || record.training_date) : "") || todayStr;
  const displayDate = formatDisplayDate(rawDate, operatorDateFormat);

  const traineeName = (record && (record.Trainee_Name || record.trainee_name)) || genericPlaceholderName;
  const customText = (record && (record.Custom_Text || record.custom_text)) || "";

  const payload = {
    template_config: operatorActiveTemplate,
    record_data: {
      trainee_name: traineeName,
      Trainee_Name: traineeName,
      training_date: displayDate,
      Training_Date: displayDate,
      custom_text: customText,
      Custom_Text: customText,
      trainer_id: operatorActiveTrainerId || "",
    },
    trainer_id: operatorActiveTrainerId || "",
    show_trim_guide: false,
    dpi: 150,
  };

  try {
    const res = await fetch("/api/preview-certificate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "فشل رندرة المعاينة");
    }

    // Inspect real prepress metrics from response headers
    const textShrunk = res.headers.get("X-Text-Shrunk") === "true";
    const shrinkPercent = parseFloat(res.headers.get("X-Shrink-Percent") || "0");
    const textOverflow = res.headers.get("X-Text-Overflow") === "true";

    if (shrinkBadge) {
      if (textOverflow) {
        shrinkBadge.className = "text-[11px] px-2.5 py-1 rounded-full bg-rose-50 text-rose-700 font-bold border border-rose-300 whitespace-nowrap animate-pulse";
        shrinkBadge.textContent = t("badge_overflow");
        if (warningBox) {
          warningBox.classList.remove("hidden");
          const warningText = document.getElementById("op-shrink-warning-text");
          if (warningText) warningText.textContent = t("warn_overflow");
        }
      } else if (textShrunk && shrinkPercent > 0) {
        shrinkBadge.className = "text-[11px] px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 font-bold border border-amber-300 whitespace-nowrap";
        shrinkBadge.textContent = `${t("badge_shrunk_pct")} ${shrinkPercent}%`;
        if (warningBox) {
          warningBox.classList.remove("hidden");
          const warningText = document.getElementById("op-shrink-warning-text");
          if (warningText) warningText.textContent = currentLang === "ar"
            ? `تم تقليص حجم الخط تلقائياً بنسبة ${shrinkPercent}% ليناسب مساحة الإطار تماماً.`
            : `Font size automatically reduced by ${shrinkPercent}% to fit the frame perfectly.`;
        }
      } else {
        shrinkBadge.className = "text-[11px] px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 font-bold border border-emerald-200 whitespace-nowrap";
        shrinkBadge.textContent = t("badge_optimal_fit");
        if (warningBox) warningBox.classList.add("hidden");
      }
    }

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    if (img) img.src = objectUrl;
  } catch (err) {
    console.error("Operator canvas render error:", err);
  } finally {
    if (overlay) overlay.classList.add("hidden");
    lucide.createIcons();
  }
}


// ==========================================================
// Interactive Designer Studio Engine (Task 3)
// ==========================================================

function pushHistoryState() {
  if (!currentTemplate) return;
  const snapshot = JSON.stringify(currentTemplate);
  if (historyStack.length > 0 && historyStack[historyStack.length - 1] === snapshot) {
    return;
  }
  historyStack.push(snapshot);
  if (historyStack.length > MAX_HISTORY) {
    historyStack.shift();
  }
  redoStack = [];
  updateUndoRedoButtons();
}

function undo() {
  if (historyStack.length === 0) return;
  const currentSnapshot = JSON.stringify(currentTemplate);
  redoStack.push(currentSnapshot);
  const prevSnapshot = historyStack.pop();
  currentTemplate = JSON.parse(prevSnapshot);
  renderFramesOnCanvas();
  renderInspector();
  updateUndoRedoButtons();
  showToast(t("toast_undo"), "info");
}

function redo() {
  if (redoStack.length === 0) return;
  const currentSnapshot = JSON.stringify(currentTemplate);
  historyStack.push(currentSnapshot);
  const nextSnapshot = redoStack.pop();
  currentTemplate = JSON.parse(nextSnapshot);
  renderFramesOnCanvas();
  renderInspector();
  updateUndoRedoButtons();
  showToast(t("toast_redo"), "info");
}

function updateUndoRedoButtons() {
  const btnUndo = document.getElementById("btn-undo");
  const btnRedo = document.getElementById("btn-redo");
  if (btnUndo) btnUndo.disabled = historyStack.length === 0;
  if (btnRedo) btnRedo.disabled = redoStack.length === 0;
}

async function toggleDesignerLivePreview() {
  const framesLayer = document.getElementById("canvas-frames-layer");
  const baseImg = document.getElementById("canvas-base-img");
  const btn = document.getElementById("btn-toggle-print-preview");
  const bleedGuide = document.getElementById("canvas-bleed-guide");
  const trimGuide = document.getElementById("canvas-trim-guide");

  if (!currentTemplate) return;

  if (!isDesignerLivePreviewActive) {
    // Turn On True Print Preview
    isDesignerLivePreviewActive = true;
    if (framesLayer) framesLayer.style.display = "none";
    if (bleedGuide) bleedGuide.style.display = "none";
    if (trimGuide) trimGuide.style.display = "none";

    if (btn) {
      btn.innerHTML = `<i data-lucide="eye-off" class="w-3.5 h-3.5 text-brand-warning"></i><span>${t("btn_cancel_preview")}</span>`;
      btn.classList.add("bg-brand-warning/30", "text-amber-300");
    }

    try {
      const sampleData = {
        trainee_name: currentLang === "ar" ? "اسم المتدرب" : "Trainee Name",
        training_date: currentLang === "ar" ? "١٩ يناير ٢٠٢٦" : "January 19, 2026"
      };
      const res = await fetch("/api/preview-certificate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_config: currentTemplate,
          record_data: sampleData,
          show_trim_guide: false,
          dpi: 200
        })
      });
      if (res.ok) {
        const blob = await res.blob();
        baseImg.src = URL.createObjectURL(blob);
      }
    } catch (e) {
      console.error("True preview error:", e);
    }
  } else {
    // Restore Canvas Editor
    isDesignerLivePreviewActive = false;
    if (framesLayer) framesLayer.style.display = "block";
    if (bleedGuide) bleedGuide.style.display = showGuides ? "block" : "none";
    if (trimGuide) trimGuide.style.display = showGuides ? "block" : "none";

    if (btn) {
      btn.innerHTML = `<i data-lucide="eye" class="w-3.5 h-3.5 text-brand-secondary"></i><span>${t("btn_print_preview")}</span>`;
      btn.classList.remove("bg-brand-warning/30", "text-amber-300");
    }

    let previewUrl = currentTemplate.base_preview_url || `/api/templates/base-preview/${currentTemplate.base_pdf_filename || "default_certificate_base.pdf"}`;
    baseImg.src = previewUrl;
  }
  lucide.createIcons();
}

function alignActiveFieldToCenterHorizontally() {
  if (!currentTemplate || !activeFieldId) return;
  const pageSetup = currentTemplate.page_setup || { width_mm: 297.0, height_mm: 210.0 };
  const pageWidth = parseFloat(pageSetup.width_mm) || 297.0;

  let target;
  if (activeFieldType === "text") {
    target = currentTemplate.fields.find((f) => f.id === activeFieldId);
  } else {
    target = (currentTemplate.signature_frames || []).find((s) => s.id === activeFieldId);
  }
  if (!target) return;

  const w = parseFloat(target.width_mm) || 50.0;
  target.x_mm = Math.round(((pageWidth - w) / 2.0) * 10) / 10;
  pushHistoryState();
  renderFramesOnCanvas();
  renderInspector();
  showToast(t("toast_center_h"), "info");
}

function alignActiveFieldToCenterVertically() {
  if (!currentTemplate || !activeFieldId) return;
  const pageSetup = currentTemplate.page_setup || { width_mm: 297.0, height_mm: 210.0 };
  const pageHeight = parseFloat(pageSetup.height_mm) || 210.0;

  let target;
  if (activeFieldType === "text") {
    target = currentTemplate.fields.find((f) => f.id === activeFieldId);
  } else {
    target = (currentTemplate.signature_frames || []).find((s) => s.id === activeFieldId);
  }
  if (!target) return;

  const h = parseFloat(target.height_mm) || 20.0;
  target.y_mm = Math.round(((pageHeight - h) / 2.0) * 10) / 10;
  pushHistoryState();
  renderFramesOnCanvas();
  renderInspector();
  showToast(t("toast_center_v"), "info");
}

function addOrFocusTraineeNameField() {
  if (!currentTemplate) return;
  if (!currentTemplate.fields) currentTemplate.fields = [];

  const existing = currentTemplate.fields.find((f) => f.id === "trainee_name");
  if (existing) {
    activeFieldId = "trainee_name";
    activeFieldType = "text";
    renderFramesOnCanvas();
    renderInspector();
    showToast(t("toast_field_selected_name"), "info");
    return;
  }

  const pageSetup = currentTemplate.page_setup || { width_mm: 297.0, height_mm: 210.0 };
  const pw = parseFloat(pageSetup.width_mm) || 297.0;
  const w = 217.0;
  const x = Math.max(10.0, Math.round(((pw - w) / 2.0) * 10) / 10);

  const newField = {
    id: "trainee_name",
    label: "اسم المتدرب",
    default_text: currentLang === "ar" ? "اسم المتدرب" : "Trainee Name",
    x_mm: x,
    y_mm: 80.0,
    width_mm: w,
    height_mm: 24.0,
    font_family: "Cairo Regular",
    english_font: "Cairo Regular",
    font_size: 32.0,
    color: "#004B87",
    horizontal_align: "center",
    vertical_align: "middle",
    max_shrink_percent: 25.0,
    baseline_offset_mm: 0.0,
  };

  currentTemplate.fields.push(newField);
  activeFieldId = "trainee_name";
  activeFieldType = "text";
  pushHistoryState();
  renderFramesOnCanvas();
  renderInspector();
  showToast(t("toast_field_added_name"), "success");
}

function addOrFocusTrainingDateField() {
  if (!currentTemplate) return;
  if (!currentTemplate.fields) currentTemplate.fields = [];

  const existing = currentTemplate.fields.find((f) => f.id === "training_date");
  if (existing) {
    activeFieldId = "training_date";
    activeFieldType = "text";
    renderFramesOnCanvas();
    renderInspector();
    showToast(t("toast_field_selected_date"), "info");
    return;
  }

  const pageSetup = currentTemplate.page_setup || { width_mm: 297.0, height_mm: 210.0 };
  const ph = parseFloat(pageSetup.height_mm) || 210.0;

  const newField = {
    id: "training_date",
    label: "تاريخ التدريب",
    default_text: "يناير ١٩، ٢٠٢٦",
    x_mm: 35.0,
    y_mm: Math.max(20.0, ph - 55.0),
    width_mm: 80.0,
    height_mm: 14.0,
    font_family: "Cairo Regular",
    english_font: "Cairo Regular",
    font_size: 13.0,
    color: "#475569",
    horizontal_align: "right",
    vertical_align: "middle",
    max_shrink_percent: 20.0,
    baseline_offset_mm: 0.0,
  };

  currentTemplate.fields.push(newField);
  activeFieldId = "training_date";
  activeFieldType = "text";
  pushHistoryState();
  renderFramesOnCanvas();
  renderInspector();
  showToast(t("toast_field_added_date"), "success");
}

function addOrFocusTrainerSignatureField() {
  if (!currentTemplate) return;
  if (!currentTemplate.signature_frames) currentTemplate.signature_frames = [];

  const existing = currentTemplate.signature_frames.find((s) => s.id === "trainer_signature");
  if (existing) {
    activeFieldId = "trainer_signature";
    activeFieldType = "signature";
    renderFramesOnCanvas();
    renderInspector();
    showToast(t("toast_field_selected_sig"), "info");
    return;
  }

  const pageSetup = currentTemplate.page_setup || { width_mm: 297.0, height_mm: 210.0 };
  const pw = parseFloat(pageSetup.width_mm) || 297.0;
  const ph = parseFloat(pageSetup.height_mm) || 210.0;

  const newSig = {
    id: "trainer_signature",
    label: "توقيع المدرب",
    x_mm: Math.max(20.0, pw - 95.0),
    y_mm: Math.max(20.0, ph - 65.0),
    width_mm: 70.0,
    height_mm: 32.0,
    baseline_offset_mm: 0.0,
    scale: 100.0,
  };

  currentTemplate.signature_frames.push(newSig);
  activeFieldId = "trainer_signature";
  activeFieldType = "signature";
  pushHistoryState();
  renderFramesOnCanvas();
  renderInspector();
  showToast(t("toast_field_added_sig"), "success");
}

function addCustomTextField() {
  if (!currentTemplate) return;
  if (!currentTemplate.fields) currentTemplate.fields = [];

  const count = currentTemplate.fields.filter((f) => f.id.startsWith("custom_text")).length + 1;
  const newId = `custom_text_${count}`;

  const newField = {
    id: newId,
    label: `حقل إضافي ${count}`,
    default_text: "نص إضافي في الشهادة",
    x_mm: 40.0,
    y_mm: 110.0,
    width_mm: 217.0,
    height_mm: 16.0,
    font_family: "Cairo Regular",
    english_font: "Cairo Regular",
    font_size: 16.0,
    color: "#1E293B",
    horizontal_align: "center",
    vertical_align: "middle",
    max_shrink_percent: 20.0,
    baseline_offset_mm: 0.0,
  };

  currentTemplate.fields.push(newField);
  activeFieldId = newId;
  activeFieldType = "text";
  pushHistoryState();
  renderFramesOnCanvas();
  renderInspector();
  showToast(currentLang === "ar" ? `تمت إضافة ${newField.label}` : `Added ${getLocalizedFieldLabel(newField)}`, "success");
}

function promptAddNewCompany() {
  const name = prompt(currentLang === "ar" ? "أدخل اسم الجهة / الشركة الجديدة:" : "Enter new Affiliate / Client name:");
  if (!name || !name.trim()) return;
  const clean = name.trim();
  const datalist = document.getElementById("company-datalist");
  if (datalist) {
    const opt = document.createElement("option");
    opt.value = clean;
    datalist.appendChild(opt);
  }
  handleTemplateCompanyChange(clean);
  const compInput = document.getElementById("designer-template-company");
  if (compInput) compInput.value = clean;
  renderInspector();
  showToast(currentLang === "ar" ? `تمت إضافة وتعيين الشركة: "${clean}"` : `Affiliate / Client added: "${clean}"`, "success");
}

function initDesignerStudio() {
  if (!designerStudioInitialized) {
    window.addEventListener("resize", debounceFitCanvas);
    window.addEventListener("mousemove", handleGlobalMouseMove);
    window.addEventListener("mouseup", handleGlobalMouseUp);

    // Keyboard Undo / Redo Shortcuts
    window.addEventListener("keydown", (e) => {
      const isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0;
      const mod = isMac ? e.metaKey : e.ctrlKey;
      if (mod && e.key.toLowerCase() === "z" && !e.shiftKey) {
        if (document.activeElement && (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "TEXTAREA")) return;
        e.preventDefault();
        undo();
      } else if ((mod && e.key.toLowerCase() === "z" && e.shiftKey) || (mod && e.key.toLowerCase() === "y")) {
        if (document.activeElement && (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "TEXTAREA")) return;
        e.preventDefault();
        redo();
      }
    });

    // Canvas click outside frames deselects active frame
    const canvasContainer = document.getElementById("designer-canvas-container");
    if (canvasContainer) {
      canvasContainer.addEventListener("mousedown", (e) => {
        if (!e.target.closest(".designer-frame")) {
          activeFieldId = null;
          activeFieldType = null;
          renderFramesOnCanvas();
          renderInspector();
        }
      });
    }
    designerStudioInitialized = true;
  }

  loadDesignerTemplates();
}

function debounceFitCanvas() {
  clearTimeout(fitCanvasDebounceTimer);
  fitCanvasDebounceTimer = setTimeout(() => {
    fitCanvasToScreen();
  }, 100);
}

async function loadDesignerTemplates() {
  try {
    const res = await fetch("/api/templates");
    if (!res.ok) throw new Error("فشل تحميل القوالب");
    const data = await res.json();
    designerTemplates = data.templates || [];

    const selectEl = document.getElementById("designer-template-select");
    if (selectEl) {
      selectEl.innerHTML = "";
      designerTemplates.forEach((tpl) => {
        const opt = document.createElement("option");
        opt.value = tpl.id;
        opt.textContent = tpl.name || tpl.id;
        selectEl.appendChild(opt);
      });
    }

    if (!currentTemplate && designerTemplates.length > 0) {
      currentTemplate = designerTemplates[0];
    }

    if (currentTemplate) {
      if (selectEl) selectEl.value = currentTemplate.id;
      const nameInput = document.getElementById("designer-template-name");
      if (nameInput) nameInput.value = currentTemplate.name || "";
      const compInput = document.getElementById("designer-template-company");
      if (compInput) compInput.value = currentTemplate.company || "";
      updatePrepressBadges();
      fitCanvasToScreen();
      renderInspector();
    }
  } catch (err) {
    console.error("Load templates error:", err);
    showToast(err.message, "error");
  }
}

function handleSelectTemplate(tplId) {
  const tpl = designerTemplates.find((t) => t.id === tplId);
  if (!tpl) return;
  currentTemplate = JSON.parse(JSON.stringify(tpl));
  const nameInput = document.getElementById("designer-template-name");
  if (nameInput) nameInput.value = currentTemplate.name || "";
  const compInput = document.getElementById("designer-template-company");
  if (compInput) compInput.value = currentTemplate.company || "";
  activeFieldId = null;
  activeFieldType = null;
  updatePrepressBadges();
  fitCanvasToScreen();
  renderInspector();
}

function handleTemplateCompanyChange(newCompany) {
  if (!currentTemplate) return;
  currentTemplate.company = newCompany.trim();
}

function handleTemplateNameChange(newName) {
  if (!currentTemplate) return;
  currentTemplate.name = newName.trim();
  const selectEl = document.getElementById("designer-template-select");
  if (selectEl && selectEl.selectedOptions[0]) {
    selectEl.selectedOptions[0].textContent = currentTemplate.name;
  }
}

function updatePrepressBadges() {
  if (!currentTemplate) return;
  const pageSetup = currentTemplate.page_setup || { width_mm: 297.0, height_mm: 210.0, bleed_mm: 3.0 };
  const trimBadge = document.getElementById("designer-trim-badge");
  const bleedBadge = document.getElementById("designer-bleed-badge");

  if (trimBadge) {
    trimBadge.textContent = `${parseFloat(pageSetup.width_mm).toFixed(1)} × ${parseFloat(pageSetup.height_mm).toFixed(1)} mm`;
  }
  if (bleedBadge) {
    bleedBadge.textContent = `${parseFloat(pageSetup.bleed_mm || 3.0).toFixed(1)} mm`;
  }
}

function toggleGuides(checked) {
  showGuides = !!checked;
  const bleedGuide = document.getElementById("canvas-bleed-guide");
  const trimGuide = document.getElementById("canvas-trim-guide");
  if (bleedGuide) bleedGuide.style.display = showGuides ? "block" : "none";
  if (trimGuide) trimGuide.style.display = showGuides ? "block" : "none";
}

function fitCanvasToScreen() {
  const container = document.getElementById("designer-canvas-container");
  const wrapper = document.getElementById("canvas-cert-wrapper");
  const baseImg = document.getElementById("canvas-base-img");
  const trimboxContainer = document.getElementById("canvas-trimbox-container");
  const bleedGuide = document.getElementById("canvas-bleed-guide");
  const trimGuide = document.getElementById("canvas-trim-guide");
  const zoomLabel = document.getElementById("canvas-zoom-label");

  if (!container || !wrapper || !currentTemplate) return;

  const pageSetup = currentTemplate.page_setup || { width_mm: 297.0, height_mm: 210.0, bleed_mm: 3.0 };
  const trimW = parseFloat(pageSetup.width_mm) || 297.0;
  const trimH = parseFloat(pageSetup.height_mm) || 210.0;

  const bleedOffsets = (currentTemplate.boxes_metadata && currentTemplate.boxes_metadata.bleed_offsets_mm)
    ? currentTemplate.boxes_metadata.bleed_offsets_mm
    : { top: 3.0, bottom: 3.0, left: 3.0, right: 3.0 };

  const bLeft = parseFloat(bleedOffsets.left) || 3.0;
  const bRight = parseFloat(bleedOffsets.right) || 3.0;
  const bTop = parseFloat(bleedOffsets.top) || 3.0;
  const bBottom = parseFloat(bleedOffsets.bottom) || 3.0;

  const totalW = trimW + bLeft + bRight;
  const totalH = trimH + bTop + bBottom;
  const ar = totalW / totalH;

  const pad = 40;
  const availW = Math.max(200, container.clientWidth - pad);
  const availH = Math.max(200, container.clientHeight - pad);

  let targetW, targetH;
  if (availW / availH > ar) {
    targetH = availH;
    targetW = targetH * ar;
  } else {
    targetW = availW;
    targetH = targetW / ar;
  }

  wrapper.style.width = `${Math.round(targetW)}px`;
  wrapper.style.height = `${Math.round(targetH)}px`;

  const trimLeftPct = (bLeft / totalW) * 100;
  const trimTopPct = (bTop / totalH) * 100;
  const trimWidthPct = (trimW / totalW) * 100;
  const trimHeightPct = (trimH / totalH) * 100;

  if (trimboxContainer) {
    trimboxContainer.style.left = `${trimLeftPct}%`;
    trimboxContainer.style.top = `${trimTopPct}%`;
    trimboxContainer.style.width = `${trimWidthPct}%`;
    trimboxContainer.style.height = `${trimHeightPct}%`;
  }

  // Base image preview
  let previewUrl = currentTemplate.base_preview_url;
  if (!previewUrl && currentTemplate.base_pdf_filename) {
    previewUrl = `/api/templates/base-preview/${currentTemplate.base_pdf_filename}`;
  }
  if (!previewUrl) {
    previewUrl = "/api/templates/base-preview/default_certificate_base.pdf";
  }

  if (baseImg && previewUrl && baseImg.getAttribute("src") !== previewUrl) {
    baseImg.src = previewUrl;
  }

  if (bleedGuide) bleedGuide.style.display = showGuides ? "block" : "none";
  if (trimGuide) trimGuide.style.display = showGuides ? "block" : "none";

  if (zoomLabel) {
    zoomLabel.textContent = `Fit: 100% (${Math.round(targetW)}×${Math.round(targetH)}px)`;
  }

  renderFramesOnCanvas();
}

function getLocalizedFieldLabel(fieldOrSig) {
  if (!fieldOrSig) return "";
  const id = fieldOrSig.id || "";
  const label = (fieldOrSig.label || "").trim();

  if (id === "trainee_name" || label === "اسم المتدرب") {
    return currentLang === "ar" ? "اسم المتدرب" : "Trainee Name";
  }
  if (id === "training_date" || label === "تاريخ التدريب") {
    return currentLang === "ar" ? "تاريخ التدريب" : "Training Date";
  }
  if (id === "trainer_signature" || id.startsWith("sig_") || label === "توقيع المدرب") {
    return currentLang === "ar" ? "توقيع المدرب" : "Trainer Signature";
  }
  if (id.startsWith("custom_text") || id.startsWith("field_") || label === "حقل إضافي" || label.startsWith("حقل إضافي")) {
    if (currentLang === "ar") {
      return label || "حقل إضافي";
    }
    return (label && !/[\u0600-\u06FF]/.test(label)) ? label : "Custom Text";
  }

  if (currentLang === "en" && /[\u0600-\u06FF]/.test(label)) {
    if (label.includes("اسم") || label.toLowerCase().includes("name")) return "Trainee Name";
    if (label.includes("تاريخ") || label.toLowerCase().includes("date")) return "Training Date";
    if (label.includes("توقيع") || label.toLowerCase().includes("sig")) return "Trainer Signature";
    return id || "Custom Field";
  }

  return label || id;
}

function getLocalizedSampleText(field) {
  if (!field) return "";
  const id = field.id || "";
  const dt = (field.default_text || "").trim();

  if (currentLang === "en") {
    if (id === "training_date" || dt === "يناير ١٩، ٢٠٢٦" || (dt.includes("يناير") && /[\u0600-\u06FF]/.test(dt))) {
      return "January 19, 2026";
    }
    if (id === "trainee_name" || dt === "سارة محمد إبراهيم المنصور" || dt === "اسم المتدرب" || dt === "اسم المتدرب التجريبي") {
      return "Trainee Name";
    }
    if (id.startsWith("custom_text") || dt === "نص إضافي في الشهادة" || dt === "نص حقل جديد" || dt === "حقل إضافي") {
      return "Custom Certificate Text";
    }
    if (dt === "شهادة إتمام برنامج تدريبي") return "Certificate of Completion";
    if (dt === "تُمنح هذه الشهادة تقديراً لاجتياز المتدرب/ـة بنجاح:") return "This certificate is proudly awarded to:";
    if (dt === "في المسار المتقدم للتصميم الطباعي وإدارة بيانات الشهادات فائقة الدقة") return "For successful completion of Advanced Certification Program";
    if (dt.startsWith("تاريخ الاعتماد:")) return "Issue Date: 2026-10-29";
  }

  if (currentLang === "ar" && dt === "سارة محمد إبراهيم المنصور") {
    return "اسم المتدرب";
  }

  return field.default_text || (currentLang === "en" ? (field.label && !/[\u0600-\u06FF]/.test(field.label) ? field.label : id) : (field.label || id));
}

function renderFramesOnCanvas() {
  const container = document.getElementById("canvas-frames-layer");
  if (!container || !currentTemplate) return;

  container.innerHTML = "";

  const pageSetup = currentTemplate.page_setup || { width_mm: 297.0, height_mm: 210.0 };
  const trimW = parseFloat(pageSetup.width_mm) || 297.0;
  const trimH = parseFloat(pageSetup.height_mm) || 210.0;

  const wrapper = document.getElementById("canvas-cert-wrapper");
  const wrapperW = wrapper ? wrapper.clientWidth : 800;

  // 1. Render Text Fields
  const fields = currentTemplate.fields || [];
  fields.forEach((f) => {
    const isSelected = activeFieldId === f.id && activeFieldType === "text";
    const frameEl = document.createElement("div");
    frameEl.className = `designer-frame absolute border-2 border-dashed border-[#49A8DE] ${isSelected ? "selected" : ""}`;
    frameEl.dataset.fieldId = f.id;
    frameEl.dataset.fieldType = "text";

    frameEl.style.left = `${(f.x_mm / trimW) * 100}%`;
    frameEl.style.top = `${(f.y_mm / trimH) * 100}%`;
    frameEl.style.width = `${(f.width_mm / trimW) * 100}%`;
    frameEl.style.height = `${(f.height_mm / trimH) * 100}%`;

    const scaledFontSize = Math.max(9, (f.font_size || 24) * (wrapperW / (trimW * 3.7795)) * 0.95);
    const cssColor = formatColorForCss(f.color);
    const alignCss = mapAlignToCss(f.horizontal_align);
    const vAlignCss = mapVAlignToCss(f.vertical_align);
    const dirCss = f.direction === "ltr" ? "ltr" : "rtl";

    frameEl.innerHTML = `
      <div class="w-full h-full flex p-1 overflow-hidden pointer-events-none truncate select-none leading-none"
           style="justify-content: ${alignCss}; align-items: ${vAlignCss}; color: ${cssColor}; font-family: '${f.font_family || 'Cairo Regular'}', sans-serif; font-size: ${scaledFontSize}px; direction: ${dirCss};">
        <span class="truncate">${getLocalizedSampleText(f)}</span>
      </div>
      <span class="absolute top-0 start-0 bg-[#004B87] text-white text-[9px] font-bold px-1.5 py-0.2 rounded-br shadow-xs pointer-events-none opacity-90 truncate max-w-[85%]">${getLocalizedFieldLabel(f)}</span>
      ${isSelected ? renderHandlesHtml() : ""}
    `;

    frameEl.addEventListener("mousedown", (e) => handleFrameMouseDown(e, f.id, "text"));
    container.appendChild(frameEl);
  });

  // 2. Render Signature Frames
  const sigFrames = currentTemplate.signature_frames || [];
  sigFrames.forEach((s) => {
    const isSelected = activeFieldId === s.id && activeFieldType === "signature";
    const frameEl = document.createElement("div");
    frameEl.className = `designer-frame sig-frame absolute border-2 border-dashed border-[#C65D9A] ${isSelected ? "selected sig-frame" : ""}`;
    frameEl.dataset.sigId = s.id;
    frameEl.dataset.fieldType = "signature";

    frameEl.style.left = `${(s.x_mm / trimW) * 100}%`;
    frameEl.style.top = `${(s.y_mm / trimH) * 100}%`;
    frameEl.style.width = `${(s.width_mm / trimW) * 100}%`;
    frameEl.style.height = `${(s.height_mm / trimH) * 100}%`;

    let sigImgSrc = "";
    if (activeTrainerForSig) {
      const tr = activeTrainers.find((t) => t.id === activeTrainerForSig);
      if (tr) sigImgSrc = tr.thumbnail_url || tr.signature_url;
    } else if (activeTrainers.length > 0) {
      sigImgSrc = activeTrainers[0].thumbnail_url || activeTrainers[0].signature_url;
    }

    const blendStyle = s.blend_multiply ? "mix-blend-mode: multiply;" : "";
    const scaleVal = (s.scale || 100) / 100.0;

    frameEl.innerHTML = `
      <div class="w-full h-full flex items-end justify-center p-1 overflow-hidden pointer-events-none select-none relative" style="${blendStyle}">
        ${
          sigImgSrc
            ? `<img src="${sigImgSrc}" alt="Signature" class="max-h-full max-w-full object-contain pointer-events-none" style="transform: scale(${scaleVal}); transform-origin: bottom center;">`
            : `<span class="text-[10px] text-[#C65D9A] font-bold flex items-center gap-1 mb-1 pointer-events-none"><i data-lucide="signature" class="w-3.5 h-3.5"></i> ${t("sig_line_placeholder")}</span>`
        }
        <div class="absolute bottom-0 inset-x-2 border-b border-[#C65D9A]/50 pointer-events-none"></div>
      </div>
      <span class="absolute top-0 start-0 bg-[#C65D9A] text-white text-[9px] font-bold px-1.5 py-0.2 rounded-br shadow-xs pointer-events-none opacity-90 truncate max-w-[85%]">${getLocalizedFieldLabel(s)}</span>
      ${isSelected ? renderHandlesHtml() : ""}
    `;

    frameEl.addEventListener("mousedown", (e) => handleFrameMouseDown(e, s.id, "signature"));
    container.appendChild(frameEl);
  });

  lucide.createIcons();
}

function renderHandlesHtml() {
  return `
    <div class="canvas-handle handle-nw" data-handle="nw"></div>
    <div class="canvas-handle handle-n" data-handle="n"></div>
    <div class="canvas-handle handle-ne" data-handle="ne"></div>
    <div class="canvas-handle handle-e" data-handle="e"></div>
    <div class="canvas-handle handle-se" data-handle="se"></div>
    <div class="canvas-handle handle-s" data-handle="s"></div>
    <div class="canvas-handle handle-sw" data-handle="sw"></div>
    <div class="canvas-handle handle-w" data-handle="w"></div>
  `;
}

function handleFrameMouseDown(e, id, type) {
  e.stopPropagation();

  activeFieldId = id;
  activeFieldType = type;

  const handleEl = e.target.closest(".canvas-handle");
  const trimboxContainer = document.getElementById("canvas-trimbox-container");
  const trimboxRect = trimboxContainer.getBoundingClientRect();

  const pageSetup = currentTemplate.page_setup || { width_mm: 297.0, height_mm: 210.0 };
  const trimW = parseFloat(pageSetup.width_mm) || 297.0;
  const trimH = parseFloat(pageSetup.height_mm) || 210.0;

  let field;
  if (type === "text") {
    field = currentTemplate.fields.find((f) => f.id === id);
  } else {
    field = (currentTemplate.signature_frames || []).find((s) => s.id === id);
  }

  if (!field) return;

  if (handleEl) {
    isResizingFrame = true;
    activeResizeHandle = handleEl.dataset.handle;
  } else {
    isDraggingFrame = true;
    activeResizeHandle = null;
  }

  dragStartMeta = {
    mouseX: e.clientX,
    mouseY: e.clientY,
    x_mm: field.x_mm,
    y_mm: field.y_mm,
    w_mm: field.width_mm,
    h_mm: field.height_mm,
    trimW: trimW,
    trimH: trimH,
    boxWidthPx: trimboxRect.width,
    boxHeightPx: trimboxRect.height,
  };

  renderFramesOnCanvas();
  renderInspector();
}

function handleGlobalMouseMove(e) {
  if (!isDraggingFrame && !isResizingFrame) return;
  if (!dragStartMeta || !currentTemplate || !activeFieldId) return;

  const dx_px = e.clientX - dragStartMeta.mouseX;
  const dy_px = e.clientY - dragStartMeta.mouseY;

  const dx_mm = (dx_px / dragStartMeta.boxWidthPx) * dragStartMeta.trimW;
  const dy_mm = (dy_px / dragStartMeta.boxHeightPx) * dragStartMeta.trimH;

  let field;
  if (activeFieldType === "text") {
    field = currentTemplate.fields.find((f) => f.id === activeFieldId);
  } else {
    field = (currentTemplate.signature_frames || []).find((s) => s.id === activeFieldId);
  }

  if (!field) return;

  if (isDraggingFrame) {
    let newX = dragStartMeta.x_mm + dx_mm;
    let newY = dragStartMeta.y_mm + dy_mm;
    newX = Math.max(0, Math.min(dragStartMeta.trimW - field.width_mm, newX));
    newY = Math.max(0, Math.min(dragStartMeta.trimH - field.height_mm, newY));

    field.x_mm = Math.round(newX * 2) / 2.0;
    field.y_mm = Math.round(newY * 2) / 2.0;
  } else if (isResizingFrame) {
    const handle = activeResizeHandle;
    let newX = dragStartMeta.x_mm;
    let newY = dragStartMeta.y_mm;
    let newW = dragStartMeta.w_mm;
    let newH = dragStartMeta.h_mm;

    if (handle.includes("e")) {
      newW = Math.max(15, dragStartMeta.w_mm + dx_mm);
      newW = Math.min(dragStartMeta.trimW - newX, newW);
    }
    if (handle.includes("s")) {
      newH = Math.max(6, dragStartMeta.h_mm + dy_mm);
      newH = Math.min(dragStartMeta.trimH - newY, newH);
    }
    if (handle.includes("w")) {
      const maxDx = dragStartMeta.w_mm - 15;
      const validDx = Math.min(maxDx, Math.max(-dragStartMeta.x_mm, dx_mm));
      newX = dragStartMeta.x_mm + validDx;
      newW = dragStartMeta.w_mm - validDx;
    }
    if (handle.includes("n")) {
      const maxDy = dragStartMeta.h_mm - 6;
      const validDy = Math.min(maxDy, Math.max(-dragStartMeta.y_mm, dy_mm));
      newY = dragStartMeta.y_mm + validDy;
      newH = dragStartMeta.h_mm - validDy;
    }

    field.x_mm = Math.round(newX * 2) / 2.0;
    field.y_mm = Math.round(newY * 2) / 2.0;
    field.width_mm = Math.round(newW * 2) / 2.0;
    field.height_mm = Math.round(newH * 2) / 2.0;
  }

  // Update frame in DOM live
  const frameEl = document.querySelector(`.designer-frame[data-field-id="${activeFieldId}"], .designer-frame[data-sig-id="${activeFieldId}"]`);
  if (frameEl) {
    frameEl.style.left = `${(field.x_mm / dragStartMeta.trimW) * 100}%`;
    frameEl.style.top = `${(field.y_mm / dragStartMeta.trimH) * 100}%`;
    frameEl.style.width = `${(field.width_mm / dragStartMeta.trimW) * 100}%`;
    frameEl.style.height = `${(field.height_mm / dragStartMeta.trimH) * 100}%`;
  }

  // Update inspector geometry inputs live
  const geoX = document.getElementById("insp-geo-x");
  const geoY = document.getElementById("insp-geo-y");
  const geoW = document.getElementById("insp-geo-w");
  const geoH = document.getElementById("insp-geo-h");
  if (geoX) geoX.value = field.x_mm;
  if (geoY) geoY.value = field.y_mm;
  if (geoW) geoW.value = field.width_mm;
  if (geoH) geoH.value = field.height_mm;
}

function handleGlobalMouseUp() {
  if (isDraggingFrame || isResizingFrame) {
    isDraggingFrame = false;
    isResizingFrame = false;
    activeResizeHandle = null;
    dragStartMeta = null;
    renderFramesOnCanvas();
  }
}

function renderInspector() {
  const panel = document.getElementById("designer-inspector-panel");
  if (!panel || !currentTemplate) return;

  if (!activeFieldId) {
    // Template Overview
    const fieldsCount = (currentTemplate.fields || []).length;
    const sigCount = (currentTemplate.signature_frames || []).length;
    const pageSetup = currentTemplate.page_setup || { width_mm: 297.0, height_mm: 210.0, bleed_mm: 3.0 };

    panel.innerHTML = `
      <div class="p-4 border-b border-slate-100 bg-slate-50/50">
        <h3 class="text-xs font-bold text-slate-800 flex items-center gap-2 mb-1">
          <i data-lucide="layers" class="w-4 h-4 text-brand-primary"></i>
          <span>${t("insp_template_settings")}</span>
        </h3>
        <p class="text-[11px] text-slate-400">${t("insp_click_field_hint")}</p>
      </div>

      <div class="p-4 flex flex-col gap-4 text-xs">
        <!-- Always Visible Company & Template Name Inputs -->
        <div class="bg-slate-50 p-3 rounded-2xl border border-slate-200/80 space-y-3">
          <div>
            <label class="block text-[11px] font-bold text-slate-700 mb-1" for="insp-company-input">${t("insp_company_label")}</label>
            <div class="flex items-center gap-1.5">
              <input type="text" id="insp-company-input" list="company-datalist" value="${currentTemplate.company || ""}" onchange="handleTemplateCompanyChange(this.value)" class="flex-1 p-2 rounded-xl border border-slate-200 text-xs bg-white font-semibold focus:border-brand-secondary focus:outline-none">
              <button onclick="promptAddNewCompany()" class="p-2 rounded-xl bg-brand-primary text-white hover:bg-[#003866] transition shrink-0" title="${t("insp_add_company_tip")}">
                <i data-lucide="plus" class="w-3.5 h-3.5"></i>
              </button>
            </div>
          </div>
          <div>
            <label class="block text-[11px] font-bold text-slate-700 mb-1" for="insp-tplname-input">${t("insp_tpl_name_label")}</label>
            <input type="text" id="insp-tplname-input" value="${currentTemplate.name || ""}" oninput="handleTemplateNameChange(this.value)" class="w-full p-2 rounded-xl border border-slate-200 text-xs bg-white font-bold text-brand-primary focus:border-brand-secondary focus:outline-none">
          </div>
          <div class="pt-2 border-t border-slate-200/60 flex justify-between text-[11px]">
            <span class="text-slate-500">${t("insp_trimbox_size")}</span>
            <span class="font-mono font-bold text-brand-primary">${pageSetup.width_mm} × ${pageSetup.height_mm} mm</span>
          </div>
          <div class="flex justify-between text-[11px]">
            <span class="text-slate-500">${t("insp_bleed_detected")}</span>
            <span class="font-mono font-bold text-emerald-600">${pageSetup.bleed_mm} mm</span>
          </div>
        </div>

        <!-- 4 Semantic Quick Field Adder Buttons -->
        <div>
          <label class="block font-bold text-slate-700 mb-2">${t("insp_add_smart_fields")}</label>
          <div class="flex flex-col gap-1.5">
            <button onclick="addOrFocusTraineeNameField()" class="w-full py-2 px-3 rounded-xl bg-brand-primary hover:bg-[#003866] text-white font-bold flex items-center justify-between text-xs transition shadow-xs">
              <span class="flex items-center gap-2"><i data-lucide="user" class="w-4 h-4 text-brand-secondary"></i> ${t("btn_add_name_field")}</span>
              <span class="text-[10px] text-blue-200 font-mono">trainee_name</span>
            </button>
            <button onclick="addOrFocusTrainingDateField()" class="w-full py-2 px-3 rounded-xl bg-slate-700 hover:bg-slate-800 text-white font-bold flex items-center justify-between text-xs transition shadow-xs">
              <span class="flex items-center gap-2"><i data-lucide="calendar" class="w-4 h-4 text-emerald-400"></i> ${t("btn_add_date_field")}</span>
              <span class="text-[10px] text-slate-300 font-mono">training_date</span>
            </button>
            <button onclick="addOrFocusTrainerSignatureField()" class="w-full py-2 px-3 rounded-xl bg-pink-700 hover:bg-pink-800 text-white font-bold flex items-center justify-between text-xs transition shadow-xs">
              <span class="flex items-center gap-2"><i data-lucide="pen-tool" class="w-4 h-4 text-pink-300"></i> ${t("btn_add_sig_field")}</span>
              <span class="text-[10px] text-pink-200 font-mono">trainer_signature</span>
            </button>
            <button onclick="addCustomTextField()" class="w-full py-2 px-3 rounded-xl bg-brand-secondary hover:bg-[#3b96cb] text-white font-bold flex items-center justify-between text-xs transition shadow-xs">
              <span class="flex items-center gap-2"><i data-lucide="type" class="w-4 h-4"></i> ${t("btn_add_custom_field")}</span>
              <span class="text-[10px] text-white/80 font-mono">custom_text</span>
            </button>
          </div>
        </div>

        <div>
          <h4 class="font-bold text-slate-700 mb-2 flex items-center justify-between">
            <span>${t("insp_fields_in_template")} (${fieldsCount + sigCount}):</span>
          </h4>
          <div class="space-y-1.5 max-h-56 overflow-y-auto">
            ${(currentTemplate.fields || []).map((f) => `
              <div onclick="selectFieldFromList('${f.id}', 'text')" class="p-2 rounded-xl border border-slate-200/80 hover:border-brand-secondary bg-white hover:bg-blue-50/30 cursor-pointer flex items-center justify-between transition">
                <div class="flex items-center gap-2 min-w-0">
                  <i data-lucide="type" class="w-3.5 h-3.5 text-[#49A8DE] shrink-0"></i>
                  <span class="font-semibold text-slate-800 truncate">${getLocalizedFieldLabel(f)}</span>
                </div>
                <span class="text-[10px] text-slate-400 font-mono">${f.x_mm},${f.y_mm}</span>
              </div>
            `).join("")}

            ${(currentTemplate.signature_frames || []).map((s) => `
              <div onclick="selectFieldFromList('${s.id}', 'signature')" class="p-2 rounded-xl border border-slate-200/80 hover:border-brand-accent bg-white hover:bg-pink-50/30 cursor-pointer flex items-center justify-between transition">
                <div class="flex items-center gap-2 min-w-0">
                  <i data-lucide="pen-tool" class="w-3.5 h-3.5 text-[#C65D9A] shrink-0"></i>
                  <span class="font-semibold text-slate-800 truncate">${getLocalizedFieldLabel(s)}</span>
                </div>
                <span class="text-[10px] text-slate-400 font-mono">${s.x_mm},${s.y_mm}</span>
              </div>
            `).join("")}
          </div>
        </div>

        <div class="pt-2 border-t border-slate-100 flex flex-col gap-2">
          <button onclick="renderLivePdfPreview()" class="w-full py-2.5 px-3 rounded-xl bg-brand-primary hover:bg-[#003866] text-white font-bold flex items-center justify-center gap-1.5 shadow-sm transition">
            <i data-lucide="sparkles" class="w-4 h-4 text-brand-secondary"></i>
            <span>${t("btn_preview_engine")}</span>
          </button>
        </div>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  // Active Frame Selected
  if (activeFieldType === "text") {
    const field = currentTemplate.fields.find((f) => f.id === activeFieldId);
    if (!field) return;

    panel.innerHTML = `
      <div class="p-4 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-blue-100 text-brand-secondary flex items-center justify-center">
            <i data-lucide="type" class="w-4 h-4"></i>
          </div>
          <div>
            <h3 class="text-xs font-bold text-slate-800 truncate">${getLocalizedFieldLabel(field)}</h3>
            <span class="text-[9px] px-1.5 py-0.2 rounded bg-blue-50 text-brand-secondary font-mono">${t("insp_badge_text_frame")}</span>
          </div>
        </div>
        <button onclick="deselectActiveField()" class="text-slate-400 hover:text-slate-600 p-1">
          <i data-lucide="x" class="w-4 h-4"></i>
        </button>
      </div>

      <div class="p-4 flex-1 overflow-y-auto flex flex-col gap-4 text-xs">
        
        <!-- Field Label & Preview Text -->
        <div>
          <label class="block font-bold text-slate-700 mb-1">${t("insp_label_preview_text")}</label>
          <textarea id="insp-sample-text" rows="2" class="w-full p-2.5 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-brand-secondary/30 focus:border-brand-secondary resize-none" oninput="updateActiveFieldText(this.value)">${getLocalizedSampleText(field)}</textarea>
        </div>

        <!-- Render Live PDF Preview Button -->
        <button onclick="renderLivePdfPreview()" class="w-full py-2 px-3 rounded-xl bg-brand-primary hover:bg-[#003866] text-white font-bold flex items-center justify-center gap-2 shadow-sm transition">
          <i data-lucide="sparkles" class="w-4 h-4 text-brand-secondary"></i>
          <span>${t("btn_preview_engine")}</span>
        </button>

        <!-- Typography: Dual Fonts (Arabic & English) -->
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block font-bold text-slate-700 mb-1">${t("insp_font_ar")}</label>
            <select id="insp-font-ar" class="w-full p-2 rounded-xl border border-slate-200 text-xs focus:border-brand-secondary" onchange="updateActiveField('font_family', this.value)">
              ${activeFonts.map((ft) => `
                <option value="${ft.name}" ${field.font_family === ft.name ? "selected" : ""}>${ft.name}</option>
              `).join("")}
            </select>
          </div>
          <div>
            <label class="block font-bold text-slate-700 mb-1">${t("insp_font_en")}</label>
            <select id="insp-font-en" class="w-full p-2 rounded-xl border border-slate-200 text-xs focus:border-brand-secondary" onchange="updateActiveField('english_font', this.value)">
              <option value="">${t("insp_same_as_ar")}</option>
              ${activeFonts.map((ft) => `
                <option value="${ft.name}" ${field.english_font === ft.name ? "selected" : ""}>${ft.name}</option>
              `).join("")}
            </select>
          </div>
        </div>

        <!-- Font Size & Auto-Shrink -->
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block font-bold text-slate-700 mb-1">${t("insp_font_size")}</label>
            <input type="number" id="insp-font-size" value="${field.font_size || 24}" min="6" max="150" step="0.5" class="w-full p-2 rounded-xl border border-slate-200 text-xs focus:border-brand-secondary font-mono" oninput="updateActiveField('font_size', parseFloat(this.value))">
          </div>
          <div>
            <label class="block font-bold text-slate-700 mb-1">${t("insp_auto_shrink")}</label>
            <input type="number" id="insp-max-shrink" value="${field.max_shrink_percent !== undefined ? field.max_shrink_percent : 20}" min="0" max="60" step="1" class="w-full p-2 rounded-xl border border-slate-200 text-xs focus:border-brand-secondary font-mono" oninput="updateActiveField('max_shrink_percent', parseFloat(this.value))">
          </div>
        </div>

        <!-- Baseline Offset -->
        <div>
          <label class="block font-bold text-slate-700 mb-1">${t("insp_baseline_offset")}</label>
          <input type="number" id="insp-baseline" value="${field.baseline_offset_mm || 0}" step="0.5" class="w-full p-2 rounded-xl border border-slate-200 text-xs focus:border-brand-secondary font-mono" oninput="updateActiveField('baseline_offset_mm', parseFloat(this.value))">
        </div>

        <!-- Center Alignment in Page Buttons -->
        <div>
          <label class="block font-bold text-slate-700 mb-1">${t("insp_center_page")}</label>
          <div class="grid grid-cols-2 gap-2">
            <button type="button" onclick="alignActiveFieldToCenterHorizontally()" class="py-1.5 px-2 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 font-bold flex items-center justify-center gap-1.5 transition text-[11px]" title="${t("insp_center_h")}">
              <i data-lucide="align-horizontal-space-around" class="w-3.5 h-3.5 text-brand-secondary"></i>
              <span>${t("insp_center_h")}</span>
            </button>
            <button type="button" onclick="alignActiveFieldToCenterVertically()" class="py-1.5 px-2 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 font-bold flex items-center justify-center gap-1.5 transition text-[11px]" title="${t("insp_center_v")}">
              <i data-lucide="align-vertical-space-around" class="w-3.5 h-3.5 text-brand-secondary"></i>
              <span>${t("insp_center_v")}</span>
            </button>
          </div>
        </div>

        <!-- 9-Point Alignment Grid -->
        <div>
          <label class="block font-bold text-slate-700 mb-1">${t("insp_align_9point")}</label>
          <div class="grid grid-cols-3 gap-1.5 bg-slate-50 p-2 rounded-xl border border-slate-200">
            ${["top", "middle", "bottom"].map((v) => 
              ["right", "center", "left"].map((h) => {
                const isActive = (field.horizontal_align === h || (!field.horizontal_align && h === "center")) && 
                                 (field.vertical_align === v || (!field.vertical_align && v === "middle"));
                const hLabel = h === "right" ? t("align_right") : h === "center" ? t("align_center") : t("align_left");
                const vLabel = v === "top" ? t("valign_top") : v === "middle" ? t("valign_middle") : t("valign_bottom");
                return `
                  <button type="button" onclick="setAlignment('${h}', '${v}')" class="py-1 px-2 rounded text-[11px] font-bold border transition ${
                    isActive ? "bg-brand-primary text-white border-brand-primary shadow-xs" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-100"
                  }">
                    ${hLabel} / ${vLabel}
                  </button>
                `;
              }).join("")
            ).join("")}
          </div>
        </div>

        <!-- Print Colors: CMYK & Hex -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="font-bold text-slate-700">${t("insp_print_color")}</label>
            <button type="button" onclick="setPurePrintBlack()" class="text-[10px] px-2 py-0.5 rounded-full bg-slate-900 text-white font-bold hover:bg-black transition flex items-center gap-1 shadow-xs" title="${t("insp_pure_black_tip")}">
              <i data-lucide="check" class="w-3 h-3 text-emerald-400"></i>
              <span>${t("insp_pure_black")}</span>
            </button>
          </div>

          <div class="grid grid-cols-4 gap-1.5 mb-2">
            <div>
              <span class="text-[10px] text-slate-400 font-mono block">C %</span>
              <input type="number" id="cmyk-c" min="0" max="100" value="${getCmykVal(field.color, 'c')}" class="w-full p-1.5 rounded-lg border border-slate-200 text-xs font-mono text-center" oninput="updateCmykColor()">
            </div>
            <div>
              <span class="text-[10px] text-slate-400 font-mono block">M %</span>
              <input type="number" id="cmyk-m" min="0" max="100" value="${getCmykVal(field.color, 'm')}" class="w-full p-1.5 rounded-lg border border-slate-200 text-xs font-mono text-center" oninput="updateCmykColor()">
            </div>
            <div>
              <span class="text-[10px] text-slate-400 font-mono block">Y %</span>
              <input type="number" id="cmyk-y" min="0" max="100" value="${getCmykVal(field.color, 'y')}" class="w-full p-1.5 rounded-lg border border-slate-200 text-xs font-mono text-center" oninput="updateCmykColor()">
            </div>
            <div>
              <span class="text-[10px] text-slate-400 font-mono block">K %</span>
              <input type="number" id="cmyk-k" min="0" max="100" value="${getCmykVal(field.color, 'k')}" class="w-full p-1.5 rounded-lg border border-slate-200 text-xs font-mono text-center font-bold text-slate-900" oninput="updateCmykColor()">
            </div>
          </div>

          <div class="flex items-center gap-2">
            <input type="color" id="hex-color-picker" value="${getHexVal(field.color)}" class="w-8 h-8 rounded-lg cursor-pointer border border-slate-200 p-0.5" onchange="updateHexColor(this.value)">
            <input type="text" id="hex-color-text" value="${getHexVal(field.color)}" class="flex-1 p-1.5 rounded-lg border border-slate-200 text-xs font-mono" onchange="updateHexColor(this.value)">
          </div>
        </div>

        <!-- Direction & Lock -->
        <div class="grid grid-cols-2 gap-2 items-center">
          <div>
            <label class="block font-bold text-slate-700 mb-1">${t("insp_text_direction")}</label>
            <select id="insp-direction" class="w-full p-2 rounded-xl border border-slate-200 text-xs focus:border-brand-secondary" onchange="updateActiveField('direction', this.value)">
              <option value="auto" ${field.direction === "auto" ? "selected" : ""}>${t("insp_dir_auto")}</option>
              <option value="rtl" ${field.direction === "rtl" ? "selected" : ""}>${t("insp_dir_rtl")}</option>
              <option value="ltr" ${field.direction === "ltr" ? "selected" : ""}>${t("insp_dir_ltr")}</option>
            </select>
          </div>
          <div class="pt-4">
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" ${field.is_locked ? "checked" : ""} onchange="updateActiveField('is_locked', this.checked)" class="rounded text-brand-secondary">
              <span class="font-bold text-slate-700 text-[11px]">${t("insp_lock_field")}</span>
            </label>
          </div>
        </div>

        <!-- Frame Geometry Coordinates (TrimBox Origin mm) -->
        <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
          <label class="block font-bold text-slate-700 mb-2">${t("insp_coords_trimbox")}</label>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span class="text-[10px] text-slate-400 font-mono">X (mm):</span>
              <input type="number" id="insp-geo-x" value="${field.x_mm}" step="0.5" class="w-full p-1.5 rounded-lg border border-slate-200 font-mono text-xs" oninput="updateActiveField('x_mm', parseFloat(this.value))">
            </div>
            <div>
              <span class="text-[10px] text-slate-400 font-mono">Y (mm):</span>
              <input type="number" id="insp-geo-y" value="${field.y_mm}" step="0.5" class="w-full p-1.5 rounded-lg border border-slate-200 font-mono text-xs" oninput="updateActiveField('y_mm', parseFloat(this.value))">
            </div>
            <div>
              <span class="text-[10px] text-slate-400 font-mono">${t("insp_width_mm")}</span>
              <input type="number" id="insp-geo-w" value="${field.width_mm}" step="0.5" class="w-full p-1.5 rounded-lg border border-slate-200 font-mono text-xs" oninput="updateActiveField('width_mm', parseFloat(this.value))">
            </div>
            <div>
              <span class="text-[10px] text-slate-400 font-mono">${t("insp_height_mm")}</span>
              <input type="number" id="insp-geo-h" value="${field.height_mm}" step="0.5" class="w-full p-1.5 rounded-lg border border-slate-200 font-mono text-xs" oninput="updateActiveField('height_mm', parseFloat(this.value))">
            </div>
          </div>
        </div>

        <!-- Delete Frame -->
        <div class="pt-2">
          <button onclick="handleDeleteActiveField()" class="w-full py-2 px-3 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold border border-rose-200 flex items-center justify-center gap-1.5 transition">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            <span>${t("insp_delete_field")}</span>
          </button>
        </div>

      </div>
    `;
    lucide.createIcons();
    return;
  }

  // Active Signature Frame Selected
  if (activeFieldType === "signature") {
    const sFrame = (currentTemplate.signature_frames || []).find((s) => s.id === activeFieldId);
    if (!sFrame) return;

    panel.innerHTML = `
      <div class="p-4 border-b border-slate-100 bg-pink-50/50 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-pink-100 text-[#C65D9A] flex items-center justify-center">
            <i data-lucide="pen-tool" class="w-4 h-4"></i>
          </div>
          <div>
            <h3 class="text-xs font-bold text-slate-800">${getLocalizedFieldLabel(sFrame)}</h3>
            <span class="text-[9px] px-1.5 py-0.2 rounded bg-pink-100 text-[#C65D9A] font-mono">${t("insp_badge_sig_frame")}</span>
          </div>
        </div>
        <button onclick="deselectActiveField()" class="text-slate-400 hover:text-slate-600 p-1">
          <i data-lucide="x" class="w-4 h-4"></i>
        </button>
      </div>

      <div class="p-4 flex-1 overflow-y-auto flex flex-col gap-4 text-xs">
        
        <!-- Test Trainer Signature Preview Selector -->
        <div>
          <label class="block font-bold text-slate-700 mb-1">${t("insp_preview_trainer")}</label>
          <select id="insp-sig-trainer" class="w-full p-2 rounded-xl border border-slate-200 text-xs focus:border-brand-accent" onchange="handleSigTrainerChange(this.value)">
            ${activeTrainers.map((tr) => `
              <option value="${tr.id}" ${activeTrainerForSig === tr.id ? "selected" : ""}>${tr.name} (${tr.is_vector ? (currentLang === "ar" ? "ملف متجهي" : "Vector PDF") : "PNG"})</option>
            `).join("")}
          </select>
        </div>

        <!-- Render Live PDF Preview Button -->
        <button onclick="renderLivePdfPreview()" class="w-full py-2 px-3 rounded-xl bg-brand-primary hover:bg-[#003866] text-white font-bold flex items-center justify-center gap-2 shadow-sm transition">
          <i data-lucide="sparkles" class="w-4 h-4 text-brand-secondary"></i>
          <span>${t("btn_preview_engine")}</span>
        </button>

        <!-- Center Alignment in Page Buttons -->
        <div>
          <label class="block font-bold text-slate-700 mb-1">${t("insp_center_sig_page")}</label>
          <div class="grid grid-cols-2 gap-2">
            <button type="button" onclick="alignActiveFieldToCenterHorizontally()" class="py-1.5 px-2 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 font-bold flex items-center justify-center gap-1.5 transition text-[11px]" title="${t("insp_center_h")}">
              <i data-lucide="align-horizontal-space-around" class="w-3.5 h-3.5 text-brand-secondary"></i>
              <span>${t("insp_center_h")}</span>
            </button>
            <button type="button" onclick="alignActiveFieldToCenterVertically()" class="py-1.5 px-2 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 font-bold flex items-center justify-center gap-1.5 transition text-[11px]" title="${t("insp_center_v")}">
              <i data-lucide="align-vertical-space-around" class="w-3.5 h-3.5 text-brand-secondary"></i>
              <span>${t("insp_center_v")}</span>
            </button>
          </div>
        </div>

        <!-- Anchor Mode & Baseline Offset -->
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block font-bold text-slate-700 mb-1">${t("insp_anchor_point")}</label>
            <select id="insp-anchor-mode" class="w-full p-2 rounded-xl border border-slate-200 text-xs focus:border-brand-accent" onchange="updateActiveField('anchor_mode', this.value)">
              <option value="bottom_center" selected>${t("insp_anchor_bottom_center")}</option>
              <option value="middle_center">${t("insp_anchor_middle_center")}</option>
            </select>
          </div>
          <div>
            <label class="block font-bold text-slate-700 mb-1">${t("insp_baseline_offset")}</label>
            <input type="number" id="insp-sig-baseline" value="${sFrame.baseline_offset_mm || 0}" step="0.5" class="w-full p-2 rounded-xl border border-slate-200 text-xs font-mono" oninput="updateActiveField('baseline_offset_mm', parseFloat(this.value))">
          </div>
        </div>

        <!-- Scale Factor Slider -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="font-bold text-slate-700">${t("insp_scale_factor")}</label>
            <span id="insp-sig-scale-badge" class="font-mono text-brand-accent font-bold">${sFrame.scale || 100}%</span>
          </div>
          <input type="range" min="30" max="250" value="${sFrame.scale || 100}" class="w-full accent-[#C65D9A]" oninput="updateSigScale(this.value)">
        </div>

        <!-- Multiply Blend Mode Toggle -->
        <div>
          <label class="flex items-center gap-2 cursor-pointer select-none bg-slate-50 p-3 rounded-xl border border-slate-200">
            <input type="checkbox" ${sFrame.blend_multiply ? "checked" : ""} onchange="updateActiveField('blend_multiply', this.checked)" class="rounded text-[#C65D9A] accent-[#C65D9A]">
            <div>
              <span class="font-bold text-slate-700 block text-[11px]">${t("insp_multiply_blend")}</span>
              <span class="text-[10px] text-slate-400 block">${t("insp_multiply_hint")}</span>
            </div>
          </label>
        </div>

        <!-- Frame Geometry Coordinates -->
        <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
          <label class="block font-bold text-slate-700 mb-2">${t("insp_sig_coords")}</label>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span class="text-[10px] text-slate-400 font-mono">X (mm):</span>
              <input type="number" id="insp-geo-x" value="${sFrame.x_mm}" step="0.5" class="w-full p-1.5 rounded-lg border border-slate-200 font-mono text-xs" oninput="updateActiveField('x_mm', parseFloat(this.value))">
            </div>
            <div>
              <span class="text-[10px] text-slate-400 font-mono">Y (mm):</span>
              <input type="number" id="insp-geo-y" value="${sFrame.y_mm}" step="0.5" class="w-full p-1.5 rounded-lg border border-slate-200 font-mono text-xs" oninput="updateActiveField('y_mm', parseFloat(this.value))">
            </div>
            <div>
              <span class="text-[10px] text-slate-400 font-mono">${t("insp_width_mm")}</span>
              <input type="number" id="insp-geo-w" value="${sFrame.width_mm}" step="0.5" class="w-full p-1.5 rounded-lg border border-slate-200 font-mono text-xs" oninput="updateActiveField('width_mm', parseFloat(this.value))">
            </div>
            <div>
              <span class="text-[10px] text-slate-400 font-mono">${t("insp_height_mm")}</span>
              <input type="number" id="insp-geo-h" value="${sFrame.height_mm}" step="0.5" class="w-full p-1.5 rounded-lg border border-slate-200 font-mono text-xs" oninput="updateActiveField('height_mm', parseFloat(this.value))">
            </div>
          </div>
        </div>

        <!-- Delete Frame -->
        <div class="pt-2">
          <button onclick="handleDeleteActiveField()" class="w-full py-2 px-3 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold border border-rose-200 flex items-center justify-center gap-1.5 transition">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            <span>${t("insp_delete_sig")}</span>
          </button>
        </div>

      </div>
    `;
    lucide.createIcons();
    return;
  }
}

function selectFieldFromList(id, type) {
  activeFieldId = id;
  activeFieldType = type;
  renderFramesOnCanvas();
  renderInspector();
}

function deselectActiveField() {
  activeFieldId = null;
  activeFieldType = null;
  renderFramesOnCanvas();
  renderInspector();
}

function updateActiveFieldText(val) {
  if (!currentTemplate || !activeFieldId || activeFieldType !== "text") return;
  const f = currentTemplate.fields.find((field) => field.id === activeFieldId);
  if (!f) return;
  f.default_text = val;
  const frameEl = document.querySelector(`.designer-frame[data-field-id="${activeFieldId}"] span`);
  if (frameEl) frameEl.textContent = val || getLocalizedSampleText(f);
}

function updateActiveField(prop, val) {
  if (!currentTemplate || !activeFieldId) return;
  let target;
  if (activeFieldType === "text") {
    target = currentTemplate.fields.find((f) => f.id === activeFieldId);
  } else {
    target = (currentTemplate.signature_frames || []).find((s) => s.id === activeFieldId);
  }
  if (!target) return;
  target[prop] = val;
  pushHistoryState();
  renderFramesOnCanvas();
}

function updateSigScale(val) {
  const num = parseInt(val, 10) || 100;
  updateActiveField("scale", num);
  const badge = document.getElementById("insp-sig-scale-badge");
  if (badge) badge.textContent = `${num}%`;
}

function handleSigTrainerChange(trId) {
  activeTrainerForSig = trId;
  renderFramesOnCanvas();
}

function setAlignment(h, v) {
  if (!currentTemplate || !activeFieldId || activeFieldType !== "text") return;
  const f = currentTemplate.fields.find((field) => field.id === activeFieldId);
  if (!f) return;
  f.horizontal_align = h;
  f.vertical_align = v;
  renderFramesOnCanvas();
  renderInspector();
}

function setPurePrintBlack() {
  if (!currentTemplate || !activeFieldId || activeFieldType !== "text") return;
  const f = currentTemplate.fields.find((field) => field.id === activeFieldId);
  if (!f) return;
  f.color = { c: 0, m: 0, y: 0, k: 100 };
  renderFramesOnCanvas();
  renderInspector();
  showToast(t("toast_pure_black"), "success");
}

function updateCmykColor() {
  if (!currentTemplate || !activeFieldId || activeFieldType !== "text") return;
  const f = currentTemplate.fields.find((field) => field.id === activeFieldId);
  if (!f) return;
  const c = parseInt(document.getElementById("cmyk-c").value, 10) || 0;
  const m = parseInt(document.getElementById("cmyk-m").value, 10) || 0;
  const y = parseInt(document.getElementById("cmyk-y").value, 10) || 0;
  const k = parseInt(document.getElementById("cmyk-k").value, 10) || 0;

  f.color = { c, m, y, k };
  renderFramesOnCanvas();
}

function updateHexColor(hexVal) {
  if (!currentTemplate || !activeFieldId || activeFieldType !== "text") return;
  const f = currentTemplate.fields.find((field) => field.id === activeFieldId);
  if (!f) return;
  f.color = hexVal;
  renderFramesOnCanvas();
  renderInspector();
}

function getCmykVal(color, component) {
  if (color && typeof color === "object" && color[component] !== undefined) {
    return color[component];
  }
  return 0;
}

function getHexVal(color) {
  if (typeof color === "string" && color.startsWith("#")) {
    return color;
  }
  if (color && color.k === 100 && !color.c && !color.m && !color.y) {
    return "#000000";
  }
  return "#004B87";
}

function formatColorForCss(color) {
  if (!color) return "#000000";
  if (typeof color === "string") return color;
  if (color.c !== undefined && color.k !== undefined) {
    const c = (parseFloat(color.c) || 0) / 100.0;
    const m = (parseFloat(color.m) || 0) / 100.0;
    const y = (parseFloat(color.y) || 0) / 100.0;
    const k = (parseFloat(color.k) || 0) / 100.0;
    const r = Math.round(255 * (1 - c) * (1 - k));
    const g = Math.round(255 * (1 - m) * (1 - k));
    const b = Math.round(255 * (1 - y) * (1 - k));
    return `rgb(${r}, ${g}, ${b})`;
  }
  if (color.r !== undefined) {
    return `rgb(${color.r}, ${color.g}, ${color.b})`;
  }
  return "#004B87";
}

function mapAlignToCss(align) {
  if (align === "center") return "center";
  if (align === "right") return "flex-end";
  if (align === "left") return "flex-start";
  return "center";
}

function mapVAlignToCss(valign) {
  if (valign === "top") return "flex-start";
  if (valign === "bottom") return "flex-end";
  return "center";
}

function handleDeleteActiveField() {
  if (!confirm(t("confirm_delete_field"))) return;
  if (!currentTemplate || !activeFieldId) return;

  if (activeFieldType === "text") {
    currentTemplate.fields = (currentTemplate.fields || []).filter((f) => f.id !== activeFieldId);
  } else {
    currentTemplate.signature_frames = (currentTemplate.signature_frames || []).filter((s) => s.id !== activeFieldId);
  }

  activeFieldId = null;
  activeFieldType = null;
  pushHistoryState();
  renderFramesOnCanvas();
  renderInspector();
  showToast(t("toast_field_deleted"), "info");
}

function addNewTextFrame() {
  if (!currentTemplate) return;
  const newId = `field_${Date.now().toString(36)}`;
  const pageSetup = currentTemplate.page_setup || { width_mm: 297.0, height_mm: 210.0 };
  const trimW = parseFloat(pageSetup.width_mm) || 297.0;
  const trimH = parseFloat(pageSetup.height_mm) || 210.0;

  const newField = {
    id: newId,
    label: "حقل إضافي",
    default_text: "نص حقل جديد",
    x_mm: Math.round((trimW / 4) * 2) / 2,
    y_mm: Math.round((trimH / 2) * 2) / 2,
    width_mm: 120.0,
    height_mm: 16.0,
    font_family: activeFonts.length > 0 ? activeFonts[0].name : "Cairo Regular",
    english_font: activeFonts.length > 0 ? activeFonts[0].name : "Cairo Regular",
    font_size: 18.0,
    color: "#1E293B",
    horizontal_align: "center",
    vertical_align: "middle",
    baseline_offset_mm: 0.0,
    max_shrink_percent: 20.0,
    direction: "auto",
    is_locked: false,
  };

  currentTemplate.fields = currentTemplate.fields || [];
  currentTemplate.fields.push(newField);
  activeFieldId = newId;
  activeFieldType = "text";

  pushHistoryState();
  renderFramesOnCanvas();
  renderInspector();
  showToast(t("toast_field_added_custom"), "success");
}

function addNewSignatureFrame() {
  if (!currentTemplate) return;
  currentTemplate.signature_frames = currentTemplate.signature_frames || [];
  const newId = `sig_${Date.now().toString(36)}`;
  const pageSetup = currentTemplate.page_setup || { width_mm: 297.0, height_mm: 210.0 };
  const trimW = parseFloat(pageSetup.width_mm) || 297.0;
  const trimH = parseFloat(pageSetup.height_mm) || 210.0;

  const newSig = {
    id: newId,
    label: "توقيع المدرب",
    x_mm: Math.round((trimW * 0.65) * 2) / 2,
    y_mm: Math.round((trimH * 0.65) * 2) / 2,
    width_mm: 68.0,
    height_mm: 30.0,
    baseline_offset_mm: 0.0,
    anchor_mode: "bottom_center",
    scale: 100.0,
    blend_multiply: true,
  };

  currentTemplate.signature_frames.push(newSig);
  activeFieldId = newId;
  activeFieldType = "signature";

  pushHistoryState();
  renderFramesOnCanvas();
  renderInspector();
  showToast(t("toast_field_added_sig"), "success");
}

async function handleBasePdfUpload(files) {
  if (!files || files.length === 0) return;
  const file = files[0];

  const overlay = document.getElementById("canvas-loading-overlay");
  const overlayText = document.getElementById("canvas-loading-text");
  if (overlay) {
    overlayText.textContent = t("overlay_pdf_inspecting");
    overlay.classList.remove("hidden");
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/templates/upload-base", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "فشل معالجة ملف PDF");
    }

    const data = await res.json();

    const cleanName = file.name.replace(/\.pdf$/i, "");
    currentTemplate = {
      name: cleanName,
      company: (currentTemplate && currentTemplate.company) ? currentTemplate.company : "",
      fields: [],
      signature_frames: [],
      base_pdf_filename: data.filename,
      base_pdf_url: data.base_pdf_url,
      base_preview_url: data.preview_url,
      boxes_metadata: data.boxes,
      page_setup: data.page_setup,
    };
    delete currentTemplate.id;
    activeFieldId = null;
    activeFieldType = null;

    const nameInput = document.getElementById("designer-template-name");
    if (nameInput) nameInput.value = cleanName;

    pushHistoryState();
    updatePrepressBadges();
    fitCanvasToScreen();
    renderInspector();

    showToast(t("toast_pdf_inspected"), "success");
  } catch (err) {
    console.error("Base PDF upload error:", err);
    showToast(err.message, "error");
  } finally {
    if (overlay) overlay.classList.add("hidden");
    lucide.createIcons();
  }
}

async function renderLivePdfPreview() {
  if (!currentTemplate) return;

  const overlay = document.getElementById("canvas-loading-overlay");
  const overlayText = document.getElementById("canvas-loading-text");
  if (overlay) {
    overlayText.textContent = t("overlay_rendering_300dpi");
    overlay.classList.remove("hidden");
  }

  const sampleRecordData = {};
  (currentTemplate.fields || []).forEach((f) => {
    sampleRecordData[f.id] = getLocalizedSampleText(f);
  });

  const payload = {
    template_config: currentTemplate,
    record_data: sampleRecordData,
    trainer_id: activeTrainerForSig || (activeTrainers.length > 0 ? activeTrainers[0].id : null),
    show_trim_guide: showGuides,
    dpi: 150,
  };

  try {
    const res = await fetch("/api/preview-certificate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "فشل توليد المعاينة");
    }

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);

    const baseImg = document.getElementById("canvas-base-img");
    if (baseImg) {
      baseImg.src = objectUrl;
    }

    showToast(t("toast_rendered_300dpi"), "success");
  } catch (err) {
    console.error("Live render error:", err);
    showToast(err.message, "error");
  } finally {
    if (overlay) overlay.classList.add("hidden");
    lucide.createIcons();
  }
}

async function handleSaveCurrentTemplate() {
  if (!currentTemplate) return;

  const saveBtn = document.getElementById("btn-save-template");
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.classList.add("opacity-60");
  }

  const compInput = document.getElementById("designer-template-company");
  if (compInput && currentTemplate) {
    currentTemplate.company = compInput.value.trim();
  }

  try {
    const res = await fetch("/api/templates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentTemplate),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "فشل حفظ القالب");
    }

    const data = await res.json();
    currentTemplate = data.template;
    showToast(t("toast_tpl_saved"), "success");
    await loadDesignerTemplates();
    await fetchCompanies();
    await fetchOperatorTemplates();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.classList.remove("opacity-60");
    }
  }
}

async function handleDuplicateCurrentTemplate() {
  if (!currentTemplate || !currentTemplate.id) return;
  try {
    const res = await fetch(`/api/templates/${currentTemplate.id}/duplicate`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("فشل نسخ القالب");
    const data = await res.json();
    currentTemplate = data.template;
    showToast(t("toast_tpl_duplicated"), "success");
    await loadDesignerTemplates();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleDeleteCurrentTemplate() {
  if (!currentTemplate || !currentTemplate.id) {
    showToast(t("toast_tpl_no_saved"), "warning");
    return;
  }
  const tplTitle = currentTemplate.name || currentTemplate.id;
  const isConfirmed = confirm(currentLang === "ar" ? `هل أنت متأكد من حذف القالب "${tplTitle}" نهائياً؟` : `Are you sure you want to permanently delete Program WorkBook "${tplTitle}"?`);
  if (!isConfirmed) return;

  try {
    const res = await fetch(`/api/templates/${encodeURIComponent(currentTemplate.id)}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "فشل حذف القالب");
    }

    showToast(t("toast_tpl_deleted"), "success");
    currentTemplate = null;
    activeFieldId = null;
    activeFieldType = null;

    const framesLayer = document.getElementById("canvas-frames-layer");
    if (framesLayer) framesLayer.innerHTML = "";
    const baseImg = document.getElementById("canvas-base-img");
    if (baseImg) baseImg.src = "";

    await loadDesignerTemplates();
    if (typeof fetchOperatorTemplates === "function") {
      await fetchOperatorTemplates();
    }
  } catch (err) {
    console.error("Delete template error:", err);
    showToast(err.message, "error");
  }
}

function exportTemplateJson() {
  if (!currentTemplate) return;
  const compInput = document.getElementById("designer-template-company");
  if (compInput) {
    currentTemplate.company = compInput.value.trim();
  }
  const jsonStr = JSON.stringify(currentTemplate, null, 2);
  const blob = new Blob([jsonStr], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${(currentTemplate.name || "template").replace(/\s+/g, "_")}.json`;
  a.click();
  URL.revokeObjectURL(url);
  showToast(t("toast_tpl_exported"), "info");
}

function importTemplateJson(files) {
  if (!files || files.length === 0) return;
  const file = files[0];
  const reader = new FileReader();
  reader.onload = async (e) => {
    try {
      const parsed = JSON.parse(e.target.result);
      if (!parsed.fields && !parsed.page_setup) {
        throw new Error("ملف JSON غير صالح كقالب شهادة");
      }
      delete parsed.id; // generate fresh id
      currentTemplate = parsed;
      await handleSaveCurrentTemplate();
      showToast(t("toast_tpl_imported"), "success");
    } catch (err) {
      showToast(err.message, "error");
    }
  };
  reader.readAsText(file);
}

// ==========================================================
// Trainer Profiles Manager Engine
// ==========================================================
function openTrainersModal(view = "list") {
  document.getElementById("trainers-modal").classList.remove("hidden");
  if (view === "new") {
    showTrainerForm();
  } else {
    hideTrainerForm();
    fetchTrainers();
  }
}

function closeTrainersModal() {
  document.getElementById("trainers-modal").classList.add("hidden");
  hideTrainerForm();
}

function showTrainerForm(trainer = null) {
  document.getElementById("trainers-list-container").classList.add("hidden");
  document.getElementById("trainer-form-container").classList.remove("hidden");
  document.getElementById("btn-add-trainer-view").classList.add("hidden");

  const titleEl = document.getElementById("trainer-form-title");
  const saveBtn = document.getElementById("btn-save-trainer");

  // Reset preview
  const previewImg = document.getElementById("trainer-sig-preview-img");
  const placeholder = document.getElementById("trainer-sig-placeholder");
  const trimDetails = document.getElementById("sig-trim-details");
  const fileInput = document.getElementById("trainer-sig-file");
  fileInput.value = "";
  trimDetails.classList.add("hidden");

  if (trainer) {
    editingTrainerId = trainer.id;
    titleEl.querySelector("span").textContent = t("form_edit_trainer_title");
    document.getElementById("trainer-id-input").value = trainer.id;
    document.getElementById("trainer-name-input").value = trainer.name || "";
    document.getElementById("trainer-sheet-input").value = trainer.sheet_url || "";
    const scriptInput = document.getElementById("trainer-script-input");
    if (scriptInput) scriptInput.value = trainer.script_url || "";
    document.getElementById("trainer-name-col-input").value = trainer.name_col || (currentLang === "en" ? "Name" : "الاسم");
    document.getElementById("trainer-time-col-input").value = trainer.time_col || "Timestamp";
    
    const scale = trainer.scale || 100;
    updateScaleValue(scale);

    if (trainer.signature_url) {
      previewImg.src = trainer.thumbnail_url || trainer.signature_url;
      previewImg.classList.remove("hidden");
      placeholder.classList.add("hidden");
      trimDetails.classList.remove("hidden");
      const unit = trainer.is_vector ? "pt (Vector PDF)" : "px";
      document.getElementById("sig-dim-info").textContent = `${trainer.signature_width || ""}x${trainer.signature_height || ""} ${unit}`;
    } else {
      previewImg.classList.add("hidden");
      placeholder.classList.remove("hidden");
    }
  } else {
    editingTrainerId = null;
    titleEl.querySelector("span").textContent = t("form_new_trainer_title");
    document.getElementById("trainer-form").reset();
    document.getElementById("trainer-id-input").value = "";
    const scriptInput = document.getElementById("trainer-script-input");
    if (scriptInput) scriptInput.value = "";
    document.getElementById("trainer-name-col-input").value = currentLang === "en" ? "Name" : "الاسم";
    document.getElementById("trainer-time-col-input").value = "Timestamp";
    updateScaleValue(100);
    previewImg.classList.add("hidden");
    placeholder.classList.remove("hidden");
  }

  lucide.createIcons();
}

function hideTrainerForm() {
  document.getElementById("trainers-list-container").classList.remove("hidden");
  document.getElementById("trainer-form-container").classList.add("hidden");
  document.getElementById("btn-add-trainer-view").classList.remove("hidden");
  editingTrainerId = null;
}

function updateScaleValue(val) {
  document.getElementById("trainer-scale-range").value = val;
  document.getElementById("trainer-scale-input").value = val;
  document.getElementById("trainer-scale-badge").textContent = `${val}%`;
}

function updateScaleRange(val) {
  let num = parseInt(val, 10);
  if (isNaN(num)) num = 100;
  if (num < 10) num = 10;
  if (num > 300) num = 300;
  updateScaleValue(num);
}

async function fetchTrainers() {
  try {
    const res = await fetch("/api/trainers");
    if (!res.ok) throw new Error("Failed to load trainers");
    const data = await res.json();
    activeTrainers = data.trainers || [];

    const sidebarCount = document.getElementById("sidebar-trainer-count");
    if (sidebarCount) sidebarCount.textContent = activeTrainers.length;
    const headerCount = document.getElementById("header-trainer-count");
    if (headerCount) headerCount.textContent = activeTrainers.length;
    const statCount = document.getElementById("stat-trainers-count");
    if (statCount) statCount.textContent = activeTrainers.length;
    const ctc = document.getElementById("card-trainers-count");
    if (ctc) ctc.textContent = activeTrainers.length;

    renderTrainersList(activeTrainers);
    renderTrainersQuickGrid(activeTrainers);
    populateOperatorTrainers(activeTrainers);
  } catch (err) {
    console.error("Fetch trainers error:", err);
    showToast(err.message, "error");
  }
}

function renderTrainersList(trainers) {
  const container = document.getElementById("trainers-cards-grid");
  if (!container) return;

  if (trainers.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-2">
        <i data-lucide="users" class="w-8 h-8 text-slate-300"></i>
        <span>${t("no_trainers_found")}</span>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  let html = "";
  trainers.forEach((tr) => {
    const sigSrc = tr.thumbnail_url || tr.signature_url || "";
    const hasSig = !!sigSrc;
    const isVector = !!tr.is_vector;

    html += `
      <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col justify-between hover:shadow-md transition">
        <div>
          <!-- Header: Name & Actions -->
          <div class="flex items-start justify-between gap-2 mb-3">
            <div class="flex items-center gap-2.5">
              <div class="w-9 h-9 rounded-xl bg-brand-primary/10 text-brand-primary flex items-center justify-center font-bold text-xs">
                ${tr.name ? tr.name.trim().charAt(0) : "T"}
              </div>
              <div>
                <div class="flex items-center gap-1.5">
                  <h4 class="text-xs font-bold text-slate-800">${tr.name}</h4>
                  ${isVector ? `<span class="bg-purple-100 text-purple-700 text-[9px] px-1.5 py-0.2 rounded font-bold border border-purple-200">${currentLang === "ar" ? "ملف متجهي" : "Vector PDF"}</span>` : ''}
                </div>
                <div class="text-[10px] text-slate-400 flex items-center gap-1">
                  <span>${tr.scale}% ${currentLang === "ar" ? "معامل التحجيم" : "Scale"}</span>
                  <span>•</span>
                  <span>${tr.name_col}</span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-1">
              <button onclick="editTrainer('${tr.id}')" class="p-1.5 text-slate-400 hover:text-brand-secondary hover:bg-slate-50 rounded-lg transition" title="${t("action_edit")}">
                <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
              </button>
              <button onclick="handleDeleteTrainer('${tr.id}')" class="p-1.5 text-slate-400 hover:text-brand-accent hover:bg-rose-50 rounded-lg transition" title="${t("action_delete")}">
                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
              </button>
            </div>
          </div>

          <!-- Cleaned Transparent Signature Preview -->
          <div class="w-full h-24 rounded-xl border border-slate-200 checkerboard-pattern flex items-center justify-center p-2 mb-3 relative overflow-hidden">
            ${
              hasSig
                ? `<img src="${sigSrc}" alt="Signature" class="max-h-full max-w-full object-contain">`
                : `<span class="text-[11px] text-slate-400 flex items-center gap-1"><i data-lucide="signature" class="w-4 h-4"></i> ${t("trainer_no_signature")}</span>`
            }
            ${
              hasSig
                ? `<span class="absolute bottom-1 end-1 bg-black/60 text-white text-[9px] px-1.5 py-0.2 rounded font-mono">${tr.signature_width || ""}x${tr.signature_height || ""} ${isVector ? 'pt' : 'px'}</span>`
                : ""
            }
          </div>

          <!-- Google Sheet URL Link -->
          ${
            tr.sheet_url
              ? `
            <a href="${tr.sheet_url}" target="_blank" rel="noopener noreferrer" class="text-[11px] text-brand-secondary hover:underline flex items-center gap-1 truncate mb-2">
              <i data-lucide="external-link" class="w-3 h-3 shrink-0"></i>
              <span class="truncate">${tr.sheet_url}</span>
            </a>
          `
              : `
            <div class="text-[11px] text-slate-400 mb-2 italic">${t("trainer_no_sheet")}</div>
          `
          }
        </div>

        <div class="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400">
          <span>${tr.created_at || ""}</span>
          <span class="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">${t("trainer_active")}</span>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
  lucide.createIcons();
}

function renderTrainersQuickGrid(trainers) {
  const containers = [
    document.getElementById("trainers-quick-grid"),
    document.getElementById("operator-trainers-grid")
  ].filter(Boolean);

  if (containers.length === 0) return;

  if (trainers.length === 0) {
    containers.forEach((c) => {
      c.innerHTML = `
        <div class="col-span-full py-8 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-2">
          <i data-lucide="user-x" class="w-6 h-6 text-slate-300"></i>
          <span>${t("no_trainers_found")}</span>
        </div>
      `;
    });
    lucide.createIcons();
    return;
  }

  let html = "";
  // Show up to 4 trainers in quick grid
  trainers.slice(0, 4).forEach((tr) => {
    const sigSrc = tr.thumbnail_url || tr.signature_url || "";
    const hasSig = !!sigSrc;
    const isVector = !!tr.is_vector;
    html += `
      <div class="bg-slate-50/70 p-4 rounded-2xl border border-slate-200/80 flex flex-col justify-between hover:bg-white hover:shadow-sm transition">
        <div>
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-1.5 min-w-0">
              <h4 class="text-xs font-bold text-slate-800 truncate">${tr.name}</h4>
              ${isVector ? `<span class="bg-purple-100 text-purple-700 text-[8px] px-1 py-0.2 rounded font-bold whitespace-nowrap">${currentLang === "ar" ? "متجهي" : "Vector"}</span>` : ''}
            </div>
            <span class="text-[10px] px-2 py-0.5 rounded-full bg-brand-primary/10 text-brand-primary font-bold whitespace-nowrap">${tr.scale}%</span>
          </div>

          <div class="w-full h-16 rounded-xl border border-slate-200 checkerboard-pattern flex items-center justify-center p-1.5 mb-2">
            ${
              hasSig
                ? `<img src="${sigSrc}" alt="Signature" class="max-h-full max-w-full object-contain">`
                : `<span class="text-[10px] text-slate-400">${t("trainer_no_signature")}</span>`
            }
          </div>
        </div>

        <div class="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-200/50">
          <span class="truncate">${tr.name_col}</span>
          <button onclick="editTrainer('${tr.id}')" class="text-brand-secondary hover:underline font-bold text-xs whitespace-nowrap">${t("action_edit")}</button>
        </div>
      </div>
    `;
  });

  containers.forEach((c) => {
    c.innerHTML = html;
  });
  lucide.createIcons();
}

function editTrainer(id) {
  const trainer = activeTrainers.find((t) => t.id === id);
  if (!trainer) return;
  openTrainersModal("form");
  showTrainerForm(trainer);
}

// On-the-fly signature preview and auto-trim demo
async function previewSignatureUpload(files) {
  if (!files || files.length === 0) return;
  const file = files[0];

  const loading = document.getElementById("trainer-sig-loading");
  const previewImg = document.getElementById("trainer-sig-preview-img");
  const placeholder = document.getElementById("trainer-sig-placeholder");
  const trimDetails = document.getElementById("sig-trim-details");
  const dimInfo = document.getElementById("sig-dim-info");

  loading.classList.remove("hidden");
  placeholder.classList.add("hidden");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/trainers/preview-signature", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "فشل تفريغ التوقيع");
    }

    const origW = res.headers.get("X-Original-Width") || "";
    const origH = res.headers.get("X-Original-Height") || "";
    const cleanW = res.headers.get("X-Cleaned-Width") || "";
    const cleanH = res.headers.get("X-Cleaned-Height") || "";
    const isVector = res.headers.get("X-Is-Vector") === "True";

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);

    previewImg.src = objectUrl;
    previewImg.classList.remove("hidden");
    trimDetails.classList.remove("hidden");

    if (origW && cleanW) {
      dimInfo.textContent = `${origW}x${origH} → ${cleanW}x${cleanH} ${isVector ? 'pt (Vector PDF Trimmed)' : 'px (Auto-Trimmed)'}`;
    } else {
      dimInfo.textContent = `${cleanW}x${cleanH} ${isVector ? 'pt (Vector PDF)' : 'px'}`;
    }

    showToast(isVector ? "تمت معالجة التوقيع الفيكتور بنجاح" : t("sig_trimmed_success"), "success");
  } catch (err) {
    showToast(err.message, "error");
    previewImg.classList.add("hidden");
    placeholder.classList.remove("hidden");
    trimDetails.classList.add("hidden");
  } finally {
    loading.classList.add("hidden");
    lucide.createIcons();
  }
}

async function handleSaveTrainer(e) {
  e.preventDefault();

  const name = document.getElementById("trainer-name-input").value.trim();
  const sheetUrl = document.getElementById("trainer-sheet-input").value.trim();
  const scriptUrl = document.getElementById("trainer-script-input") ? document.getElementById("trainer-script-input").value.trim() : "";
  const nameCol = document.getElementById("trainer-name-col-input").value.trim() || (currentLang === "en" ? "Name" : "الاسم");
  const timeCol = document.getElementById("trainer-time-col-input").value.trim() || "Timestamp";
  const scale = document.getElementById("trainer-scale-input").value || 100;
  const fileInput = document.getElementById("trainer-sig-file");

  if (!name) {
    showToast(t("toast_enter_trainer_name"), "warning");
    return;
  }

  const formData = new FormData();
  formData.append("name", name);
  formData.append("sheet_url", sheetUrl);
  formData.append("script_url", scriptUrl);
  formData.append("name_col", nameCol);
  formData.append("time_col", timeCol);
  formData.append("scale", scale);

  if (fileInput.files && fileInput.files.length > 0) {
    formData.append("signature_file", fileInput.files[0]);
  }

  const saveBtn = document.getElementById("btn-save-trainer");
  saveBtn.disabled = true;
  saveBtn.classList.add("opacity-60");

  try {
    let url = "/api/trainers";
    let method = "POST";

    if (editingTrainerId) {
      url = `/api/trainers/${editingTrainerId}`;
      method = "PUT";
    }

    const res = await fetch(url, {
      method: method,
      body: formData,
    });

    const result = await res.json();
    if (!res.ok) {
      throw new Error(result.detail || "فشل حفظ بيانات المدرب");
    }

    showToast(t("toast_trainer_saved"), "success");
    await fetchTrainers();
    hideTrainerForm();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    saveBtn.disabled = false;
    saveBtn.classList.remove("opacity-60");
  }
}

async function handleDeleteTrainer(id) {
  if (!confirm(t("confirm_delete_trainer"))) return;

  try {
    const res = await fetch(`/api/trainers/${id}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "فشل حذف المدرب");
    }
    showToast(t("toast_trainer_deleted"), "info");
    fetchTrainers();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ==========================================================
// Toast Notification Engine
// ==========================================================
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "pointer-events-auto flex items-center gap-3 p-4 rounded-2xl shadow-xl border text-xs font-bold transition-all duration-300 transform translate-y-3 opacity-0";

  let iconName = "info";
  let bgClass = "bg-white text-slate-800 border-slate-200";

  if (type === "success") {
    iconName = "check-circle-2";
    bgClass = "bg-[#004B87] text-white border-brand-secondary";
  } else if (type === "warning") {
    iconName = "alert-triangle";
    bgClass = "bg-[#F8B145] text-slate-900 border-amber-300";
  } else if (type === "error") {
    iconName = "x-circle";
    bgClass = "bg-[#C65D9A] text-white border-rose-300";
  }

  toast.classList.add(...bgClass.split(" "));

  toast.innerHTML = `
    <i data-lucide="${iconName}" class="w-5 h-5 shrink-0"></i>
    <span class="flex-1">${message}</span>
  `;

  container.appendChild(toast);
  lucide.createIcons();

  requestAnimationFrame(() => {
    toast.classList.remove("translate-y-3", "opacity-0");
  });

  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-3");
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, 4000);
}


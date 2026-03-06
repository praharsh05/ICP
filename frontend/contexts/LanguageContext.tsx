"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";

type Language = "ar" | "en";

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(
  undefined
);

const translations = {
  ar: {
    // Header Navigation
    "header.features": "الميزات",
    "header.about": "حول النظام",
    "header.signIn": "تسجيل الدخول",
    "header.accessSystem": "دخول النظام",

    // Hero Section
    "hero.badge": "مدعوم بـ ICP",
    "hero.title": "فاميلي جراف - مصمم لذكاء العلاقات",
    "hero.subtitle":
      "ابحث وتحقق وشاهد روابط العائلة للمواطنين والمقيمين. أدخل رقماً موحداً لرؤية شجرة عائلة حية، وتوسيع العقد، وتتبع الأزواج والأطفال، والتحقق من العلاقات. قائم على الأدلة، آمن، وسريع.",
    "hero.accessSystem": "دخول النظام",
    "hero.signIn": "تسجيل الدخول",
    "hero.secure": "آمن وموثوق",
    "hero.governmentGrade": "نتائج قائمة على الأدلة",
    "hero.uaeCompliant": "",

    // Features Section
    "features.title": "كل ما تحتاجه لذكاء العائلة والعلاقات",
    "features.subtitle": "ميزات مصممة خصيصاً لاستكشاف الروابط الحقيقية",

    // Feature 1 - One ID → Full Family Tree
    "feature1.title": "رقم واحد ← شجرة عائلة كاملة",
    "feature1.description":
      "اكتب رقماً موحداً. شاهد شجرة حية فوراً. انقر على أي شخص لتوسيع/طي الأزواج والآباء والأطفال، مع التحكم في العمق بحد أدنى ثلاثة أجيال.",
    "feature1.badge": "شجرة فورية من رقم واحد",

    // Feature 2 - Family Tree & Lineage For Citizens
    "feature2.title": "شجرة العائلة والنسب للمواطنين",
    "feature2.description":
      "يطبق قواعد دفتر العائلة الرسمية لعرض القرابة المعتمدة: رب الأسرة، تعدد الزوجات، إعادة الزواج/الطلاق، والانتقالات بين الأجيال (الابن يشكل دفتراً جديداً، البنت تنضم لزوجها).",
    "feature2.badge": "قائم على الأدلة والقواعد",

    // Feature 3 - Resident Relationship Graph
    "feature3.title": "خريطة علاقات المقيمين",
    "feature3.description":
      "يحسب العلاقات بين المقيمين من أدلة الإقامة المعتمدة التي تربط الكفلاء بالمعالين، ويحدد روابط الزوج/الطفل عند وجودها. استكشف أي شخص، وسّع دائرته.",
    "feature3.badge": "تخطيط بالأدلة فقط، مدرك للوقت",

    // Feature 4 - Common Ancestor Finder
    "feature4.title": "مكتشف الأجداد المشتركين",
    "feature4.description":
      "يحسب فوراً السلف المشترك الأدنى (LCA) بين شخصين. يبرز السلف المشترك، ويظهر كلا مسارَي العلاقة، وعد الخطوات، ويدمج الأشجار عند نقطة الالتقاء.",
    "feature4.badge": "سلف مشترك + مسار العلاقة",

    // Feature 5 - Fast, Responsive Exploration
    "feature5.title": "استكشاف سريع ومرن",
    "feature5.description":
      "نقاط GraphQL محسّنة لنتائج سريعة على مجموعة الفرعية.",
    "feature5.badge": "تفاعلات بأجزاء من الثانية (هدف )",

    // Feature 6 - Hover Over Cards & Person Information
    "feature6.title": "بطاقات التمرير ومعلومات الشخص",
    "feature6.description":
      "اطلع على التفاصيل الرئيسية بنظرة سريعة. مرر فوق أي عقدة لرؤية بطاقة مدمجة تحتوي على الاسم، الرقم الموحد، العمر/تاريخ الميلاد، الجنسية، دون مغادرة الخريطة.",
    "feature6.badge": "سياق بنظرة واحدة",

    // Feature 7 - Ready to Scale After PoC
    "feature7.title": "جاهز للتوسع بعد ",
    "feature7.description":
      "خطوط الأنابيب جاهزة للإنتاج: وظائف Spark، تحميلات مقسمة، وقيود/فهارس Neo4j. الانتقال من المجموعة الفرعية إلى النطاق الكامل بأقل إعادة تصميم.",
    "feature7.badge": "مصمم للتوسع",

    // Feature 8 - Secure by Design
    "feature8.title": "آمن بالتصميم",
    "feature8.description":
      "جميع البيانات تبقى على الخوادم المحلية. نستخرج عبر Trino، ونحول عبر Spark، ونحمل إلى Neo4j. لا استدعاءات خارجية، لا اعتماد على الإنترنت.",
    "feature8.badge": "تنفيذ محلي 100%",

    // CTA Section
    "cta.title": "هل أنت مستعد لاستكشاف روابط العائلة الحقيقية؟",
    "cta.subtitle":
      "افتح للبحث بالرقم الموحد، وشاهد شجرة عائلة قائمة على الأدلة، ووسّع العلاقات",
    "cta.button": "دخول النظام",

    // Footer
    "footer.title": "فاميلي جراف - شجرة العائلة وتخطيط العلاقات ",
    "footer.authority":
      "الهيئة الاتحادية للهوية والجنسية والجمارك وأمن المنافذ",
    "footer.system": "النظام",
    "footer.authority.section": "الهيئة",
    "footer.support": "الدعم",
    "footer.documentation": "التوثيق",
    "footer.userGuide": "دليل المستخدم",
    "footer.aboutICP": "حول زوي",
    "footer.mission": "المهمة",
    "footer.services": "الخدمات",
    "footer.contact": "اتصل بنا",
    "footer.helpCenter": "مركز المساعدة",
    "footer.privacy": "سياسة الخصوصية",
    "footer.security": "إرشادات الأمان",
    "footer.technical": "الدعم التقني",

    // App Dashboard
    "app.title": "كورتكس– ذكاء اصطناعي مصمم لتميز العمل الحكومي",
    "app.subtitle":
      "ارفع وحلل واستخرج الرؤى من مستنداتك باستخدام تقنية الذكاء الاصطناعي المتطورة. أنشئ عروضاً تقديمية وملخصات وذكاء قابل للتنفيذ.",
    "app.search": "ابحث في مساحات العمل...",
    "app.newNotebook": "مساحة عمل جديدة",
    "app.createNotebook": "إنشاء مساحة عمل جديدة",
    "app.notebookName": "أدخل اسم مساحة العمل...",
    "app.create": "إنشاء",
    "app.cancel": "إلغاء",
    "app.noNotebooks": "لم يتم العثور على مساحات عمل",
    "app.adjustSearch": "جرب تعديل مصطلحات البحث",
    "app.getStarted": "ابدأ",
    "app.getStartedDesc":
      "أنشئ مساحة عملك الأولى لبدء تحليل المستندات بالذكاء الاصطناعي",
    "app.createFirst": "إنشاء أول مساحة عمل",
    "app.created": "تم الإنشاء",
    "app.docs": "مستند",
    "app.chats": "محادثة",
    "app.deleteNotebook": "حذف مساحة العمل",
    "app.deleteConfirm": "لا يمكن التراجع عن هذا الإجراء",
    "app.deleteWarning": "هل أنت متأكد من أنك تريد حذف",
    "app.deleteDescription":
      "سيؤدي هذا إلى حذف مساحة العمل نهائياً وجميع مستنداته وسجل المحادثات والمحتوى المُنشأ.",
    "app.deleting": "جاري الحذف...",

    // Profile Type Modal
    "profile.title": "اختر نوع الملف الشخصي",
    "profile.subtitle": "حدد من تريد البحث عنه. يمكنك التبديل لاحقاً.",
    "profile.citizens": "مواطنون",
    "profile.citizensDesc":
      "استخدم قواعد دفتر العائلة لعرض الآباء والأزواج والأطفال والنسب.",
    "profile.residents": "مقيمون",
    "profile.residentsDesc":
      "استخدم أدلة الإقامة والكفالة لعرض الكفلاء والمعالين والحالة عبر الوقت.",
    "profile.continue": "متابعة",
    "profile.evidenceBased": "جميع النتائج قائمة على الأدلة.",

    // Common
    "common.loading": "جاري التحميل...",
    "common.settings": "الإعدادات",
    "common.logout": "تسجيل الخروج",
    "common.back": "العودة",
    "common.sources": "المصادر",
    "common.chat": "المحادثة",
    "common.studio": "الاستوديو",
    "common.processing": "جاري المعالجة...",
    "common.add": "إضافة",
    "common.noSources": "لا توجد مصادر بعد",
    "common.addFiles": "أضف ملفات PDF أو مستندات أو ملفات نصية",
    "common.addSourceToStart": "أضف مصدراً للبدء",
    "common.uploadToChat":
      "ارفع المستندات لبدء المحادثة حول محتواها بالذكاء الاصطناعي",
    "common.startConversation": "ابدأ محادثة",
    "common.askQuestions": "اسأل عن المستندات المرفوعة",
    "common.uploadSourcesFirst": "ارفع المصادر أولاً لبدء المحادثة",
    "common.askAboutSources": "اسأل عن مصادرك...",
    "common.generalChatMode":
      "💬 وضع الدردشة العامة - قم بتحميل المستندات للحصول على إجابات تعتمد على السياق",
    "common.documentChatMode":
      "📄 وضع تحليل المستندات - الإجابات مستندة إلى مصادرك",
    "common.askAnything": "اسأل أي شيء...",
    "common.pasteText": "لصق نص",
    "common.pasteTextSource": "لصق نص كمصدر",
    "common.textTitle": "عنوان النص",
    "common.enterTitle": "أدخل عنوان النص...",
    "common.pasteContent": "الصق المحتوى هنا...",
    "common.addAsSource": "إضافة كمصدر",
    "common.textAdded": "تمت إضافة النص بنجاح",
    "common.deleteSource": "حذف المصدر",
    "common.deleteSourceConfirm": "هل أنت متأكد من حذف هذا المصدر؟",
    "common.sourceDeleted": "تم حذف المصدر بنجاح",
    "common.source": "مصدر",
    "common.message": "رسالة",
    "common.aiContentAppear": "سيظهر المحتوى المُنشأ بالذكاء الاصطناعي هنا",
    "common.more": "المزيد",
    "common.rename": "إعادة تسمية",
    "common.share": "مشاركة",
    "common.delete": "حذف",
    "common.renameNotebook": "إعادة تسمية مساحة العمل",
    "common.notebookName": "اسم مساحة العمل",
    "common.save": "حفظ",
    confirmDeleteNotebook:
      "هل أنت متأكد من أنك تريد حذف مساحة العمل هذه؟ لا يمكن التراجع عن هذا الإجراء.",
    linkCopied: "تم نسخ رابط مساحة العمل إلى الحافظة!",
  },
  en: {
    // Header Navigation
    "header.features": "Features",
    "header.about": "About",
    "header.signIn": "Sign In",
    "header.accessSystem": "Access System",

    // Hero Section
    "hero.badge": "Powered by ICP",
    "hero.title": "Family Tree - Built for Relationship Intelligence",
    "hero.subtitle":
      "Search, verify, and visualize family links for citizens & residents. Enter your Unified ID to see a living family tree, expand nodes, trace spouses and children, and verify relationships. Evidence-based, secure, and fast.",
    "hero.accessSystem": "Access System",
    "hero.signIn": "Sign In",
    "hero.secure": "Secure & Reliable",
    "hero.governmentGrade": "Evidence-based Results",
    "hero.uaeCompliant": "",

    // Features Section
    "features.title":
      "Everything you need for family & relationship intelligence",
    "features.subtitle": "Purpose-built features to explore real connections",

    // Feature 1 - One ID → Full Family Tree
    "feature1.title": "One ID → Full Family Tree",
    "feature1.description":
      "Type a unified number. Instantly view a living tree. Click any person to expand/collapse spouses, parents, and children, depth controls with minimum three generations.",
    "feature1.badge": "Instant tree from one ID",

    // Feature 2 - Family Tree & Lineage For Citizens
    "feature2.title": "Family Tree & Lineage For Citizens",
    "feature2.description":
      "Applies official family-book rules to render verified kinship: head of family, multiple wives, remarriage/divorce, and generational moves.",
    "feature2.badge": "Evidence-based, rule-driven",

    // Feature 3 - Resident Relationship Graph
    "feature3.title": "Resident Relationship Graph",
    "feature3.description":
      "Computes relationships between residents from verified residency evidence linking sponsors and dependents, identifying spouse/child connections when present. Explore any person, expand their circle.",
    "feature3.badge": "Evidence-only, time-aware mapping",

    // Feature 4 - Common Ancestor Finder
    "feature4.title": "Common Ancestor Finder",
    "feature4.description":
      "Instantly computes the Lowest Common Ancestor (LCA) between two people. Highlights the shared ancestor, shows both relationship paths, hop counts, and merges the trees at the meeting point.",
    "feature4.badge": "Common Ancestor + Relationship Path",

    // Feature 5 - Fast, Responsive Exploration
    "feature5.title": "Fast, Responsive Exploration",
    "feature5.description":
      "Graph endpoints are tuned for quick results on the data subset.",
    "feature5.badge": "Sub-second interactions",

    // Feature 6 - Hover Over Cards & Person Information
    "feature6.title": "Instant Access to Detailed Person Information",
    "feature6.description":
      "See key details at a glance. Hover over any node to view a spanshot with name, Unified ID, DoB, nationality, without leaving the graph.",
    "feature6.badge": "At-a-glance context",

    // Feature 7 - Ready to Scale After PoC
    "feature7.title": "Ready to Scale",
    "feature7.description":
      "Pipelines are production-ready: Spark jobs, partitioned loads, and Neo4j constraints/indexes. Move from subset to full scale with minimal redesign.",
    "feature7.badge": "Designed for scale",

    // Feature 8 - Secure by Design
    "feature8.title": "Secure by Design",
    "feature8.description":
      "All data stays on-prem. We extract via Trino, transform via Spark, load into Neo4j. No external calls, no internet dependency.",
    "feature8.badge": "100% on-prem execution",

    // CTA Section
    "cta.title": "Ready to explore real family connections?",
    "cta.subtitle":
      "Open the to search by unified number, view an evidence-based family tree, and expand relationships",
    "cta.button": "Access System",

    // Footer
    "footer.title": "FamilyGraph - Family Tree & Relationship Mapping",
    "footer.authority":
      "Federal Authority for Identity, Citizenship, Customs & Port Security",
    "footer.system": "System",
    "footer.authority.section": "Authority",
    "footer.support": "Support",
    "footer.documentation": "Documentation",
    "footer.userGuide": "User Guide",
    "footer.aboutICP": "About ICP",
    "footer.mission": "Mission",
    "footer.services": "Services",
    "footer.contact": "Contact",
    "footer.helpCenter": "Help Center",
    "footer.privacy": "Privacy Policy",
    "footer.security": "Security Guidelines",
    "footer.technical": "Technical Support",

    // App Dashboard
    "app.title": "CORTEX – AI Built for Government Excellence",
    "app.subtitle":
      "Upload, analyze, and generate insights from your documents using advanced AI technology. Create presentations, summaries, and actionable intelligence.",
    "app.search": "Search your workspaces...",
    "app.newNotebook": "New Workspace",
    "app.createNotebook": "Create New Workspace",
    "app.notebookName": "Enter workspace name...",
    "app.create": "Create",
    "app.cancel": "Cancel",
    "app.noNotebooks": "No workspaces found",
    "app.adjustSearch": "Try adjusting your search terms",
    "app.getStarted": "Get Started",
    "app.getStartedDesc":
      "Create your first workspace to begin analyzing documents with AI",
    "app.createFirst": "Create First Workspace",
    "app.created": "Created",
    "app.docs": "doc",
    "app.chats": "chat",
    "app.deleteNotebook": "Delete Workspace",
    "app.deleteConfirm": "This action cannot be undone",
    "app.deleteWarning": "Are you sure you want to delete",
    "app.deleteDescription":
      "This will permanently delete the workspace and all its documents, chat history, and generated content.",
    "app.deleting": "Deleting...",

    // Profile Type Modal
    "profile.title": "Choose Profile Type",
    "profile.subtitle":
      "Select who you want to search for. You can switch later.",
    "profile.citizens": "Citizens",
    "profile.citizensDesc":
      "Use family-book rules to view parents, spouses, children, and lineage.",
    "profile.residents": "Residents",
    "profile.residentsDesc":
      "Use residency & sponsorship evidence to view sponsors, dependents, and status over time.",
    "profile.continue": "Continue",
    "profile.evidenceBased": "All results are evidence-based.",

    // Common
    "common.loading": "Loading...",
    "common.settings": "Settings",
    "common.logout": "Logout",
    "common.back": "Back",
    "common.sources": "Sources",
    "common.chat": "Chat",
    "common.studio": "Studio",
    "common.processing": "Processing...",
    "common.add": "Add",
    "common.noSources": "No sources yet",
    "common.addFiles": "Add PDFs, docs, or text files",
    "common.addSourceToStart": "Add a source to get started",
    "common.uploadToChat":
      "Upload documents to start chatting about their contents with AI",
    "common.startConversation": "Start a conversation",
    "common.askQuestions": "Ask questions about your uploaded documents",
    "common.uploadSourcesFirst": "Upload sources first to start chatting",
    "common.askAboutSources": "Ask about your sources...",
    "common.generalChatMode":
      "💬 General chat mode - Upload documents for context-aware responses",
    "common.documentChatMode":
      "📄 Document analysis mode - Responses based on your sources",
    "common.askAnything": "Ask anything...",
    "common.pasteText": "Paste Text",
    "common.pasteTextSource": "Paste Text as Source",
    "common.textTitle": "Text Title",
    "common.enterTitle": "Enter text title...",
    "common.pasteContent": "Paste your content here...",
    "common.addAsSource": "Add as Source",
    "common.textAdded": "Text added successfully",
    "common.deleteSource": "Delete Source",
    "common.deleteSourceConfirm":
      "Are you sure you want to delete this source?",
    "common.sourceDeleted": "Source deleted successfully",
    "common.source": "source",
    "common.message": "message",
    "common.aiContentAppear": "AI-generated content will appear here",
    "common.more": "More",
    "common.rename": "Rename",
    "common.share": "Share",
    "common.delete": "Delete",
    "common.renameNotebook": "Rename Workspace",
    "common.notebookName": "Workspace name",
    "common.save": "Save",
    confirmDeleteNotebook:
      "Are you sure you want to delete this workspace? This action cannot be undone.",
    linkCopied: "Workspace link copied to clipboard!",
  },
};

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [language, setLanguageState] = useState<Language>("ar"); // Default to Arabic

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem("language", lang);

    // Update HTML attributes
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = lang;

    // Add/remove Arabic styling classes
    if (lang === "ar") {
      document.body.classList.add("arabic-text");
    } else {
      document.body.classList.remove("arabic-text");
    }
  };

  const t = (key: string): string => {
    return translations[language][key as keyof typeof translations.ar] || key;
  };

  useEffect(() => {
    const savedLanguage = localStorage.getItem("language") as Language;
    if (savedLanguage && (savedLanguage === "ar" || savedLanguage === "en")) {
      setLanguage(savedLanguage);
    } else {
      // Default to Arabic
      setLanguage("ar");
    }
  }, []);

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
};

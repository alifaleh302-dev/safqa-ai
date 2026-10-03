# AGENTS.md — دليل العمل على هذا المستودع

## نظرة عامة
نظام userbot يتفاوض مع العملاء داخل مجموعات تليجرام بأسلوب بشري، مدعوم بـ Google Gemini،
مع واجهة ويب مستقلة للإدارة. الهدف/المنتجات/الأسعار/الحدود تُحدَّد من داخل البرومبت.

## البنية
- `backend/app/main.py` — نقطة دخول FastAPI، إعادة توصيل الحسابات عند الإقلاع، انتظار قاعدة البيانات.
- `backend/app/models.py` — جداول SQLAlchemy (accounts, prompts, groups, messages, decisions, events).
- `backend/app/auth.py` + `routers/auth.py` — مصادقة JWT للمشرف (login/me).
- `backend/app/services/telegram_manager.py` — إدارة عملاء Telethon، حلقة الاستماع، الردّ، وإعادة الاتصال التلقائي.
- `backend/app/services/engine.py` — طبقة قرار AI تُعيد JSON (reply/ignore/escalate) مع حَقن كتالوج المنتجات.
- `backend/app/services/gemini.py` — عميل Gemini REST مع retry/backoff وسلسلة نماذج بديلة.
- `backend/app/services/knowledge.py` — قاعدة معرفة المنتجات (RAG بسيط) من `data/products.json`.
- `backend/app/services/ws_manager.py` — بثّ حيّ عبر WebSocket للواجهة.
- `backend/app/services/humanize.py` — تأخيرات و«يكتب الآن» وتقسيم الرسائل.
- `backend/app/routers/` — accounts, prompts, groups, monitor, settings, knowledge, auth.
- `frontend/src/pages/` — Dashboard, Accounts, Prompts, Groups, Monitor, Playground, Knowledge, Login, Settings.
- `frontend/src/useLiveMonitor.ts` — hook لاستهلاك بثّ WebSocket.
- `docs/ARCHITECTURE.md` — التخطيط المعماري الكامل.

## أوامر أساسية
```bash
# كل النظام (موصى به) — 3 حاويات: db + backend + frontend
cp .env.example .env    # املأ TELEGRAM_API_ID/HASH و GEMINI_API_KEY و SECRET_KEY
sudo docker compose up --build     # الواجهة: http://localhost:12000
sudo docker compose logs -f backend

# Backend محلياً
cd backend && pip install -r requirements.txt
export PATH="$HOME/.local/bin:$PATH"
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend محلياً
cd frontend && npm install && npm run dev   # منفذ 12000، يمرّر /api إلى 8000
npm run build                                # للتحقق من أخطاء TypeScript
```

## النشر (Docker)
- `docker-compose.yml`: `db` (Postgres 16 + healthcheck) → `backend` (ينتظر صحة القاعدة) → `frontend` (nginx).
- nginx يمرّر `/api/` و`/api/ws` (مع ترويسات WebSocket) إلى الـ backend.
- متغيّرات Postgres (`POSTGRES_*`) تُبنى منها `DATABASE_URL` تلقائياً للحاويات.
- مجلّد `backend/data/` يُربط كـ volume لحفظ جلسات Telethon و`products.json`؛ يُنسخ الكتالوج من `backend/seed/` إن كان المجلّد فارغاً.

## اصطلاحات
- Python: type hints، Pydantic v2، SQLAlchemy 2.0 (`Mapped`/`mapped_column`).
- **معرّفات تليجرام 64-بت:** استخدم `BigInteger` لأي عمود يحمل `telegram_id` أو `telegram_message_id`
  (SQLite يتساهل لكن Postgres `INTEGER` يفشل بـ NumericValueOutOfRange).
- الواجهة عربية RTL، بدون مكتبة UI خارجية (CSS مخصص في `index.css`).
- لا تُضِف تعليقات تكرّر الكود؛ علّق فقط على ما هو غير بديهي.
- كل قرار AI يُسجَّل في جدول `decisions`؛ كل خطأ/حدث في `events`.
- كل مسارات `/api` محميّة بـ JWT عدا `/api/health` و`/api/auth/login`؛ بثّ WebSocket يُصادَق عبر `?token=`.

## قواعد مهمة للمستقبل
- **لا تُرسل رسائل جماعية** ولا ترفع الحدود دون سبب — خطر حظر الحساب.
- الوضع الافتراضي الآمن للمجموعات هو `mention`.
- `mode` يحدّد *متى* ينظر البوت (mention/always/off)، و`reply_scope` يحدّد *هل* يردّ:
  `relevant` (افتراضي) يتجاهل الرسائل غير المتعلّقة بالعرض، `all` يردّ على أي رسالة موجّهة.
- `max_replies_per_user_per_day` (افتراضي 2، و0 = بلا حد): سقف ردود لنفس الشخص/24س
  لمنع مظهر البوت المفرط. العدّ يعتمد على `messages.sender_id` + قرارات `reply`.
- **سبب الردّ المزدوج:** عميلان متصلان لنفس الحساب (استعادة عند الإقلاع + إعادة اتصال يدوية)
  يستقبلان نفس التحديث ويردّان مرّتين. الحل: `_register` يفصل العميل القديم، + إزالة تكرار
  الوارد حسب `telegram_message_id` في بداية المعالجة.
- عند اتهام العميل بأنه بوت: تبرير واحد فقط ثم مواصلة الموضوع؛ لا تكرار للنفي.
- أي حالة حساسة (شكوى/استرداد/وعد قانوني) يجب أن تُعاد كـ `escalate` لا كـ `reply`.
- مؤشر «يكتب…» يجب أن يبقى ظاهراً طوال زمن الكتابة الفعلي عبر `_show_typing`
  (تليجرام يمسحه بعد ثوانٍ، لذا يُعاد إرساله كل `TYPING_PING_INTERVAL`).
- ملف `.env` وملفات `*.session` ممنوعة من git (انظر `.gitignore`).
- تُشفَّر جلسات Telethon بمفتاح `SECRET_KEY` عبر Fernet — تغييره يُبطل الجلسات المحفوظة.
- أعمدة جديدة تُضاف عبر `_apply_light_migrations()` في `db.py` (لا يوجد أداة migrations بعد).

## الحالة الحالية (المرحلة 2 — مكتملة)
Backend + Frontend + Postgres تعمل عبر `docker compose up` (3 حاويات). متضمّن:
- **WebSocket** للمراقبة الحيّة (لا polling).
- **RAG** لكتالوج المنتجات (`backend/data/products.json`) محقون في برومبت القرار.
- **JWT** لمصادقة المشرف على الواجهة وكل مسارات API.
- **إعادة اتصال تلقائي** لحسابات Telethon مع backoff، وإعادة توصيل عند الإقلاع.
- **Gemini**: retry/backoff للأخطاء العابرة + سلسلة نماذج بديلة (`GEMINI_FALLBACK_MODELS`).
- اختُبر التفاوض فعلياً (عربي/إنجليزي): قراءة السعر الصحيح من الكتالوج + توجيه العميل للخاص + تصعيد الحالات الحساسة.
- لم يُختبر بعد على حساب تليجرام حقيقي — يحتاج `TELEGRAM_API_ID/HASH` فعلية.

## الخطوات التالية
إصدارات البرومبت و A/B، لوحة تحليلات للقرارات، اختبار على حساب تليجرام حقيقي، تنبيهات للتصعيد.

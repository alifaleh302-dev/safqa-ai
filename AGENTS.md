# AGENTS.md — دليل العمل على هذا المستودع

## نظرة عامة
نظام userbot يتفاوض مع العملاء داخل مجموعات تليجرام بأسلوب بشري، مدعوم بـ Google Gemini،
مع واجهة ويب مستقلة للإدارة. الهدف/المنتجات/الأسعار/الحدود تُحدَّد من داخل البرومبت.

## البنية
- `backend/app/main.py` — نقطة دخول FastAPI وتسجيل الـ routers.
- `backend/app/models.py` — جداول SQLAlchemy (accounts, prompts, groups, messages, decisions, events).
- `backend/app/services/telegram_manager.py` — إدارة عملاء Telethon وحلقة الاستماع والردّ.
- `backend/app/services/engine.py` — طبقة قرار AI تُعيد JSON (reply/ignore/escalate).
- `backend/app/services/gemini.py` — عميل Gemini REST.
- `backend/app/services/humanize.py` — تأخيرات و«يكتب الآن» وتقسيم الرسائل.
- `backend/app/routers/` — accounts, prompts, groups, monitor, settings.
- `frontend/src/pages/` — Dashboard, Accounts, Prompts, Groups, Monitor, Playground, Settings.
- `docs/ARCHITECTURE.md` — التخطيط المعماري الكامل.

## أوامر أساسية
```bash
# Backend
cd backend && pip install -r requirements.txt
export PATH="$HOME/.local/bin:$PATH"
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm install && npm run dev   # منفذ 12000، يمرّر /api إلى 8000
npm run build                                # للتحقق من أخطاء TypeScript
```

## اصطلاحات
- Python: type hints، Pydantic v2، SQLAlchemy 2.0 (`Mapped`/`mapped_column`).
- الواجهة عربية RTL، بدون مكتبة UI خارجية (CSS مخصص في `index.css`).
- لا تُضِف تعليقات تكرّر الكود؛ علّق فقط على ما هو غير بديهي.
- كل قرار AI يُسجَّل في جدول `decisions`؛ كل خطأ/حدث في `events`.

## قواعد مهمة للمستقبل
- **لا تُرسل رسائل جماعية** ولا ترفع الحدود دون سبب — خطر حظر الحساب.
- الوضع الافتراضي الآمن للمجموعات هو `mention`.
- أي حالة حساسة (شكوى/استرداد/وعد قانوني) يجب أن تُعاد كـ `escalate` لا كـ `reply`.
- ملف `.env` وملفات `*.session` ممنوعة من git (انظر `.gitignore`).
- تُشفَّر جلسات Telethon بمفتاح `SECRET_KEY` عبر Fernet — تغييره يُبطل الجلسات المحفوظة.

## الحالة الحالية (المرحلة 0/MVP — مكتملة)
Backend قابل للتشغيل، واجهة React تعمل (build ناجح)، تكامل Gemini عبر REST، تكامل Telethon
(إرسال كود/تحقق/2FA/اتصال/انقطاع)، محاكاة بشرية، حدود معدّل، مراقبة حيّة.
لم يُختبر بعد على حساب تليجرام حقيقي — يحتاج مفاتيح API فعلية.

## الخطوات التالية
WebSocket للحظيّة، RAG للمنتجات، مصادقة الواجهة، إصدارات البرومبت و A/B، دعم Postgres في الإنتاج.

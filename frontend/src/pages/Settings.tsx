import { useEffect, useState } from "react";
import { api } from "../api";
import type { Settings } from "../types";

interface Props {
  notify: (text: string, kind?: "ok" | "err") => void;
}

export default function SettingsPage({ notify }: Props) {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [telegramApiId, setTelegramApiId] = useState("");
  const [telegramApiHash, setTelegramApiHash] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("gemini-1.5-flash");
  const [minDelay, setMinDelay] = useState("2");
  const [maxDelay, setMaxDelay] = useState("9");
  const [perHour, setPerHour] = useState("20");
  const [perDay, setPerDay] = useState("200");

  useEffect(() => {
    api.settings.get().then((s) => {
      setSettings(s);
      setGeminiModel(s.gemini_model);
      setPerHour(String(s.max_replies_per_hour));
      setPerDay(String(s.max_replies_per_day));
    }).catch(() => undefined);
  }, []);

  async function save() {
    try {
      const payload: Record<string, unknown> = {
        gemini_model: geminiModel,
        max_replies_per_hour: Number(perHour),
        max_replies_per_day: Number(perDay),
        reply_min_delay: Number(minDelay),
        reply_max_delay: Number(maxDelay),
      };
      if (telegramApiId) payload.telegram_api_id = Number(telegramApiId);
      if (telegramApiHash) payload.telegram_api_hash = telegramApiHash;
      if (geminiKey) payload.gemini_api_key = geminiKey;
      const s = await api.settings.update(payload);
      setSettings(s);
      setTelegramApiId("");
      setTelegramApiHash("");
      setGeminiKey("");
      notify("تم حفظ الإعدادات");
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  return (
    <>
      <h2>الإعدادات</h2>
      <div className="card">
        <h3>تليجرام (my.telegram.org)</h3>
        <div className="row">
          <input placeholder="API ID" value={telegramApiId} onChange={(e) => setTelegramApiId(e.target.value)} />
          <input placeholder="API Hash" value={telegramApiHash} onChange={(e) => setTelegramApiHash(e.target.value)} />
        </div>
        <p className="muted small" style={{ marginTop: 8 }}>
          الحالة: {settings?.telegram_api_configured ? "مُعدّ ✅" : "غير مُعدّ ⚠️"} — تُترك الحقول للتحديث فقط.
        </p>
      </div>

      <div className="card">
        <h3>Gemini (Google AI Studio)</h3>
        <div className="row">
          <input placeholder="GEMINI_API_KEY" value={geminiKey} onChange={(e) => setGeminiKey(e.target.value)} type="password" />
          <input placeholder="الموديل" value={geminiModel} onChange={(e) => setGeminiModel(e.target.value)} />
        </div>
        <p className="muted small" style={{ marginTop: 8 }}>
          الحالة: {settings?.gemini_configured ? "مُعدّ ✅" : "غير مُعدّ ⚠️"}
        </p>
      </div>

      <div className="card">
        <h3>محاكاة الأسلوب البشري والحدود</h3>
        <div className="row">
          <label className="muted small">
            أقل تأخير للرد (ثانية)
            <input value={minDelay} onChange={(e) => setMinDelay(e.target.value)} />
          </label>
          <label className="muted small">
            أقصى تأخير للرد (ثانية)
            <input value={maxDelay} onChange={(e) => setMaxDelay(e.target.value)} />
          </label>
          <label className="muted small">
            حد الردود/ساعة
            <input value={perHour} onChange={(e) => setPerHour(e.target.value)} />
          </label>
          <label className="muted small">
            حد الردود/يوم
            <input value={perDay} onChange={(e) => setPerDay(e.target.value)} />
          </label>
        </div>
      </div>

      <button className="primary" onClick={save}>
        حفظ الإعدادات
      </button>
    </>
  );
}

import { useEffect, useState } from "react";
import { api } from "../api";
import type { Prompt } from "../types";

interface Props {
  notify: (text: string, kind?: "ok" | "err") => void;
}

const SAMPLE = `أنت مندوب مبيعات عربي محترف تتفاوض داخل مجموعات تليجرام بأسلوب بشري طبيعي.

الهدف:
- جعل العميل يراسلك على الخاص لإكمال التفاوض مع صاحب العمل شخصياً.
- لا تكشف أنك ذكاء اصطناعي أبداً.

المنتج والسعر:
- المنتج: (اكتب اسم المنتج هنا)
- السعر المعلن: (اكتب السعر)
- الحد الأدنى المسموح: (اكتب الحد الأدنى)
- لا توعد بخصم أو موعد تسليم غير مذكور هنا.

الأسلوب:
- ردود قصيرة وطبيعية بالعربية أو الإنجليزية حسب لغة العميل.
- لا تستخدم قوائم أو إيموجي إلا إذا استخدمها العميل.
- كن ودوداً ومهنياً دون مبالغة.

التصعيد:
- إذا طلب العميل شيئاً خارج هذه القواعد (شكوى، استرداد، وعد قانوني) صعّد الأمر لإنسان.`;

export default function Prompts({ notify }: Props) {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [name, setName] = useState("");
  const [text, setText] = useState(SAMPLE);
  const [editing, setEditing] = useState<number | null>(null);

  async function load() {
    setPrompts(await api.prompts.list());
  }
  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  async function save() {
    if (!name.trim() || !text.trim()) return notify("أدخل الاسم ونص البرومبت", "err");
    try {
      if (editing) {
        await api.prompts.update(editing, { name, system_text: text });
        notify("تم تحديث البرومبت");
      } else {
        await api.prompts.create({ name, system_text: text });
        notify("تم إنشاء البرومبت");
      }
      setName("");
      setText(SAMPLE);
      setEditing(null);
      await load();
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  function edit(p: Prompt) {
    setEditing(p.id);
    setName(p.name);
    setText(p.system_text);
    window.scrollTo(0, 0);
  }

  async function toggle(p: Prompt) {
    try {
      await api.prompts.update(p.id, { active: !p.active });
      await load();
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  async function remove(p: Prompt) {
    if (!confirm(`حذف البرومبت «${p.name}»؟`)) return;
    try {
      await api.prompts.remove(p.id);
      await load();
      notify("تم الحذف");
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  return (
    <>
      <h2>البرومبتات (قواعد التفاوض)</h2>
      <div className="card">
        <p className="muted">
          هنا تكتب الهدف والمنتجات والأسعار والحدود والأسلوب. هذا النص هو عقل المتفاوض وقواعده.
        </p>
        <input placeholder="اسم البرومبت (مثال: حملة المنتج X)" value={name} onChange={(e) => setName(e.target.value)} />
        <textarea
          style={{ marginTop: 10, minHeight: 220 }}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="row" style={{ marginTop: 10 }}>
          <button className="primary" onClick={save}>
            {editing ? "حفظ التعديلات" : "إنشاء"}
          </button>
          {editing && (
            <button
              className="ghost"
              onClick={() => {
                setEditing(null);
                setName("");
                setText(SAMPLE);
              }}
            >
              إلغاء التعديل
            </button>
          )}
        </div>
      </div>

      {prompts.map((p) => (
        <div className="card" key={p.id}>
          <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong>{p.name}</strong> <span className="muted small">v{p.version}</span>{" "}
              <span className={`badge ${p.active ? "reply" : "ignore"}`}>{p.active ? "مُفعّل" : "معطّل"}</span>
            </div>
            <div className="row" style={{ flex: "0 0 auto" }}>
              <button onClick={() => edit(p)}>تعديل</button>
              <button onClick={() => toggle(p)}>{p.active ? "تعطيل" : "تفعيل"}</button>
              <button className="bad" onClick={() => remove(p)}>
                حذف
              </button>
            </div>
          </div>
          <pre className="muted small" style={{ whiteSpace: "pre-wrap", marginTop: 10 }}>
            {p.system_text.slice(0, 400)}
            {p.system_text.length > 400 ? "…" : ""}
          </pre>
        </div>
      ))}
    </>
  );
}

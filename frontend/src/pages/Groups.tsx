import { useEffect, useState } from "react";
import { api } from "../api";
import type { Account, Group, Prompt } from "../types";

interface Props {
  notify: (text: string, kind?: "ok" | "err") => void;
}

export default function Groups({ notify }: Props) {
  const [groups, setGroups] = useState<Group[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [telegramId, setTelegramId] = useState("");
  const [title, setTitle] = useState("");
  const [accountId, setAccountId] = useState<number | "">("");
  const [promptId, setPromptId] = useState<number | "">("");
  const [mode, setMode] = useState<Group["mode"]>("mention");
  const [replyScope, setReplyScope] = useState<Group["reply_scope"]>("relevant");
  const [perUserLimit, setPerUserLimit] = useState(2);

  async function load() {
    const [g, a, p] = await Promise.all([api.groups.list(), api.accounts.list(), api.prompts.list()]);
    setGroups(g);
    setAccounts(a);
    setPrompts(p);
    if (a.length && accountId === "") setAccountId(a[0].id);
    if (p.length && promptId === "") setPromptId(p[0].id);
  }
  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  async function create() {
    const tid = Number(telegramId);
    if (!tid) return notify("أدخل معرّف المجموعة الرقمي (يبدأ بـ -100)", "err");
    try {
      await api.groups.create({
        telegram_id: tid,
        title,
        account_id: accountId === "" ? null : accountId,
        prompt_id: promptId === "" ? null : promptId,
        mode,
        reply_scope: replyScope,
        max_replies_per_user_per_day: perUserLimit,
      });
      setTelegramId("");
      setTitle("");
      await load();
      notify("تمت إضافة المجموعة");
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  async function update(g: Group, patch: Partial<Group>) {
    try {
      await api.groups.update(g.id, patch);
      await load();
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  async function resolve(g: Group) {
    try {
      await api.groups.resolve(g.id);
      await load();
      notify("تم جلب عنوان المجموعة");
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  async function remove(g: Group) {
    if (!confirm("حذف هذه المجموعة من المراقبة؟")) return;
    try {
      await api.groups.remove(g.id);
      await load();
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  return (
    <>
      <h2>المجموعات المراقَبة</h2>
      <div className="card">
        <p className="muted">
          أضف معرّف المجموعة (ID الرقمي). يمكنك الحصول عليه بتحويل رابط أو باستخدام تطبيق. الوضع «mention»
          يجعل الحساب يرد فقط عند ذكره أو الرد عليه — وهو الأكثر أماناً. نطاق الردّ «ذو صلة» يجعل
          الذكاء يتجاهل الرسائل غير المتعلّقة بعرضك حتى لا يردّ على كل من في المجموعة.
        </p>
        <div className="row">
          <input placeholder="معرّف المجموعة (مثال: -1001234567890)" value={telegramId} onChange={(e) => setTelegramId(e.target.value)} />
          <input placeholder="عنوان اختياري" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <select value={accountId} onChange={(e) => setAccountId(e.target.value === "" ? "" : Number(e.target.value))}>
            <option value="">— اختر الحساب —</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.label}
              </option>
            ))}
          </select>
          <select value={promptId} onChange={(e) => setPromptId(e.target.value === "" ? "" : Number(e.target.value))}>
            <option value="">— اختر البرومبت —</option>
            {prompts.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} (v{p.version})
              </option>
            ))}
          </select>
          <select value={mode} onChange={(e) => setMode(e.target.value as Group["mode"])}>
            <option value="mention">عند الذكر فقط (mention)</option>
            <option value="always">دائماً (always)</option>
            <option value="off">معطّل (off)</option>
          </select>
          <select value={replyScope} onChange={(e) => setReplyScope(e.target.value as Group["reply_scope"])}>
            <option value="relevant">ردّ ذو صلة فقط</option>
            <option value="all">ردّ على كل رسالة موجّهة</option>
          </select>
          <label className="muted small" style={{ display: "flex", alignItems: "center", gap: 6 }}>
            حدّ الردود لكل شخص/24س
            <input
              type="number"
              min={0}
              style={{ width: 70 }}
              value={perUserLimit}
              onChange={(e) => setPerUserLimit(Number(e.target.value))}
            />
          </label>
          <button className="primary" onClick={create}>
            إضافة
          </button>
        </div>
      </div>

      {groups.map((g) => (
        <div className="card" key={g.id}>
          <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong>{g.title || "بدون عنوان"}</strong>{" "}
              <span className="muted small">{g.telegram_id}</span>{" "}
              <span className={`badge ${g.active ? "reply" : "ignore"}`}>{g.active ? "مُراقَبة" : "موقوفة"}</span>
            </div>
            <div className="row" style={{ flex: "0 0 auto" }}>
              <button onClick={() => resolve(g)}>جلب العنوان</button>
              <button onClick={() => update(g, { active: !g.active })}>{g.active ? "إيقاف" : "تشغيل"}</button>
              <button className="bad" onClick={() => remove(g)}>
                حذف
              </button>
            </div>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <select value={g.account_id ?? ""} onChange={(e) => update(g, { account_id: e.target.value ? Number(e.target.value) : null })}>
              <option value="">— الحساب —</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.label}
                </option>
              ))}
            </select>
            <select value={g.prompt_id ?? ""} onChange={(e) => update(g, { prompt_id: e.target.value ? Number(e.target.value) : null })}>
              <option value="">— البرومبت —</option>
              {prompts.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <select value={g.mode} onChange={(e) => update(g, { mode: e.target.value as Group["mode"] })}>
              <option value="mention">mention</option>
              <option value="always">always</option>
              <option value="off">off</option>
            </select>
            <select value={g.reply_scope} onChange={(e) => update(g, { reply_scope: e.target.value as Group["reply_scope"] })}>
              <option value="relevant">ذو صلة</option>
              <option value="all">الكل</option>
            </select>
            <label className="muted small" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              حدّ/شخص/24س
              <input
                type="number"
                min={0}
                style={{ width: 70 }}
                value={g.max_replies_per_user_per_day}
                onChange={(e) => update(g, { max_replies_per_user_per_day: Number(e.target.value) })}
              />
            </label>
          </div>
        </div>
      ))}
    </>
  );
}

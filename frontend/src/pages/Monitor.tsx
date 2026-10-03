import { useEffect, useState } from "react";
import { api } from "../api";
import type { Decision, Group, Message } from "../types";

export default function Monitor() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [selected, setSelected] = useState<number | "">("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [auto, setAuto] = useState(true);

  useEffect(() => {
    api.groups.list().then(setGroups).catch(() => undefined);
  }, []);

  useEffect(() => {
    async function tick() {
      const [m, d] = await Promise.all([
        api.monitor.messages(selected === "" ? undefined : selected),
        api.monitor.decisions(),
      ]);
      setMessages(m);
      setDecisions(d.filter((x) => selected === "" || x.group_id === selected));
    }
    tick().catch(() => undefined);
    if (!auto) return;
    const id = window.setInterval(() => tick().catch(() => undefined), 4000);
    return () => window.clearInterval(id);
  }, [selected, auto]);

  return (
    <>
      <h2>المراقبة الحيّة</h2>
      <div className="card">
        <div className="row" style={{ alignItems: "center" }}>
          <select value={selected} onChange={(e) => setSelected(e.target.value === "" ? "" : Number(e.target.value))}>
            <option value="">كل المجموعات</option>
            {groups.map((g) => (
              <option key={g.id} value={g.id}>
                {g.title || g.telegram_id}
              </option>
            ))}
          </select>
          <label className="muted small" style={{ display: "flex", alignItems: "center", gap: 6, minWidth: "auto" }}>
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} style={{ width: "auto" }} />
            تحديث تلقائي كل 4 ثوانٍ
          </label>
        </div>
      </div>

      <div className="card">
        <h3>المحادثات</h3>
        {messages.length === 0 && <p className="muted">لا توجد رسائل بعد.</p>}
        <div className="chat">
          {[...messages].reverse().map((m) => (
            <div key={m.id} className={`bubble ${m.direction}`}>
              <div className="small" style={{ opacity: 0.8, marginBottom: 3 }}>
                {m.direction === "in" ? m.sender_name : "أنا"} · {new Date(m.created_at).toLocaleTimeString("ar")}
              </div>
              {m.text}
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h3>قرارات الذكاء الاصطناعي</h3>
        {decisions.length === 0 && <p className="muted">لا توجد قرارات بعد.</p>}
        {decisions.slice(0, 20).map((d) => (
          <div key={d.id} className="card" style={{ background: "var(--panel-2)", marginBottom: 8 }}>
            <span className={`badge ${d.action}`}>{d.action}</span>
            <span className="muted small" style={{ marginInlineStart: 8 }}>
              {new Date(d.created_at).toLocaleTimeString("ar")}
            </span>
            <div className="small muted" style={{ marginTop: 6 }}>{d.reason}</div>
            {d.reply_text && (
              <div style={{ marginTop: 8, padding: 8, background: "var(--bg)", borderRadius: 8 }}>{d.reply_text}</div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

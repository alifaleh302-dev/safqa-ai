import { useEffect, useState } from "react";
import { api } from "../api";
import type { Group } from "../types";
import { useLiveMonitor } from "../useLiveMonitor";

export default function Monitor() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [selected, setSelected] = useState<number | "">("");
  const { messages, decisions, connected } = useLiveMonitor(true);

  useEffect(() => {
    api.groups.list().then(setGroups).catch(() => undefined);
  }, []);

  const shownMessages = messages.filter((m) => selected === "" || m.group_id === selected);
  const shownDecisions = decisions.filter((d) => selected === "" || d.group_id === selected);

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
          <span className={`badge ${connected ? "online" : "offline"}`}>
            {connected ? "● متصل لحظياً" : "○ إعادة الاتصال…"}
          </span>
        </div>
      </div>

      <div className="card">
        <h3>المحادثات</h3>
        {shownMessages.length === 0 && <p className="muted">لا توجد رسائل بعد.</p>}
        <div className="chat">
          {[...shownMessages].reverse().map((m) => (
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
        {shownDecisions.length === 0 && <p className="muted">لا توجد قرارات بعد.</p>}
        {shownDecisions.slice(0, 20).map((d) => (
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

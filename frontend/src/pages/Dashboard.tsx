import { useEffect, useState } from "react";
import { api } from "../api";
import type { Account, Decision, Event, Group, Message, Settings } from "../types";

export default function Dashboard() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [settings, setSettings] = useState<Settings | null>(null);

  useEffect(() => {
    async function load() {
      const [a, g, m, d, e, s] = await Promise.all([
        api.accounts.list(),
        api.groups.list(),
        api.monitor.messages(),
        api.monitor.decisions(),
        api.monitor.events(),
        api.settings.get(),
      ]);
      setAccounts(a);
      setGroups(g);
      setMessages(m);
      setDecisions(d);
      setEvents(e);
      setSettings(s);
    }
    load().catch(() => undefined);
  }, []);

  const online = accounts.filter((a) => a.status === "online").length;
  const replies = decisions.filter((d) => d.action === "reply").length;
  const escalations = decisions.filter((d) => d.action === "escalate").length;

  return (
    <>
      <h2>لوحة التحكم</h2>
      <div className="grid">
        <Stat title="الحسابات المتصلة" value={`${online} / ${accounts.length}`} />
        <Stat title="المجموعات المراقَبة" value={`${groups.filter((g) => g.active).length} / ${groups.length}`} />
        <Stat title="إجمالي الرسائل" value={messages.length} />
        <Stat title="ردود AI" value={replies} />
        <Stat title="حالات تصعيد" value={escalations} />
        <Stat
          title="حالة Gemini"
          value={settings?.gemini_configured ? "مُفعّل ✅" : "غير مُعدّ ⚠️"}
        />
      </div>

      {settings && !settings.telegram_api_configured && (
        <div className="card" style={{ borderColor: "var(--warn)" }}>
          <strong>⚠️ لم يتم إعداد بيانات تليجرام بعد.</strong>
          <p className="muted">
            اذهب إلى «الإعدادات» وأدخل Telegram API ID/Hash ومفتاح Gemini للبدء. يمكنك الحصول على
            API ID/Hash من my.telegram.org.
          </p>
        </div>
      )}

      <div className="card">
        <h3>أحدث الأحداث</h3>
        {events.length === 0 && <p className="muted">لا توجد أحداث بعد.</p>}
        {events.slice(0, 10).map((e) => (
          <div key={e.id} className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
            <span className={`badge ${e.level}`}>{e.level}</span>
            <span style={{ flex: 3 }}>{e.message}</span>
            <span className="muted small">{new Date(e.created_at).toLocaleString("ar")}</span>
          </div>
        ))}
      </div>
    </>
  );
}

function Stat({ title, value }: { title: string; value: string | number }) {
  return (
    <div className="card">
      <div className="muted small">{title}</div>
      <div style={{ fontSize: 24, fontWeight: 700, marginTop: 6 }}>{value}</div>
    </div>
  );
}

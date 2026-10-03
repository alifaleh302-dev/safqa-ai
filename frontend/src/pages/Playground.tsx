import { useEffect, useState } from "react";
import { api } from "../api";
import type { Group } from "../types";

interface Props {
  notify: (text: string, kind?: "ok" | "err") => void;
}

export default function Playground({ notify }: Props) {
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState<number | "">("");
  const [sender, setSender] = useState("عميل");
  const [text, setText] = useState("");
  const [result, setResult] = useState<{ action: string; reply: string; reason: string } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.groups.list().then((g) => {
      setGroups(g);
      if (g.length) setGroupId(g[0].id);
    }).catch(() => undefined);
  }, []);

  async function run() {
    if (groupId === "" || !text.trim()) return notify("اختر مجموعة واكتب رسالة", "err");
    setLoading(true);
    setResult(null);
    try {
      const r = await api.monitor.test({ group_id: groupId, text, sender_name: sender });
      setResult(r);
    } catch (e) {
      notify(String((e as Error).message), "err");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h2>تجربة الردود (بدون إرسال إلى تليجرام)</h2>
      <div className="card">
        <p className="muted">
          اكتب رسالة كأنك عميل، وسيولّد المتفاوض رده وفق البرومبت المرتبط بالمجموعة. آمن تماماً — لا يُرسل شيء
          إلى تليجرام.
        </p>
        <div className="row">
          <select value={groupId} onChange={(e) => setGroupId(e.target.value === "" ? "" : Number(e.target.value))}>
            <option value="">— اختر المجموعة —</option>
            {groups.map((g) => (
              <option key={g.id} value={g.id}>
                {g.title || g.telegram_id}
              </option>
            ))}
          </select>
          <input value={sender} onChange={(e) => setSender(e.target.value)} placeholder="اسم المرسل" />
        </div>
        <textarea
          style={{ marginTop: 10 }}
          placeholder="مثال: بكم هذا المنتج؟ وهل يوجد خصم؟"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div style={{ marginTop: 10 }}>
          <button className="primary" onClick={run} disabled={loading}>
            {loading ? "جارٍ التفكير…" : "توليد الرد"}
          </button>
        </div>
      </div>

      {result && (
        <div className="card">
          <div>
            القرار: <span className={`badge ${result.action}`}>{result.action}</span>
          </div>
          {result.reason && <div className="muted small" style={{ marginTop: 8 }}>السبب: {result.reason}</div>}
          {result.reply && (
            <div style={{ marginTop: 12 }}>
              <div className="muted small">الرد المقترح:</div>
              <div className="bubble out" style={{ maxWidth: "100%" }}>{result.reply}</div>
            </div>
          )}
        </div>
      )}
    </>
  );
}

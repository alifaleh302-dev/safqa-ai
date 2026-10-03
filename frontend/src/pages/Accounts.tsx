import { useEffect, useState } from "react";
import { api } from "../api";
import type { Account } from "../types";

interface Props {
  notify: (text: string, kind?: "ok" | "err") => void;
}

export default function Accounts({ notify }: Props) {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [label, setLabel] = useState("");
  const [phone, setPhone] = useState("");
  const [flow, setFlow] = useState<{ id: number; step: "code" | "password" } | null>(null);
  const [value, setValue] = useState("");

  async function load() {
    setAccounts(await api.accounts.list());
  }
  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  async function create() {
    if (!label || !phone) return notify("أدخل الاسم ورقم الهاتف", "err");
    try {
      await api.accounts.create({ label, phone });
      setLabel("");
      setPhone("");
      await load();
      notify("تمت إضافة الحساب. الآن اضغط «تسجيل الدخول».");
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  async function action(fn: () => Promise<unknown>, okMsg: string) {
    try {
      await fn();
      await load();
      notify(okMsg);
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  async function sendCode(id: number) {
    try {
      await api.accounts.sendCode(id);
      setFlow({ id, step: "code" });
      setValue("");
      await load();
      notify("تم إرسال كود التحقق إلى تليجرام. أدخله هنا.");
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  async function submitCode() {
    if (!flow) return;
    try {
      const acc = await api.accounts.verifyCode(flow.id, value);
      setValue("");
      if (acc.status === "awaiting_password") {
        setFlow({ id: flow.id, step: "password" });
        notify("الحساب محمي بكلمة مرور (2FA). أدخلها.");
      } else {
        setFlow(null);
        notify("تم تسجيل الدخول والاتصال بنجاح ✅");
      }
      await load();
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  async function submitPassword() {
    if (!flow) return;
    try {
      await api.accounts.verifyPassword(flow.id, value);
      setFlow(null);
      setValue("");
      await load();
      notify("تم تسجيل الدخول بنجاح ✅");
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  return (
    <>
      <h2>الحسابات (Userbot)</h2>
      <div className="card">
        <p className="muted">
          أضف حساب تليجرام (يُفضّل حساب مخصّص لا حسابك الشخصي) ثم سجّل الدخول. تُخزّن الجلسة مشفّرة.
        </p>
        <div className="row">
          <input placeholder="اسم الحساب (مثال: حساب المبيعات)" value={label} onChange={(e) => setLabel(e.target.value)} />
          <input placeholder="رقم الهاتف بصيغة دولية +20..." value={phone} onChange={(e) => setPhone(e.target.value)} />
          <button className="primary" onClick={create}>
            إضافة حساب
          </button>
        </div>
      </div>

      {flow && (
        <div className="card" style={{ borderColor: "var(--accent)" }}>
          <strong>{flow.step === "code" ? "أدخل كود التحقق" : "أدخل كلمة مرور 2FA"}</strong>
          <div className="row" style={{ marginTop: 10 }}>
            <input
              placeholder={flow.step === "code" ? "12345" : "كلمة المرور"}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              type={flow.step === "password" ? "password" : "text"}
            />
            <button className="primary" onClick={flow.step === "code" ? submitCode : submitPassword}>
              تأكيد
            </button>
            <button className="ghost" onClick={() => setFlow(null)}>
              إلغاء
            </button>
          </div>
        </div>
      )}

      {accounts.map((a) => (
        <div className="card" key={a.id}>
          <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong>{a.label}</strong> <span className="muted small">{a.phone}</span>
              <div style={{ marginTop: 6 }}>
                <span className={`badge ${a.status}`}>{a.status}</span>
                {a.has_session && <span className="muted small" style={{ marginInlineStart: 8 }}>جلسة محفوظة</span>}
              </div>
            </div>
            <div className="row" style={{ flex: "0 0 auto" }}>
              {a.status !== "online" && (
                <button className="good" onClick={() => sendCode(a.id)}>
                  تسجيل الدخول
                </button>
              )}
              {a.status !== "online" && a.has_session && (
                <button onClick={() => action(() => api.accounts.connect(a.id), "تم الاتصال")}>اتصال بالجلسة</button>
              )}
              {a.status === "online" && (
                <button onClick={() => action(() => api.accounts.disconnect(a.id), "تم قطع الاتصال")}>قطع الاتصال</button>
              )}
              <button
                className="bad"
                onClick={() => {
                  if (confirm("تأكيد حذف الحساب؟")) action(() => api.accounts.remove(a.id), "تم الحذف");
                }}
              >
                حذف
              </button>
            </div>
          </div>
        </div>
      ))}
    </>
  );
}

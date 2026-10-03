import { useState } from "react";
import { api, setToken } from "../api";

interface Props {
  onSuccess: (username: string) => void;
}

export default function Login({ onSuccess }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.auth.login(username, password);
      setToken(res.access_token);
      onSuccess(res.username);
    } catch (err) {
      setError(String((err as Error).message));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <h1>🤖 المتفاوض الذكي</h1>
        <p className="muted">سجّل الدخول للوصول إلى لوحة الإدارة</p>
        <label className="muted small">اسم المستخدم</label>
        <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        <label className="muted small" style={{ marginTop: 12, display: "block" }}>
          كلمة المرور
        </label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <div className="login-error">{error}</div>}
        <button className="primary" type="submit" disabled={loading} style={{ marginTop: 16, width: "100%" }}>
          {loading ? "جارٍ الدخول…" : "دخول"}
        </button>
      </form>
    </div>
  );
}

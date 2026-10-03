import { useState } from "react";
import Dashboard from "./pages/Dashboard";
import Accounts from "./pages/Accounts";
import Prompts from "./pages/Prompts";
import Groups from "./pages/Groups";
import Monitor from "./pages/Monitor";
import Playground from "./pages/Playground";
import SettingsPage from "./pages/Settings";

type PageKey = "dashboard" | "accounts" | "prompts" | "groups" | "monitor" | "playground" | "settings";

const NAV: { key: PageKey; label: string }[] = [
  { key: "dashboard", label: "لوحة التحكم" },
  { key: "accounts", label: "الحسابات" },
  { key: "prompts", label: "البرومبتات" },
  { key: "groups", label: "المجموعات" },
  { key: "monitor", label: "المراقبة الحيّة" },
  { key: "playground", label: "تجربة الردود" },
  { key: "settings", label: "الإعدادات" },
];

export default function App() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const [toast, setToast] = useState<{ text: string; kind: "ok" | "err" } | null>(null);

  function notify(text: string, kind: "ok" | "err" = "ok") {
    setToast({ text, kind });
    window.setTimeout(() => setToast(null), 5000);
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>🤖 المتفاوض الذكي</h1>
        <p>Telegram AI Negotiator</p>
        {NAV.map((item) => (
          <button
            key={item.key}
            className={`nav-item ${page === item.key ? "active" : ""}`}
            onClick={() => setPage(item.key)}
          >
            {item.label}
          </button>
        ))}
      </aside>

      <main className="content">
        {page === "dashboard" && <Dashboard />}
        {page === "accounts" && <Accounts notify={notify} />}
        {page === "prompts" && <Prompts notify={notify} />}
        {page === "groups" && <Groups notify={notify} />}
        {page === "monitor" && <Monitor />}
        {page === "playground" && <Playground notify={notify} />}
        {page === "settings" && <SettingsPage notify={notify} />}
      </main>

      {toast && (
        <div className="toast" style={{ borderColor: toast.kind === "err" ? "var(--danger)" : "var(--accent-2)" }}>
          {toast.kind === "err" ? "⚠️ " : "✅ "}
          {toast.text}
        </div>
      )}
    </div>
  );
}

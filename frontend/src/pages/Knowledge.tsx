import { useEffect, useState } from "react";
import { api } from "../api";
import type { KnowledgeBase, Product } from "../types";

interface Props {
  notify: (text: string, kind?: "ok" | "err") => void;
}

const EMPTY: Product = { name: "", name_en: "", price: 0, min_price: 0, currency: "USD", features: [], delivery: "" };

export default function Knowledge({ notify }: Props) {
  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [preview, setPreview] = useState("");
  const [query, setQuery] = useState("");

  async function load() {
    const data = await api.knowledge.get();
    setKb(data);
    setProducts(data.products);
    setPreview(data.rendered);
  }
  useEffect(() => {
    load().catch((e) => notify(String((e as Error).message), "err"));
  }, []);

  function update(index: number, patch: Partial<Product>) {
    setProducts((prev) => prev.map((p, i) => (i === index ? { ...p, ...patch } : p)));
  }

  function add() {
    setProducts((prev) => [...prev, { ...EMPTY }]);
  }

  function remove(index: number) {
    setProducts((prev) => prev.filter((_, i) => i !== index));
  }

  async function save() {
    try {
      const cleaned = products
        .filter((p) => p.name.trim())
        .map((p) => ({
          ...p,
          features: (p.features ?? []).filter((f) => f.trim()),
        }));
      const data = await api.knowledge.update({ currency: "USD", products: cleaned });
      setKb(data);
      setProducts(data.products);
      setPreview(data.rendered);
      notify("تم حفظ قاعدة المنتجات");
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  async function runPreview() {
    try {
      const data = await api.knowledge.get();
      setPreview(data.rendered);
      notify("تم تحديث المعاينة");
    } catch (e) {
      notify(String((e as Error).message), "err");
    }
  }

  return (
    <>
      <h2>قاعدة المنتجات (RAG)</h2>
      <div className="card">
        <p className="muted">
          المنتجات والأسعار هنا تُحقن تلقائياً في البرومبت المُرسل للذكاء، فلا حاجة لكتابة الأسعار يدوياً في
          البرومبت. «الحد الأدنى» يبقى مخفياً عن العميل ويستخدمه الذكاء كحدّ للتفاوض.
        </p>
        <div className="muted small">الملف: {kb?.path}</div>
      </div>

      {products.map((p, i) => (
        <div className="card" key={i}>
          <div className="row">
            <input placeholder="الاسم بالعربية" value={p.name} onChange={(e) => update(i, { name: e.target.value })} />
            <input placeholder="الاسم بالإنجليزية" value={p.name_en ?? ""} onChange={(e) => update(i, { name_en: e.target.value })} />
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            <input
              type="number"
              placeholder="السعر"
              value={p.price ?? 0}
              onChange={(e) => update(i, { price: Number(e.target.value) })}
            />
            <input
              type="number"
              placeholder="الحد الأدنى (مخفي)"
              value={p.min_price ?? 0}
              onChange={(e) => update(i, { min_price: Number(e.target.value) })}
            />
            <input placeholder="العملة" value={p.currency ?? ""} onChange={(e) => update(i, { currency: e.target.value })} />
            <input placeholder="التسليم" value={p.delivery ?? ""} onChange={(e) => update(i, { delivery: e.target.value })} />
          </div>
          <input
            style={{ marginTop: 8 }}
            placeholder="الميزات مفصولة بفواصل"
            value={(p.features ?? []).join(", ")}
            onChange={(e) => update(i, { features: e.target.value.split(",").map((s) => s.trim()) })}
          />
          <div style={{ marginTop: 10 }}>
            <button className="bad" onClick={() => remove(i)}>
              حذف المنتج
            </button>
          </div>
        </div>
      ))}

      <div className="row" style={{ marginBottom: 14 }}>
        <button onClick={add}>+ إضافة منتج</button>
        <button className="primary" onClick={save}>
          حفظ
        </button>
      </div>

      <div className="card">
        <h3>معاينة السياق المُحقون</h3>
        <p className="muted small">هذا هو النص الذي يُضاف إلى البرومبت فعلياً.</p>
        <pre style={{ whiteSpace: "pre-wrap", fontSize: 13, color: "var(--muted)" }}>{preview}</pre>
        <div className="row" style={{ marginTop: 8 }}>
          <input placeholder="جرّب استعلاماً لرؤية المنتجات الأكثر صلة" value={query} onChange={(e) => setQuery(e.target.value)} />
          <button onClick={runPreview}>تحديث</button>
        </div>
      </div>
    </>
  );
}

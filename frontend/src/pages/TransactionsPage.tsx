import { useCallback, useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";
import { api, json } from "../api";
import { dateLabel, naira } from "../format";
import { CATEGORIES, type Category, type Direction, type ImportResult, type TxnPage } from "../types";

const PAGE_SIZE = 25;

export default function TransactionsPage() {
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<"" | Category>("");
  const [q, setQ] = useState("");
  const [data, setData] = useState<TxnPage | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [drag, setDrag] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    const p = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    if (filter) p.set("category", filter);
    if (q.trim()) p.set("q", q.trim());
    api<TxnPage>(`/v1/transactions?${p}`).then(setData).catch((e) => setError(e.message));
  }, [page, filter, q]);

  useEffect(() => { load(); }, [load]);

  async function upload(file: File) {
    setError(""); setResult(null); setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      setResult(await api<ImportResult>("/v1/transactions/import", { method: "POST", body: fd }));
      setPage(1); load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault(); setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) upload(f);
  }

  async function recategorise(id: string, category: Category) {
    try {
      await api(`/v1/transactions/${id}`, { method: "PATCH", body: json({ category }) });
      load();
    } catch (e) { setError((e as Error).message); }
  }

  async function remove(id: string) {
    if (!confirm("Delete this transaction?")) return;
    await api(`/v1/transactions/${id}`, { method: "DELETE" }).catch((e) => setError(e.message));
    load();
  }

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Transactions</h1>
          <p className="muted">Upload statements as often as you like — lines you've already uploaded are skipped automatically.</p>
        </div>
        <button className="btn ghost" onClick={() => setShowManual(!showManual)}>{showManual ? "Close" : "Add a cash sale or expense"}</button>
      </div>

      {showManual && <ManualEntry onAdded={() => { setShowManual(false); load(); }} />}

      <div className={`dropzone ${drag ? "drag" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={onDrop}>
        <div>
          <h2>Upload a statement</h2>
          <p className="muted small" style={{ marginTop: 4, maxWidth: "52ch" }}>
            CSV from any Nigerian bank, OPay, Moniepoint or PalmPay, up to 2 MB. Needs a date, a description, and either an amount or debit/credit columns.
            No statement handy? Try the <a href="/sample-statement.csv" download>sample statement</a> (then its <a href="/sample-statement-feb-2026.csv" download>missing February</a>).
          </p>
        </div>
        <div>
          <input ref={fileInput} type="file" accept=".csv,text/csv" hidden onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
          <button className="btn" disabled={uploading} onClick={() => fileInput.current?.click()}>{uploading ? "Reading statement…" : "Choose CSV file"}</button>
        </div>
      </div>

      {result && (
        <div className={`alert ${result.imported ? "ok" : "note"}`} role="status" style={{ marginTop: 12 }}>
          Added {result.imported} new transaction{result.imported === 1 ? "" : "s"}
          {result.duplicates > 0 && `, skipped ${result.duplicates} already uploaded`}
          {result.rejected > 0 && `, ${result.rejected} row(s) couldn't be read`}.
          {result.errors.length > 0 && <details style={{ marginTop: 6 }}><summary>Show unreadable rows</summary><ul>{result.errors.map((e) => <li key={e}>{e}</li>)}</ul></details>}
        </div>
      )}
      {error && <div className="alert" role="alert" style={{ marginTop: 12 }}>{error}</div>}

      <div className="toolbar">
        <input className="inline" placeholder="Search descriptions" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} aria-label="Search descriptions" />
        <select className="inline" value={filter} onChange={(e) => { setFilter(e.target.value as Category | ""); setPage(1); }} aria-label="Filter by category">
          <option value="">All categories</option>
          {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        {data && <span className="muted small">{data.total.toLocaleString()} transactions</span>}
      </div>

      {data && data.total === 0 ? (
        <div className="empty panel">
          <h2>{filter || q ? "No transactions match" : "No transactions yet"}</h2>
          <p>{filter || q ? "Clear the search or category filter to see everything." : "Upload a statement above to get your readiness score."}</p>
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="table">
            <thead><tr><th>Date</th><th>Description</th><th className="hide-sm">Category</th><th className="amt">Amount</th><th aria-label="Actions" /></tr></thead>
            <tbody>
              {data?.items.map((t) => (
                <tr key={t.id}>
                  <td style={{ whiteSpace: "nowrap" }}>{dateLabel(t.txn_date)}</td>
                  <td className="narr">{t.narration}{t.counterparty && <small>{t.counterparty}</small>}</td>
                  <td className="hide-sm">
                    <select className={t.category === "uncategorised" ? "needs" : ""} value={t.category}
                      onChange={(e) => recategorise(t.id, e.target.value as Category)} aria-label="Category">
                      {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  </td>
                  <td className={`amt ${t.direction}`}>{t.direction === "credit" ? "+" : "−"}{naira(t.amount_kobo)}</td>
                  <td><button className="icon-btn" onClick={() => remove(t.id)} aria-label="Delete transaction" title="Delete">×</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {pages > 1 && (
        <div className="pager">
          <button className="btn ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span className="small num">Page {page} of {pages}</span>
          <button className="btn ghost" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      )}
    </>
  );
}

function ManualEntry({ onAdded }: { onAdded: () => void }) {
  const [f, setF] = useState({ txn_date: new Date().toISOString().slice(0, 10), narration: "", amount: "", direction: "credit" as Direction, category: "sales" as Category });
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/v1/transactions", { method: "POST", body: json({ txn_date: f.txn_date, narration: f.narration, amount_naira: Number(f.amount), direction: f.direction, category: f.category }) });
      onAdded();
    } catch (err) { setError((err as Error).message); }
  }

  return (
    <form className="panel grid-form" onSubmit={submit} style={{ marginBottom: 20 }}>
      <label className="field">Date<input type="date" value={f.txn_date} onChange={(e) => setF({ ...f, txn_date: e.target.value })} required /></label>
      <label className="field">Money
        <select value={f.direction} onChange={(e) => setF({ ...f, direction: e.target.value as Direction, category: e.target.value === "credit" ? "sales" : "inventory" })}>
          <option value="credit">Came in</option><option value="debit">Went out</option>
        </select>
      </label>
      <label className="field full">What was it?<input value={f.narration} onChange={(e) => setF({ ...f, narration: e.target.value })} required placeholder="e.g. Cash sales, Saturday market" /></label>
      <label className="field">Amount (₦)<input type="number" min="1" step="any" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} required /></label>
      <label className="field">Category
        <select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value as Category })}>
          {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </label>
      {error && <div className="alert full" role="alert">{error}</div>}
      <div className="full"><button className="btn">Add transaction</button></div>
    </form>
  );
}

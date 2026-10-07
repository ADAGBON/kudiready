import { useEffect, useState, type FormEvent } from "react";
import { api, json } from "../api";
import { dateLabel } from "../format";
import type { ShareLink } from "../types";

const linkFor = (token: string) => `${window.location.origin}/p/${token}`;

export default function SharePage() {
  const [links, setLinks] = useState<ShareLink[]>([]);
  const [label, setLabel] = useState("");
  const [created, setCreated] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const load = () => api<ShareLink[]>("/v1/share-links").then(setLinks).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    setError(""); setCopied(false);
    try {
      const l = await api<ShareLink>("/v1/share-links", { method: "POST", body: json({ label }) });
      setCreated(linkFor(l.token!));
      setLabel("");
      load();
    } catch (err) { setError((err as Error).message); }
  }

  async function revoke(id: string) {
    if (!confirm("Revoke this link? Anyone holding it will lose access.")) return;
    await api(`/v1/share-links/${id}`, { method: "DELETE" });
    load();
  }

  async function copy() {
    if (!created) return;
    try { await navigator.clipboard.writeText(created); setCopied(true); } catch { /* user can copy manually */ }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Share with a lender</h1>
          <p className="muted">Each link is read-only, shows your file as it is right now, and expires after 14 days. Revoke it any time. Lenders don't need an account.</p>
        </div>
      </div>

      <form className="panel" onSubmit={create} style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
        <label className="field" style={{ flex: "1 1 260px" }}>Who is this link for?
          <input value={label} onChange={(e) => setLabel(e.target.value)} required maxLength={80} placeholder="e.g. LAPO Microfinance, Ikeja branch" />
        </label>
        <button className="btn">Create link</button>
      </form>

      {created && (
        <div className="alert ok" role="status" style={{ marginTop: 12, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ wordBreak: "break-all", flex: "1 1 300px" }}>{created}</span>
          <button className="btn ghost" type="button" onClick={copy}>{copied ? "Copied" : "Copy link"}</button>
          <a className="btn ghost" href={created} target="_blank" rel="noreferrer">Preview</a>
        </div>
      )}
      {created && <p className="small muted" style={{ marginTop: 6 }}>Copy it now — for your security we can't show this link again.</p>}
      {error && <div className="alert" role="alert" style={{ marginTop: 12 }}>{error}</div>}

      <div className="section">
        <header><h2>Your links</h2></header>
        {links.length === 0 ? <p className="muted">You haven't shared your file yet.</p> : (
          <table className="table">
            <thead><tr><th>For</th><th>Created</th><th>Expires</th><th>Views</th><th aria-label="Status" /></tr></thead>
            <tbody>
              {links.map((l) => {
                const expired = new Date(l.expires_at) < new Date();
                return (
                  <tr key={l.id}>
                    <td>{l.label}</td>
                    <td>{dateLabel(l.created_at)}</td>
                    <td>{dateLabel(l.expires_at)}</td>
                    <td className="num">{l.view_count}</td>
                    <td>{l.revoked ? <span className="muted">Revoked</span> : expired ? <span className="muted">Expired</span> :
                      <button className="btn danger" onClick={() => revoke(l.id)}>Revoke</button>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

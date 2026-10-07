import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, json } from "../api";
import { useAuth } from "../auth";
import { SECTOR_LABELS, type Business } from "../types";

const EMPTY: Business = {
  name: "", sector: "retail_trade", state: "Lagos", years_operating: 1, employees: 0,
  has_cac_registration: false, has_tin: false, has_business_account: false, keeps_written_records: false,
};

export default function BusinessPage({ setup = false }: { setup?: boolean }) {
  const nav = useNavigate();
  const { refresh } = useAuth();
  const [b, setB] = useState<Business>(EMPTY);
  const [states, setStates] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<{ states: string[] }>("/v1/business/options", {}, false).then((o) => setStates(o.states)).catch(() => {});
    if (!setup) api<Business>("/v1/business").then(setB).catch((e) => setError(e.message));
  }, [setup]);

  const set = <K extends keyof Business>(k: K, v: Business[K]) => { setB({ ...b, [k]: v }); setSaved(false); };

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const { id: _id, ...body } = b as Business & { created_at?: string };
    delete (body as { created_at?: string }).created_at;
    try {
      await api("/v1/business", { method: setup ? "POST" : "PUT", body: json(body) });
      if (setup) { await refresh(); nav("/transactions"); } else setSaved(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{setup ? "Tell us about your business" : "Business profile"}</h1>
          <p className="muted">Lenders read your numbers against who you are. These details also decide which registration steps appear in your fix list.</p>
        </div>
      </div>
      <form className="panel grid-form" onSubmit={submit}>
        <label className="field full">Business name
          <input value={b.name} onChange={(e) => set("name", e.target.value)} required minLength={2} placeholder="e.g. Mama Ada Provisions" />
        </label>
        <label className="field">What you do
          <select value={b.sector} onChange={(e) => set("sector", e.target.value)}>
            {Object.entries(SECTOR_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label className="field">State
          <select value={b.state} onChange={(e) => set("state", e.target.value)}>
            {(states.length ? states : [b.state]).map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <label className="field">Years in business
          <input type="number" min={0} max={100} value={b.years_operating} onChange={(e) => set("years_operating", Number(e.target.value))} />
        </label>
        <label className="field">People working with you
          <input type="number" min={0} max={10000} value={b.employees} onChange={(e) => set("employees", Number(e.target.value))} />
        </label>
        <fieldset className="full" style={{ border: 0, padding: 0, margin: 0, display: "grid", gap: 12 }}>
          <legend style={{ fontWeight: 600, marginBottom: 10 }}>Which of these do you have?</legend>
          <label className="check"><input type="checkbox" checked={b.has_cac_registration} onChange={(e) => set("has_cac_registration", e.target.checked)} />CAC business registration</label>
          <label className="check"><input type="checkbox" checked={b.has_tin} onChange={(e) => set("has_tin", e.target.checked)} />Tax Identification Number (TIN)</label>
          <label className="check"><input type="checkbox" checked={b.has_business_account} onChange={(e) => set("has_business_account", e.target.checked)} />A bank account used only for the business</label>
          <label className="check"><input type="checkbox" checked={b.keeps_written_records} onChange={(e) => set("keeps_written_records", e.target.checked)} />A sales book or written records</label>
          <span className="small muted">We only store yes or no — never your CAC, TIN or BVN numbers.</span>
        </fieldset>
        {error && <div className="alert full" role="alert">{error}</div>}
        {saved && <div className="alert ok full" role="status">Profile saved. Your score has been updated.</div>}
        <div className="full"><button className="btn" disabled={busy}>{busy ? "Saving…" : setup ? "Save and continue" : "Save profile"}</button></div>
      </form>
    </>
  );
}

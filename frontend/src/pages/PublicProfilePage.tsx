import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { Breakdown, CapacityNote, CashflowChart, Facts, GapList, ScorePanel } from "../components/Report";
import { dateLabel } from "../format";
import { SECTOR_LABELS, type Assessment } from "../types";

export default function PublicProfilePage() {
  const { token } = useParams();
  const [a, setA] = useState<Assessment | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Assessment>(`/v1/public/profile/${encodeURIComponent(token ?? "")}`, {}, false).then(setA).catch((e) => setError(e.message));
  }, [token]);

  if (error) return <div className="public"><h1>Link unavailable</h1><p className="muted" style={{ marginTop: 8 }}>{error}. Ask the business owner for a new link.</p></div>;
  if (!a) return <div className="public"><p className="muted">Loading credit file…</p></div>;

  const b = a.business;
  const formal = [b.has_cac_registration && "CAC registered", b.has_tin && "Has TIN", b.has_business_account && "Separate business account"].filter(Boolean);
  return (
    <div className="public">
      <div className="public-head">
        <div className="brand" style={{ color: "var(--indigo)", padding: 0 }}><span className="brand-mark">K</span>KudiReady credit file</div>
        <button className="btn ghost no-print" onClick={() => window.print()}>Print or save as PDF</button>
      </div>
      <h1>{b.name}</h1>
      <p className="muted" style={{ margin: "6px 0 24px" }}>
        {SECTOR_LABELS[b.sector] ?? b.sector}, {b.state}. {b.years_operating} year(s) trading, {b.employees} staff. {formal.length ? formal.join(", ") + "." : "Not yet formally registered."}
        <br />Prepared for {a.label} on {dateLabel(a.shared_at ?? a.generated_at)}.
      </p>
      <ScorePanel a={a} />
      <div className="section"><Facts ind={a.indicators} capacity={a.capacity} /><CapacityNote /></div>
      {a.indicators.monthly && <div className="section"><header><h2>Money in and out by month</h2></header><CashflowChart monthly={a.indicators.monthly} /></div>}
      <div className="section"><header><h2>How the score is made</h2></header><Breakdown pillars={a.score.pillars} /></div>
      {a.gaps.length > 0 && <div className="section"><header><h2>Known gaps in this file</h2></header><GapList gaps={a.gaps} /></div>}
      <p className="disclaimer">
        Figures are computed from statements the business uploaded; KudiReady does not verify them with the issuing bank. The readiness score measures how complete and lender-legible the records are. It is not a credit score, a credit decision, or a recommendation to lend.
      </p>
    </div>
  );
}

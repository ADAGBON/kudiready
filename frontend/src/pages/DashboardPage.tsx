import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Breakdown, CapacityNote, CashflowChart, Facts, GapList, ScorePanel } from "../components/Report";
import type { Assessment } from "../types";

export function useAssessment() {
  const [a, setA] = useState<Assessment | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Assessment>("/v1/readiness").then(setA).catch((e) => setError(e.message));
  }, []);
  return { a, error };
}

export default function DashboardPage() {
  const { a, error } = useAssessment();
  if (error) return <div className="alert" role="alert">{error}</div>;
  if (!a) return <p className="muted">Reading your records…</p>;

  const ind = a.indicators;
  return (
    <>
      <div className="page-head">
        <div>
          <h1>{a.business.name}</h1>
          <p className="muted">{a.summary}</p>
        </div>
        {ind.has_data && <Link className="btn ghost" to="/share">Share with a lender</Link>}
      </div>

      <ScorePanel a={a} />

      {!ind.has_data ? (
        <div className="empty">
          <h2>Upload your first statement</h2>
          <p>Download a CSV statement from your bank app, OPay, Moniepoint or PalmPay and upload it. Six months or more gives lenders a fair picture.</p>
          <Link className="btn" to="/transactions">Upload a statement</Link>
        </div>
      ) : (
        <>
          <div className="section">
            <Facts ind={ind} capacity={a.capacity} />
            <CapacityNote />
          </div>

          <div className="section">
            <header><h2>Money in and out by month</h2></header>
            <CashflowChart monthly={ind.monthly ?? []} />
          </div>

          <div className="section">
            <header>
              <h2>What to fix first</h2>
              <Link to="/fix">See all {a.gaps.length}</Link>
            </header>
            <GapList gaps={a.gaps} limit={3} />
          </div>

          <div className="section">
            <header><h2>How your score is made</h2></header>
            <Breakdown pillars={a.score.pillars} />
          </div>
        </>
      )}
    </>
  );
}

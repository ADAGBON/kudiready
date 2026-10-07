import { Link } from "react-router-dom";
import { GapList } from "../components/Report";
import { useAssessment } from "./DashboardPage";

export default function FixPage() {
  const { a, error } = useAssessment();
  if (error) return <div className="alert" role="alert">{error}</div>;
  if (!a) return <p className="muted">Checking your file…</p>;

  const potential = Math.round(a.gaps.reduce((s, g) => s + g.points_available, 0));
  return (
    <>
      <div className="page-head">
        <div>
          <h1>What to fix</h1>
          <p className="muted">
            Sorted by what matters most to a lender. {potential > 0 && <>Fixing everything here could add up to {potential} points.</>}
          </p>
        </div>
      </div>
      {a.gaps.length ? (
        <GapList gaps={a.gaps} />
      ) : (
        <div className="empty">
          <h2>Nothing left to fix</h2>
          <p>Your file is complete. Share it with a lender when you're ready to apply.</p>
          <Link className="btn" to="/share">Share with a lender</Link>
        </div>
      )}
      <p className="small muted" style={{ marginTop: 24 }}>
        Records fixes: upload or categorise on the <Link to="/transactions">Transactions</Link> page. Registration fixes: tick them on your <Link to="/profile">business profile</Link> once done.
      </p>
    </>
  );
}

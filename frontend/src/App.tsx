import { Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import AuthPage from "./pages/AuthPage";
import BusinessPage from "./pages/BusinessPage";
import DashboardPage from "./pages/DashboardPage";
import FixPage from "./pages/FixPage";
import PublicProfilePage from "./pages/PublicProfilePage";
import SharePage from "./pages/SharePage";
import TransactionsPage from "./pages/TransactionsPage";

function Shell() {
  const { user, logout } = useAuth();
  const link = ({ isActive }: { isActive: boolean }) => `link${isActive ? " active" : ""}`;
  return (
    <div className="shell">
      <nav className="nav no-print" aria-label="Main">
        <a className="brand" href="/"><span className="brand-mark">K</span>KudiReady</a>
        <NavLink to="/" end className={link}>Overview</NavLink>
        <NavLink to="/transactions" className={link}>Transactions</NavLink>
        <NavLink to="/fix" className={link}>What to fix</NavLink>
        <NavLink to="/share" className={link}>Share</NavLink>
        <NavLink to="/profile" className={link}>Profile</NavLink>
        <div className="nav-foot">
          {user?.full_name}<br />
          <button className="linkish" onClick={logout}>Log out</button>
        </div>
      </nav>
      <main className="content"><Outlet /></main>
    </div>
  );
}

function Protected() {
  const { user, loading } = useAuth();
  if (loading) return <p className="muted" style={{ padding: 40 }}>Loading…</p>;
  if (!user) return <AuthPage />;
  if (!user.has_business) return <main className="content" style={{ margin: "0 auto" }}><BusinessPage setup /></main>;
  return <Shell />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/p/:token" element={<PublicProfilePage />} />
      <Route element={<Protected />}>
        <Route index element={<DashboardPage />} />
        <Route path="transactions" element={<TransactionsPage />} />
        <Route path="fix" element={<FixPage />} />
        <Route path="share" element={<SharePage />} />
        <Route path="profile" element={<BusinessPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

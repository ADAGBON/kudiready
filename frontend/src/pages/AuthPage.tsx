import { useState, type FormEvent } from "react";
import { useAuth } from "../auth";

export default function AuthPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("register");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "register") await register(name, email, password);
      else await login(email, password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <aside className="auth-side adire">
        <a className="brand" href="/" style={{ padding: 0 }}><span className="brand-mark">K</span>KudiReady</a>
        <div>
          <h1>Your statements already tell lenders your story.</h1>
          <p>Upload your bank or mobile-money statement. See how a loan officer reads your business, what's missing, and exactly what to fix before you apply.</p>
        </div>
        <ul className="ledger-lines" aria-hidden="true">
          <li><span>Record quality</span><span>23 / 25</span></li>
          <li><span>Cash-flow strength</span><span>12 / 25</span></li>
          <li><span>Stability & trend</span><span>19 / 25</span></li>
          <li><span>Obligations & risk</span><span>20 / 25</span></li>
        </ul>
      </aside>
      <form className="auth-form" onSubmit={submit} noValidate>
        <div>
          <h2>{mode === "register" ? "Create your account" : "Log in"}</h2>
          <p className="muted" style={{ marginTop: 6 }}>Free for business owners. Your records stay private until you share them.</p>
        </div>
        {mode === "register" && (
          <label className="field">Your full name
            <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" required minLength={2} />
          </label>
        )}
        <label className="field">Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
        </label>
        <label className="field">Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "register" ? "new-password" : "current-password"} required minLength={8} />
          {mode === "register" && <span className="hint">At least 8 characters</span>}
        </label>
        {error && <div className="alert" role="alert">{error}</div>}
        <button className="btn" disabled={busy} type="submit">
          {busy ? "Please wait…" : mode === "register" ? "Create account" : "Log in"}
        </button>
        <p className="small muted">
          {mode === "register" ? "Already have an account? " : "New to KudiReady? "}
          <button type="button" className="linkish" onClick={() => { setMode(mode === "register" ? "login" : "register"); setError(""); }}>
            {mode === "register" ? "Log in" : "Create an account"}
          </button>
        </p>
      </form>
    </div>
  );
}

// Presentation pieces shared by the owner dashboard and the lender's public view.
import type { Assessment, Gap, Indicators, Pillar } from "../types";
import { monthLabel, naira, nairaShort, pct } from "../format";

function Ticks({ pillar }: { pillar: Pillar }) {
  // 25 ticks per pillar = 1 point each, like tally marks in a ledger.
  return (
    <div className="ticks" role="img" aria-label={`${pillar.points} of ${pillar.max} points`}>
      {Array.from({ length: pillar.max }, (_, i) => {
        const fill = Math.max(0, Math.min(1, pillar.points - i));
        const cls = fill >= 1 ? "on" : fill > 0 ? "part" : "";
        return <i key={i} className={cls} style={{ ["--i" as string]: i, ["--fill" as string]: `${fill * 100}%` }} />;
      })}
    </div>
  );
}

export function ScorePanel({ a }: { a: Assessment }) {
  const s = a.score;
  return (
    <section className="score-panel adire" aria-label="Credit readiness score">
      <div>
        <div className="score-number num">
          {s.total}
          <small> / 100</small>
        </div>
        <span className="band" data-band={s.band}>{s.band}</span>
        {s.cap_reason && <p className="cap-note">{s.cap_reason}. Upload more months to lift it.</p>}
      </div>
      <div className="tallies">
        {s.pillars.map((p) => (
          <div className="tally-row" key={p.code}>
            <span className="name">{p.name}</span>
            <Ticks pillar={p} />
            <span className="pts">{p.points.toFixed(0)}/{p.max}</span>
          </div>
        ))}
        {s.pillars.length === 0 && <p style={{ color: "#c9d0ea" }}>Your four readiness areas appear here once you upload a statement.</p>}
      </div>
    </section>
  );
}

export function Facts({ ind, capacity }: { ind: Indicators; capacity: Assessment["capacity"] }) {
  if (!ind.has_data) return null;
  return (
    <div className="facts">
      <div className="fact">
        <div className="v">{nairaShort(ind.avg_monthly_inflow_kobo ?? 0)}</div>
        <div className="k">Average money in per month</div>
      </div>
      <div className="fact">
        <div className="v">{pct(ind.operating_margin)}</div>
        <div className="k">Kept after running costs</div>
      </div>
      <div className="fact">
        <div className="v">{ind.months_with_data} months</div>
        <div className="k">{monthLabel(ind.period_start!, true)} – {monthLabel(ind.period_end!, true)}</div>
      </div>
      <div className="fact">
        <div className="v">{capacity ? nairaShort(capacity.indicative_repayment_kobo) : "—"}</div>
        <div className="k">Repayment you could carry monthly*</div>
      </div>
    </div>
  );
}

export function CashflowChart({ monthly }: { monthly: NonNullable<Indicators["monthly"]> }) {
  const W = 760, H = 240, pad = { l: 56, r: 8, t: 12, b: 28 };
  const max = Math.max(1, ...monthly.flatMap((m) => [m.inflow_kobo, m.outflow_kobo]));
  const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
  const slot = iw / monthly.length, bw = Math.min(18, slot / 3);
  const y = (v: number) => pad.t + ih - (v / max) * ih;
  const ticks = [0, 0.5, 1].map((f) => f * max);
  return (
    <div className="chart-wrap">
      <div className="legend" style={{ marginBottom: 8 }}>
        <span style={{ ["--c" as string]: "var(--in)" }}>Money in</span>
        <span style={{ ["--c" as string]: "var(--ink-3)" }}>Money out</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Monthly money in and money out">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke="var(--rule)" />
            <text x={pad.l - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--ink-3)">{nairaShort(t)}</text>
          </g>
        ))}
        {monthly.map((m, i) => {
          const cx = pad.l + slot * i + slot / 2;
          const missing = m.inflow_kobo === 0 && m.outflow_kobo === 0;
          return (
            <g key={m.month}>
              <title>{`${monthLabel(m.month, true)}: in ${naira(m.inflow_kobo)}, out ${naira(m.outflow_kobo)}`}</title>
              {missing ? (
                <rect x={cx - bw - 1} y={pad.t} width={bw * 2 + 2} height={ih} fill="var(--palm-pale)" stroke="var(--palm)" strokeDasharray="3 3" rx="3" />
              ) : (
                <>
                  <rect x={cx - bw - 1} y={y(m.inflow_kobo)} width={bw} height={pad.t + ih - y(m.inflow_kobo)} fill="var(--in)" rx="2" />
                  <rect x={cx + 1} y={y(m.outflow_kobo)} width={bw} height={pad.t + ih - y(m.outflow_kobo)} fill="var(--ink-3)" rx="2" />
                </>
              )}
              <text x={cx} y={H - 8} textAnchor="middle" fontSize="11" fill={missing ? "#8a5d00" : "var(--ink-2)"}>{monthLabel(m.month)}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function Breakdown({ pillars }: { pillars: Pillar[] }) {
  return (
    <div className="breakdown">
      {pillars.map((p) => (
        <div key={p.code}>
          <h3><span>{p.name}</span><span className="num">{p.points.toFixed(1)} / {p.max}</span></h3>
          {p.components.map((c) => (
            <div className="comp" key={c.code}>
              <span>{c.label}</span>
              <span className="p">{c.points.toFixed(1)} / {c.max}</span>
              <span className="d">{c.detail}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

const KIND: Record<Gap["kind"], string> = { data: "Records", formalisation: "Registration", financial: "Business health" };

export function GapList({ gaps, limit }: { gaps: Gap[]; limit?: number }) {
  const shown = limit ? gaps.slice(0, limit) : gaps;
  return (
    <ul className="gaps">
      {shown.map((g) => (
        <li className="gap" key={g.code}>
          <span className={`sev ${g.severity}`} aria-label={`${g.severity} priority`} />
          <div>
            <h3>{g.title}</h3>
            <p>{g.detail}</p>
            <span className="kind">{KIND[g.kind]}</span>
          </div>
          {g.points_available >= 0.5 ? <span className="gain">up to +{Math.round(g.points_available)}</span> : <span />}
        </li>
      ))}
    </ul>
  );
}

export function CapacityNote() {
  return (
    <p className="small muted" style={{ marginTop: 10 }}>
      * Indicative only: 35% of your average monthly free cash after all costs and existing loan repayments. It is a planning aid, not a loan offer or credit decision.
    </p>
  );
}

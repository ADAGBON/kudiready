export type Direction = "credit" | "debit";

export const CATEGORIES = {
  sales: "Sales",
  other_income: "Other income",
  loan_in: "Loan received",
  inventory: "Stock & supplies",
  rent: "Rent",
  payroll: "Staff pay",
  utilities: "Power, data & fuel",
  transport: "Transport & delivery",
  tax: "Tax & levies",
  loan_repayment: "Loan repayment",
  bank_charges: "Bank charges",
  transfer: "Own-account transfer",
  other_expense: "Other expense",
  uncategorised: "Not yet categorised",
} as const;
export type Category = keyof typeof CATEGORIES;

export const SECTOR_LABELS: Record<string, string> = {
  retail_trade: "Retail & provisions",
  food_services: "Food & catering",
  agriculture: "Agriculture",
  manufacturing: "Manufacturing",
  fashion_tailoring: "Fashion & tailoring",
  transport_logistics: "Transport & logistics",
  beauty_personal_care: "Beauty & personal care",
  ict_services: "ICT services",
  construction: "Construction",
  other: "Other",
};

export interface User { id: string; email: string; full_name: string; has_business: boolean }

export interface Business {
  id?: string;
  name: string;
  sector: string;
  state: string;
  years_operating: number;
  employees: number;
  has_cac_registration: boolean;
  has_tin: boolean;
  has_business_account: boolean;
  keeps_written_records: boolean;
}

export interface Txn {
  id: string;
  txn_date: string;
  narration: string;
  counterparty: string | null;
  amount_kobo: number;
  direction: Direction;
  category: Category;
  category_source: string;
  source: "csv" | "manual";
}

export interface TxnPage { items: Txn[]; total: number; page: number; page_size: number }

export interface ImportResult { rows_read: number; imported: number; duplicates: number; rejected: number; errors: string[] }

export interface Component { code: string; label: string; points: number; max: number; detail: string }
export interface Pillar { code: string; name: string; points: number; max: number; components: Component[] }
export interface Gap {
  code: string;
  title: string;
  detail: string;
  severity: "high" | "medium" | "low";
  kind: "data" | "formalisation" | "financial";
  points_available: number;
}

export interface Indicators {
  has_data: boolean;
  period_start?: string;
  period_end?: string;
  span_months?: number;
  months_with_data?: number;
  missing_months?: string[];
  transaction_count?: number;
  total_inflow_kobo?: number;
  total_outflow_kobo?: number;
  avg_monthly_inflow_kobo?: number;
  avg_monthly_net_kobo?: number;
  operating_margin?: number | null;
  positive_months_ratio?: number;
  inflow_volatility_cv?: number | null;
  debt_service_ratio?: number | null;
  top_customer_share?: number | null;
  monthly?: { month: string; inflow_kobo: number; outflow_kobo: number }[];
}

export interface Assessment {
  indicators: Indicators;
  score: { total: number; raw_total?: number; cap_reason?: string | null; band: string; pillars: Pillar[] };
  gaps: Gap[];
  capacity: { monthly_free_cash_kobo: number; indicative_repayment_kobo: number } | null;
  summary: string;
  business: Omit<Business, "id" | "keeps_written_records">;
  generated_at: string;
  label?: string;
  shared_at?: string;
}

export interface ShareLink { id: string; label: string; expires_at: string; revoked: boolean; view_count: number; created_at: string; token?: string }

export type WarningItem = {
  level: string;
  code: string;
  message: string;
  detail: string | null;
};

export type Realization = {
  sell_id: string;
  symbol: string;
  isin: string | null;
  name: string | null;
  broker: string;
  sell_date: string;
  buy_date: string;
  quantity: number;
  proceeds_pln: number;
  cost_pln: number;
  fees_pln: number;
  gain_pln: number;
  sell_currency: string;
  sell_price: number;
  buy_price: number;
  buy_currency: string;
  nbp_sell_rate: number;
  nbp_buy_rate: number;
  nbp_sell_table_date: string;
  nbp_buy_table_date: string;
  country: string | null;
};

export type DividendRow = {
  id: string;
  date: string;
  symbol: string;
  isin: string | null;
  name: string | null;
  broker: string;
  country: string | null;
  gross_pln: number;
  withholding_pln: number;
  polish_tax_19: number;
  credit_pln: number;
  to_pay_pln: number;
  currency: string;
  nbp_rate: number;
  nbp_table_date: string;
};

export type InterestRow = {
  id: string;
  date: string;
  broker: string;
  gross_pln: number;
  withholding_pln: number;
  currency: string;
  nbp_rate: number;
  nbp_table_date: string;
  notes: string;
};

export type OpenLot = {
  symbol: string;
  isin: string | null;
  name: string | null;
  broker: string;
  buy_date: string;
  quantity: number;
  price: number;
  currency: string;
  cost_pln: number;
  nbp_rate: number;
  nbp_table_date: string;
};

export type PitZgCountry = {
  country: string;
  country_name: string;
  securities_revenue_pln: number;
  securities_costs_pln: number;
  securities_income_pln: number;
  dividends_gross_pln: number;
  dividends_withholding_pln: number;
  interest_gross_pln: number;
};

export type Pit38Fields = {
  field_22_revenue: number;
  field_23_costs: number;
  field_28_income: number;
  field_29_loss: number;
  field_30_prior_losses: number;
  field_31_tax_base: number;
  field_33_tax: number;
  field_35_tax_due: number;
  field_47_div_tax: number;
  field_48_foreign_credit: number;
  field_49_div_to_pay: number;
  field_51_total_tax: number;
  field_72_pit_zg_count: number;
};

export type TaxSummary = {
  tax_year: number;
  brokers: string[];
  imported_files: string[];
  transaction_count: number;
  buy_count: number;
  sell_count: number;
  dividend_count: number;
  revenue_pln: number;
  costs_pln: number;
  income_pln: number;
  loss_pln: number;
  prior_losses_applied_pln: number;
  tax_base_pln: number;
  capital_gains_tax_pln: number;
  dividends_gross_pln: number;
  dividends_withholding_pln: number;
  dividends_tax_pln: number;
  dividends_credit_pln: number;
  dividends_to_pay_pln: number;
  interest_gross_pln: number;
  interest_tax_pln: number;
  total_tax_pln: number;
  unmatched_sold_qty: number;
  pit38: Pit38Fields;
  realizations: Realization[];
  dividends: DividendRow[];
  interest: InterestRow[];
  open_lots: OpenLot[];
  pit_zg: PitZgCountry[];
  warnings: WarningItem[];
  skipped: string[];
  disclaimer: string;
};

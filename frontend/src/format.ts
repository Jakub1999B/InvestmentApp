export const pln = new Intl.NumberFormat("pl-PL", {
  style: "currency",
  currency: "PLN",
  minimumFractionDigits: 2,
});

export const qty = new Intl.NumberFormat("pl-PL", {
  maximumFractionDigits: 6,
});

export function brokerLabel(code: string): string {
  const map: Record<string, string> = {
    trading212: "Trading 212",
    xtb: "XTB",
    generic: "CSV",
  };
  return map[code] || code;
}

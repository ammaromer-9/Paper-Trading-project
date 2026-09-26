const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

// Formats a Decimal-as-string or number as US dollars, e.g. "$1,234.56".
// Money values come from the backend already rounded; this only changes
// how they're displayed, never the underlying number.
export function formatCurrency(value) {
  return currencyFormatter.format(Number(value));
}

// Formats a Decimal-as-string or number as a signed dollar amount,
// e.g. "+$12.50" or "-$3.00", so gains/losses read clearly without
// relying on color alone.
export function formatSignedCurrency(value) {
  const number = Number(value);
  const formatted = currencyFormatter.format(Math.abs(number));
  if (number > 0) return `+${formatted}`;
  if (number < 0) return `-${formatted}`;
  return formatted;
}

// Formats a percent value (already a percentage, e.g. 12.5 means 12.5%)
// as a signed percentage string, e.g. "+12.50%" or "-3.00%".
export function formatSignedPercent(value) {
  const number = Number(value) / 100;
  const formatted = percentFormatter.format(Math.abs(number));
  if (number > 0) return `+${formatted}`;
  if (number < 0) return `-${formatted}`;
  return formatted;
}

// Returns the CSS class to color a gain/loss amount.
export function amountClass(value) {
  const number = Number(value);
  if (number > 0) return "amount-positive";
  if (number < 0) return "amount-negative";
  return "amount-neutral";
}

// Formats an ISO timestamp as a readable local date/time, e.g. "Jan 5, 2026, 3:45 PM".
export function formatDateTime(isoString) {
  return new Date(isoString).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

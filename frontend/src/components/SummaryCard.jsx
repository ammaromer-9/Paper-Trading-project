export default function SummaryCard({ label, value, valueClassName }) {
  return (
    <div className="summary-card">
      <span className="summary-label">{label}</span>
      <span className={`summary-value ${valueClassName || ""}`}>{value}</span>
    </div>
  );
}

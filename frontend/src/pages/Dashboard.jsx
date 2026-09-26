import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import SummaryCard from "../components/SummaryCard";
import { amountClass, formatCurrency, formatSignedCurrency, formatSignedPercent } from "../utils/format";

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadPortfolio() {
      setLoading(true);
      setError("");
      try {
        const data = await api.getPortfolio();
        if (!cancelled) setPortfolio(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadPortfolio();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <p className="page">Loading your portfolio...</p>;
  if (error)
    return (
      <p className="banner banner-error" role="alert">
        {error}
      </p>
    );

  const { cash_balance, holdings, total_value } = portfolio;
  // The backend rounds each holding's gain_loss individually; summing those
  // already-rounded numbers here is just an aggregate for display, not a
  // recalculation of any money the app relies on.
  const totalGainLoss = holdings.reduce((sum, holding) => sum + Number(holding.gain_loss), 0);

  return (
    <div className="page">
      <h1>Dashboard</h1>

      <div className="summary-cards">
        <SummaryCard label="Cash balance" value={formatCurrency(cash_balance)} />
        <SummaryCard label="Total portfolio value" value={formatCurrency(total_value)} />
        <SummaryCard
          label="Total gain/loss"
          value={formatSignedCurrency(totalGainLoss)}
          valueClassName={amountClass(totalGainLoss)}
        />
      </div>

      {holdings.length === 0 ? (
        <div className="empty-state">
          <p>You don&rsquo;t own any stocks yet.</p>
          <Link to="/trade" className="button-primary">
            Make your first trade
          </Link>
        </div>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Shares</th>
                <th>Avg cost</th>
                <th>Current price</th>
                <th>Market value</th>
                <th>Gain/loss</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => (
                <tr key={holding.ticker}>
                  <td>{holding.ticker}</td>
                  <td>{holding.shares}</td>
                  <td>{formatCurrency(holding.avg_cost)}</td>
                  <td>{formatCurrency(holding.current_price)}</td>
                  <td>{formatCurrency(holding.market_value)}</td>
                  <td className={amountClass(holding.gain_loss)}>
                    {formatSignedCurrency(holding.gain_loss)} (
                    {formatSignedPercent(holding.gain_loss_percent)})
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

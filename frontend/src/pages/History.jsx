import { useEffect, useState } from "react";
import { api } from "../api";
import { formatCurrency, formatDateTime } from "../utils/format";

export default function History() {
  const [trades, setTrades] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadTrades() {
      setLoading(true);
      setError("");
      try {
        const data = await api.getTrades();
        if (!cancelled) setTrades(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadTrades();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <p className="page">Loading trade history...</p>;
  if (error)
    return (
      <p className="banner banner-error" role="alert">
        {error}
      </p>
    );

  return (
    <div className="page">
      <h1>Trade history</h1>

      {trades.length === 0 ? (
        <div className="empty-state">
          <p>You haven&rsquo;t made any trades yet.</p>
        </div>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Side</th>
                <th>Ticker</th>
                <th>Shares</th>
                <th>Price</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.id}>
                  <td>{formatDateTime(trade.timestamp)}</td>
                  <td className={trade.side === "buy" ? "side-buy" : "side-sell"}>
                    {trade.side === "buy" ? "Buy" : "Sell"}
                  </td>
                  <td>{trade.ticker}</td>
                  <td>{trade.shares}</td>
                  <td>{formatCurrency(trade.price)}</td>
                  <td>{formatCurrency(Number(trade.price) * trade.shares)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

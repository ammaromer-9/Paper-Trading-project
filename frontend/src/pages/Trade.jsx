import { useEffect, useState } from "react";
import { api } from "../api";
import { formatCurrency } from "../utils/format";

export default function Trade() {
  const [portfolio, setPortfolio] = useState(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState("");

  const [tickerInput, setTickerInput] = useState("");
  const [quote, setQuote] = useState(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteError, setQuoteError] = useState("");

  const [side, setSide] = useState("buy");
  const [sharesInput, setSharesInput] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [tradeError, setTradeError] = useState("");
  const [tradeSuccess, setTradeSuccess] = useState("");

  useEffect(() => {
    loadPortfolio();
  }, []);

  async function loadPortfolio() {
    setPageLoading(true);
    setPageError("");
    try {
      const data = await api.getPortfolio();
      setPortfolio(data);
    } catch (err) {
      setPageError(err.message);
    } finally {
      setPageLoading(false);
    }
  }

  function handleTickerChange(event) {
    setTickerInput(event.target.value);
    // A quote only applies to the ticker it was fetched for; once the
    // user edits the field, that quote is stale until they check again.
    setQuote(null);
    setConfirming(false);
    setTradeSuccess("");
  }

  async function handleCheckPrice(event) {
    event.preventDefault();
    const ticker = tickerInput.trim();
    if (!ticker) return;

    setQuoteLoading(true);
    setQuoteError("");
    setQuote(null);
    setTradeSuccess("");
    try {
      const data = await api.getQuote(ticker);
      setQuote(data);
    } catch (err) {
      setQuoteError(err.status === 404 ? "Ticker not found." : err.message);
    } finally {
      setQuoteLoading(false);
    }
  }

  const shares = Number(sharesInput);
  const sharesValid = Number.isInteger(shares) && shares > 0;
  const estimatedTotal = quote && sharesValid ? Number(quote.price) * shares : null;

  const existingHolding = quote
    ? portfolio?.holdings.find((holding) => holding.ticker === quote.ticker)
    : null;

  function handleReview(event) {
    event.preventDefault();
    setConfirming(true);
  }

  async function handleConfirm() {
    setSubmitting(true);
    setTradeError("");
    try {
      if (side === "buy") {
        await api.buy(quote.ticker, shares);
      } else {
        await api.sell(quote.ticker, shares);
      }
      setTradeSuccess(
        `${side === "buy" ? "Bought" : "Sold"} ${shares} share${shares === 1 ? "" : "s"} of ${quote.ticker}.`,
      );
      setConfirming(false);
      setSharesInput("");
      await loadPortfolio();
    } catch (err) {
      setTradeError(err.message);
      setConfirming(false);
    } finally {
      setSubmitting(false);
    }
  }

  if (pageLoading) return <p className="page">Loading...</p>;
  if (pageError)
    return (
      <p className="banner banner-error" role="alert">
        {pageError}
      </p>
    );

  return (
    <div className="page">
      <h1>Trade</h1>

      <form className="card" onSubmit={handleCheckPrice}>
        <label htmlFor="ticker">Ticker symbol</label>
        <div className="ticker-search">
          <input
            id="ticker"
            type="text"
            value={tickerInput}
            onChange={handleTickerChange}
            placeholder="e.g. AAPL"
            autoComplete="off"
          />
          <button type="submit" className="button-secondary" disabled={quoteLoading || !tickerInput.trim()}>
            {quoteLoading ? "Checking..." : "Check price"}
          </button>
        </div>
        {quoteError && (
          <p className="banner banner-error" role="alert">
            {quoteError}
          </p>
        )}
      </form>

      {quote && (
        <div className="card">
          <p className="quote-price">
            {quote.ticker}: <strong>{formatCurrency(quote.price)}</strong>
          </p>

          <div className="side-toggle" role="group" aria-label="Buy or sell">
            <button
              type="button"
              className={side === "buy" ? "button-primary" : "button-secondary"}
              onClick={() => setSide("buy")}
            >
              Buy
            </button>
            <button
              type="button"
              className={side === "sell" ? "button-primary" : "button-secondary"}
              onClick={() => setSide("sell")}
            >
              Sell
            </button>
          </div>

          <p className="field-hint">
            {side === "buy"
              ? `Cash available: ${formatCurrency(portfolio.cash_balance)}`
              : `Shares owned: ${existingHolding ? existingHolding.shares : 0}`}
          </p>

          <form onSubmit={handleReview}>
            <label htmlFor="shares">Shares</label>
            <input
              id="shares"
              type="number"
              min="1"
              step="1"
              value={sharesInput}
              onChange={(event) => {
                setSharesInput(event.target.value);
                setConfirming(false);
              }}
              required
            />

            {estimatedTotal !== null && (
              <p className="field-hint">Estimated total: {formatCurrency(estimatedTotal)}</p>
            )}

            {tradeError && (
              <p className="banner banner-error" role="alert">
                {tradeError}
              </p>
            )}

            {!confirming && (
              <button type="submit" className="button-primary" disabled={!sharesValid}>
                Review trade
              </button>
            )}
          </form>

          {confirming && (
            <div className="confirm-box">
              <p>
                {side === "buy" ? "Buy" : "Sell"} {shares} {quote.ticker} for about{" "}
                {formatCurrency(estimatedTotal)}?
              </p>
              <div className="confirm-actions">
                <button
                  type="button"
                  className="button-primary"
                  onClick={handleConfirm}
                  disabled={submitting}
                >
                  {submitting ? "Submitting..." : "Confirm"}
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => setConfirming(false)}
                  disabled={submitting}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {tradeSuccess && (
            <p className="banner banner-success" role="status">
              {tradeSuccess}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

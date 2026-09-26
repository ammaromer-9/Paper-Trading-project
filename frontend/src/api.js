const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function extractErrorMessage(body) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // FastAPI's 422 validation error shape: a list of {msg, loc, ...}.
    return detail.map((item) => item.msg).join(", ");
  }
  return "Something went wrong. Please try again.";
}

async function request(path, { method = "GET", body, form = false, auth = true } = {}) {
  const headers = {};
  let requestBody;

  if (body !== undefined) {
    if (form) {
      headers["Content-Type"] = "application/x-www-form-urlencoded";
      requestBody = new URLSearchParams(body).toString();
    } else {
      headers["Content-Type"] = "application/json";
      requestBody = JSON.stringify(body);
    }
  }

  if (auth) {
    const token = localStorage.getItem("token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, { method, headers, body: requestBody });

  let data = null;
  try {
    data = await response.json();
  } catch {
    // No JSON body (e.g. a network-level failure page) - leave data as null.
  }

  if (!response.ok) {
    // Only a request that was actually sending a token counts as a session
    // expiring; a plain wrong-password login attempt is also a 401 but
    // shouldn't log anyone out.
    if (response.status === 401 && auth) {
      localStorage.removeItem("token");
      localStorage.removeItem("email");
      window.dispatchEvent(new CustomEvent("auth:expired"));
    }
    throw new ApiError(extractErrorMessage(data), response.status);
  }

  return data;
}

export const api = {
  signup: (email, password) =>
    request("/signup", { method: "POST", body: { email, password }, auth: false }),

  login: (email, password) =>
    request("/login", {
      method: "POST",
      body: { username: email, password },
      form: true,
      auth: false,
    }),

  getQuote: (ticker) => request(`/quote/${encodeURIComponent(ticker)}`, { auth: false }),

  getPortfolio: () => request("/portfolio"),

  getTrades: () => request("/trades"),

  buy: (ticker, shares) => request("/buy", { method: "POST", body: { ticker, shares } }),

  sell: (ticker, shares) => request("/sell", { method: "POST", body: { ticker, shares } }),
};

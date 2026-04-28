import React, { useState } from "react";
import "./App.css";

type ActionResult = {
  label: string;
  status: number | null;
  message: string;
};

const API_BASES = {
  auth: "http://localhost:8081",
  gateway: "http://localhost:8082",
  payment: "http://localhost:8083",
  notification: "http://localhost:8084",
};

type View = "customer" | "admin";

const App: React.FC = () => {
  const [view, setView] = useState<View>("customer");
  const [loading, setLoading] = useState<string | null>(null);
  const [result, setResult] = useState<ActionResult | null>(null);

  const callApi = async (label: string, fn: () => Promise<Response>) => {
    try {
      setLoading(label);
      setResult(null);
      const res = await fn();
      const text = await res.text();
      setResult({
        label,
        status: res.status,
        message: text || "No body",
      });
    } catch (err: any) {
      setResult({
        label,
        status: null,
        message: err?.message || "Request failed",
      });
    } finally {
      setLoading(null);
    }
  };

  const isLoading = (label: string) => loading === label;

  return (
    <div className="app-root">
      {/* Amazon-like header */}
      <header className="app-header">
        <div className="logo">
          Logi<span className="logo-highlight">Mart</span>
        </div>
        <div className="header-search">
          <input
            className="header-search-input"
            placeholder="Search for products..."
          />
        </div>
        <nav className="header-nav">
          <button
            className={`nav-button ${view === "customer" ? "nav-button-active" : ""}`}
            onClick={() => setView("customer")}
          >
            Customer
          </button>
          <button
            className={`nav-button ${view === "admin" ? "nav-button-active" : ""}`}
            onClick={() => setView("admin")}
          >
            Admin
          </button>
        </nav>
      </header>

      <main className="app-main">
        {view === "customer" ? (
          <>
            <h1 className="page-title">Shop at LogiMart</h1>
            <p className="page-subtitle">
              A simple SaaS storefront backed by auth, API gateway, payment and notification services.
            </p>
            <section className="card-grid">
              <div className="card">
                <h2 className="card-title">Sign in</h2>
                <p className="card-text">
                  Simulate customer login using the <strong>auth-service</strong>.
                </p>
                <div className="card-actions">
                  <button
                    className="btn primary"
                    disabled={loading !== null}
                    onClick={() =>
                      callApi("Login as Alice", () =>
                        fetch(`${API_BASES.auth}/auth/login`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({
                            username: "alice",
                            password: "secret",
                          }),
                        })
                      )
                    }
                  >
                    {isLoading("Login as Alice") ? "Calling..." : "Login as Alice"}
                  </button>
                  <button
                    className="btn danger"
                    disabled={loading !== null}
                    onClick={() =>
                      callApi("Login failure (bad-user)", () =>
                        fetch(`${API_BASES.auth}/auth/login`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({
                            username: "bad-user",
                            password: "secret",
                          }),
                        })
                      )
                    }
                  >
                    {isLoading("Login failure (bad-user)") ? "Calling..." : "Trigger failed login"}
                  </button>
                </div>
              </div>

              <div className="card">
                <h2 className="card-title">Browse via API gateway</h2>
                <p className="card-text">
                  Simulate traffic going through the <strong>api-gateway</strong>.
                </p>
                <div className="card-actions">
                  <button
                    className="btn primary"
                    disabled={loading !== null}
                    onClick={() =>
                      callApi("Normal request", () =>
                        fetch(`${API_BASES.gateway}/api/request`)
                      )
                    }
                  >
                    {isLoading("Normal request") ? "Calling..." : "Normal request"}
                  </button>
                  <button
                    className="btn warning"
                    disabled={loading !== null}
                    onClick={() =>
                      callApi("High latency request", () =>
                        fetch(
                          `${API_BASES.gateway}/api/request?simulateLatency=true`
                        )
                      )
                    }
                  >
                    {isLoading("High latency request")
                      ? "Calling..."
                      : "Simulate high latency"}
                  </button>
                </div>
              </div>

              <div className="card">
                <h2 className="card-title">Checkout</h2>
                <p className="card-text">
                  Trigger the <strong>payment-service</strong>.
                </p>
                <div className="card-actions">
                  <button
                    className="btn success"
                    disabled={loading !== null}
                    onClick={() =>
                      callApi("Payment success", () =>
                        fetch(`${API_BASES.payment}/payments/charge`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({
                            userId: "u1",
                            amount: "10.00",
                            currency: "USD",
                          }),
                        })
                      )
                    }
                  >
                    {isLoading("Payment success")
                      ? "Calling..."
                      : "Simulate payment success"}
                  </button>
                  <button
                    className="btn danger"
                    disabled={loading !== null}
                    onClick={() =>
                      callApi("Payment timeout", () =>
                        fetch(
                          `${API_BASES.payment}/payments/charge?simulateTimeout=true`,
                          {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                              userId: "u1",
                              amount: "10.00",
                              currency: "USD",
                            }),
                          }
                        )
                      )
                    }
                  >
                    {isLoading("Payment timeout")
                      ? "Calling..."
                      : "Simulate payment timeout"}
                  </button>
                </div>
              </div>

              <div className="card">
                <h2 className="card-title">Notifications</h2>
                <p className="card-text">
                  Use the <strong>notification-service</strong> to send order updates.
                </p>
                <div className="card-actions">
                  <button
                    className="btn success"
                    disabled={loading !== null}
                    onClick={() =>
                      callApi("Notification success", () =>
                        fetch(`${API_BASES.notification}/notifications/send`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({
                            channel: "email",
                            recipient: "user@example.com",
                            body: "Your order has been shipped!",
                          }),
                        })
                      )
                    }
                  >
                    {isLoading("Notification success")
                      ? "Calling..."
                      : "Send notification"}
                  </button>
                  <button
                    className="btn danger"
                    disabled={loading !== null}
                    onClick={() =>
                      callApi("Notification failure", () =>
                        fetch(
                          `${API_BASES.notification}/notifications/send?simulateFailure=true`,
                          {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                              channel: "email",
                              recipient: "user@example.com",
                              body: "Your order has been shipped!",
                            }),
                          }
                        )
                      )
                    }
                  >
                    {isLoading("Notification failure")
                      ? "Calling..."
                      : "Simulate notification failure"}
                  </button>
                </div>
              </div>
            </section>
          </>
        ) : (
          <>
            <h1 className="page-title">Admin – Anomaly controls</h1>
            <p className="page-subtitle">
              Internal view to deliberately inject abnormal behavior for testing the anomaly detection system.
            </p>
            <section className="card-grid">
              <div className="card">
                <h2 className="card-title">Authentication failure storm</h2>
                <p className="card-text">
                  Fire a burst of failed logins to produce <strong>ERROR</strong> logs
                  in the <strong>auth-service</strong>.
                </p>
                <div className="card-actions">
                  <button
                    className="btn danger"
                    disabled={loading !== null}
                    onClick={async () => {
                      await callApi("Burst of failed logins", async () => {
                        // Fire a few requests in parallel
                        const promises: Promise<Response>[] = [];
                        for (let i = 0; i < 5; i++) {
                          promises.push(
                            fetch(`${API_BASES.auth}/auth/login`, {
                              method: "POST",
                              headers: { "Content-Type": "application/json" },
                              body: JSON.stringify({
                                username: "bad-user",
                                password: "secret",
                              }),
                            })
                          );
                        }
                        const responses = await Promise.all(promises);
                        return responses[responses.length - 1];
                      });
                    }}
                  >
                    {isLoading("Burst of failed logins")
                      ? "Running..."
                      : "Trigger failure burst"}
                  </button>
                </div>
              </div>

              <div className="card">
                <h2 className="card-title">API latency degradation</h2>
                <p className="card-text">
                  Send multiple high-latency requests through the{" "}
                  <strong>api-gateway</strong> to produce <strong>WARN</strong> logs.
                </p>
                <div className="card-actions">
                  <button
                    className="btn warning"
                    disabled={loading !== null}
                    onClick={async () => {
                      await callApi("Latency spike burst", async () => {
                        const promises: Promise<Response>[] = [];
                        for (let i = 0; i < 5; i++) {
                          promises.push(
                            fetch(
                              `${API_BASES.gateway}/api/request?simulateLatency=true`
                            )
                          );
                        }
                        const responses = await Promise.all(promises);
                        return responses[responses.length - 1];
                      });
                    }}
                  >
                    {isLoading("Latency spike burst")
                      ? "Running..."
                      : "Trigger latency spike"}
                  </button>
                </div>
              </div>

              <div className="card">
                <h2 className="card-title">Payment provider timeouts</h2>
                <p className="card-text">
                  Repeated payment attempts that hit provider timeouts in the{" "}
                  <strong>payment-service</strong>.
                </p>
                <div className="card-actions">
                  <button
                    className="btn danger"
                    disabled={loading !== null}
                    onClick={async () => {
                      await callApi("Timeout burst", async () => {
                        const promises: Promise<Response>[] = [];
                        for (let i = 0; i < 5; i++) {
                          promises.push(
                            fetch(
                              `${API_BASES.payment}/payments/charge?simulateTimeout=true`,
                              {
                                method: "POST",
                                headers: {
                                  "Content-Type": "application/json",
                                },
                                body: JSON.stringify({
                                  userId: "u1",
                                  amount: "10.00",
                                  currency: "USD",
                                }),
                              }
                            )
                          );
                        }
                        const responses = await Promise.all(promises);
                        return responses[responses.length - 1];
                      });
                    }}
                  >
                    {isLoading("Timeout burst")
                      ? "Running..."
                      : "Trigger timeout burst"}
                  </button>
                </div>
              </div>

              <div className="card">
                <h2 className="card-title">Notification delivery failures</h2>
                <p className="card-text">
                  Repeated notification attempts that fail in the{" "}
                  <strong>notification-service</strong>.
                </p>
                <div className="card-actions">
                  <button
                    className="btn danger"
                    disabled={loading !== null}
                    onClick={async () => {
                      await callApi("Notification failure burst", async () => {
                        const promises: Promise<Response>[] = [];
                        for (let i = 0; i < 5; i++) {
                          promises.push(
                            fetch(
                              `${API_BASES.notification}/notifications/send?simulateFailure=true`,
                              {
                                method: "POST",
                                headers: {
                                  "Content-Type": "application/json",
                                },
                                body: JSON.stringify({
                                  channel: "email",
                                  recipient: "user@example.com",
                                  body: "Your order has been shipped!",
                                }),
                              }
                            )
                          );
                        }
                        const responses = await Promise.all(promises);
                        return responses[responses.length - 1];
                      });
                    }}
                  >
                    {isLoading("Notification failure burst")
                      ? "Running..."
                      : "Trigger notification failure storm"}
                  </button>
                </div>
              </div>
            </section>
          </>
        )}

        <section className="result-panel">
          <h2 className="result-title">Last action result</h2>
          {result ? (
            <div className="result-body">
              <div>
                <span className="label">Action:</span> {result.label}
              </div>
              <div>
                <span className="label">Status:</span>{" "}
                {result.status ?? "N/A"}
              </div>
              <div className="result-message">
                {result.message}
              </div>
            </div>
          ) : (
            <p className="result-placeholder">
              Trigger any action above to see the API response here.
            </p>
          )}
        </section>
      </main>

      <footer className="app-footer">
        © {new Date().getFullYear()} LogiMart – Demo SaaS for real-time log anomaly detection.
      </footer>
    </div>
  );
};

export default App;

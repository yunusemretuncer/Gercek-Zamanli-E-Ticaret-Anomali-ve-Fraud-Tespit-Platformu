import { useState, useEffect, useRef } from "react";
import axios from "axios";
import TransactionFeed from "./components/TransactionFeed";
import FraudAlertPanel from "./components/FraudAlertPanel";
import FraudRateChart from "./components/FraudRateChart";
import UserView from "./components/UserView";
import "./index.css";

const API = "http://localhost:8000";
const WS  = "ws://localhost:8000/ws/transactions";

export default function App() {
  const [transactions, setTransactions] = useState([]);
  const [alerts, setAlerts]             = useState([]);
  const [wsStatus, setWsStatus]         = useState("connecting");
  const wsRef = useRef(null);

  // Load existing transactions on mount
  useEffect(() => {
    axios.get(`${API}/transactions`).then((r) => setTransactions(r.data)).catch(() => {});
  }, []);

  // WebSocket — fraud alerts
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS);
      wsRef.current = ws;

      ws.onopen  = () => setWsStatus("online");
      ws.onclose = () => { setWsStatus("offline"); setTimeout(connect, 3000); };
      ws.onerror = () => ws.close();

      ws.onmessage = (e) => {
        const alert = JSON.parse(e.data);
        setAlerts((prev) => [...prev.slice(-49), alert]);
        // Mark matching transaction as fraud in feed
        setTransactions((prev) =>
          prev.map((tx) => tx.id === alert.transaction_id ? { ...tx, is_fraud: true } : tx)
        );
      };
    };
    connect();
    return () => wsRef.current?.close();
  }, []);

  // Poll for new transactions every 3s
  useEffect(() => {
    const interval = setInterval(() => {
      axios.get(`${API}/transactions`).then((r) => setTransactions(r.data)).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const totalFraud = transactions.filter((t) => t.is_fraud).length;
  const fraudRate  = transactions.length > 0
    ? ((totalFraud / transactions.length) * 100).toFixed(1)
    : "0.0";

  return (
    <div className="app">
      <div className="header">
        <h1>🛡 Fraud Detection Platform</h1>
        <span className={`badge ${wsStatus !== "online" ? "offline" : ""}`}>
          {wsStatus === "online" ? "● LIVE" : "○ OFFLINE"}
        </span>
      </div>

      {/* Stats */}
      <div className="grid-3">
        <div className="card">
          <h2>Toplam İşlem</h2>
          <div className="stat-value">{transactions.length}</div>
          <div className="stat-sub">tüm zamanlar</div>
        </div>
        <div className="card">
          <h2>Fraud Tespit</h2>
          <div className="stat-value stat-fraud">{totalFraud}</div>
          <div className="stat-sub">işaretlenmiş işlem</div>
        </div>
        <div className="card">
          <h2>Fraud Oranı</h2>
          <div className="stat-value stat-fraud">{fraudRate}%</div>
          <div className="stat-sub">toplam içinde</div>
        </div>
      </div>

      {/* Chart */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h2>Fraud Oranı (Dakikaya Göre)</h2>
        <FraudRateChart transactions={transactions} />
      </div>

      {/* Feed + Alerts */}
      <div className="grid">
        <div className="card">
          <h2>Canlı İşlem Akışı</h2>
          <TransactionFeed transactions={transactions} />
        </div>
        <div className="card">
          <h2>🚨 Fraud Alarm Paneli</h2>
          <FraudAlertPanel alerts={alerts} />
        </div>
      </div>

      {/* User view */}
      <div className="card">
        <h2>Kullanıcı Bazlı Görünüm</h2>
        <UserView />
      </div>
    </div>
  );
}

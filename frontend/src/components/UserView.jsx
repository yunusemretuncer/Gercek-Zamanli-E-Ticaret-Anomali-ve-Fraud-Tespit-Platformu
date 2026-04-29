import { useState } from "react";
import axios from "axios";

export default function UserView() {
  const [userId, setUserId] = useState("");
  const [txs, setTxs] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const search = async () => {
    if (!userId.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await axios.get(`http://localhost:8000/transactions/users/${userId}`);
      setTxs(res.data);
    } catch (e) {
      setError("Kullanıcı bulunamadı veya hata oluştu.");
      setTxs(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="user-search">
        <input
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder="user_id girin (örn: user_42)"
        />
        <button onClick={search}>Ara</button>
      </div>
      {loading && <div className="empty">Yükleniyor...</div>}
      {error && <div className="empty" style={{ color: "#f87171" }}>{error}</div>}
      {txs && (
        <div className="feed">
          {txs.length === 0 && <div className="empty">Bu kullanıcıya ait işlem yok.</div>}
          {txs.map((tx) => (
            <div key={tx.id} className={`tx-row ${tx.is_fraud ? "fraud" : ""}`}>
              <div>
                <span style={{ fontSize: 11, color: "#64748b" }}>
                  {new Date(tx.timestamp).toLocaleString()}
                </span>
                <span className="location"> · {tx.location}</span>
              </div>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <span className={`amount ${tx.is_fraud ? "fraud" : ""}`}>
                  ${parseFloat(tx.amount).toFixed(2)}
                </span>
                <span className={`tag ${tx.is_fraud ? "fraud" : ""}`}>
                  {tx.is_fraud ? "🚨 FRAUD" : "✓ OK"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

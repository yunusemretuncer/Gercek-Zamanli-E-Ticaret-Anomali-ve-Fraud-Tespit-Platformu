export default function TransactionFeed({ transactions }) {
  if (transactions.length === 0) {
    return <div className="empty">Henüz işlem yok. Swagger üzerinden transaction gönderin.</div>;
  }
  return (
    <div className="feed">
      {[...transactions].reverse().map((tx) => (
        <div key={tx.id} className={`tx-row ${tx.is_fraud ? "fraud" : ""}`}>
          <div>
            <span className="user">{tx.user_id}</span>
            <span className="location"> · {tx.location}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
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
  );
}

export default function FraudAlertPanel({ alerts }) {
  if (alerts.length === 0) {
    return (
      <div className="empty">
        <div style={{ fontSize: 32, marginBottom: 8 }}>🛡</div>
        <div>Fraud alarmı yok</div>
        <div style={{ fontSize: 11, color: "#374151", marginTop: 4 }}>Sistem izleniyor...</div>
      </div>
    );
  }
  return (
    <div className="alerts">
      {[...alerts].reverse().map((alert, i) => (
        <div key={i} className="alert-row">
          <div className="alert-header">
            <span className="alert-user">🚨 {alert.user_id}</span>
            <span className="alert-time">
              {new Date(alert.detected_at).toLocaleTimeString()}
            </span>
          </div>
          <div className="alert-rules">
            İhlal: <strong style={{ color: "#fca5a5" }}>{alert.rules_violated.join(", ")}</strong>
          </div>
          <div style={{ fontSize: 11, color: "#374151", marginTop: 4 }}>
            TX: {alert.transaction_id?.slice(0, 8)}...
          </div>
        </div>
      ))}
    </div>
  );
}
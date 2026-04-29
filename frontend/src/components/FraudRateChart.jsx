import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine
} from "recharts";

export default function FraudRateChart({ transactions }) {
  const now = Date.now();
  const WINDOW_MS = 5 * 60 * 1000; // son 5 dakika

  // Son 5 dakikayı 15 saniyelik dilimlere böl
  const buckets = {};
  transactions.forEach((tx) => {
    const d = new Date(tx.created_at || tx.timestamp);
    if (now - d.getTime() > WINDOW_MS) return;
    // 15 saniyelik bucket
    const bucket = Math.floor(d.getTime() / 15000) * 15000;
    if (!buckets[bucket]) buckets[bucket] = { ts: bucket, total: 0, fraud: 0 };
    buckets[bucket].total++;
    if (tx.is_fraud) buckets[bucket].fraud++;
  });

  const data = Object.values(buckets)
    .sort((a, b) => a.ts - b.ts)
    .map((d) => ({
      time: new Date(d.ts).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      rate: d.total > 0 ? Math.round((d.fraud / d.total) * 100) : 0,
      total: d.total,
    }));

  if (data.length === 0)
    return <div className="empty">Grafik için veri bekleniyor...</div>;

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{
        background: "#0f1117", border: "1px solid #f87171",
        borderRadius: 8, padding: "10px 14px", fontSize: 12
      }}>
        <div style={{ color: "#94a3b8", marginBottom: 4 }}>🕐 {label}</div>
        <div style={{ color: "#f87171", fontWeight: 700 }}>
          Fraud Oranı: {payload[0].value}%
        </div>
        <div style={{ color: "#64748b" }}>
          Toplam: {payload[0].payload.total} işlem
        </div>
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="fraudGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#f87171" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2433" vertical={false} />
        <XAxis
          dataKey="time"
          stroke="#2d3748"
          tick={{ fontSize: 10, fill: "#4b5563" }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          stroke="#2d3748"
          tick={{ fontSize: 11, fill: "#4b5563" }}
          tickLine={false}
          axisLine={false}
          unit="%"
          domain={[0, 100]}
          width={36}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={50} stroke="#f87171" strokeDasharray="4 4" strokeOpacity={0.3} />
        <Area
          type="monotone"
          dataKey="rate"
          stroke="#f87171"
          strokeWidth={2.5}
          fill="url(#fraudGradient)"
          dot={false}
          activeDot={{ r: 5, fill: "#f87171", stroke: "#0f1117", strokeWidth: 2 }}
          isAnimationActive={true}
          animationDuration={400}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
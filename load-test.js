import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },
    { duration: '1m', target: 100 },
    { duration: '1m', target: 200 },
    { duration: '30s', target: 0 },
  ],
};

export default function () {
  const payload = JSON.stringify({
    user_id: `user-${__VU}`,
    amount: Math.floor(Math.random() * 1000) + 1,
    location: "Istanbul"
  });

  const res = http.post(
    'http://fraud.deneme/api/transactions',
    payload,
    {
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  check(res, {
    'status is successful': (r) => r.status >= 200 && r.status < 300,
  });

  sleep(0.1);
}
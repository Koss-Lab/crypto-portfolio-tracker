
-- 📌 Crypto Portfolio Tracker - Useful Queries

-- 1. Show all users
SELECT * FROM users;

-- 2. Show first 5 transactions
SELECT * FROM transactions LIMIT 5;

-- 3. Show all transactions ordered by most recent
SELECT * FROM transactions
ORDER BY date DESC;

-- 4. Show last 5 transactions only
SELECT * FROM transactions
ORDER BY date DESC
LIMIT 5;

-- 5. Insert a manual transaction example
INSERT INTO transactions (user_id, coin, transaction_type, amount, price)
VALUES (1, 'BTC', 'BUY', 0.5, 40000);

-- 6. Group transactions by month and coin (net amount bought/sold)
SELECT DATE_TRUNC('month', date) AS month,
       coin,
       SUM(CASE WHEN transaction_type = 'BUY' THEN amount ELSE -amount END) AS net_amount
FROM transactions
GROUP BY month, coin
ORDER BY month DESC;

-- 7. Get all current prices snapshot
SELECT * FROM prices;

-- 8. Show all transactions of a specific user (example: user_id = 1)
SELECT * FROM transactions
WHERE user_id = 1
ORDER BY date DESC;

-- 9. Calculate total number of transactions per user
SELECT u.username, COUNT(t.id) AS total_transactions
FROM users u
LEFT JOIN transactions t ON u.id = t.user_id
GROUP BY u.username
ORDER BY total_transactions DESC;

-- 10. Find top 5 holders by USD portfolio value (requires updated prices)
SELECT u.username,
       SUM(
           CASE
               WHEN t.transaction_type = 'BUY' THEN t.amount * p.price
               WHEN t.transaction_type = 'SELL' THEN -t.amount * p.price
               ELSE 0
           END
       ) AS portfolio_value_usd
FROM users u
JOIN transactions t ON u.id = t.user_id
JOIN prices p ON t.coin = p.coin
GROUP BY u.username
ORDER BY portfolio_value_usd DESC
LIMIT 5;

-- 11. count the number of transactions per type
SELECT transaction_type, COUNT(*) FROM transactions GROUP BY transaction_type;

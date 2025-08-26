CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    coin VARCHAR(20) NOT NULL,
    amount NUMERIC NOT NULL,
    price NUMERIC NOT NULL,
    transaction_type VARCHAR(10) CHECK (transaction_type IN ('buy','sell')),
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

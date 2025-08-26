-- Users table
DROP TABLE IF EXISTS users CASCADE;
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL
);

-- Transactions table
DROP TABLE IF EXISTS transactions CASCADE;
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    coin VARCHAR(20) NOT NULL,
    amount NUMERIC NOT NULL,
    price NUMERIC NOT NULL,
    transaction_type VARCHAR(10) CHECK (transaction_type IN ('BUY','SELL')),
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

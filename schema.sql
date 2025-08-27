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
    transaction_type VARCHAR(10) CHECK (transaction_type IN ('BUY','SELL','SEND','RECEIVE')),
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Prices table (latest snapshots)
DROP TABLE IF EXISTS prices CASCADE;
CREATE TABLE prices (
    id SERIAL PRIMARY KEY,
    coin VARCHAR(20) NOT NULL,
    price NUMERIC NOT NULL,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FX rates (USD base)
DROP TABLE IF EXISTS fx_rates CASCADE;
CREATE TABLE fx_rates (
    id SERIAL PRIMARY KEY,
    base_currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    currency VARCHAR(10) NOT NULL, -- e.g. 'EUR', 'ILS'
    rate NUMERIC NOT NULL,         -- e.g. 0.92, 3.70
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fx_rates_curr_date ON fx_rates(currency, date);

-- Price alerts
DROP TABLE IF EXISTS alerts CASCADE;
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    coin VARCHAR(20) NOT NULL,
    operator VARCHAR(1) NOT NULL CHECK (operator IN ('>','<')),
    threshold NUMERIC NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    triggered_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(active);

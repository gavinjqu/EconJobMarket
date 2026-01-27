-- Create a dedicated schema (namespace) for your project
CREATE SCHEMA IF NOT EXISTS amm;

-- Optional: keep your objects discoverable without writing amm.table every time
ALTER ROLE amm SET search_path = amm, public;

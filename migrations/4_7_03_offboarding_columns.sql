-- Stempeluhr 4.7.03 - Offboarding-Spalten für PostgreSQL
ALTER TABLE employees ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS exit_date DATE NULL;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NULL;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS offboarding_note TEXT NULL;
UPDATE employees SET status = 'active' WHERE status IS NULL;

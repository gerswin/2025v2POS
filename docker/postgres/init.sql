-- PostgreSQL Initialization Script for Tiquemax POS System

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- For better indexing

-- Set timezone
SET timezone = 'America/Caracas';

-- Create custom types if needed
-- CREATE TYPE order_status AS ENUM ('pending', 'completed', 'cancelled');

-- Performance tuning for the database
ALTER DATABASE tiquemax_pos SET work_mem = '16MB';
ALTER DATABASE tiquemax_pos SET maintenance_work_mem = '128MB';
ALTER DATABASE tiquemax_pos SET effective_cache_size = '256MB';
ALTER DATABASE tiquemax_pos SET shared_buffers = '128MB';

-- Create read-only user for reports (optional)
-- DO
-- $$
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tiquemax_readonly') THEN
--         CREATE ROLE tiquemax_readonly WITH LOGIN PASSWORD 'changeme';
--     END IF;
-- END
-- $$;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE tiquemax_pos TO tiquemax;
GRANT ALL PRIVILEGES ON DATABASE tiquemax_pos TO tiquemax;

-- Log successful initialization
\echo 'PostgreSQL initialization completed successfully'

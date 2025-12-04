-- Database initialization script
-- This script sets up the PostgreSQL database with required extensions

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm extension for text similarity search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create indexes on commonly queried fields will be handled by Alembic migrations

-- Verify extensions are installed
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp', 'pg_trgm');

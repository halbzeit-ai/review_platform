-- Check extraction_experiments table schema for PostgreSQL (for production)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'extraction_experiments' 
  AND table_schema = 'public'
ORDER BY ordinal_position;
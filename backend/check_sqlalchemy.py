import psycopg2
try:
    conn = psycopg2.connect('postgresql://review_user:\!prod_Halbzeit1024@localhost:5432/review-platform')
    print('✅ Connection successful!')
    conn.close()
except Exception as e:
    print('❌ Connection failed:', e)

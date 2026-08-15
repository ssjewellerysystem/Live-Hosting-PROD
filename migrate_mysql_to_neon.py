import pymysql
import psycopg2

# =====================================
# Railway MySQL Connection
# =====================================
mysql_conn = pymysql.connect(
    host="thomas.proxy.rlwy.net",
    port=10126,
    user="root",
    password="pgFFWSVcOwHEKNBIDeORObDLzsLbdqyN",
    database="railway",
    cursorclass=pymysql.cursors.DictCursor
)

# =====================================
# Neon PostgreSQL Connection
# =====================================
pg_conn = psycopg2.connect(
    host="ep-bold-base-ao7v7l2l-pooler.c-2.ap-southeast-1.aws.neon.tech",
    port=5432,
    user="neondb_owner",
    password="npg_GOsy48HeAJhP",
    dbname="neondb",
    sslmode="require"
)

mysql_cur = mysql_conn.cursor()
pg_cur = pg_conn.cursor()

# Migration order is important because of foreign keys
tables = [
    "users",
    "categories",
    "products",
    "carts",
    "orders",
    "order_items"
]

for table in tables:
    print(f"\nMigrating {table}...")

    mysql_cur.execute(f"SELECT * FROM {table}")
    rows = mysql_cur.fetchall()

    if not rows:
        print(f"{table}: 0 rows")
        continue

    columns = list(rows[0].keys())
    col_names = ",".join(columns)

    placeholders = ",".join(["%s"] * len(columns))

    success_count = 0

    for row in rows:

        values = []

        for col in columns:
            value = row[col]

            # =====================================
            # USERS TABLE BOOLEAN CONVERSION
            # =====================================
            if table == "users":
                if col in [
                    "is_blocked",
                    "is_admin",
                    "email_verified",
                    "first_login"
                ]:
                    value = bool(value) if value is not None else None

            # =====================================
            # ORDERS TABLE BOOLEAN CONVERSION
            # =====================================
            if table == "orders":
                if col == "terms_accepted":
                    value = bool(value) if value is not None else None

            values.append(value)

        try:
            pg_cur.execute(
                f"""
                INSERT INTO {table}
                ({col_names})
                VALUES ({placeholders})
                """,
                values
            )

            success_count += 1

        except Exception as e:
            print(f"Error in {table}: {e}")
            pg_conn.rollback()

    pg_conn.commit()

    print(
        f"{table}: {success_count}/{len(rows)} rows migrated successfully"
    )

print("\nMigration completed!")

mysql_cur.close()
pg_cur.close()
mysql_conn.close()
pg_conn.close()
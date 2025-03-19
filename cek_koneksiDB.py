from sqlalchemy import create_engine

# DATABASE_URL di sini ya, formatnya jan ampe salah busset
DATABASE_URL = "mysql+pymysql://root:@localhost:3306/klasemen"

# Membuat engine untuk menghubungkan ke MySQL
engine = create_engine(DATABASE_URL)

# uji koneksi
try:
    with engine.connect() as connection:
        print("Koneksi berhasil!")
except Exception as e:
    print(f"Terjadi kesalahan: {e}")
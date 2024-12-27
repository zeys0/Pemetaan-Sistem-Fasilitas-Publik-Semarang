from pymongo import MongoClient

try:
    client = MongoClient(
        "mongodb+srv://test:7fVu15XCDyr7OEEO@cluster0.hqpph8x.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    )
    client.server_info()  # Mengecek koneksi
    print("Koneksi MongoDB berhasil!")
except Exception as e:
    print(f"Koneksi MongoDB gagal: {e}")

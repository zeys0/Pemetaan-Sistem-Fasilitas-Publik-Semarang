from pymongo import MongoClient

try:
    client = MongoClient(
        "mongodb+srv://rafly:dbrafly@cluster0.lweon5s.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    )
    client.server_info()  # Mengecek koneksi
    print("Koneksi MongoDB berhasil!")
except Exception as e:
    print(f"Koneksi MongoDB gagal: {e}")

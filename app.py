import jwt
import json
import os
import folium
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from os.path import join, dirname
from folium.plugins import MarkerCluster
from pymongo import MongoClient, DESCENDING
from dotenv import load_dotenv
from datetime import datetime, timedelta
import hashlib
from flask_paginate import Pagination
from bson import ObjectId


app = Flask(__name__)
dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)


MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME")
SECRET_KEY = os.environ.get("SECRET_KEY")
TOKEN_KEY = os.environ.get("TOKEN_KEY")
TOKEN_USER = os.environ.get("TOKEN_USER")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
app.secret_key = SECRET_KEY


# Memuat geojson agar bisa digunakan
with open("./static/json/semarang.geojson") as f:
    geojson_data = json.load(f)

# Preview map
preview_map = folium.Map(location=[-7.011374, 110.395078], zoom_start=12)

# Membuat polygon semarang
folium.GeoJson(
    geojson_data,
    style_function=lambda feature: {
        "color": "black",
        "weight": 2,
        "fillOpacity": 0.5,
    },
).add_to(preview_map)

preview_map.save("static/preview/preview_map.html")


def update_map():
    # Inisialisasi peta
    marker_cluster = MarkerCluster().add_to(preview_map)

    # Mapping kategori ke warna
    category_colors = {
        "Fasilitas Kesehatan": "red",
        "Fasilitas Pendidikan": "blue",
        "Fasilitas Transportasi": "green",
        "Fasilitas Keamanan": "purple",
        "Fasilitas Administrasi Publik": "orange",
        "Fasilitas Hiburan": "cadetblue",
    }

    # Ambil data dari database
    places = db.places.find()
    for place in places:
        # Tentukan warna berdasarkan kategori
        category = place["category"]
        marker_color = category_colors.get(
            category, "gray"
        )  # Default warna jika kategori tidak dikenal

        # Konten popup
        popup_content = f"""
        <b>{place['name']}</b><br>
        {place['description']}<br>
        <img src='/static/uploads/{place['image']}' width='200'><br>
        Alamat: {place['address']}<br>
        Kategori: {category}
        """

        # Tambahkan marker dengan warna sesuai kategori
        folium.Marker(
            [place["location"]["latitude"], place["location"]["longitude"]],
            popup=folium.Popup(popup_content, max_width=300),
            icon=folium.Icon(color=marker_color),
        ).add_to(marker_cluster)

    # Tambahkan legenda sebagai HTML
    legend_html = """
     <div style="
     position: fixed; 
     top: 10px; right: 10px; width: 200px; height: auto; 
     background-color: white; z-index:9999; font-size:14px; 
     border:1px solid black; border-radius:5px; padding: 10px;">
     <b>Keterangan Warna:</b><br>
     <i style="background:red; width:10px; height:10px; display:inline-block; border-radius:50%;"></i> Fasilitas Kesehatan<br>
     <i style="background:blue; width:10px; height:10px; display:inline-block; border-radius:50%;"></i> Fasilitas Pendidikan<br>
     <i style="background:green; width:10px; height:10px; display:inline-block; border-radius:50%;"></i> Fasilitas Transportasi<br>
     <i style="background:purple; width:10px; height:10px; display:inline-block; border-radius:50%;"></i> Fasilitas Keamanan<br>
     <i style="background:orange; width:10px; height:10px; display:inline-block; border-radius:50%;"></i> Fasilitas Administrasi Publik<br>
     <i style="background:cadetblue; width:10px; height:10px; display:inline-block; border-radius:50%;"></i> Fasilitas Hiburan<br>
     </div>
     """
    preview_map.get_root().html.add_child(folium.Element(legend_html))

    # Simpan peta ke file
    preview_map.save("static/preview/preview_map.html")


@app.route("/")
def home():
    update_map()  # Tidak menampilkan legenda

    # Hitung jumlah fasilitas berdasarkan kategori
    category_counts = db.places.aggregate(
        [{"$group": {"_id": "$category", "count": {"$sum": 1}}}]
    )

    # Format hasil menjadi dictionary
    category_data = {item["_id"]: item["count"] for item in category_counts}

    total_places = db.places.count_documents({})

    return render_template(
        "main/home.html",
        enable_scroll_nav=False,
        category_data=category_data,
        total_places=total_places,
    )


@app.route("/location")
def locationFacility():

    categories = db.places.distinct("category")
    return render_template(
        "main/homeLocation.html",
        categories=categories,
        enable_scroll_nav=False,
    )


@app.route("/location/<category>")
def FacilityCategory(category):
    # Mengambil data dan mengonversi cursor ke list
    locations_cursor = db.places.find({"category": category})
    locations = list(locations_cursor)  # Mengonversi cursor ke list

    # Mengirim data ke template
    return render_template(
        "main/locationCategory.html",
        category=category,
        locations=locations,  # Kirim list ke template
        enable_scroll_nav=False,
    )


#########################################
#                                       #
#            Login Validate             #--------------------------------------------------------------------------
#                                       #
#########################################


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login/login.html")
    else:
        username_receive = request.form["username_give"]
        password_receive = request.form["password_give"]
        password_hash = hashlib.sha3_256(password_receive.encode("utf-8")).hexdigest()
        result = db.users.find_one(
            {
                "username": username_receive,
                "password": password_hash,
            }
        )
        if result:
            role = result.get("role", "user")
            payload = {
                "id": username_receive,
                "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
            return jsonify({"result": "success", "token": token, "role": role})
        else:
            return jsonify(
                {
                    "result": "fail",
                    "msg": "We could not find a user with that id/password combination",
                }
            )


#########################################
#                                       #
# ->>>>>>>>>>END LOGIN VALIDATE<<<<<<<<-#------------------------------------------------------------------------------
#                                       #
#########################################


#########################################
#                                       #
#            Admin Facility FUNCTION    #------------------------------------------------------------------------------
#                                       #
#########################################


@app.route("/admin")
def adminHome():
    token_receive = request.cookies.get(TOKEN_USER)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        update_map()
        total_places = db.places.count_documents({})
        return render_template("dashboard/HomeDash.html", total_places=total_places)
    except jwt.ExpiredSignatureError:
        msg = "Your token has expired"
        return redirect(url_for("login"), msg=msg)
    except jwt.exceptions.DecodeError:
        msg = "There was a problem logging you in"
        return redirect(url_for("login"))


@app.route("/admin/facility")
def PlaceManages():

    token_receive = request.cookies.get(TOKEN_USER)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload.get("id")})
        category = request.args.get("category", None)
        query = {"category": category} if category else {}

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 3, type=int)
        offset = (page - 1) * per_page

        facilities = list(
            db.places.find(query)
            .sort("created_at", DESCENDING)
            .skip(offset)
            .limit(per_page)
        )

        total = db.places.count_documents(query)

        pagination = Pagination(
            page=page,
            per_page=per_page,
            total=total,
            show_single_page=False,
            alignment="end",
        )

        return render_template(
            "dashboard/FacilityManage.html",
            places_coll=facilities,
            pagination=pagination,
            user_info=user_info,
        )

    except jwt.ExpiredSignatureError:
        msg = "Your token has expired"
        return redirect(url_for("login"), msg=msg)
    except jwt.exceptions.DecodeError:
        msg = "There was a problem logging you in"
        return redirect(url_for("login"))


@app.route("/admin/facility/add", methods=["POST"])
def addFacility():
    token_receive = request.cookies.get(TOKEN_USER)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        name = request.form.get("name")
        address = request.form.get("address")
        category = request.form.get("category")
        latitude = float(request.form.get("latitude"))
        longitude = float(request.form.get("longitude"))
        description = request.form.get("description")
        image = request.files["images"]

        if image:
            save_to = "static/uploads"
            if not os.path.exists(save_to):
                os.makedirs(save_to)

        ext = image.filename.split(".")[-1]
        file_name = f"facility-{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        image.save(f"{save_to}/{file_name}")

        db.places.insert_one(
            {
                "name": name,
                "address": address,
                "category": category,
                "location": {"latitude": latitude, "longitude": longitude},
                "description": description,
                "image": file_name,
                "created_at": datetime.now(),
            }
        )

        update_map()

        flash("Facility data is successfully added.")
        return redirect(url_for("PlaceManages"))

    except jwt.ExpiredSignatureError:
        msg = "Your token has expired"
        return redirect(url_for("login"), msg=msg)
    except jwt.exceptions.DecodeError:
        msg = "There was a problem logging you in"
        return redirect(url_for("login"))


@app.route("/facility/edit/<id>", methods=["POST"])
def editFacility(id):

    name = request.form.get("name")
    address = request.form.get("address")
    category = request.form.get("category")
    latitude = float(request.form.get("latitude"))
    longitude = float(request.form.get("longitude"))
    description = request.form.get("description")
    image = request.files["images"]

    if image:
        save_to = "static/uploads"
        facility = db.places.find_one({"_id": ObjectId(id)})
        target = f"static/uploads/{facility['image']}"

        if os.path.exists(target):
            os.remove(target)

        ext = image.filename.split(".")[-1]
        file_name = f"facility-{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        image.save(f"{save_to}/{file_name}")

        db.places.update_one({"_id": ObjectId(id)}, {"$set": {"image": file_name}})

    db.places.update_one(
        {"_id": ObjectId(id)},
        {
            "$set": {
                "name": name,
                "address": address,
                "category": category,
                "location": {"latitude": latitude, "longitude": longitude},
                "description": description,
            }
        },
    )

    update_map()
    flash("Facility data is successfully updated.")
    return redirect(url_for("PlaceManages"))


@app.route("/facility/delete/<id>", methods=["POST"])
def deleteFacility(id):
    facility = db.places.find_one({"_id": ObjectId(id)})
    target = f"static/uploads/{facility['image']}"

    if os.path.exists(target):
        os.remove(target)

    db.places.delete_one({"_id": ObjectId(id)})
    update_map()
    flash("Facility data was successfully deleted.")
    return redirect(url_for("PlaceManages"))


#########################################
#                                       #
# ->>>>>>>>>>>>>>>END admin<<<<<<<<<<<<-#------------------------------------------------------------------------------------------
#                                       #
#########################################


if __name__ == "__main__":
    app.run("0.0.0.0", port=8000, debug=True)

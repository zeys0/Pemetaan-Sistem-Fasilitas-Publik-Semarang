import jwt
import json
import os
import folium
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from os.path import join, dirname
from folium.plugins import MarkerCluster
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta
import hashlib

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


@app.route("/")
def home():
    return render_template("main/home.html", enable_scroll_nav=False)


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


@app.route("/admin")
def adminHome():
    token_receive = request.cookies.get(TOKEN_USER)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])

        return render_template("dashboard/HomeDash.html")
    except jwt.ExpiredSignatureError:
        msg = "Your token has expired"
        return redirect(url_for("login"), msg=msg)
    except jwt.exceptions.DecodeError:
        msg = "There was a problem logging you in"
        return redirect(url_for("login"))


@app.route("/map", methods=["GET", "POST"])
def map():
    if request.method == "POST":
        name = request.form["name"]
        lat = float(request.form["lat"])
        lon = float(request.form["lon"])
        img_url = request.form["img_url"]
        price_range = request.form["price_range"]
        desc = request.form["desc"]

        db.places.insert_one(
            {
                "name": name,
                "lat": lat,
                "lon": lon,
                "image_url": img_url,
                "price_range": price_range,
                "description": desc,
            }
        )

        flash("Berhasil Menambah data")
        return redirect(url_for("map"))

    marker_cluster = MarkerCluster().add_to(preview_map)
    places = db.places.find()
    for place in places:
        popup_content = f"""
        <b>{place['name']}</b><br>
        {place['description']}<br>
        <img src='{place['image_url']}' width='200'><br>
        Rating: ⭐⭐⭐⭐⭐ 5/5<br>
        Harga: {place['price_range']}
        """
        folium.Marker([place["lat"], place["lon"]], popup=popup_content).add_to(
            marker_cluster
        )
    preview_map.save("static/preview/preview_map.html")
    return render_template("main/map.html", enable_scroll_nav=False)


if __name__ == "__main__":
    app.run("0.0.0.0", port=8000, debug=True)

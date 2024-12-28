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


@app.route("/")
def home():
    return render_template("main/home.html", enable_scroll_nav=False)


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

        return render_template("dashboard/HomeDash.html")
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

    flash("Facility data is successfully updated.")
    return redirect(url_for("PlaceManages"))


@app.route("/facility/delete/<id>", methods=["POST"])
def deleteFacility(id):
    facility = db.places.find_one({"_id": ObjectId(id)})
    target = f"static/uploads/{facility['image']}"

    if os.path.exists(target):
        os.remove(target)

    db.places.delete_one({"_id": ObjectId(id)})
    flash("Facility data was successfully deleted.")
    return redirect(url_for("PlaceManages"))


#########################################
#                                       #
# ->>>>>>>>>>>>>>>END admin<<<<<<<<<<<<-#------------------------------------------------------------------------------------------
#                                       #
#########################################


@app.route("/map", methods=["GET", "POST"])
def map():

    marker_cluster = MarkerCluster().add_to(preview_map)
    places = db.places.find()
    for place in places:
        popup_content = f"""
        <b>{place['name']}</b><br>
        {place['description']}<br>
        <img src='{place['image_url']}' width='200'><br>
        Harga: {place['price_range']}
        """
        folium.Marker([place["lat"], place["lon"]], popup=popup_content).add_to(
            marker_cluster
        )
    preview_map.save("static/preview/preview_map.html")
    return render_template("main/map.html", enable_scroll_nav=False)


if __name__ == "__main__":
    app.run("0.0.0.0", port=8000, debug=True)

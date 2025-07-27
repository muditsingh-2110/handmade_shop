import os
import gspread
import json
import os # Make sure 'os' and 'json' are imported at the top of your file
from oauth2client.service_account import ServiceAccountCredentials
# Add these imports at the top of your app.py if they aren't there
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
from flask import (
    Flask, render_template, session, redirect, url_for,
    request, flash
)

UPLOAD_FOLDER = 'upload'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
DELIVERY_CHARGE = 150

app = Flask(__name__)
app.secret_key = 'your-super-secret-key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Product data
bracelets = [
    {"id": 1, "name": "Flower Bracelet", "description": "flower bracelet in theme of pink beads and purple beads", "image": "bracelet1.jpg", "price": 99},
    {"id": 2, "name": "Beads Bracelet", "description": "Simple purple and pink beads bracelet ", "image": "bracelet2.jpg", "price": 59},
    {"id": 3, "name": "Name Bracelet", "description": "personalized name bracelet in cute Pastel purple colour ", "image": "bracelet3.jpg", "price": 99},
    {"id": 4, "name": "Pretty Pink Colour Bracelet", "description": "Pretty pink colour bracelet to embrace your soft hand look with a red cute sunflower attachment", "image": "bracelet4.jpg", "price": 99},
]
charms = [
    {"id": 5, "name": "Attractive Phone Charm", "description": "Cute Pastel pink simple but attractive phone charm with a rabbit charm attached on it", "image": "charm1.jpg", "price": 99},
    {"id": 6, "name": "BTS Theme Phone Charm", "description": "BTS theme phone charm with letters BTS and pastel pink+purple beads", "image": "charm2.jpg", "price": 99},

]
combos = [
    {"id": 7, "name": "Charm & Bracelet Combo", "description": "combo of two - bracelet+phone charm in theme of blue and white beads with butterfly charm ", "image": "combo1.jpg", "price": 149},
    {"id": 8, "name": "BLue Ocean Theme Gift Hamper", "description": "bracelet+clutcher+phone charm+keychain", "image": "combo2.jpg", "price": 249},
    {"id": 9, "name": "Pastel Pink  Theme Gift Hamper", "description": "bracelet+phone charm+clutcher+rubber band ", "image": "combo3.jpg", "price": 149},

]
mugs = [
    {"id": 10, "name": "Pink Bow Design Mug", "description": "cute little pink bow design mug good to go with your aesthetics ", "image": "mug1.jpg", "price": 149},
    {"id": 11, "name": "Pastel Tulip  Mug", "description": "pastel tulip theme coffee mug", "image": "mug2.jpg", "price": 249},
    {"id": 12, "name": "Big Bow with Me  Mug", "description": "Big bow with the text of Me on it. in colour scheme of cute pink+white", "image": "mug3.jpg", "price": 249},
    {"id": 13, "name": "Skull Design Mug", "description": "skull design coffee mug for your loved one.", "image": "mug4.jpg", "price": 279},
    {"id": 14, "name": "Little Hearts Design Mug", "description": "little hearts design in red colour .", "image": "mug5.jpg", "price": 249},
]
keyrings = [
    {"id": 15, "name": "Bow  Keychain", "description": "Blue+white beads bow keychain looks good on your handbag+laptop bags", "image": "keyring1.jpg", "price": 79},
    {"id": 16, "name": "Bow  Keychain", "description": "Bow keychain based on beads having soft touch in the colour scheme of soft purple+white", "image": "keyring2.jpg", "price": 79},
]

# (Replace the old all_products line with this one)
all_products = {p["id"]: p for p in bracelets + charms + combos + mugs + keyrings}
def get_cart():
    if 'cart' not in session:
        session['cart'] = {}
    return session['cart']

def save_cart(cart):
    session['cart'] = cart

def cart_items_details():
    cart = get_cart()
    items = []
    subtotal = 0
    for pid, qty in cart.items():
        product = all_products.get(int(pid))
        if product:
            items.append({'product': product, 'quantity': qty})
            subtotal += product["price"] * qty
    return items, subtotal

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

def get_gsheet():
    # Set your Google Sheet Name exactly as it appears in Google Sheets
    SHEET_NAME = "handmade_orders"  # <-- Change this to your actual sheet name!
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_json_str = os.environ.get('GCP_CREDS_JSON')
    if not creds_json_str:
        raise ValueError("GCP_CREDS_JSON environment variable not set!")

    creds_info = json.loads(creds_json_str)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet
# --- New function to upload to Google Drive ---
def upload_to_drive_and_get_link(file_stream, filename):
    """Uploads a file to Google Drive and returns a shareable link."""
    
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # Securely load credentials from the environment variable
        creds_json_str = os.environ.get('GCP_CREDS_JSON')
        if not creds_json_str:
            raise ValueError("GCP_CREDS_JSON environment variable not set!")
        creds_info = json.loads(creds_json_str)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)

        # Build the Drive service
        drive_service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': filename}
        media = MediaIoBaseUpload(BytesIO(file_stream.read()), mimetype='image/jpeg', resumable=True)
        
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        file_id = file.get('id')
        drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
        
        return file.get('webViewLink')
        
    except Exception as e:
        print(f"An error occurred during file upload: {e}")
        return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/bracelets")
def bracelets_page():
    return render_template("bracelets.html", bracelets=bracelets)

@app.route("/charms")
def charms_page():
    return render_template("charms.html", charms=charms)

@app.route("/combos")
def combos_page():
    return render_template("combos.html", combos=combos)

@app.route("/mugs")
def mugs_page():
    return render_template("mugs.html", mugs=mugs)

@app.route("/keyrings")
def keyrings_page():
    return render_template("keyrings.html", keyrings=keyrings)

@app.route("/cart")
def cart():
    items, subtotal = cart_items_details()
    return render_template("cart.html", cart_items=items, total_price=subtotal)

@app.route("/add_to_cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    cart = get_cart()
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    save_cart(cart)
    flash("Item added to cart!", "success")
    return redirect(request.referrer or url_for("cart"))

@app.route("/remove_from_cart/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart = get_cart()
    pid = str(product_id)
    if pid in cart:
        del cart[pid]
        save_cart(cart)
        flash("Item removed!", "info")
    return redirect(url_for("cart"))

@app.route("/checkout")
def checkout():
    items, subtotal = cart_items_details()
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart"))
    total = subtotal + DELIVERY_CHARGE
    return render_template(
        "checkout.html",
        cart_items=items,
        subtotal=subtotal,
        delivery_charge=DELIVERY_CHARGE,
        total_price=total,
    )

@app.route("/place_order", methods=["POST"])
def place_order():
    cart_items, subtotal = cart_items_details()
    total = subtotal + DELIVERY_CHARGE
    name = request.form.get('name', 'Anonymous')
    contact = request.form.get('contact', '')
    email = request.form.get('email', '')
    address = request.form.get('address', '') # CHANGE 1: GET THE ADDRESS
    upi_txn = request.form.get('upi_txn', '')
    screenshot = request.files.get('screenshot')
    screenshot_filename = ""
    if screenshot and allowed_file(screenshot.filename):
        unique_filename = f"{name.replace(' ', '_')}_{contact}_{screenshot.filename}"
        # Call the new function to upload the screenshot
        drive_link = upload_to_drive_and_get_link(screenshot, unique_filename)
        
        if drive_link:
            screenshot_link = drive_link
        else:
            screenshot_link = "Error uploading to Google Drive"
    try:
        sheet = get_gsheet()
        item_summary = "; ".join(f"{i['product']['name']} x{i['quantity']}" for i in cart_items)
        # CHANGE 2: ADD 'address' TO THE ROW
        sheet.append_row([
            name, contact, email, address,
            item_summary, subtotal, DELIVERY_CHARGE, total,
            upi_txn, screenshot_link,
        ])
        success = True
    except Exception as e:
        print("Google Sheets Error:", e)
    session.pop('cart', None)
    if success:
        flash("Order placed! Thank you for shopping. We will contact you soon.", "success")
    else:
        flash("Order received, but there was a problem saving to Google Sheets. We will contact you soon.", "warning")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
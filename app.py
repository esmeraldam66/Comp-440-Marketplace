from getpass import getpass
import re
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import messagebox, simpledialog
import bcrypt
import mysql.connector
from mysql.connector import IntegrityError

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": getpass("Enter your MySQL root password: "),
    "database": "comp440",
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

current_user = None

def delete_item(item_id):
    if current_user is None:
        return False, "Please log in first."

    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "DELETE FROM item "
            "WHERE itemID = %s AND username = %s",
            (item_id, current_user)
        )

        if cur.rowcount == 0:
            conn.rollback()
            return False, "Item not found or you do not own it."

        conn.commit()
        return True, "Item deleted successfully!"

    except mysql.connector.Error as error:
        if conn is not None:
            conn.rollback()

        return False, error.msg

    finally:
        if conn is not None:
            conn.close()
            
def update_item_price(item_id, price_text):
    if current_user is None:
        return False, "Please log in first."

    try:
        price = Decimal(price_text.strip())

        if not price.is_finite():
            return False, "Enter a valid price."

        if price < 0 or price > Decimal("99999999.99"):
            return False, "Price must be between 0 and 99999999.99."

        if price != price.quantize(Decimal("0.01")):
            return False, "Price can have at most two decimal places."

    except InvalidOperation:
        return False, "Enter a valid price, such as 19.99."

    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT itemID FROM item "
            "WHERE itemID = %s AND username = %s "
            "FOR UPDATE",
            (item_id, current_user)
        )

        if cur.fetchone() is None:
            conn.rollback()
            return False, "Item not found or you do not own it."

        cur.execute(
            "UPDATE item SET price = %s "
            "WHERE itemID = %s AND username = %s",
            (price, item_id, current_user)
        )

        conn.commit()
        return True, "Price updated successfully!"

    except mysql.connector.Error as error:
        if conn is not None:
            conn.rollback()

        return False, error.msg

    finally:
        if conn is not None:
            conn.close()

def get_my_items():
    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT itemID, title, price, datePosted "
            "FROM item "
            "WHERE username = %s "
            "ORDER BY itemID",
            (current_user,)
        )

        items = cur.fetchall()
        return True, items

    except mysql.connector.Error as error:
        return False, error.msg

    finally:
        if conn is not None:
            conn.close()

def create_item(title, description, price_text, categories_text):
    if current_user is None:
        return False, "Please log in first."

    title = title.strip()
    description = description.strip()

    if title == "" or description == "":
        return False, "Title and description are required."

    if len(title) > 100:
        return False, "Title must be 100 characters or fewer."

    try:
        price = Decimal(price_text.strip())

        if not price.is_finite():
            return False, "Enter a valid price."

        if price < 0 or price > Decimal("99999999.99"):
            return False, "Price must be between 0 and 99999999.99."

        if price != price.quantize(Decimal("0.01")):
            return False, "Price can have at most two decimal places."

    except InvalidOperation:
        return False, "Enter a valid price, such as 19.99."

    categories = []

    for name in categories_text.split(","):
        name = name.strip()

        if re.fullmatch("[a-z]{1,35}", name) is None:
            return False, "Use lowercase category words, like books,gaming."

        if name not in categories:
            categories.append(name)

    conn = None

    try:
        conn = get_connection()
        conn.start_transaction()
        cur = conn.cursor()

        result = cur.callproc(
            "add_item",
            (title, description, price, current_user, 0)
        )

        item_id = result[4]

        for name in categories:
            cur.execute(
                "INSERT INTO category (categoryName, itemID) "
                "VALUES (%s, %s)",
                (name, item_id)
            )

        conn.commit()
        return True, "Item posted successfully!"

    except mysql.connector.Error as error:
        if conn is not None:
            conn.rollback()

        return False, error.msg

    finally:
        if conn is not None:
            conn.close()

def register_user(username, password, confirm, first, last, email, phone):

    if not all([username, password, confirm, first, last, email, phone]):
        return False, "All fields are required."
    if password != confirm:
        return False, "Passwords do not match."

    conn = get_connection()
    try:
        cur = conn.cursor()

       
        cur.execute("SELECT 1 FROM `user` WHERE username = %s", (username,))
        if cur.fetchone():
            return False, "Username already exists."

        
        cur.execute("SELECT 1 FROM `user` WHERE email = %s", (email,))
        if cur.fetchone():
            return False, "Email already registered."

       
        cur.execute("SELECT 1 FROM `user` WHERE phone = %s", (phone,))
        if cur.fetchone():
            return False, "Phone number already registered."

  
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cur.execute(
            "INSERT INTO `user` (username, password, firstName, lastName, email, phone) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (username, hashed, first, last, email, phone),
        )
        conn.commit()
        return True, "Account created! Log in."
    except IntegrityError:

        return False, "Username, email, or phone already exists."
    finally:
        conn.close()

def login_user(username, password):
    
    if not username or not password:
        return False, "Enter your username and password."
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT password, firstName FROM `user` WHERE username = %s", (username,)
        )
        row = cur.fetchone()
        if row and bcrypt.checkpw(password.encode("utf-8"), row[0].encode("utf-8")):
            return True, f"Welcome, {row[1]}!"
        return False, "Invalid username or password."
    finally:
        conn.close()



def clear_window():
    for widget in window.winfo_children():
        widget.destroy()


def signup_page():
    clear_window()

    tk.Label(window, text="Sign Up", font=("Arial", 20)).pack(pady=15)

    entries = {}

    fields = [
        "Username",
        "Password",
        "Confirm Password",
        "First Name",
        "Last Name",
        "Email",
        "Phone"
    ]

    for field in fields:
        tk.Label(window, text=field).pack()

        if field == "Password" or field == "Confirm Password":
            entry = tk.Entry(window, show="*")
        else:
            entry = tk.Entry(window)

        entry.pack(pady=5)
        entries[field] = entry

    def signup():
        for field in fields:
            if entries[field].get().strip() == "":
                messagebox.showerror("Error", "Please fill in every field.")
                return

        password = entries["Password"].get()
        confirm_password = entries["Confirm Password"].get()

        if password != confirm_password:
            messagebox.showerror("Error", "Passwords do not match.")
            return

        ok, msg = register_user(
            entries["Username"].get().strip(),
            password,
            confirm_password,
            entries["First Name"].get().strip(),
            entries["Last Name"].get().strip(),
            entries["Email"].get().strip(),
            entries["Phone"].get().strip(),
        )
        if ok:
            messagebox.showinfo("Sign Up", msg)
            login_page()
        else:
            messagebox.showerror("Sign Up", msg)

    tk.Button(window, text="Sign Up", command=signup).pack(pady=10)
    tk.Button(window, text="Back to Login", command=login_page).pack()


def login_page():
    clear_window()

    tk.Label(window, text="Login", font=("Arial", 20)).pack(pady=15)

    tk.Label(window, text="Username").pack()
    username_entry = tk.Entry(window)
    username_entry.pack(pady=5)

    tk.Label(window, text="Password").pack()
    password_entry = tk.Entry(window, show="*")
    password_entry.pack(pady=5)

    def login():
        global current_user
        username = username_entry.get().strip()
        password = password_entry.get()

        if username == "" or password == "":
            messagebox.showerror("Error", "Enter your username and password.")
            return

        ok, msg = login_user(username, password)
        if ok:
            current_user = username
            menu_page()
        else:
            messagebox.showerror("Login", msg)

    tk.Button(window, text="Login", command=login).pack(pady=10)
    tk.Button(window, text="Create Account", command=signup_page).pack()

def add_item_page():
    clear_window()

    tk.Label(
        window, text="Add Item", font=("Arial", 20)
    ).pack(pady=15)

    tk.Label(window, text="Title").pack()
    title_entry = tk.Entry(window, width=35)
    title_entry.pack(pady=5)

    tk.Label(window, text="Description").pack()
    description_entry = tk.Text(window, width=35, height=5)
    description_entry.pack(pady=5)

    tk.Label(window, text="Price").pack()
    price_entry = tk.Entry(window, width=35)
    price_entry.pack(pady=5)

    tk.Label(window, text="Categories separated by commas").pack()
    categories_entry = tk.Entry(window, width=35)
    categories_entry.pack(pady=5)

    tk.Label(window, text="Example: books,gaming").pack()

    def submit_item():
        title = title_entry.get()
        description = description_entry.get("1.0", "end-1c")
        price = price_entry.get()
        categories = categories_entry.get()

        ok, msg = create_item(
            title, description, price, categories
        )

        if ok:
            messagebox.showinfo("Add Item", msg)
            menu_page()
        else:
            messagebox.showerror("Add Item", msg)

    tk.Button(
        window, text="Post Item", command=submit_item
    ).pack(pady=15)

    tk.Button(
        window, text="Back to Menu", command=menu_page
    ).pack()

def change_price(item_id):
    new_price = simpledialog.askstring(
        "Update Price",
        "Enter the new price:"
    )

    if new_price is None:
        return

    ok, msg = update_item_price(item_id, new_price)

    if ok:
        messagebox.showinfo("Update Price", msg)
        my_items_page()
    else:
        messagebox.showerror("Update Price", msg)
    
def my_items_page():
    clear_window()

    tk.Label(
        window, text="My Items", font=("Arial", 20)
    ).pack(pady=15)

    ok, result = get_my_items()

    if not ok:
        messagebox.showerror("My Items", result)
        menu_page()
        return

    if len(result) == 0:
        tk.Label(
            window, text="You have not posted any items."
        ).pack(pady=10)

    else:
        for item in result:
            item_id = item[0]
            title = item[1]
            price = item[2]
            date_posted = item[3]

            item_text = (
                f"ID: {item_id} | {title}\n"
                f"Price: ${price:.2f}\n"
                f"Date posted: {date_posted}"
            )

            tk.Label(
                window,
                text=item_text,
                justify="left",
                wraplength=350
            ).pack(pady=10)
            tk.Button(
                window,
                text="Update Price",
                command=lambda selected_id=item_id: change_price(
                    selected_id
                )
            ).pack(pady=4)

    tk.Button(
        window, text="Back to Menu", command=menu_page
    ).pack(pady=15)


def menu_page():
    clear_window()

    tk.Label(
        window, text="Menu", font=("Arial", 20)
    ).pack(pady=15)

    tk.Label(
        window, text=f"Logged in as: {current_user}"
    ).pack(pady=5)

    tk.Button(
        window,
        text="Add Item",
        width=20,
        command=add_item_page
    ).pack(pady=4)
    tk.Button(
        window,
        text="My Items",
        width=20,
        command=my_items_page
    ).pack(pady=4)

    
    for name in [
        "Categories", "Search", "Write Review", "Queries"
    ]:
        tk.Button(
            window,
            text=name,
            width=20,
            command=lambda n=name: messagebox.showinfo(
                n, "Coming soon"
            )
        ).pack(pady=4)

    tk.Button(
        window, text="Log out", command=logout
    ).pack(pady=15)

def logout():
    global current_user
    current_user = None
    login_page()

    
window = tk.Tk()
window.title("User Registration and Login")
window.geometry("400x600")

login_page()
window.mainloop()

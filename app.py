from getpass import getpass
import re
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import messagebox, simpledialog
import bcrypt
import mysql.connector
from mysql.connector import IntegrityError
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": getpass("Enter your MySQL root password: "),
    "database": "comp440",
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

current_user = None

def get_top_posters(date_text):
    date_text = date_text.strip()

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text) is None:
        return False, "Enter a date as YYYY-MM-DD."

    try:
        selected_date = datetime.strptime(
            date_text, "%Y-%m-%d"
        ).date()

    except ValueError:
        return False, "Enter a valid calendar date."

    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT username, COUNT(*) AS item_count "
            "FROM item "
            "WHERE datePosted = %s "
            "GROUP BY username "
            "HAVING COUNT(*) = ("
            "    SELECT MAX(daily_counts.item_count) "
            "    FROM ("
            "        SELECT COUNT(*) AS item_count "
            "        FROM item "
            "        WHERE datePosted = %s "
            "        GROUP BY username"
            "    ) AS daily_counts"
            ") "
            "ORDER BY username",
            (selected_date, selected_date)
        )

        users = cur.fetchall()
        return True, users

    except mysql.connector.Error as error:
        return False, error.msg

    finally:
        if conn is not None:
            conn.close()


def get_only_poor_reviewers():
    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT username "
            "FROM review "
            "GROUP BY username "
            "HAVING COUNT(*) = SUM("
            "    CASE WHEN rating = 'Poor' THEN 1 ELSE 0 END"
            ") "
            "ORDER BY username"
        )

        users = cur.fetchall()
        return True, users

    except mysql.connector.Error as error:
        return False, error.msg

    finally:
        if conn is not None:
            conn.close()


def get_users_without_poor_reviews():
    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT user.username "
            "FROM `user` AS user "
            "WHERE NOT EXISTS ("
            "    SELECT 1 "
            "    FROM item "
            "    JOIN review ON item.itemID = review.itemID "
            "    WHERE item.username = user.username "
            "    AND review.rating = 'Poor'"
            ") "
            "ORDER BY user.username"
        )

        users = cur.fetchall()
        return True, users

    except mysql.connector.Error as error:
        return False, error.msg

    finally:
        if conn is not None:
            conn.close()

def get_positive_review_items(username):
    username = username.strip()

    if username == "":
        return False, "Enter a seller's username."

    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT item.itemID, item.title, item.price "
            "FROM item "
            "WHERE item.username = %s "
            "AND EXISTS ("
            "    SELECT 1 FROM review "
            "    WHERE review.itemID = item.itemID"
            ") "
            "AND NOT EXISTS ("
            "    SELECT 1 FROM review "
            "    WHERE review.itemID = item.itemID "
            "    AND review.rating IN ('Fair', 'Poor')"
            ") "
            "ORDER BY item.itemID",
            (username,)
        )

        items = cur.fetchall()
        return True, items

    except mysql.connector.Error as error:
        if conn is not None:
            conn.rollback()

        return False, error.msg

    finally:
        if conn is not None:
            conn.close()

def get_users_by_categories(category_x, category_y):
    category_x = category_x.strip()
    category_y = category_y.strip()

    for category in [category_x, category_y]:
        if re.fullmatch("[a-z]{1,35}", category) is None:
            return False, "Enter one lowercase word for each category."

    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT DISTINCT first_item.username, first_item.datePosted "
            "FROM item AS first_item "
            "JOIN category AS first_category "
            "ON first_item.itemID = first_category.itemID "
            "JOIN item AS second_item "
            "ON first_item.username = second_item.username "
            "AND first_item.datePosted = second_item.datePosted "
            "AND first_item.itemID <> second_item.itemID "
            "JOIN category AS second_category "
            "ON second_item.itemID = second_category.itemID "
            "WHERE first_category.categoryName = %s "
            "AND second_category.categoryName = %s "
            "ORDER BY first_item.username, first_item.datePosted",
            (category_x, category_y)
        )

        users = cur.fetchall()
        return True, users

    except mysql.connector.Error as error:
        return False, error.msg

    finally:
        if conn is not None:
            conn.close()

def get_most_expensive_items():
    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT category.categoryName, item.itemID, "
            "item.title, item.price "
            "FROM item "
            "JOIN category ON item.itemID = category.itemID "
            "WHERE item.price = ("
            "    SELECT MAX(other_item.price) "
            "    FROM item AS other_item "
            "    JOIN category AS other_category "
            "    ON other_item.itemID = other_category.itemID "
            "    WHERE other_category.categoryName = category.categoryName"
            ") "
            "ORDER BY category.categoryName, item.itemID"
        )

        items = cur.fetchall()
        return True, items

    except mysql.connector.Error as error:
        return False, error.msg

    finally:
        if conn is not None:
            conn.close()

def submit_review(item_id_text, rating, comment):
    if current_user is None:
        return False, "Please log in first."

    try:
        item_id = int(item_id_text.strip())

        if item_id <= 0:
            return False, "Enter a valid item ID."

    except ValueError:
        return False, "Item ID must be a whole number."

    if rating not in ["Excellent", "Good", "Fair", "Poor"]:
        return False, "Select a valid rating."

    comment = comment.strip()

    if comment == "" or len(comment) > 300:
        return False, "Comment must be between 1 and 300 characters."

    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT itemID FROM item WHERE itemID = %s",
            (item_id,)
        )

        if cur.fetchone() is None:
            return False, "Item not found."

        cur.callproc(
            "add_review",
            (rating, comment, item_id, current_user)
        )

        conn.commit()
        return True, "Review submitted successfully!"

    except mysql.connector.Error as error:
        if conn is not None:
            conn.rollback()

        return False, error.msg

    finally:
        if conn is not None:
            conn.close()

def search_by_category(category_name):
    category_name = category_name.strip()

    if re.fullmatch("[a-z]{1,35}", category_name) is None:
        return False, "Enter one lowercase word, like books."

    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT item.itemID, item.title, item.price, "
            "item.username, item.datePosted "
            "FROM item "
            "JOIN category ON item.itemID = category.itemID "
            "WHERE category.categoryName = %s "
            "ORDER BY item.itemID",
            (category_name,)
        )

        items = cur.fetchall()
        return True, items

    except mysql.connector.Error as error:
        return False, error.msg

    finally:
        if conn is not None:
            conn.close()

def remove_category(item_id, category_name):
    if current_user is None:
        return False, "Please log in first."

    category_name = category_name.strip()

    if re.fullmatch("[a-z]{1,35}", category_name) is None:
        return False, "Enter one lowercase word, like books."

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
            "SELECT categoryName FROM category WHERE itemID = %s",
            (item_id,)
        )

        categories = cur.fetchall()

        found = False

        for category in categories:
            if category[0] == category_name:
                found = True

        if not found:
            conn.rollback()
            return False, "This item does not have that category."

        if len(categories) <= 1:
            conn.rollback()
            return False, "An item must keep at least one category."

        cur.execute(
            "DELETE FROM category "
            "WHERE itemID = %s AND categoryName = %s",
            (item_id, category_name)
        )

        conn.commit()
        return True, "Category removed successfully!"

    except mysql.connector.Error as error:
        if conn is not None:
            conn.rollback()

        return False, error.msg

    finally:
        if conn is not None:
            conn.close()

def assign_category(item_id, category_name):
    if current_user is None:
        return False, "Please log in first."

    category_name = category_name.strip()

    if re.fullmatch("[a-z]{1,35}", category_name) is None:
        return False, "Enter one lowercase word, like books."

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
            "SELECT categoryName FROM category "
            "WHERE itemID = %s AND categoryName = %s",
            (item_id, category_name)
        )

        if cur.fetchone() is not None:
            conn.rollback()
            return False, "This item already has that category."

        cur.execute(
            "INSERT INTO category (categoryName, itemID) "
            "VALUES (%s, %s)",
            (category_name, item_id)
        )

        conn.commit()
        return True, "Category added successfully!"

    except mysql.connector.Error as error:
        if conn is not None:
            conn.rollback()

        return False, error.msg

    finally:
        if conn is not None:
            conn.close()

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

def confirm_delete(item_id):
    confirmed = messagebox.askyesno(
        "Delete Item",
        "Delete this item? Its categories and reviews "
        "will also be removed."
    )

    if not confirmed:
        return

    ok, msg = delete_item(item_id)

    if ok:
        messagebox.showinfo("Delete Item", msg)
        my_items_page()
    else:
        messagebox.showerror("Delete Item", msg)
 
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
                window,
                text="Delete Item",
                command=lambda selected_id=item_id: confirm_delete(
                    selected_id
                )
            ).pack(pady=4)

    tk.Button(
        window, text="Back to Menu", command=menu_page
    ).pack(pady=15)

def categories_page():
    clear_window()

    tk.Label(
        window, text="Categories", font=("Arial", 20)
    ).pack(pady=15)

    ok, items = get_my_items()

    if not ok:
        messagebox.showerror("Categories", items)
        menu_page()
        return

    if len(items) == 0:
        tk.Label(
            window, text="Post an item before adding categories."
        ).pack(pady=10)

    else:
        item_list = tk.Listbox(window, width=40, height=8)
        item_list.pack(pady=10)

        for item in items:
            item_list.insert(
                tk.END, f"ID: {item[0]} | {item[1]}"
            )

        tk.Label(window, text="Select an item above.").pack()

        tk.Label(
            window, text="Category (one lowercase word)"
        ).pack(pady=5)

        category_entry = tk.Entry(window, width=30)
        category_entry.pack(pady=5)

        def add_category():
            selection = item_list.curselection()

            if len(selection) == 0:
                messagebox.showerror(
                    "Categories", "Select an item first."
                )
                return

            selected_item = items[selection[0]]
            item_id = selected_item[0]
            category_name = category_entry.get()

            ok, msg = assign_category(item_id, category_name)

            if ok:
                messagebox.showinfo("Categories", msg)
                category_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Categories", msg)

        tk.Button(
            window, text="Add Category", command=add_category
        ).pack(pady=10)
        def delete_category():
            selection = item_list.curselection()

            if len(selection) == 0:
                messagebox.showerror(
                    "Categories", "Select an item first."
                )
                return

            selected_item = items[selection[0]]
            item_id = selected_item[0]
            category_name = category_entry.get()

            ok, msg = remove_category(item_id, category_name)

            if ok:
                messagebox.showinfo("Categories", msg)
                category_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Categories", msg)

        tk.Button(
            window,
            text="Remove Category",
            command=delete_category
        ).pack(pady=5)

    tk.Button(
        window, text="Back to Menu", command=menu_page
    ).pack(pady=15)

def search_page():
    clear_window()

    tk.Label(
        window, text="Search by Category", font=("Arial", 20)
    ).pack(pady=15)

    tk.Label(window, text="Enter a category, like books").pack()

    category_entry = tk.Entry(window, width=30)
    category_entry.pack(pady=5)

    results_box = tk.Text(
        window, width=42, height=15, wrap="word"
    )

    def search():
        category_name = category_entry.get()
        ok, result = search_by_category(category_name)

        results_box.config(state="normal")
        results_box.delete("1.0", tk.END)

        if not ok:
            messagebox.showerror("Search", result)

        elif len(result) == 0:
            results_box.insert(
                tk.END, "No items found in this category."
            )

        else:
            for item in result:
                item_text = (
                    f"ID: {item[0]} | {item[1]}\n"
                    f"Price: ${item[2]:.2f}\n"
                    f"Seller: {item[3]}\n"
                    f"Date posted: {item[4]}\n"
                    "------------------------------\n"
                )

                results_box.insert(tk.END, item_text)

        results_box.config(state="disabled")

    tk.Button(
        window, text="Search", command=search
    ).pack(pady=10)

    results_box.pack(pady=5)
    results_box.config(state="disabled")

    tk.Button(
        window, text="Back to Menu", command=menu_page
    ).pack(pady=10)

def review_page():
    clear_window()

    tk.Label(
        window, text="Write Review", font=("Arial", 20)
    ).pack(pady=15)

    tk.Label(
        window, text="Use Search to find an item's ID."
    ).pack(pady=5)

    tk.Label(window, text="Item ID").pack()
    item_id_entry = tk.Entry(window, width=30)
    item_id_entry.pack(pady=5)

    tk.Label(window, text="Rating").pack()

    rating_choice = tk.StringVar(window)
    rating_choice.set("Excellent")

    tk.OptionMenu(
        window,
        rating_choice,
        "Excellent",
        "Good",
        "Fair",
        "Poor"
    ).pack(pady=5)

    tk.Label(window, text="Comment (1-300 characters)").pack()

    comment_entry = tk.Text(
        window, width=35, height=5, wrap="word"
    )
    comment_entry.pack(pady=5)

    tk.Label(
        window, text="Reviews cannot be edited after submission."
    ).pack(pady=5)

    def post_review():
        item_id = item_id_entry.get()
        rating = rating_choice.get()
        comment = comment_entry.get("1.0", "end-1c")

        confirmed = messagebox.askyesno(
            "Submit Review",
            "Submit this review? You cannot edit it afterward."
        )

        if not confirmed:
            return

        ok, msg = submit_review(item_id, rating, comment)

        if ok:
            messagebox.showinfo("Write Review", msg)
            menu_page()
        else:
            messagebox.showerror("Write Review", msg)

    tk.Button(
        window, text="Submit Review", command=post_review
    ).pack(pady=10)

    tk.Button(
        window, text="Back to Menu", command=menu_page
    ).pack(pady=10)

def query_one_page():
    clear_window()

    tk.Label(
        window,
        text="Most Expensive Items by Category",
        font=("Arial", 14),
        wraplength=350
    ).pack(pady=15)

    ok, result = get_most_expensive_items()

    if not ok:
        messagebox.showerror("Query 1", result)
        queries_page()
        return

    results_box = tk.Text(
        window, width=42, height=20, wrap="word"
    )
    results_box.pack(pady=10)

    if len(result) == 0:
        results_box.insert(tk.END, "No items found.")

    else:
        for item in result:
            item_text = (
                f"Category: {item[0]}\n"
                f"ID: {item[1]} | {item[2]}\n"
                f"Price: ${item[3]:.2f}\n"
                "------------------------------\n"
            )

            results_box.insert(tk.END, item_text)

    results_box.config(state="disabled")

    tk.Button(
        window,
        text="Back to Queries",
        command=queries_page
    ).pack(pady=10)

def query_two_page():
    clear_window()

    tk.Label(
        window,
        text="Users Who Posted in Two Categories",
        font=("Arial", 14),
        wraplength=350
    ).pack(pady=15)

    tk.Label(window, text="Category X").pack()
    category_x_entry = tk.Entry(window, width=30)
    category_x_entry.pack(pady=5)

    tk.Label(window, text="Category Y").pack()
    category_y_entry = tk.Entry(window, width=30)
    category_y_entry.pack(pady=5)

    results_box = tk.Text(
        window, width=42, height=12, wrap="word"
    )

    def run_query():
        category_x = category_x_entry.get()
        category_y = category_y_entry.get()

        ok, result = get_users_by_categories(
            category_x, category_y
        )

        results_box.config(state="normal")
        results_box.delete("1.0", tk.END)

        if not ok:
            messagebox.showerror("Query 2", result)

        elif len(result) == 0:
            results_box.insert(tk.END, "No matching users found.")

        else:
            for user in result:
                user_text = (
                    f"Username: {user[0]}\n"
                    f"Date posted: {user[1]}\n"
                    "------------------------------\n"
                )

                results_box.insert(tk.END, user_text)

        results_box.config(state="disabled")

    tk.Button(
        window, text="Run Query", command=run_query
    ).pack(pady=10)

    results_box.pack(pady=5)
    results_box.config(state="disabled")

    tk.Button(
        window,
        text="Back to Queries",
        command=queries_page
    ).pack(pady=10)

def query_three_page():
    clear_window()

    tk.Label(
        window,
        text="Seller's Items with Only Excellent or Good Reviews",
        font=("Arial", 14),
        wraplength=350
    ).pack(pady=15)

    tk.Label(window, text="Seller username").pack()

    username_entry = tk.Entry(window, width=30)
    username_entry.pack(pady=5)

    results_box = tk.Text(
        window, width=42, height=15, wrap="word"
    )

    def run_query():
        username = username_entry.get()
        ok, result = get_positive_review_items(username)

        results_box.config(state="normal")
        results_box.delete("1.0", tk.END)

        if not ok:
            messagebox.showerror("Query 3", result)

        elif len(result) == 0:
            results_box.insert(tk.END, "No matching items found.")

        else:
            for item in result:
                item_text = (
                    f"ID: {item[0]} | {item[1]}\n"
                    f"Price: ${item[2]:.2f}\n"
                    "------------------------------\n"
                )

                results_box.insert(tk.END, item_text)

        results_box.config(state="disabled")

    tk.Button(
        window, text="Run Query", command=run_query
    ).pack(pady=10)

    results_box.pack(pady=5)
    results_box.config(state="disabled")

    tk.Button(
        window,
        text="Back to Queries",
        command=queries_page
    ).pack(pady=10)

def query_four_page():
    clear_window()

    tk.Label(
        window,
        text="Users with the Most Posts on a Date",
        font=("Arial", 14),
        wraplength=350
    ).pack(pady=15)

    tk.Label(window, text="Date: YYYY-MM-DD").pack()

    date_entry = tk.Entry(window, width=30)
    date_entry.pack(pady=5)

    results_box = tk.Text(
        window, width=42, height=14, wrap="word"
    )

    def run_query():
        date_text = date_entry.get()
        ok, result = get_top_posters(date_text)

        results_box.config(state="normal")
        results_box.delete("1.0", tk.END)

        if not ok:
            messagebox.showerror("Query 4", result)

        elif len(result) == 0:
            results_box.insert(
                tk.END, "No items were posted on this date."
            )

        else:
            for user in result:
                user_text = (
                    f"Username: {user[0]}\n"
                    f"Items posted: {user[1]}\n"
                    "------------------------------\n"
                )

                results_box.insert(tk.END, user_text)

        results_box.config(state="disabled")

    tk.Button(
        window, text="Run Query", command=run_query
    ).pack(pady=10)

    results_box.pack(pady=5)
    results_box.config(state="disabled")

    tk.Button(
        window,
        text="Back to Queries",
        command=queries_page
    ).pack(pady=10)


def query_five_page():
    clear_window()

    tk.Label(
        window,
        text="Users Who Have Written Only Poor Reviews",
        font=("Arial", 14),
        wraplength=350
    ).pack(pady=15)

    ok, result = get_only_poor_reviewers()

    if not ok:
        messagebox.showerror("Query 5", result)
        queries_page()
        return

    results_box = tk.Text(
        window, width=42, height=18, wrap="word"
    )
    results_box.pack(pady=10)

    if len(result) == 0:
        results_box.insert(tk.END, "No matching users found.")

    else:
        for user in result:
            results_box.insert(
                tk.END, f"Username: {user[0]}\n\n"
            )

    results_box.config(state="disabled")

    tk.Button(
        window,
        text="Back to Queries",
        command=queries_page
    ).pack(pady=10)


def query_six_page():
    clear_window()

    tk.Label(
        window,
        text="Users Whose Items Have Never Received a Poor Review",
        font=("Arial", 14),
        wraplength=350
    ).pack(pady=15)

    ok, result = get_users_without_poor_reviews()

    if not ok:
        messagebox.showerror("Query 6", result)
        queries_page()
        return

    results_box = tk.Text(
        window, width=42, height=18, wrap="word"
    )
    results_box.pack(pady=10)

    if len(result) == 0:
        results_box.insert(tk.END, "No matching users found.")

    else:
        for user in result:
            results_box.insert(
                tk.END, f"Username: {user[0]}\n\n"
            )

    results_box.config(state="disabled")

    tk.Button(
        window,
        text="Back to Queries",
        command=queries_page
    ).pack(pady=10)

def queries_page():
    clear_window()

    tk.Label(
        window, text="Queries", font=("Arial", 20)
    ).pack(pady=15)

    tk.Button(
        window,
        text="1. Most expensive items by category",
        command=query_one_page,
        wraplength=320
    ).pack(pady=8)

    tk.Button(
        window,
        text="2. Users who posted in categories X and Y",
        command=query_two_page,
        wraplength=320
    ).pack(pady=8)

    tk.Button(
        window,
        text="3. Seller's items with only positive reviews",
        command=query_three_page,
        wraplength=320
    ).pack(pady=8)

    tk.Button(
        window,
        text="4. Users with the most posts on a date",
        command=query_four_page,
        wraplength=320
    ).pack(pady=8)

    tk.Button(
        window,
        text="5. Users who have written only Poor reviews",
        command=query_five_page,
        wraplength=320
    ).pack(pady=8)

    tk.Button(
        window,
        text="6. Users whose items have no Poor reviews",
        command=query_six_page,
        wraplength=320
    ).pack(pady=8)

    tk.Button(
        window,
        text="Back to Menu",
        command=menu_page
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
    tk.Button(
        window,
        text="Categories",
        width=20,
        command=categories_page
    ).pack(pady=4)
    tk.Button(
        window,
        text="Search",
        width=20,
        command=search_page
    ).pack(pady=4)
    tk.Button(
        window,
        text="Write Review",
        width=20,
        command=review_page
    ).pack(pady=4)

    
    tk.Button(
        window,
        text="Queries",
        width=20,
        command=queries_page
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

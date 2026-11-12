import tkinter as tk
from tkinter import messagebox
import bcrypt
import mysql.connector
from mysql.connector import IntegrityError

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YourSQLPassword",
    "database": "comp440",
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)



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
        username = username_entry.get().strip()
        password = password_entry.get()

        if username == "" or password == "":
            messagebox.showerror("Error", "Enter your username and password.")
            return

        ok, msg = login_user(username, password)
        if ok:
            messagebox.showinfo("Login", msg)
        else:
            messagebox.showerror("Login", msg)

    tk.Button(window, text="Login", command=login).pack(pady=10)
    tk.Button(window, text="Create Account", command=signup_page).pack()


window = tk.Tk()
window.title("User Registration and Login")
window.geometry("400x600")

login_page()
window.mainloop()

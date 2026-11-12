<div align="center">

# 🛍️ Comp-440 Marketplace ✨

*A cozy little marketplace app: sign up, log in, and (soon!) post and review items* 💖

![Python](https://img.shields.io/badge/Python-3-ffb6c1?style=for-the-badge&logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-database-c3b1e1?style=for-the-badge&logo=mysql&logoColor=white)
![Tkinter](https://img.shields.io/badge/Tkinter-GUI-a7d8f0?style=for-the-badge)

**COMP 440 · Team 6 · Phase 1** 🌷

🎬 [Watch our demo video](https://youtu.be/xDfh11z8CCU)

</div>

---

## 🌸 What it does

- 📝 **Sign up** with a username, password, name, email and phone
- 🔐 **Log in** safely. Passwords are scrambled with **bcrypt**, so they're never stored as plain text
- 🚫 **No duplicates.** Each username, email and phone number can only be used once
- 🛡️ **SQL injection protection.** Every query uses placeholders (`%s`), so sneaky input can't break the database

## 🗂️ Database tables

| Table | What it holds |
|-------|---------------|
| 👤 `user` | Accounts: username, hashed password, name, email, phone |
| 🧸 `item` | Things for sale: title, description, price, date posted |
| ⭐ `review` | Ratings (Excellent / Good / Fair / Poor) and comments on items |
| 🏷️ `category` | Lowercase tags for items, like `electronics` or `books` |

✨ **Fun rule:** a trigger makes sure each user can post **at most 2 items per day**.

## 🚀 How to run it

**1. Install the helpers** 📦

```
pip install mysql-connector-python bcrypt
```

**2. Make the database** 🗄️

Run `schema.sql` in MySQL (Workbench or the command line).

**3. Add your MySQL password** 🔑

Open `app.py` and replace `YourSQLPassword` in `DB_CONFIG` with your own password.
⚠️ Don't push your real password to GitHub!

**4. Start the app** 🎉

```
python app.py
```

## 📁 Files

```
Comp-440-Marketplace/
├── app.py        💻 the app (login + sign up screens)
├── schema.sql    🗄️ creates the database and tables
└── README.md     🌷 you are here!
```

---

<div align="center">

Made with 💕 and lots of ☕ by Team 6

</div>

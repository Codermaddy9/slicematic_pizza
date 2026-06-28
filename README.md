# 🍕 SliceMatic Ordering System

A **Gradio-based Pizza Ordering Application** developed as part of the **FDE Academy – PizzaFlow Applied Project**.

---

## 📌 Overview

SliceMatic is an interactive pizza ordering system built using **Python** and **Gradio**. The application allows users to build customized pizza orders, manage a shopping cart, generate professional invoices, and place orders using multiple payment methods.

---

## ✨ Features

- 👤 Customer Registration
  - Name Validation
  - Mobile Number Validation

- 🍕 Dynamic Menu Loading
  - Pizza Bases
  - Pizza Types
  - Toppings
  - Loaded directly from text files

- 🛒 Shopping Cart
  - Multiple pizza combinations
  - Add / Remove items
  - Running subtotal

- 💰 Billing Engine
  - Automatic subtotal calculation
  - 10% discount on orders of 5+ pizzas
  - 18% GST calculation
  - Professional invoice generation

- 💳 Payment Methods
  - Cash
  - Card
  - UPI

- 📝 Order Logging
  - Local log file
  - Optional Hugging Face Dataset integration

---

## 📂 Project Structure

```
SliceMatic-Ordering-System/
│
├── slicematic_cart.py
├── Types_of_Base.txt
├── Types_of_Pizza.txt
├── Types_of_Toppings.txt
├── orders_log.txt
├── requirements.txt
├── README.md
└── .gitignore
```

---

## ⚙️ Requirements

- Python 3.10+
- Gradio
- huggingface_hub *(Optional)*

Install dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Run the Application

```bash
python slicematic_cart.py
```

The application will launch locally in your default browser.

---

## 📋 Menu File Format

The application loads menu items from

- Types_of_Base.txt
- Types_of_Pizza.txt
- Types_of_Toppings.txt

Each file follows the format

```
ID;Name;Price
```

Example

```
1;Thin Crust;120
2;Chicago Deep Dish;180
```

---

## 💵 Pricing Rules

| Rule | Value |
|------|-------|
| Maximum quantity per combo | 10 |
| Maximum pizzas per order | 10 |
| Discount | 10% on 5+ pizzas |
| GST | 18% after discount |

---

## 💳 Payment Options

- 💵 Cash
- 💳 Card
- 📱 UPI

---

## 🛠️ Tech Stack

- Python
- Gradio
- HTML
- CSS
- Hugging Face Hub *(Optional)*
- Decimal Module

---

## 🚀 Future Enhancements

- 📊 Order History Dashboard
- 📦 Inventory Management
- 👨‍💼 Admin Portal
- 📧 Email / SMS Notifications
- 🗄️ Database Integration
- 🔐 User Authentication
- 🍳 Kitchen Dashboard
- 📦 Real-time Inventory Tracking
- 📈 Sales Analytics Dashboard

---

## 👨‍💻 Author

**Madhav Mehta**

Developed as part of the **FDE Academy – PizzaFlow Applied Project**.

---
⭐ If you found this project interesting, feel free to star the repository.

# 🍕 SliceMatic Ordering System

A **Gradio-based Pizza Ordering Application** developed as part of the **FDE Academy – PizzaFlow Applied Project**.

The application provides an interactive pizza ordering experience with dynamic menu loading, cart management, automatic billing, and multiple payment options.

---

## 🚀 Features

* 👤 Customer registration with **Name** and **Mobile Number** validation
* 🍕 Dynamic menu loaded from external text files
* 🫓 Multiple pizza base (crust) options
* 🧄 Optional toppings
* 🛒 Shopping cart supporting multiple pizza combinations
* 💰 Automatic subtotal, discount, GST, and final bill calculation
* 🎁 **10% discount** for qualifying orders
* 💳 Multiple payment methods:

  * Cash
  * Card
  * UPI
* 🧾 Professional invoice/receipt generation
* 📝 Local order logging
* ☁️ Optional Hugging Face Dataset logging for cloud persistence
* 🎨 Interactive and responsive Gradio user interface

---

## 📂 Project Structure

```text
SliceMatic-Ordering-System/
│
├── slicematic_cart.py          # Main application
├── Types_of_Base.txt           # Pizza base menu
├── Types_of_Pizza.txt          # Pizza menu
├── Types_of_Toppings.txt       # Toppings menu
├── orders_log.txt              # Auto-generated order log
├── requirements.txt            # Project dependencies
├── README.md
└── .gitignore
```

---

## ⚙️ Requirements

* Python 3.10+
* Gradio
* huggingface_hub *(optional for cloud logging)*

Install the required packages:

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Application

```bash
python slicematic_cart.py
```

Once started, Gradio launches a local web application that can be accessed through your browser.

---

## 📋 Menu File Format

The application loads menu items from:

* `Types_of_Base.txt`
* `Types_of_Pizza.txt`
* `Types_of_Toppings.txt`

Each file follows the format:

```text
ID;Name;Price
```

Example:

```text
1;Thin Crust;120
2;Chicago Deep Dish;180
```

---

## 💵 Pricing Rules

| Rule                       |                              Value |
| -------------------------- | ---------------------------------: |
| Maximum quantity per combo |                                 10 |
| Maximum pizzas per order   |                                 10 |
| Discount                   | 10% (Orders with 5 or more pizzas) |
| GST                        |       18% (Applied after discount) |

---

## 💳 Payment Methods

* 💵 Cash
* 💳 Card
* 📱 UPI

---

## 🛠️ Technologies Used

* Python
* Gradio
* HTML & CSS
* Hugging Face Hub *(optional)*
* Python Decimal module for accurate financial calculations

---

## 🔮 Future Enhancements

* 📊 Order History Dashboard
* 📦 Inventory Management System
* 👨‍💼 Admin Portal
* 📧 Email & SMS Notifications
* 🗄️ Database Integration
* 🔐 User Authentication
* 🍳 Kitchen Dashboard with Real-Time Order Queue
* 📈 Real-Time Inventory Tracking
* 📱 Mobile-Friendly Responsive UI
* 📊 Sales Analytics Dashboard

---

## 👨‍💻 Author

**Madhav Mehta**
**Ishan Shekar**
**Shashidharr**

Developed as part of the **FDE Academy – PizzaFlow Applied Project**.

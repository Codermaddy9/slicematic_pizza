🍕 SliceMatic Ordering System
A Gradio-based Pizza Ordering Application developed as part of the
FDE Academy PizzaFlow Applied Project.
Features
👤 Customer registration (Name & Mobile Number validation)
🍕 Dynamic menu loaded from text files
🫓 Multiple crust base options
🧄 Optional toppings
🛒 Shopping cart with multiple items
💰 Automatic subtotal, discount, GST and final bill calculation
🎁 10% discount for qualifying orders
💳 Multiple payment options (Cash, Card, UPI)
🧾 Professional order receipt
📝 Local order logging
☁️ Optional Hugging Face Dataset logging
Project Structure
    SliceMatic-Ordering-System/
    │
    ├── slicematic_cart.py
    ├── Types_of_Base.txt
    ├── Types_of_Pizza.txt
    ├── Types_of_Toppings.txt
    ├── orders_log.txt          # Auto-generated
    ├── requirements.txt
    ├── README.md
    └── .gitignore

Requirements
Python 3.10+
Gradio
huggingface_hub (optional)
Install dependencies:
``` bash
pip install -r requirements.txt
```
Running the Application
``` bash
python slicematic_cart.py
```
The Gradio application will start locally and open in your browser.
Menu Files
The application reads menu items from:
`Types_of_Base.txt`
`Types_of_Pizza.txt`
`Types_of_Toppings.txt`
Each file follows this format:
    ID;Name;Price

Example:
    1;Thin Crust;120
    2;Chicago Deep Dish;180

Pricing Rules
Maximum quantity per combo: 10
Maximum pizzas per order: 10
Orders with 5 or more pizzas receive a 10% discount
18% GST is applied after the discount
Payment Methods
Cash
Card
UPI
Technologies Used
Python
Gradio
HTML/CSS
Hugging Face Hub (optional)
Decimal module for accurate billing
Future Improvements
Order history dashboard
Inventory management
Admin portal
Email/SMS notifications
Database integration
User authentication
Kitchen app- which shows real time inventory available
Author
Madhav Mehta
Developed as part of the FDE Academy PizzaFlow Applied Project.

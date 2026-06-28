"""
SliceMatic Ordering System — Stage 2 MVP (Cart Edition v4)
FDE Academy · Batch 2487 · PizzaFlow Applied Project

v4 changes (UI reliability fixes):
  - Every step's controls are wrapped in `gr.Group(visible=False)`. The render
    function toggles GROUPS, never individual button visibility. This avoids
    a Gradio quirk where buttons inside a Row that's initially all-hidden
    sometimes fail to re-appear when set visible=True.
  - Every component is initialized with its proper starting value at creation
    time (so the UI is functional even if demo.load doesn't fire).
  - Each post-cart step has its own Back button inside its own group.
  - Every event handler is wrapped in _safe() — exceptions show as a banner
    instead of silently killing the UI.
  - demo.queue() enabled so HF dataset upload doesn't block the UI.

Customer journey (unchanged):
  name → phone → [base → pizza → topping → qty → cart] (loop) → bill → payment → done
"""

import gradio as gr
import re
import os
import sys
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────
DISCOUNT_THRESHOLD = 5
DISCOUNT_RATE      = Decimal("0.10")
GST_RATE           = Decimal("0.18")
MAX_QTY            = 10
MAX_ORDER_QTY      = 10
LOG_FILE           = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orders_log.txt")
MENU_FILES = {
    "base":    "Types_of_Base.txt",
    "pizza":   "Types_of_Pizza.txt",
    "topping": "Types_of_Toppings.txt",
}

# ── Menu loading ──────────────────────────────────────────────────────────────
def load_menu_file(filepath: str) -> list[dict]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Menu file not found: {filepath}")
    items = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(";")]
            if len(parts) < 3:
                print(f"WARNING: {filepath} line {line_num} malformed — skipped.", file=sys.stderr)
                continue
            item_id, name, price_str = parts[0], parts[1], parts[2]
            if not name:
                continue
            try:
                price = Decimal(price_str)
            except Exception:
                print(f"WARNING: {filepath} line {line_num} bad price — skipped.", file=sys.stderr)
                continue
            items.append({"id": item_id, "name": name, "price": price})
    return items


def load_all_menus() -> dict:
    menus = {}
    errors = []
    for category, filepath in MENU_FILES.items():
        try:
            items = load_menu_file(filepath)
            if not items:
                errors.append(f"Menu file '{filepath}' has no valid items.")
            menus[category] = items
        except FileNotFoundError as e:
            errors.append(str(e))
    if errors:
        raise RuntimeError("\n".join(errors))
    return menus


try:
    MENUS = load_all_menus()
    MENU_LOAD_ERROR = None
except RuntimeError as e:
    MENUS = {}
    MENU_LOAD_ERROR = str(e)


# ── Validation ────────────────────────────────────────────────────────────────
def validate_name(name: str) -> str | None:
    if not name or not name.strip():
        return "Name cannot be blank or spaces only. Please enter your name."
    name = name.strip()
    if len(name) < 2:
        return "Name must be at least 2 characters."
    if len(name) > 40:
        return "Name must be 40 characters or fewer."
    if not re.fullmatch(r"[A-Za-z ]+", name):
        return "Name must contain letters and spaces only — no digits or symbols."
    return None


def validate_phone(phone: str) -> str | None:
    if not phone or not phone.strip():
        return "Phone number is required."
    phone = phone.strip()
    if not phone.isdigit():
        return "Phone number must contain digits only."
    if len(phone) != 10:
        return f"Phone number must be exactly 10 digits (you entered {len(phone)})."
    if phone[0] not in "6789":
        return "Invalid number. Indian mobile numbers must start with 6, 7, 8, or 9."
    return None


def validate_quantity(qty_str) -> tuple[int | None, str | None]:
    if qty_str is None or not str(qty_str).strip():
        return None, "Quantity is required."
    qty_str = str(qty_str).strip()
    if "." in qty_str:
        return None, "Please enter a whole number between 1 and 10 — decimals are not allowed."
    try:
        qty = int(qty_str)
    except ValueError:
        return None, f"Please enter a whole number between 1 and {MAX_QTY} — '{qty_str}' is not valid."
    if qty <= 0:
        return None, "Minimum order is 1 pizza."
    if qty > MAX_QTY:
        return None, f"Maximum per combo is {MAX_QTY} pizzas."
    return qty, None


def validate_menu_selection(choice_str: str, menu_items: list) -> tuple[dict | None, str | None]:
    if not choice_str or not choice_str.strip():
        return None, "Selection is required. Please enter a number from the list."
    choice_str = choice_str.strip()
    if "." in choice_str:
        return None, f"Please enter a whole number between 1 and {len(menu_items)}."
    try:
        idx = int(choice_str)
    except ValueError:
        return None, f"Please enter a number between 1 and {len(menu_items)} — '{choice_str}' is not valid."
    if idx < 1 or idx > len(menu_items):
        return None, f"Please enter a number between 1 and {len(menu_items)}."
    return menu_items[idx - 1], None


# ── Pricing engine ────────────────────────────────────────────────────────────
def compute_bill_for_cart(cart: list[dict]) -> dict:
    total_qty = sum(line["qty"] for line in cart)
    line_subtotals = []
    order_subtotal = Decimal("0")
    for line in cart:
        unit = line["base"]["price"] + line["pizza"]["price"] + line["topping"]["price"]
        sub  = unit * line["qty"]
        line_subtotals.append(sub)
        order_subtotal += sub
    if total_qty >= DISCOUNT_THRESHOLD:
        discount = (order_subtotal * DISCOUNT_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        discount = Decimal("0.00")
    post_discount = order_subtotal - discount
    gst           = (post_discount * GST_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    final_total   = post_discount + gst
    return {
        "line_subtotals": line_subtotals,
        "total_qty":      total_qty,
        "subtotal":       order_subtotal,
        "discount":       discount,
        "post_discount":  post_discount,
        "gst":            gst,
        "final_total":    final_total,
    }


# ── HTML helpers ──────────────────────────────────────────────────────────────
def menu_display_html(category: str) -> str:
    items = MENUS.get(category, [])
    category_labels = {
        "base":    ("AVAILABLE CRUST BASES", "🍕"),
        "pizza":   ("AVAILABLE PIZZAS",      "🍕"),
        "topping": ("AVAILABLE TOPPINGS",    "🧄"),
    }
    label, icon = category_labels.get(category, ("MENU", "🍕"))
    cards = ""
    for i, item in enumerate(items):
        cards += (
            f'<div style="display:flex; align-items:center; justify-content:space-between;'
            f'background:#ffffff; border:1px solid #000000; border-left:3px solid #14532D;'
            f'border-radius:8px; padding:12px 16px; margin-bottom:8px;">'
            f'<div style="display:flex; align-items:center; gap:12px;">'
            f'<div style="background:#14532D; color:#ffffff; font-weight:800; font-size:13px;'
            f'width:28px; height:28px; border-radius:50%; display:flex; align-items:center;'
            f'justify-content:center; flex-shrink:0;">{i+1}</div>'
            f'<span style="font-size:14px; font-weight:600; color:#000000;">{item["name"]}</span>'
            f'</div>'
            f'<div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:20px;'
            f'padding:4px 12px; font-size:13px; font-weight:700; color:#14532D; white-space:nowrap;">'
            f'₹{item["price"]:.2f}</div>'
            f'</div>'
        )
    return (
        f'<div style="margin:10px 0;">'
        f'<div style="font-size:11px; font-weight:800; color:#000000; letter-spacing:1.5px;'
        f'margin-bottom:10px;">{icon} {label}</div>'
        f'{cards}'
        f'<div style="font-size:12px; color:#000000; margin-top:6px; font-style:italic;">'
        f'Enter the number (1–{len(items)}) in the box below</div>'
        f'</div>'
    )


def render_cart_html(cart: list[dict]) -> str:
    if not cart:
        return (
            '<div style="border:1px dashed #BBF7D0; border-radius:8px; padding:24px; text-align:center; background:#F0FDF4;">'
            '<div style="font-size:32px; margin-bottom:8px;">🛒</div>'
            '<div style="font-size:13px; color:#000000; font-weight:600;">Your cart is empty.</div>'
            '<div style="font-size:12px; color:#333333; margin-top:4px;">Items you add will appear here.</div>'
            '</div>'
        )
    bill = compute_bill_for_cart(cart)
    rows = ""
    for idx, (line, sub) in enumerate(zip(cart, bill["line_subtotals"])):
        topping_name = line["topping"]["name"] if line["topping"] else "No Topping"
        rows += (
            f'<div style="display:flex; justify-content:space-between; align-items:flex-start;'
            f'border-bottom:1px solid #000000; padding:10px 0; gap:8px;">'
            f'<div style="flex:1; font-size:13px; color:#000000;">'
            f'<div style="font-size:11px; color:#444444; font-weight:700;">Item {idx+1}</div>'
            f'<strong>{line["pizza"]["name"]}</strong><br>'
            f'<span style="color:#000000; font-size:12px;">Base: {line["base"]["name"]} · Topping: {topping_name}</span><br>'
            f'<span style="color:#000000; font-size:12px;">Qty: {line["qty"]}</span>'
            f'</div>'
            f'<div style="font-size:14px; font-weight:700; color:#14532D; white-space:nowrap;">₹{sub:.2f}</div>'
            f'</div>'
        )
    item_word = "item" if bill["total_qty"] == 1 else "items"
    if bill["total_qty"] >= DISCOUNT_THRESHOLD:
        discount_note = '<div style="color:#B45309; font-size:12px; font-weight:700; margin-top:6px;">🎉 10% discount unlocked at checkout!</div>'
    else:
        remaining = DISCOUNT_THRESHOLD - bill["total_qty"]
        word = "pizza" if remaining == 1 else "pizzas"
        discount_note = f'<div style="color:#000000; font-size:12px; margin-top:6px;">Add {remaining} more {word} to unlock a 10% discount!</div>'
    return (
        f'<div style="border:1px solid #BBF7D0; border-radius:8px; padding:16px; background:#F0FDF4;">'
        f'<div style="font-size:14px; font-weight:800; color:#14532D; margin-bottom:10px;">🛒 Your Cart ({bill["total_qty"]} {item_word})</div>'
        f'{rows}'
        f'<div style="display:flex; justify-content:space-between; padding:10px 0; font-size:14px; font-weight:700; color:#000000; border-top:2px solid #14532D; margin-top:8px;">'
        f'<span>Running Subtotal</span><span>₹{bill["subtotal"]:.2f}</span></div>'
        f'{discount_note}'
        f'<div style="font-size:11px; color:#444444; margin-top:6px;">Discount & GST calculated at checkout.</div>'
        f'</div>'
    )


def render_bill_html(state: dict) -> str:
    cart = state["cart"]
    if not cart:
        return ""
    bill  = compute_bill_for_cart(cart)
    name  = state["name"]
    phone = state["phone"]
    mode  = state.get("payment", "")

    rows = ""
    for line, sub in zip(cart, bill["line_subtotals"]):
        topping_name = line["topping"]["name"] if line["topping"] else "No Topping"
        rows += (
            f'<div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #000000;">'
            f'<div style="font-size:13px; color:#000000; flex:1;">'
            f'<strong style="color:#000000;">{line["pizza"]["name"]}</strong> × {line["qty"]}<br>'
            f'<span style="color:#000000; font-size:12px;">Base: {line["base"]["name"]} · Topping: {topping_name}</span>'
            f'</div>'
            f'<div style="font-size:13px; font-weight:700; color:#000000; white-space:nowrap;">₹{sub:.2f}</div>'
            f'</div>'
        )

    discount_row = ""
    if bill["discount"] > 0:
        discount_row = (
            f'<div style="display:flex; justify-content:space-between; padding:8px 12px; background:#DCFCE7; border-radius:4px; margin:6px 0;">'
            f'<span style="font-size:13px; color:#B45309; font-weight:700;">Discount (10% — qty ≥ {DISCOUNT_THRESHOLD})</span>'
            f'<span style="font-size:13px; color:#B45309; font-weight:800;">− ₹{bill["discount"]:.2f}</span>'
            f'</div>'
        )

    payment_section = ""
    if mode:
        mode_messages = {
            "Cash": "💵 Please hand exact cash to the counter staff.",
            "Card": "💳 Card machine will be presented — please tap or insert.",
            "UPI":  "📱 Scan the QR code at the counter to complete payment.",
        }
        payment_section = (
            '<div style="margin:0 20px 16px; padding:14px 16px; background:#DCFCE7;'
            'border-left:4px solid #16A34A; border-radius:8px;">'
            f'<div style="font-size:14px; font-weight:800; color:#14532D; margin-bottom:5px;">💳 Payment: {mode}</div>'
            f'<div style="font-size:13px; font-weight:600; color:#000000;">{mode_messages.get(mode, "")}</div>'
            '</div>'
        )

    item_word = "item" if bill["total_qty"] == 1 else "items"
    return (
        '<div style="font-family:Helvetica Neue,Arial,sans-serif;'
        'border:2px solid #14532D; border-radius:10px; overflow:hidden; background:#ffffff;">'

        '<div style="background:#14532D; padding:16px 20px;">'
        '<div style="font-size:18px; font-weight:800; letter-spacing:1.5px; color:#ffffff;">🍕 SLICEMATIC</div>'
        '<div style="font-size:11px; color:#86EFAC; margin-top:3px;">New Ashok Nagar, East Delhi · Order Receipt</div>'
        '</div>'

        '<div style="background:#F0FDF4; padding:12px 20px; border-bottom:1px solid #BBF7D0;">'
        f'<div style="font-size:14px; font-weight:800; color:#000000;">{name.strip()}'
        f'<span style="font-size:12px; font-weight:500; color:#000000; margin-left:6px;">· {phone.strip()}</span></div>'
        f'<div style="font-size:11px; color:#000000; font-weight:600; margin-top:4px;">{datetime.now().strftime("%d %b %Y, %I:%M %p")}</div>'
        '</div>'

        '<div style="padding:14px 20px; background:#ffffff; border-bottom:2px solid #000000;">'
        '<div style="font-size:10px; font-weight:800; color:#000000; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:8px;">Order Details</div>'
        f'{rows}'
        '</div>'

        '<div style="padding:12px 20px; background:#ffffff;">'
        f'<div style="display:flex; justify-content:space-between; padding:6px 0;">'
        f'<span style="font-size:13px; color:#000000; font-weight:600;">Subtotal ({bill["total_qty"]} {item_word})</span>'
        f'<span style="font-size:13px; font-weight:800; color:#000000;">₹{bill["subtotal"]:.2f}</span></div>'
        f'{discount_row}'
        f'<div style="display:flex; justify-content:space-between; padding:6px 0; border-top:1px solid #000000;">'
        f'<span style="font-size:13px; color:#000000; font-weight:600;">After discount</span>'
        f'<span style="font-size:13px; font-weight:800; color:#000000;">₹{bill["post_discount"]:.2f}</span></div>'
        f'<div style="display:flex; justify-content:space-between; padding:6px 0;">'
        f'<span style="font-size:13px; color:#000000; font-weight:600;">GST @ 18%</span>'
        f'<span style="font-size:13px; font-weight:800; color:#000000;">₹{bill["gst"]:.2f}</span></div>'
        f'<div style="display:flex; justify-content:space-between; padding:12px 0 6px; border-top:2px solid #14532D; margin-top:6px;">'
        f'<span style="font-size:16px; font-weight:800; color:#14532D;">TOTAL PAYABLE</span>'
        f'<span style="font-size:16px; font-weight:800; color:#14532D;">₹{bill["final_total"]:.2f}</span></div>'
        '</div>'

        + payment_section +

        '<div style="padding:10px 20px; background:#F0FDF4; border-top:1px solid #BBF7D0; text-align:center;">'
        '<span style="font-size:11px; font-weight:600; color:#000000;">Thank you for ordering from SliceMatic · 30-min delivery guaranteed</span>'
        '</div></div>'
    )


# ── Persistence ───────────────────────────────────────────────────────────────
def _build_record(state: dict, bill: dict, payment_mode: str, timestamp: str) -> str:
    lines = [
        f"TIMESTAMP|{timestamp}",
        f"CUSTOMER|{state['name'].strip()}|{state['phone'].strip()}",
    ]
    for i, (line, sub) in enumerate(zip(state["cart"], bill["line_subtotals"])):
        topping_name  = line["topping"]["name"] if line["topping"] else "No Topping"
        topping_price = line["topping"]["price"] if line["topping"] else Decimal("0")
        lines += [
            f"LINE|{i+1}",
            f"BASE|{line['base']['id']}|{line['base']['name']}|{line['base']['price']:.2f}",
            f"PIZZA|{line['pizza']['id']}|{line['pizza']['name']}|{line['pizza']['price']:.2f}",
            f"TOPPING|{line['topping']['id'] if line['topping'] else '0'}|{topping_name}|{topping_price:.2f}",
            f"QUANTITY|{line['qty']}",
            f"LINE_SUBTOTAL|{sub:.2f}",
        ]
    lines += [
        f"ORDER_SUBTOTAL|{bill['subtotal']:.2f}",
        f"DISCOUNT|{bill['discount']:.2f}",
        f"GST|{bill['gst']:.2f}",
        f"TOTAL|{bill['final_total']:.2f}",
        f"PAYMENT|{payment_mode}",
    ]
    return "\n".join(lines)


def _save_to_hf_dataset(record: str) -> bool:
    hf_token = os.environ.get("HF_TOKEN")
    hf_repo  = os.environ.get("HF_DATASET_REPO")
    if not hf_token or not hf_repo:
        return False
    try:
        from huggingface_hub import HfApi
        import tempfile
        api = HfApi(token=hf_token)
        existing = ""
        try:
            local_path = api.hf_hub_download(
                repo_id=hf_repo, filename="orders_log.txt",
                repo_type="dataset", token=hf_token
            )
            with open(local_path, "r", encoding="utf-8") as f:
                existing = f.read()
        except Exception:
            pass
        updated = existing + record + "\n\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
            tmp.write(updated)
            tmp_path = tmp.name
        api.upload_file(
            path_or_fileobj=tmp_path, path_in_repo="orders_log.txt",
            repo_id=hf_repo, repo_type="dataset", token=hf_token,
            commit_message=f"Order logged at {datetime.now().isoformat(timespec='seconds')}",
        )
        os.unlink(tmp_path)
        return True
    except Exception as e:
        print(f"HF DATASET UPLOAD ERROR: {e}", file=sys.stderr)
        return False


def persist_order(state: dict, bill: dict, payment_mode: str, timestamp: str) -> None:
    record = _build_record(state, bill, payment_mode, timestamp)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(record + "\n\n")
    except OSError as e:
        print(f"LOCAL LOG ERROR: {e}", file=sys.stderr)
    _save_to_hf_dataset(record)


# ── State ─────────────────────────────────────────────────────────────────────
def initial_state() -> dict:
    return {
        "step":      "name",
        "name":      "",
        "phone":     "",
        "base":      None,
        "pizza":     None,
        "topping":   None,
        "qty":       None,
        "cart":      [],
        "payment":   "",
        "timestamp": "",
    }


def step_instruction(state: dict) -> tuple[str, str]:
    """Returns (instruction_html, placeholder) for the current step."""
    step = state["step"]
    cart_size = len(state["cart"])
    combo_tag = ""
    if step in ("base", "pizza", "topping", "qty"):
        combo_tag = (
            f'<div style="font-size:11px; font-weight:700; color:#B45309; letter-spacing:1px; margin-bottom:4px;">'
            f'BUILDING ITEM #{cart_size + 1}</div>'
        )

    def wrap(icon, title, body):
        return (
            f'<div style="color:#000000;">'
            f'{combo_tag}'
            f'<div style="font-size:17px; font-weight:700; color:#000000; margin-bottom:8px;">{icon} {title}</div>'
            f'<div style="font-size:13px; color:#000000;">{body}</div>'
            f'</div>'
        )

    if step == "name":
        return wrap("👤", "Enter your name", "Letters and spaces only, 2–40 characters."), "e.g. Rahul Sharma"
    if step == "phone":
        return wrap("📱", "Enter your mobile number", "Exactly 10 digits · Must start with 6, 7, 8, or 9."), "e.g. 9876543210"
    if step == "base":
        body = f'Choose your base crust:{menu_display_html("base")}Enter the number from the list above.'
        return wrap("🫓", "Choose a base", body), "e.g. 1"
    if step == "pizza":
        body = f'Choose your pizza:{menu_display_html("pizza")}Enter the number from the list above.'
        return wrap("🍕", "Choose a pizza", body), "e.g. 1"
    if step == "topping":
        skip_hint = (
            '<div style="background:#FFFBEB;border:1px solid #FCD34D;'
            'border-radius:6px;padding:10px 14px;margin-top:10px;">'
            '<p style="margin:0;font-size:13px;font-weight:700;color:#92400E;">'
            '💡 No topping? Use the button below.'
            '</p></div>'
        )
        body = f'Choose your topping:{menu_display_html("topping")}{skip_hint}'
        return wrap("🧄", "Choose a topping (optional)", body), "e.g. 1"
    if step == "qty":
        total = sum(l["qty"] for l in state["cart"])
        cap = MAX_ORDER_QTY - total
        body = (
            f'Enter a whole number from 1 to {min(MAX_QTY, cap)}.<br>'
            f'<span style="color:#14532D; font-weight:600;">💡 Total order of {DISCOUNT_THRESHOLD}+ pizzas unlocks 10% off!</span>'
        )
        return wrap("🔢", "How many of this combo?", body), "e.g. 2"
    if step == "cart":
        return wrap(
            "🛒", "Cart Review",
            "Your cart is on the right. Use the buttons below to add another item, remove the last one, or checkout."
        ), ""
    if step == "bill":
        return wrap(
            "🧾", "Review Your Bill",
            "Your itemised bill is on the right. Review it and proceed when ready."
        ), ""
    if step == "payment":
        return wrap(
            "💳", "Select Payment Mode",
            "Click one of the buttons below to place your order. <strong>One click = order placed.</strong>"
        ), ""
    return "", ""


# ── State transition functions ────────────────────────────────────────────────
def submit_text(user_input_value: str, state: dict) -> tuple[dict, str]:
    """Handle textbox submission. Returns (new_state, error_msg)."""
    step = state["step"]
    state = dict(state)
    state["cart"] = list(state["cart"])

    if step == "name":
        err = validate_name(user_input_value)
        if err:
            return state, err
        state["name"]      = user_input_value.strip()
        state["timestamp"] = datetime.now().isoformat(timespec="seconds")
        state["step"]      = "phone"
        return state, ""

    if step == "phone":
        err = validate_phone(user_input_value)
        if err:
            return state, err
        state["phone"] = user_input_value.strip()
        state["step"]  = "base"
        return state, ""

    if step == "base":
        item, err = validate_menu_selection(user_input_value, MENUS["base"])
        if err:
            return state, err
        state["base"] = item
        state["step"] = "pizza"
        return state, ""

    if step == "pizza":
        item, err = validate_menu_selection(user_input_value, MENUS["pizza"])
        if err:
            return state, err
        state["pizza"] = item
        state["step"] = "topping"
        return state, ""

    if step == "topping":
        item, err = validate_menu_selection(user_input_value, MENUS["topping"])
        if err:
            return state, err
        state["topping"] = item
        state["step"] = "qty"
        return state, ""

    if step == "qty":
        qty, err = validate_quantity(user_input_value)
        if err:
            return state, err
        total = sum(l["qty"] for l in state["cart"])
        if total + qty > MAX_ORDER_QTY:
            available = MAX_ORDER_QTY - total
            return state, (
                f"Your cart already has {total} pizza(s). "
                f"You can add at most {available} more (order cap is {MAX_ORDER_QTY})."
            )
        state["cart"].append({
            "base":    state["base"],
            "pizza":   state["pizza"],
            "topping": state["topping"],
            "qty":     qty,
        })
        state["base"] = state["pizza"] = state["topping"] = state["qty"] = None
        state["step"] = "cart"
        return state, ""

    # Submit pressed on a non-text-input step — should not happen, but be safe
    return state, ""


def go_back(state: dict) -> dict:
    step = state["step"]
    state = dict(state)
    state["cart"] = list(state["cart"])

    # Back from "base" with items in cart → return to cart (not phone)
    if step == "base" and state["cart"]:
        state["step"] = "cart"
        return state

    back_map = {
        "phone":   "name",
        "base":    "phone",
        "pizza":   "base",
        "topping": "pizza",
        "qty":     "topping",
        "bill":    "cart",
        "payment": "bill",
    }
    prev = back_map.get(step)
    if prev:
        state["step"] = prev
        # Clear field we're stepping back from
        clear_map = {"pizza": "pizza", "topping": "topping", "qty": "qty"}
        if step in clear_map:
            state[clear_map[step]] = None
    return state


def skip_topping_action(state: dict) -> dict:
    state = dict(state)
    state["cart"] = list(state["cart"])
    state["topping"] = {"id": "0", "name": "No Topping", "price": Decimal("0")}
    state["step"] = "qty"
    return state


def add_another_action(state: dict) -> dict:
    state = dict(state)
    state["cart"] = list(state["cart"])
    state["base"] = state["pizza"] = state["topping"] = state["qty"] = None
    state["step"] = "base"
    return state


def remove_last_action(state: dict) -> tuple[dict, str]:
    state = dict(state)
    state["cart"] = list(state["cart"])
    if state["cart"]:
        state["cart"].pop()
    if not state["cart"]:
        return state, "Cart is now empty — add at least one item to continue."
    return state, ""


def checkout_action(state: dict) -> tuple[dict, str]:
    state = dict(state)
    state["cart"] = list(state["cart"])
    if not state["cart"]:
        return state, "Add at least one item to your cart before checking out."
    state["step"] = "bill"
    return state, ""


def to_payment_action(state: dict) -> dict:
    state = dict(state)
    state["cart"] = list(state["cart"])
    state["step"] = "payment"
    return state


def place_order_action(payment_choice: str, state: dict) -> tuple[dict, str]:
    state = dict(state)
    state["cart"] = list(state["cart"])
    if payment_choice not in ("Cash", "Card", "UPI"):
        return state, "Invalid payment choice."
    if not state["cart"]:
        return state, "Cannot place an order with an empty cart."
    state["payment"] = payment_choice
    bill = compute_bill_for_cart(state["cart"])
    persist_order(state, bill, payment_choice, state["timestamp"])
    state["step"] = "done"
    return state, ""


# ── ONE render function — toggles GROUPS, not individual buttons ──────────────
# OUTPUTS order (MUST match render's return list):
#   0  instruction_md
#   1  error_md
#   2  grp_input        (visible during name/phone/base/pizza/topping/qty)
#   3  user_input       (value="", placeholder=...)
#   4  grp_skip         (visible only during topping step)
#   5  grp_cart         (visible during cart step)
#   6  grp_bill         (visible during bill step)
#   7  grp_payment      (visible during payment step)
#   8  right_col_html   (cart preview, or bill)
#   9  state
def render(state: dict, error_msg: str = "") -> list:
    step = state["step"]
    is_text_step = step in ("name", "phone", "base", "pizza", "topping", "qty")
    is_topping   = step == "topping"
    is_cart      = step == "cart"
    is_bill      = step == "bill"
    is_payment   = step == "payment"
    is_done      = step == "done"

    # Instruction HTML (or "Order Placed" card for done step)
    if is_done:
        instr_html = (
            '<div style="background:#F0FDF4; border:2px solid #16A34A; border-radius:10px; padding:20px;">'
            '<div style="font-size:24px; font-weight:800; color:#14532D; margin-bottom:12px;">✅ Order Placed!</div>'
            f'<div style="font-size:16px; font-weight:700; color:#000000; margin-bottom:8px;">Thank you, {state["name"].strip()}!</div>'
            '<div style="font-size:14px; color:#000000; line-height:1.6;">'
            'Your pizza is being prepared 🍕<br>'
            '<strong style="color:#14532D;">Estimated delivery: 30 minutes</strong><br>'
            '<span style="font-size:12px;">Click <strong>Start New Order</strong> below to place another order.</span>'
            '</div></div>'
        )
        placeholder = ""
    else:
        instr_raw, placeholder = step_instruction(state)
        instr_html = (
            f'<div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:14px 18px;">{instr_raw}</div>'
            if instr_raw else ""
        )

    # Error banner
    if error_msg:
        err_html = (
            f'<div style="background:#FEF2F2;border:1px solid #FECACA;border-left:4px solid #DC2626;'
            f'border-radius:6px;padding:10px 14px;color:#991B1B;font-size:13px;font-weight:500;">⚠️ {error_msg}</div>'
        )
        err_visible = True
    else:
        err_html = ""
        err_visible = False

    # Right column: cart preview during ordering, bill from checkout onwards
    if step in ("bill", "payment", "done"):
        right_html = render_bill_html(state)
    else:
        right_html = render_cart_html(state["cart"])

    return [
        instr_html,                                                       # 0
        gr.update(value=err_html, visible=err_visible),                   # 1
        gr.update(visible=is_text_step),                                  # 2 grp_input
        gr.update(value="", placeholder=placeholder),                     # 3 user_input
        gr.update(visible=is_topping),                                    # 4 grp_skip
        gr.update(visible=is_cart),                                       # 5 grp_cart
        gr.update(visible=is_bill),                                       # 6 grp_bill
        gr.update(visible=is_payment),                                    # 7 grp_payment
        right_html,                                                       # 8 right_col_html
        state,                                                            # 9 state
    ]


# ── Gradio UI ─────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
    .header-box { background: #14532D; color: white; padding: 20px 24px;
                  border-radius: 10px; margin-bottom: 16px; }
    .header-box h1 { margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 1px; }
    .header-box p  { margin: 4px 0 0; opacity: .75; font-size: 13px; }
"""

THEME = gr.themes.Base(
    primary_hue="green",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Inter"), "sans-serif"],
)

with gr.Blocks(title="SliceMatic Ordering System") as demo:

    gr.HTML("""
    <div class="header-box">
      <h1>🍕 SliceMatic Ordering System</h1>
      <p>New Ashok Nagar, East Delhi · Digital-first pizza ordering · 30-min delivery guarantee</p>
    </div>
    """)

    if MENU_LOAD_ERROR:
        gr.Markdown(f"## ❌ Startup Error\n\n```\n{MENU_LOAD_ERROR}\n```\n\nPlease ensure all menu files are present and restart.")
    else:
        # Compute initial values up front so the UI is functional even if
        # demo.load() never fires.
        _init_state = initial_state()
        _init_instr_raw, _init_placeholder = step_instruction(_init_state)
        _init_instr_html = (
            f'<div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:14px 18px;">{_init_instr_raw}</div>'
        )
        _init_right_html = render_cart_html(_init_state["cart"])

        state = gr.State(_init_state)

        with gr.Row():
            # ── LEFT COLUMN: step controls ────────────────────────────────────
            with gr.Column(scale=3):
                instruction_md = gr.HTML(value=_init_instr_html)
                error_md       = gr.HTML(value="", visible=False)

                # GROUP: text input steps (name/phone/base/pizza/topping/qty)
                with gr.Group(visible=True) as grp_input:
                    user_input = gr.Textbox(
                        label="Your answer",
                        placeholder=_init_placeholder,
                        autofocus=True,
                    )
                    with gr.Row():
                        submit_btn  = gr.Button("Next →", variant="primary")
                        back_input_btn = gr.Button("← Go Back", variant="secondary", size="sm")

                # GROUP: skip topping (only topping step)
                with gr.Group(visible=False) as grp_skip:
                    skip_btn = gr.Button("Skip Topping (No Topping for this Combo)", variant="secondary")

                # GROUP: cart step
                with gr.Group(visible=False) as grp_cart:
                    with gr.Row():
                        add_another_btn = gr.Button("➕ Add Another Item", variant="secondary")
                        remove_last_btn = gr.Button("🗑 Remove Last Item",  variant="secondary")
                        checkout_btn    = gr.Button("Checkout →",           variant="primary")

                # GROUP: bill step
                with gr.Group(visible=False) as grp_bill:
                    with gr.Row():
                        back_bill_btn  = gr.Button("← Back to Cart",        variant="secondary")
                        to_payment_btn = gr.Button("Continue to Payment →", variant="primary")

                # GROUP: payment step — three direct pay buttons + back
                with gr.Group(visible=False) as grp_payment:
                    with gr.Row():
                        pay_cash_btn = gr.Button("💵 Pay with Cash", variant="primary")
                        pay_card_btn = gr.Button("💳 Pay with Card", variant="primary")
                        pay_upi_btn  = gr.Button("📱 Pay with UPI",  variant="primary")
                    back_payment_btn = gr.Button("← Back to Bill", variant="secondary", size="sm")

                # Always visible: reset
                reset_btn = gr.Button("🔄 Start New Order", size="sm")

            # ── RIGHT COLUMN: cart preview / bill ─────────────────────────────
            with gr.Column(scale=2):
                gr.Markdown("### 🧾 Cart / Bill")
                right_col_html = gr.HTML(value=_init_right_html)

        # ── Outputs in render() order ─────────────────────────────────────────
        OUTPUTS = [
            instruction_md,    # 0
            error_md,          # 1
            grp_input,         # 2
            user_input,        # 3
            grp_skip,          # 4
            grp_cart,          # 5
            grp_bill,          # 6
            grp_payment,       # 7
            right_col_html,    # 8
            state,             # 9
        ]

        # ── Safe wrapper: catches exceptions and shows them as a banner ──────
        def _safe(fn):
            def wrapped(*args):
                try:
                    return fn(*args)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    st = args[-1] if args and isinstance(args[-1], dict) else initial_state()
                    return render(st, f"Internal error — please try again. ({type(e).__name__}: {e})")
            return wrapped

        # ── Event handlers ────────────────────────────────────────────────────

        @_safe
        def on_submit_text(text, st):
            new_state, err = submit_text(text or "", st)
            return render(new_state, err)
        submit_btn.click(fn=on_submit_text, inputs=[user_input, state], outputs=OUTPUTS)
        user_input.submit(fn=on_submit_text, inputs=[user_input, state], outputs=OUTPUTS)

        @_safe
        def on_back(st):
            return render(go_back(st))
        back_input_btn.click(fn=on_back, inputs=[state], outputs=OUTPUTS)
        back_bill_btn.click(fn=on_back, inputs=[state], outputs=OUTPUTS)
        back_payment_btn.click(fn=on_back, inputs=[state], outputs=OUTPUTS)

        @_safe
        def on_skip(st):
            return render(skip_topping_action(st))
        skip_btn.click(fn=on_skip, inputs=[state], outputs=OUTPUTS)

        @_safe
        def on_add_another(st):
            return render(add_another_action(st))
        add_another_btn.click(fn=on_add_another, inputs=[state], outputs=OUTPUTS)

        @_safe
        def on_remove_last(st):
            new_state, err = remove_last_action(st)
            return render(new_state, err)
        remove_last_btn.click(fn=on_remove_last, inputs=[state], outputs=OUTPUTS)

        @_safe
        def on_checkout(st):
            new_state, err = checkout_action(st)
            return render(new_state, err)
        checkout_btn.click(fn=on_checkout, inputs=[state], outputs=OUTPUTS)

        @_safe
        def on_to_payment(st):
            return render(to_payment_action(st))
        to_payment_btn.click(fn=on_to_payment, inputs=[state], outputs=OUTPUTS)

        @_safe
        def on_pay_cash(st):
            new_state, err = place_order_action("Cash", st)
            return render(new_state, err)
        pay_cash_btn.click(fn=on_pay_cash, inputs=[state], outputs=OUTPUTS)

        @_safe
        def on_pay_card(st):
            new_state, err = place_order_action("Card", st)
            return render(new_state, err)
        pay_card_btn.click(fn=on_pay_card, inputs=[state], outputs=OUTPUTS)

        @_safe
        def on_pay_upi(st):
            new_state, err = place_order_action("UPI", st)
            return render(new_state, err)
        pay_upi_btn.click(fn=on_pay_upi, inputs=[state], outputs=OUTPUTS)

        @_safe
        def on_reset(*_args):
            return render(initial_state())
        reset_btn.click(fn=on_reset, inputs=[state], outputs=OUTPUTS)

        # Belt-and-suspenders: re-render on page load
        demo.load(fn=on_reset, inputs=[state], outputs=OUTPUTS)

    gr.Markdown(
        "---\n"
        "*FDE Academy · Group 7 · PizzaFlow Applied Project · Stage 2 MVP (Cart Edition v4)*  \n"
        f"*Discount threshold: total qty ≥ {DISCOUNT_THRESHOLD} → {int(DISCOUNT_RATE*100)}% off · "
        f"GST: {int(GST_RATE*100)}% on post-discount total*"
    )


if __name__ == "__main__":
    demo.queue()   # process handlers via queue so slow ops (HF upload) don't block
    demo.launch(share=False, theme=THEME, css=CUSTOM_CSS)

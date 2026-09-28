# Mock orders database. Keys are customer WhatsApp numbers.
ORDERS = {
    "whatsapp:+2347076096366": [
        {
            "order_id": "ORD-1001",
            "item": "Chocolate cake (large)",
            "quantity": 1,
            "status": "pending",
            "payment_status": "unpaid",
            "delivery": "Saturday, 2pm",
        },
        {
            "order_id": "ORD-1002",
            "item": "Meat pie",
            "quantity": 12,
            "status": "confirmed",
            "payment_status": "paid",
            "delivery": "Sunday, 10am",
        },
    ]
}


def get_orders(customer_id):
    return ORDERS.get(customer_id, [])


def cancel_order(customer_id, order_id):
    for order in ORDERS.get(customer_id, []):
        if order["order_id"] == order_id:
            if order["status"] == "cancelled":
                return {"ok": False, "reason": "Order is already cancelled."}
            if order["payment_status"] == "paid":
                return {
                    "ok": False,
                    "reason": "Order is already paid. Cancelling needs the owner because it may involve a refund.",
                }
            order["status"] = "cancelled"
            return {"ok": True, "order_id": order_id, "status": "cancelled"}
    return {"ok": False, "reason": "Order not found for this customer."}
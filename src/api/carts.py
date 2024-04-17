from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

# EVENTUALLY MAKE NEW TABLE TO TRACK CARTS
cart_id = 0
cart_dict = {}

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   


# LOL WHAT
@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """

    # STEP 2) do i need to change this already returning success
    print(customers)
    # customer_list = []
    # for customer in customers:
    #     customer_list.append({"customer_name": customer.customer_name, "character_class":customer.character_class, "level":customer.level})

    
    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    # STEP 3) TESTED! INCREMENTS ACCORDINGLY add checks
    global cart_id
    cart_id += 1
    cart_dict[cart_id] = {}
    return {"cart_id": cart_id} # cast to str?


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    # STEP 4) add checks in db if item exists and cart id 
    # finds cart values and updates item with cart's quantity
    curr_cart = cart_dict[cart_id]
    curr_cart[item_sku] = cart_item.quantity
    print(f"DICTIONARY: {cart_dict}")
    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    # add payment logic can we assume they will always have enough?

    curr_cart = cart_dict[cart_id]
    gold_paid = 0
    potions_bought = 0
    with db.engine.begin() as connection:
        # for each item in cart evaluate how much is in global
        for sku,quantity in curr_cart.items():
            result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
            global_green_pots = result.num_green_potions
            global_red_pots = result.num_red_potions
            global_blue_pots = result.num_blue_potions
            gold_global = result.gold
            print(f"BEFORE PURCHASE: {global_green_pots} potions and {gold_global} coins and they want {quantity} potions")

            # if there is enough in global continue payment
            if "green" in sku.lower():
                print("wants green")
                if global_green_pots >= quantity:
                    global_green_pots -= quantity
                    potions_bought += quantity
                    gold_paid += quantity * 50
                else:
                    potions_bought += global_green_pots
                    gold_paid +=  global_green_pots * 50
                    global_green_pots = 0
            if "red" in sku.lower():    
                print("wants red")
                if global_red_pots >= quantity:
                    global_red_pots -= quantity
                    potions_bought += quantity
                    gold_paid += quantity * 50
                else:
                    potions_bought += global_red_pots
                    gold_paid +=  global_red_pots * 50
                    global_red_pots = 0
            if "blue" in sku.lower():
                print("wants blue")
                if global_blue_pots >= quantity:
                    global_blue_pots -= quantity
                    potions_bought += quantity
                    gold_paid += quantity * 50
                else: # give them whatever is left
                    potions_bought += global_blue_pots
                    gold_paid +=  global_blue_pots * 50
                    global_blue_pots = 0
            gold_global += gold_paid
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_potions = :gp, num_red_potions = :rp, num_blue_potions = :bp"), [{"gp": global_green_pots,"rp": global_red_pots,"bp": global_blue_pots}])
        # updates green pots and gold with transaction
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = :gold_global"), [{"gold_global": gold_global }])
        print(f"AFTER PURCHASE: {global_green_pots} potions and {gold_global} coins")
    return {"total_potions_bought": potions_bought, "total_gold_paid": gold_paid}

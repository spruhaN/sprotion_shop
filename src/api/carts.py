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
    Endpoint to log which customers visited the shop on a specific visit.
    """
    query = """
        INSERT INTO customer_visits (visit_id, name, class, level)
        VALUES (:visit_id, :name, :class, :level)
    """

    with db.engine.begin() as connection:
        for customer in customers:
            connection.execute(sqlalchemy.text(query), {
                'visit_id': visit_id,
                'name': customer.customer_name,
                'class': customer.character_class,
                'level': customer.level
            })
    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    print("creating cart")
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("insert into carts default values returning id")).first()
        return result.id
    return -50


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """

    # STEP 4)
    print(f"adding to cart {cart_id} ({item_sku}: {cart_item.quantity})")
    with db.engine.begin() as connection:
        print(item_sku)
        result = connection.execute(sqlalchemy.text("INSERT INTO public.cart_items (cart_id, potion_id, quantity) SELECT :cart_id, id, :quantity FROM public.potions WHERE sku = :sku"), {'cart_id': cart_id, 'sku': item_sku, 'quantity': cart_item.quantity})

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    print(f"checking out cart {cart_id}")

    with db.engine.begin() as connection:
        # get all values with cart id
        cart_items = connection.execute(sqlalchemy.text("SELECT potion_id, quantity FROM cart_items WHERE cart_id = :cart_id"), {'cart_id': cart_id}).mappings().all()

        total_cost = 0
        total_potions_sold = 0

        for item in cart_items:
            # use potion id and get price and current inventory
            potion_details = connection.execute(sqlalchemy.text("SELECT price,inventory FROM potions WHERE id = :pot_id"),{'pot_id': item['potion_id']}).first()

            # give whats possible
            if potion_details.inventory >= item.quantity:
                sell_quantity = item.quantity
            else:
                sell_quantity = potion_details.inventory

            total_potions_sold += sell_quantity
            total_cost += (sell_quantity * potion_details.price)

            # calculate and update values
            res = connection.execute(sqlalchemy.text("UPDATE potions SET inventory = inventory - :sold_no WHERE id = :pot_id"),{'sold_no': sell_quantity, 'pot_id':item['potion_id']})

        res = connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = gold + :added"),{'added': total_cost})
    print(f"prev state num pots: {total_potions_sold} cost: {total_cost}")

    return {"total_potions_bought": total_potions_sold, "total_gold_paid": total_cost}


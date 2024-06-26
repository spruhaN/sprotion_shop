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
    # SQL Query Base
    sql_query_base = """
        SELECT 
            cart_items.cart_id,
            cart_items.quantity,
            potions.sku,
            cart_items.potion_id,
            carts.customer_id,
            customers.name,
            customers.class,
            customers.level,
            cart_items.time,
            potions.price
        FROM cart_items
        JOIN carts ON cart_items.cart_id = carts.id
        JOIN customers ON carts.customer_id = customers.id
        JOIN potions ON cart_items.potion_id = potions.id
        """
    query_params = {}

    # Filtering logic
    if customer_name != "":
        sql_query_base += " WHERE customers.name ILIKE :cust_name"
        query_params["cust_name"] = f"%{customer_name}%"
    if potion_sku != "":
        if "WHERE" in sql_query_base:
            sql_query_base += " AND potions.sku ILIKE :potion_sku"
        else:
            sql_query_base += " WHERE potions.sku ILIKE :potion_sku"
        query_params["potion_sku"] = f"%{potion_sku}%"

    # Pagination logic
    previous_page_token = ""
    if not search_page:
        search_page = "1"
    query_params["current_page"] = int(search_page)
    if query_params["current_page"] > 1:
        previous_page_token = str(query_params["current_page"] - 1)

    # Sorting logic
    if not sort_col or sort_col == search_sort_options.timestamp:
        sort_col = "cart_items.time"
    elif sort_col == search_sort_options.line_item_total:
        sort_col = "cart_items.quantity"
    elif sort_col == search_sort_options.customer_name:
        sort_col = "customers.name"
    elif sort_col == search_sort_options.item_sku:
        sort_col = "potions.sku"

    if not sort_order or sort_order == search_sort_order.desc:
        sort_order = "DESC"
    elif sort_order == search_sort_order.asc:
        sort_order = "ASC"

    sql_query_base += f" ORDER BY {sort_col} {sort_order} LIMIT 5 OFFSET {5 * (query_params['current_page'] - 1)}"

    # Count query for pagination
    count_sql_query = """
        SELECT COUNT(*)
        FROM cart_items
        JOIN carts ON cart_items.cart_id = carts.id
        JOIN customers ON carts.customer_id = customers.id
        JOIN potions ON cart_items.potion_id = potions.id
        """
    if customer_name:
        count_sql_query += " WHERE customers.name LIKE :cust_name"
    if potion_sku:
        count_sql_query += " AND potions.sku = :potion_sku" if "WHERE" in count_sql_query else " WHERE potions.sku = :potion_sku"

    # Execute queries
    with db.engine.begin() as connection:
        total_items = connection.execute(sqlalchemy.text(count_sql_query), query_params).scalar()
        query_results = connection.execute(sqlalchemy.text(sql_query_base), query_params).fetchall()

    # Format results
    formatted_results = []
    for row in query_results:
        print(f"{row.sku}: {row.price}")
        formatted_results.append({
            "line_item_id": row.cart_id,
            "item_sku": row.sku,
            "customer_name": row.name,
            "line_item_total": row.quantity * row.price,
            "timestamp": row.time,
        })

    # Calculate next page
    next_page_token = ""
    if total_items - ((query_params["current_page"] - 1) * 5) > 5:
        next_page_token = str(query_params["current_page"] + 1)

    # Debug print
    print(f"AT PAGE {query_params['current_page']} (prev: {previous_page_token}) (next: {next_page_token}) HAS ELEMENTS {formatted_results}")

    # Output
    return {
        "previous": previous_page_token,
        "next": next_page_token,
        "results": formatted_results,
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
            print(f"visited by {customer.customer_name}")
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
        cust_result = connection.execute(sqlalchemy.text("insert into customers (name,class,level) values (:cust_name,:cust_class,:cust_level) returning id"), {"cust_name":new_cart.customer_name,"cust_class":new_cart.character_class,"cust_level":new_cart.level}).first()
        cust_id = cust_result.id

        result = connection.execute(sqlalchemy.text("insert into carts (customer_id) values (:cust_id) returning id"), {"cust_id": cust_id}).first()
        print(f"id: {result.id} with customer {cust_id}")
        return {"cart_id": result.id}
    return {"cart_id": -1}


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
            sql_qry = """
                SELECT 
                    p.price AS price,
                    COALESCE(SUM(pl.delta), 0) AS inventory 
                FROM 
                    potions AS p
                LEFT JOIN 
                    potion_ledger AS pl ON p.id = pl.potion_id
                WHERE 
                    p.id = :pot_id
                GROUP BY 
                    p.price
                """
            potion_details = connection.execute(sqlalchemy.text(sql_qry),{'pot_id': item['potion_id']}).first()

            # give whats possible
            if potion_details.inventory >= item.quantity:
                sell_quantity = item.quantity
            else:
                sell_quantity = potion_details.inventory

            total_potions_sold += sell_quantity
            total_cost += (sell_quantity * potion_details.price)

            # calculate and update values
            res = connection.execute(sqlalchemy.text("INSERT INTO global_ledger (potion_id, potion_delta, gold_delta) VALUES (:pot_id,:sold_no,:total_cost) RETURNING id AS init_ledger_id;"),{'sold_no': -sell_quantity, 'pot_id':item['potion_id'], 'total_cost': total_cost}).first()
            ledger_id = res.init_ledger_id
            connection.execute(sqlalchemy.text("INSERT INTO potion_ledger (ledger_id, potion_id, delta) VALUES (:ledger_id, :pot_id, :sold_no)"),{'ledger_id': ledger_id, 'sold_no': -sell_quantity, 'pot_id':item['potion_id']})
            connection.execute(sqlalchemy.text("INSERT INTO gold_ledger (ledger_id, gold_delta) VALUES (:ledger_id, :total_cost)"),{'ledger_id': ledger_id, 'total_cost': total_cost})


    print(f"prev state num pots: {total_potions_sold} cost: {total_cost}")

    return {"total_potions_bought": total_potions_sold, "total_gold_paid": total_cost}

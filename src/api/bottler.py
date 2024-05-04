from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}") # what should i be doing with order id
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"delivering potions: {potions_delivered} order_id: {order_id}")
    
    with db.engine.begin() as connection:
        for potion in potions_delivered:

            # grabs id of potion being made
            result = connection.execute(sqlalchemy.text("SELECT id FROM potions WHERE potion_type = :potion_type"), {'potion_type': potion.potion_type}).first()
            potion_id = result.id
            
            # gets delta of each color 
            delta = [potion.potion_type[0] * potion.quantity, potion.potion_type[1] * potion.quantity, potion.potion_type[2] * potion.quantity, potion.potion_type[3] * potion.quantity]
            print(f"adding {potion.quantity} of {potion_id} with {delta}")
            
            # adds ml diff into total ledger
            res = connection.execute(sqlalchemy.text("INSERT INTO global_ledger (red_ml_delta, green_ml_delta, blue_ml_delta, dark_ml_delta, potion_id, potion_delta) VALUES (:rm,:gm,:bm,:dm, :pid, :pdelta) returning id AS ledger_id"), {"gm" : -delta[1], "rm" : -delta[0], "bm" : -delta[2], "dm" : -delta[3], "pid":potion_id, "pdelta": potion.quantity}).first()
            ledger_id = res.ledger_id
            
            # adds potion diff to total ledger
            connection.execute(sqlalchemy.text("INSERT INTO ml_ledger (ledger_id, red_ml, green_ml, blue_ml, dark_ml) VALUES (:ledger_id, :rm, :gm, :bm, :dm)"), {"ledger_id" : ledger_id, "gm" : -delta[1], "rm" : -delta[0], "bm" : -delta[2], "dm" : -delta[3]})
            connection.execute(sqlalchemy.text("INSERT INTO potion_ledger (ledger_id, potion_id, delta) VALUES (:ledger_id, :pid, :pdelta)"), {"ledger_id" : ledger_id, "pid" : potion_id, "pdelta": potion.quantity})
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    print("planning bottles")
    x = 5 # capacity
    green_ml = 0
    red_ml = 0
    blue_ml = 0
    bottle_cart = []
    sql_qry = """
                SELECT 
                    p.sku AS sku,
                    p.inventory AS current_inventory,  -- Renamed to avoid confusion
                    p.potion_type AS potion_type,
                    COALESCE(SUM(pl.delta), 0) AS total_inventory,
                    p.mixed AS mixed
                FROM
                    potions AS p
                LEFT JOIN
                    potion_ledger AS pl ON p.id = pl.potion_id
                GROUP BY 
                    p.sku,
                    p.inventory,
                    p.potion_type,
                    p.mixed
                ORDER BY 
                    total_inventory ASC,
                    mixed DESC;
                """
    # STEP 1) 
    with db.engine.begin() as connection:
        # grab all available ml
        available_colors = []
        result_global = connection.execute(sqlalchemy.text("SELECT SUM(red_ml_delta) AS red_ml,SUM(green_ml_delta) AS green_ml, SUM(blue_ml_delta) AS blue_ml, SUM(dark_ml_delta) AS dark_ml FROM global_ledger")).first()
        available_colors.append(result_global.red_ml)
        available_colors.append(result_global.green_ml)
        available_colors.append(result_global.blue_ml)
        available_colors.append(result_global.dark_ml)
        print(f"available ml inventory: {available_colors}")

        # grab possible potions
        potions = connection.execute(sqlalchemy.text(sql_qry)).mappings().all()

        additions = {potion['sku']: {'added': [0, 0, 0, 0], 'inventory': 0} for potion in potions}
        print(len(potions))
        cant_add = 0  # Initialize to a non-zero value to enter the loop
        while cant_add < len(potions):
            for potion in potions:
                # for each color check if enough if so add potion type to addition
                check = check_color(available_colors, potion['potion_type'])
                curr_i = additions[potion['sku']]['inventory']
                if check_color(available_colors, potion['potion_type']) is True and additions[potion['sku']]['inventory'] < 5:
                    # make this a loop later
                    additions[potion['sku']]['added'][0] += potion['potion_type'][0]
                    additions[potion['sku']]['added'][1] += potion['potion_type'][1]
                    additions[potion['sku']]['added'][2] += potion['potion_type'][2]
                    additions[potion['sku']]['added'][3] += potion['potion_type'][3]
                    available_colors[0] -= potion['potion_type'][0]
                    available_colors[1] -= potion['potion_type'][1]
                    available_colors[2] -= potion['potion_type'][2]
                    available_colors[3] -= potion['potion_type'][3]
                    additions[potion['sku']]['inventory'] += 1
                    cant_add = 0
                else:
                    cant_add += 1


        # Prepare the bottle cart based on accumulated additions
        bottle_cart = []
        for id, addition in additions.items():
                if sum(addition['added']) >= 100:
                    num_bottles = sum(addition['added']) // 100
                    normalized_addition = [int(amt/num_bottles) for amt in addition['added']]
                    bottle_cart.append({
                                            "potion_type": normalized_addition,
                                            "quantity": num_bottles
                                        })
    
    print(f"bottle plan: {bottle_cart}")
    return bottle_cart

def check_color(available, wanted):
    check = 0
    for i in range(4):
        avail_ml = available[i]
        wanted_ml = wanted[i]
        if avail_ml >= wanted_ml:
            check+=1
    return check == 4

if __name__ == "__main__":
    print(get_bottle_plan())
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
    # STEP 2) kinda tested!
    
    with db.engine.begin() as connection:
        # grab available ml and pots(green)
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
        available_inventory = [result.num_red_ml, result.num_green_ml, result.num_blue_ml, result.num_dark_ml]

        # for each potion
        for potion in potions_delivered:
            type = potion.potion_type
            num = potion.quantity
            
            result = connection.execute(sqlalchemy.text("SELECT id, inventory FROM potions WHERE potion_type = :potion_type"), {'potion_type': type}).first()
            potion_id = result.id
            potion_inventory = result.inventory + potion.quantity
            available_inventory[0] -= potion.potion_type[0] * potion.quantity
            available_inventory[1] -= potion.potion_type[1] * potion.quantity
            available_inventory[2] -= potion.potion_type[2] * potion.quantity
            available_inventory[3] -= potion.potion_type[3] * potion.quantity
            # id
            # can make sql text and execute separate
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :gm, num_red_ml =  :rm, num_blue_ml =  :bm, num_dark_ml = :dm"), {"gm" : available_inventory[1], "rm" : available_inventory[0], "bm" : available_inventory[2], "dm" : available_inventory[3]})
            connection.execute(sqlalchemy.text("UPDATE potions SET inventory = :inven WHERE id = :potion_id"), {"inven" : potion_inventory, "potion_id" : potion_id})
        # print(f"UPDATED INVENTORY {green_ml} ml and {green_pots} potions left")
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
    # STEP 1) 
    with db.engine.begin() as connection:
        # grab all available ml
        available_colors = []
        result_global = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
        available_colors.append(result_global.num_red_ml)
        available_colors.append(result_global.num_green_ml)
        available_colors.append(result_global.num_blue_ml)
        available_colors.append(result_global.num_dark_ml)
        print(f"available ml inventory: {available_colors}")

        # grab possible potions
        potions = connection.execute(sqlalchemy.text("SELECT sku, inventory, potion_type FROM public.potions WHERE inventory < 5 ORDER BY mixed DESC, inventory ASC")).mappings().all()


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
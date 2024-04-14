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
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")
    # STEP 2) kinda tested!
    
    with db.engine.begin() as connection:
        # grab available ml and pots(green)
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
        green_ml = result.num_green_ml
        green_pots = result.num_green_potions
        red_ml = result.num_red_ml
        red_pots = result.num_red_potions
        blue_ml = result.num_blue_ml
        blue_pots = result.num_blue_potions

        # print(f"CURR INVENTORY {green_ml} ml and {green_pots} potions left")

        # for each potion
        for potion in potions_delivered:

            if potion.potion_type[1] != 0:
                green_ml -= potion.potion_type[1] * potion.quantity # each potion has 100 ml for now
                green_pots += potion.quantity
            if potion.potion_type[0] != 0:
                red_ml -= potion.potion_type[0] * potion.quantity # each potion has 100 ml for now
                red_pots += potion.quantity
            if potion.potion_type[2] != 0:
                blue_ml -= potion.potion_type[2] * potion.quantity # each potion has 100 ml for now
                blue_pots += potion.quantity

        # can make sql text and execute separate
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :gm, num_green_potions = :gp, num_red_ml =  :rm, num_red_potions = :rp, num_blue_ml = :bm, num_blue_potions = :bp"), {"gm" : green_ml, "gp": green_pots, "rp": red_pots, "rm" : red_ml, "bp": blue_pots, "bm" : blue_ml})
        # print(f"UPDATED INVENTORY {green_ml} ml and {green_pots} potions left")
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    green_ml = 0
    red_ml = 0
    blue_ml = 0
    bottle_cart = []
    # STEP 1) 
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
        green_ml = result.num_green_ml//100
        red_ml = result.num_red_ml//100
        blue_ml = result.num_blue_ml//100

        if green_ml > 0:
            bottle_cart.append({
                "potion_type": [0, 100, 0, 0], # already sums up to 100
                "quantity": green_ml, # floor for bottle num
            })
        if red_ml > 0:
            bottle_cart.append({
                "potion_type": [100, 0, 0, 0], # already sums up to 100
                "quantity": red_ml, # floor for bottle num
            })
        if blue_ml > 0:
            bottle_cart.append({
                "potion_type": [0, 0, 100, 0], # already sums up to 100
                "quantity": blue_ml, # floor for bottle num
            })
    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into GREEN potions.

    return bottle_cart

if __name__ == "__main__":
    print(get_bottle_plan())
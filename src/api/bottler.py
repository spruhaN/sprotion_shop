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
    # STEP 2)
    
    with db.engine.begin() as connection:
        # grab available ml and pots(green)
        result = connection.execute(sqlalchemy.text("SELECT num_green_ml, num_green_potions FROM global_inventory"))
        green_ml = result.first().num_green_ml
        green_pots = result.first().num_green_potions

        # for each potion
        for potion in potions_delivered:
            green_ml -= potion.potion_type[1] * potion.quantity # each potion has 100 ml for now
            green_pots += potion.quantity

        # can make sql text and execute separate
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :green_ml, num_green_potions = :green_pots"), {"green_ml" : green_ml, "green_pots": green_pots})
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # STEP 1) 
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory"))
    green_ml = result.first().num_green_ml
    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into GREEN potions.

    return [
            {
                "potion_type": [0, 100, 0, 0], # already sums up to 100
                "quantity": green_ml//100, # floor for bottle num
            }
        ]

if __name__ == "__main__":
    print(get_bottle_plan())
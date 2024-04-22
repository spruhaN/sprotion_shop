from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ """
    total_pots = 0
    total_ml = 0
    total_gold = 0
    with db.engine.begin() as connection:
        global_inv = connection.execute(sqlalchemy.text("SELECT num_red_ml + num_green_ml + num_blue_ml + num_dark_ml AS total_ml, gold FROM global_inventory")).first()
        potion_inv = connection.execute(sqlalchemy.text("SELECT SUM(inventory) AS total_pots FROM potions")).first()
    return {"number_of_potions": potion_inv.total_pots, "ml_in_barrels": global_inv.total_ml , "gold": global_inv.gold}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return {
        "potion_capacity": 0,
        "ml_capacity": 0
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return "OK"

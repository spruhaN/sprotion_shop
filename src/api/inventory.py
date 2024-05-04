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
        ml_inv = connection.execute(sqlalchemy.text("SELECT COALESCE(SUM(red_ml) + SUM(green_ml) + SUM(blue_ml) + SUM(dark_ml), 0) AS total_ml FROM ml_ledger;")).first().total_ml
        gold_inv = connection.execute(sqlalchemy.text("SELECT COALESCE(SUM(gold_delta), 0) AS total_gold FROM gold_ledger")).first().total_gold
        potion_inv = connection.execute(sqlalchemy.text("SELECT COALESCE(SUM(delta), 0) AS total_potions FROM potion_ledger")).first().total_potions
    return {"number_of_potions": potion_inv, "ml_in_barrels": ml_inv , "gold": gold_inv}

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

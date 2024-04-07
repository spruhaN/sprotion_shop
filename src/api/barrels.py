from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    green_ml = 0
    gold = 0
    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_ml, gold FROM global_inventory"))
        green_ml = result.first().num_green_ml
        gold = result.first().gold

        for barrel in barrels_delivered:
            # adds barrel ml to global and subtracts gold
            green_ml += (barrel.potion_type[1] * barrel.quantity)
            gold -= barrel.price * barrel.quantity

    # combine later 
    # updates transaction
    with db.engine.begin() as connection:
        query = sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :green_ml , gold = :gold")
        result = connection.execute(query, {'green_ml': green_ml, 'gold': gold})
        connection.commit()
    return "OK"

# Gets called once a day should i subtract gold here or in deliver??
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    # purchases the barrels for the day
    print(wholesale_catalog)

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_potions, gold FROM global_inventory"))
        green_pots = result.first().num_green_potions
        gold = result.first().gold

        if green_pots < 10: # if there are less than 10 potions buy 1 green barrel
            for barrel in wholesale_catalog:
                if barrel.sku == "SMALL_GREEN_BARREL":
                    if gold >= barrel.price:
                        return [
                            {
                                "sku": "SMALL_GREEN_BARREL",
                                "quantity": 1,
                            }
                        ]
                else:
                    return []


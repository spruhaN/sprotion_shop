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
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
        green_ml = result.num_green_ml
        red_ml = result.num_red_ml
        blue_ml = result.num_blue_ml
        gold = result.gold
        print(f"CURRENT INV: (g: {green_ml}ml) (r: {red_ml}ml) (b: {blue_ml} ml) ({gold}coins)")
        for barrel in barrels_delivered:
            green_ml += (barrel.potion_type[1] * barrel.ml_per_barrel * barrel.quantity)
            red_ml += (barrel.potion_type[0] * barrel.ml_per_barrel * barrel.quantity)
            blue_ml += (barrel.potion_type[2] *  barrel.ml_per_barrel * barrel.quantity)
            gold -= barrel.price * barrel.quantity

        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :green_ml, num_red_ml = :red_ml, num_blue_ml = :blue_ml"), {"green_ml" : green_ml, "blue_ml": blue_ml, "red_ml": red_ml})

    print(f"UPDATED INV: (g: {green_ml}ml) (r: {red_ml}ml) (b: {blue_ml} ml) ({gold}coins)")
    return "OK"

@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    # purchases the barrels for the day
    print(wholesale_catalog)
    print("testing plan endpoint")
    barrel_cart = []

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
        green_pots = result.num_green_potions
        red_pots = result.num_red_potions
        blue_pots = result.num_blue_potions
        gold = result.gold

        # make this better later :/ has collisions
        if green_pots < 10:
            for barrel in wholesale_catalog:
                if "green" in barrel.sku.lower():
                    if gold >= barrel.price:
                        barrel_cart.append({
                                            "sku": barrel.sku,
                                            "quantity": 1,
                                        })
                        gold -= barrel.price
        if red_pots < 10: 
            for barrel in wholesale_catalog:
                if "red" in barrel.sku.lower():
                    if gold >= barrel.price:
                        barrel_cart.append({
                                            "sku": barrel.sku,
                                            "quantity": 1,
                                        })
                        gold -= barrel.price
        if blue_pots < 10: 
            for barrel in wholesale_catalog:
                if "blue" in barrel.sku.lower():
                    if gold >= barrel.price:
                        barrel_cart.append({
                                            "sku": barrel.sku,
                                            "quantity": 1,
                                        })
                        gold -= barrel.price
    return barrel_cart


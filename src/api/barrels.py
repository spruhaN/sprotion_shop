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
    print(f"delivering barrels: {barrels_delivered} order_id: {order_id}")
    with db.engine.begin() as connection:
        green_ml = 0
        red_ml = 0
        blue_ml = 0
        dark_ml = 0
        gold = 0
        for barrel in barrels_delivered: # for now quantity is always one
            green_ml += (barrel.potion_type[1] * barrel.ml_per_barrel * barrel.quantity)
            red_ml += (barrel.potion_type[0] * barrel.ml_per_barrel * barrel.quantity)
            blue_ml += (barrel.potion_type[2] *  barrel.ml_per_barrel * barrel.quantity)
            dark_ml += (barrel.potion_type[3] *  barrel.ml_per_barrel * barrel.quantity)
            gold -= barrel.price * barrel.quantity 
        res = connection.execute(sqlalchemy.text("INSERT INTO global_ledger (red_ml_delta, green_ml_delta, blue_ml_delta, dark_ml_delta, gold_delta) VALUES (:red_ml,:green_ml,:blue_ml,:dark_ml,:gold) RETURNING id AS init_ledger_id;"), {"red_ml": red_ml, "green_ml": green_ml, "blue_ml": blue_ml, "dark_ml": dark_ml, "gold":gold}).first()
        ledger_id = res.init_ledger_id
        connection.execute(sqlalchemy.text("INSERT INTO ml_ledger (ledger_id, red_ml, green_ml, blue_ml, dark_ml) VALUES (:ledger_id, :red_ml,:green_ml,:blue_ml,:dark_ml)"), {"red_ml": red_ml, "green_ml": green_ml, "blue_ml": blue_ml, "dark_ml": dark_ml, "ledger_id":ledger_id})
        connection.execute(sqlalchemy.text("INSERT INTO gold_ledger (ledger_id, gold_delta) VALUES (:ledger_id,:gold)"), {"ledger_id": ledger_id, "gold":gold})

    print(f"update diffs: (g: {green_ml}ml) (r: {red_ml}ml) (b: {blue_ml} ml) (d: {dark_ml} ml) ({gold}coins)")
    return "OK"


# REMOVING ALL COMPLEX LOGIC still buys too much red SO MIX INITIAL CATALOG TI ALTERNATE COLORS
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    with db.engine.begin() as connection:
        res = connection.execute(sqlalchemy.text(
            """
            SELECT 
                SUM(red_ml_delta) AS red_ml,
                SUM(blue_ml_delta) AS green_ml,
                SUM(green_ml_delta) AS blue_ml,
                SUM(dark_ml_delta) AS dark_ml,
                SUM(gold_delta) AS gold
            FROM 
                global_ledger
            """)).first()
        
        red_ml = res.red_ml
        green_ml = res.green_ml
        blue_ml = res.blue_ml
        dark_ml = res.dark_ml
        gold = res.gold

    ml_capacity = 10000

    barrel_plan = []
    barrelsize = 500
    # wholesale_catalog = [Barrel(sku='SMALL_RED_BARREL', ml_per_barrel=500, potion_type=[1, 0, 0, 0], price=100, quantity=10), Barrel(sku='SMALL_GREEN_BARREL', ml_per_barrel=500, potion_type=[0, 1, 0, 0], price=100, quantity=10), Barrel(sku='SMALL_BLUE_BARREL', ml_per_barrel=500, potion_type=[0, 0, 1, 0], price=120, quantity=10), Barrel(sku='MINI_RED_BARREL', ml_per_barrel=200, potion_type=[1, 0, 0, 0], price=60, quantity=1), Barrel(sku='MINI_GREEN_BARREL', ml_per_barrel=200, potion_type=[0, 1, 0, 0], price=60, quantity=1), Barrel(sku='MINI_BLUE_BARREL', ml_per_barrel=200, potion_type=[0, 0, 1, 0], price=60, quantity=1)]
    barrel_list = sorted(wholesale_catalog, key=lambda barrel: barrel.ml_per_barrel, reverse=True)

    for barrel in wholesale_catalog:
        if barrel.potion_type == [0, 1, 0, 0] and (barrel.ml_per_barrel >= barrelsize or (green_ml < 1000 and barrel.ml_per_barrel >= 500)):
            cap = ml_capacity/3 - green_ml
            qty = int(cap // barrel.ml_per_barrel)
            while barrel.price*qty > gold and qty > 0:
                qty -= 1
            if qty > 0:
                gold -= barrel.price*qty
                barrel_plan.append({
                    "sku": barrel.sku,
                    "quantity": qty,
                })
                green_ml += barrel.ml_per_barrel * qty

        elif barrel.potion_type == [1, 0, 0, 0] and (barrel.ml_per_barrel >= barrelsize or (red_ml < 1000 and barrel.ml_per_barrel >= 500)):
            cap = ml_capacity/3 - red_ml
            qty = int(cap // barrel.ml_per_barrel)
            while barrel.price*qty > gold and qty > 0:
                qty -= 1
            if qty > 0:
                gold -= barrel.price*qty
                barrel_plan.append({
                    "sku": barrel.sku,
                    "quantity": qty,
                })
                red_ml += barrel.ml_per_barrel * qty
    
        elif barrel.potion_type == [0, 0, 1, 0] and (barrel.ml_per_barrel >= barrelsize or (blue_ml < 1000 and barrel.ml_per_barrel >= 500)):
            cap = ml_capacity/3 - blue_ml
            qty = int(cap // barrel.ml_per_barrel)
            while barrel.price*qty > gold and qty > 0:
                qty -= 1
            if qty > 0:
                gold -= barrel.price*qty
                barrel_plan.append({
                    "sku": barrel.sku,
                    "quantity": qty,
                })
                blue_ml += barrel.ml_per_barrel * qty
                

    return barrel_plan
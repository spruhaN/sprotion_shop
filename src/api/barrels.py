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

    barrel_plan = []
    # wholesale_catalog = [Barrel(sku='MEDIUM_RED_BARREL', ml_per_barrel=2500, potion_type=[1, 0, 0, 0], price=250, quantity=10), Barrel(sku='SMALL_RED_BARREL', ml_per_barrel=500, potion_type=[1, 0, 0, 0], price=100, quantity=10), Barrel(sku='MEDIUM_GREEN_BARREL', ml_per_barrel=2500, potion_type=[0, 1, 0, 0], price=250, quantity=10), Barrel(sku='SMALL_GREEN_BARREL', ml_per_barrel=500, potion_type=[0, 1, 0, 0], price=100, quantity=10), Barrel(sku='MEDIUM_BLUE_BARREL', ml_per_barrel=2500, potion_type=[0, 0, 1, 0], price=300, quantity=10), Barrel(sku='SMALL_BLUE_BARREL', ml_per_barrel=500, potion_type=[0, 0, 1, 0], price=120, quantity=10), Barrel(sku='MINI_RED_BARREL', ml_per_barrel=200, potion_type=[1, 0, 0, 0], price=60, quantity=1), Barrel(sku='MINI_GREEN_BARREL', ml_per_barrel=200, potion_type=[0, 1, 0, 0], price=60, quantity=1), Barrel(sku='MINI_BLUE_BARREL', ml_per_barrel=200, potion_type=[0, 0, 1, 0], price=60, quantity=1), Barrel(sku='LARGE_DARK_BARREL', ml_per_barrel=10000, potion_type=[0, 0, 0, 1], price=750, quantity=10), Barrel(sku='LARGE_BLUE_BARREL', ml_per_barrel=10000, potion_type=[0, 0, 1, 0], price=600, quantity=30), Barrel(sku='LARGE_GREEN_BARREL', ml_per_barrel=10000, potion_type=[0, 1, 0, 0], price=400, quantity=30), Barrel(sku='LARGE_RED_BARREL', ml_per_barrel=10000, potion_type=[1, 0, 0, 0], price=500, quantity=30)]
    print(f" planning barrels: {wholesale_catalog}")
    barrel_list = sorted(wholesale_catalog, key=lambda barrel: barrel.ml_per_barrel, reverse=True)
    for barrel in barrel_list:
        potion_needed = (green_ml < 1000 and barrel.potion_type == [0, 1, 0, 0]) or \
                    (green_ml < 1000 and barrel.potion_type == [1, 0, 0, 0]) or \
                    (green_ml < 1000 and barrel.potion_type == [0, 0, 1, 0]) or \
                    (green_ml < 1000 and barrel.potion_type == [0, 0, 0, 1])
        
        if barrel.ml_per_barrel > 200 or (potion_needed and barrel.ml_per_barrel > 300):
            num_barrels = int(10000/barrel.ml_per_barrel)

            for i in range(num_barrels, 0, -1):
                if barrel.price * i <= gold:
                    num_barrels = i
                    break
                
            if num_barrels > 0 and gold >= (barrel.price * num_barrels):
                gold -= barrel.price * num_barrels
                barrel_plan.append({
                    "sku": barrel.sku,
                    "quantity": num_barrels,
                })
                if barrel.potion_type == [0, 1, 0, 0]:
                    green_ml += barrel.ml_per_barrel * num_barrels
                elif barrel.potion_type == [1, 0, 0, 0]:
                    red_ml += barrel.ml_per_barrel * num_barrels
                elif barrel.potion_type == [0, 0, 1, 0]:
                    blue_ml += barrel.ml_per_barrel * num_barrels
                elif barrel.potion_type == [0, 0, 0, 1]:
                    dark_ml += barrel.ml_per_barrel * num_barrels
    print(f"planning to get {barrel_plan}")
    return barrel_plan
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
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
        green_ml = result.num_green_ml
        red_ml = result.num_red_ml
        blue_ml = result.num_blue_ml
        dark_ml = result.num_dark_ml
        gold = result.gold
        print(f"current: (g: {green_ml} ml) (r: {red_ml}ml) (b: {blue_ml} ml) (d: {dark_ml} ml) ({gold}coins)")
        for barrel in barrels_delivered: # for now quantity is always one
            green_ml += (barrel.potion_type[1] * barrel.ml_per_barrel * barrel.quantity)
            red_ml += (barrel.potion_type[0] * barrel.ml_per_barrel * barrel.quantity)
            blue_ml += (barrel.potion_type[2] *  barrel.ml_per_barrel * barrel.quantity)
            dark_ml += (barrel.potion_type[2] *  barrel.ml_per_barrel * barrel.quantity)
            gold -= barrel.price * barrel.quantity 

        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :green_ml, num_red_ml = :red_ml, num_blue_ml = :blue_ml, num_dark_ml = :dark_ml, gold = :gold"), {"green_ml" : green_ml, "blue_ml": blue_ml, "red_ml": red_ml,"dark_ml": dark_ml , "gold": gold})

    print(f"update: (g: {green_ml}ml) (r: {red_ml}ml) (b: {blue_ml} ml) (d: {dark_ml} ml) ({gold}coins)")
    return "OK"

@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    # wholesale_catalog = [Barrel(sku='MEDIUM_RED_BARREL', ml_per_barrel=2500, potion_type=[1, 0, 0, 0], price=250, quantity=10), Barrel(sku='SMALL_RED_BARREL', ml_per_barrel=500, potion_type=[1, 0, 0, 0], price=100, quantity=10), Barrel(sku='MEDIUM_GREEN_BARREL', ml_per_barrel=2500, potion_type=[0, 1, 0, 0], price=250, quantity=10), Barrel(sku='SMALL_GREEN_BARREL', ml_per_barrel=500, potion_type=[0, 1, 0, 0], price=100, quantity=10), Barrel(sku='MEDIUM_BLUE_BARREL', ml_per_barrel=2500, potion_type=[0, 0, 1, 0], price=300, quantity=10), Barrel(sku='SMALL_BLUE_BARREL', ml_per_barrel=500, potion_type=[0, 0, 1, 0], price=120, quantity=10), Barrel(sku='MINI_RED_BARREL', ml_per_barrel=200, potion_type=[1, 0, 0, 0], price=60, quantity=1), Barrel(sku='MINI_GREEN_BARREL', ml_per_barrel=200, potion_type=[0, 1, 0, 0], price=60, quantity=1), Barrel(sku='MINI_BLUE_BARREL', ml_per_barrel=200, potion_type=[0, 0, 1, 0], price=60, quantity=1), Barrel(sku='LARGE_DARK_BARREL', ml_per_barrel=10000, potion_type=[0, 0, 0, 1], price=750, quantity=10), Barrel(sku='LARGE_BLUE_BARREL', ml_per_barrel=10000, potion_type=[0, 0, 1, 0], price=600, quantity=30), Barrel(sku='LARGE_GREEN_BARREL', ml_per_barrel=10000, potion_type=[0, 1, 0, 0], price=400, quantity=30), Barrel(sku='LARGE_RED_BARREL', ml_per_barrel=10000, potion_type=[1, 0, 0, 0], price=500, quantity=30)]
    # purchases the barrels for the day
    print(f"planning barrels \ncatalog: {wholesale_catalog}\n")

    # get budget
    gold = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).first()
        gold = result.gold

    # get ml to fufill capacity
    requirements = get_wanted_ml()

    print(f"wanted ml: {requirements}")

    # w/ constraints get optimized barrel plan
    selected = get_wanted_barrels(wholesale_catalog, requirements, gold)

    return selected


# so now only considers smaller barrels more for more diversity but only considers each barrel once...
# make it such that it looks for quantity as well
def get_wanted_barrels(barrels, requirements, budget):
    selected_barrels = []
    total_cost = 0
    colors = ['red', 'green', 'blue', 'dark']
    color_index = 0  # Start with the first color

    def actual_ml(barrel, color_index):
        return barrel.potion_type[color_index] * barrel.ml_per_barrel

    def barrel_score(barrel):
        contributions = [actual_ml(barrel, idx) for idx in range(4) if requirements[idx] > 0]
        if all(contribution == 0 for contribution in contributions):
            return 0  # If barrel meets none of the wanted ml
        score = sum((requirements[idx] - actual_ml(barrel, idx)) ** 2 
                    for idx in range(4) if requirements[idx] > 0)
        return score / barrel.price if barrel.price <= budget else 0

    while sum(requirements) > 0 and budget > 0:
        # filter barrels that can contribute to the current color and have a score greater than 0
        filtered_barrels = [barrel for barrel in barrels if actual_ml(barrel, color_index) > 0 and barrel_score(barrel) > 0]
        if not filtered_barrels:
            color_index = (color_index + 1) % 4  # move to the next color
            continue

        # sort barrels by their ml_per_barrel (ascending for smaller size) and then by actual ml contribution (descending)
        filtered_barrels.sort(key=lambda barrel: (barrel.ml_per_barrel, -actual_ml(barrel, color_index)))

        best_barrel = filtered_barrels[0]
        if total_cost + best_barrel.price <= budget:
            selected_barrels.append({
                "sku": best_barrel.sku,
                "quantity": 1
            })
            total_cost += best_barrel.price
            budget -= best_barrel.price

            # update requirements based on the selected barrel
            for i in range(4):
                requirements[i] = max(0, requirements[i] - actual_ml(best_barrel, i))

            barrels.remove(best_barrel)  # avoids reselection
            # thoughts: if enough quantity decrement and make score less
        else:
            break  # Stop if the barrel is too expensive

        color_index = (color_index + 1) % 4  # Cycle to the next color

    return selected_barrels





# returns wanted ml for potions to reach ideal capacity
# NEXT CHANGE ACCOUNT FOR INVENTORY AND AVAILABLE ML
# WANTED SHOULD BE THE DIFF OF BOTH IDEAL AMTS
def get_wanted_ml(): # modify this later to contain bias based on time
    capacity = 4
    wanted_red = 0
    wanted_green = 0
    wanted_blue = 0
    wanted_dark = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT sku,potion_type,inventory FROM potions WHERE inventory < 4"))
        for row in result.mappings():
            print(row)
            potion_type = row['potion_type']
            inventory = row['inventory']
            sku = row['sku']
            n = capacity - inventory
            wanted_red += potion_type[0] * n
            wanted_green += potion_type[1] * n
            wanted_blue += potion_type[2] * n
            wanted_dark += potion_type[3] * n
    return [wanted_red, wanted_green, wanted_blue, wanted_dark]


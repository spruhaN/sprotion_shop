from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

# STEP 1) TESTED!
@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    green_pots = 0
    red_pots = 0
    blue_pots = 0
    catalog = []
    # get available green pots from inventory
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
        green_pots = result.num_green_potions
        red_pots = result.num_red_potions
        blue_pots = result.num_blue_potions

        if green_pots != 0:
            catalog.append({
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": green_pots,
                "price": 50,
                "potion_type": [0, 100, 0, 0],
            })
        if red_pots != 0:
            catalog.append({
                "sku": "RED_POTION_0",
                "name": "red potion",
                "quantity": red_pots,
                "price": 50,
                "potion_type": [100, 0, 0, 0],
            })
        if blue_pots != 0:
            catalog.append({
                "sku": "BLUE_POTION_0",
                "name": "blue potion",
                "quantity": blue_pots,
                "price": 50,
                "potion_type": [0, 0, 100, 0],
            })
    
    # else return how many are available
    return catalog

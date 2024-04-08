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
    # get available green pots from inventory
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory"))
        green_pots = result.first().num_green_potions

        # if no green pots then []
        if green_pots == 0:
            return []
    
    # else return how many are available
    return [
            {
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": green_pots,
                "price": 50,
                "potion_type": [0, 100, 0, 0],
            }
        ]

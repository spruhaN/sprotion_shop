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
    catalog = []
    with db.engine.begin() as connection:
        results = connection.execute(sqlalchemy.text("SELECT sku, inventory, price, potion_type FROM public.potions WHERE inventory > 0 ORDER BY inventory DESC")).mappings().all()
        count = 0
        
        for result in results:
            potion_type = [int(n) for n in result['potion_type']]
            catalog.append({
                "sku": result['sku'],
                "name": f"{result['sku'].split('_')[0].lower()} potion",
                "quantity": result['inventory'],
                "price": result['price'],
                "potion_type": potion_type
            })
            count += 1
            if count == 6:
                break
        
    return catalog
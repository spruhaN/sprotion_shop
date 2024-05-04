from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    sql_qry = """
            SELECT 
                p.sku AS sku, 
                p.id AS id, 
                p.price AS price,
                p.potion_type AS potion_type, 
                COALESCE(SUM(pl.delta), 0) AS inventory
            FROM 
                potions AS p
            LEFT JOIN 
                potion_ledger AS pl ON p.id = pl.potion_id
            GROUP BY 
                p.sku, 
                p.id, 
                p.price, 
                p.potion_type
            HAVING 
                COALESCE(SUM(pl.delta), 0) > 0
            ORDER BY 
                inventory DESC;
            """
    catalog = []
    with db.engine.begin() as connection:
        results = connection.execute(sqlalchemy.text(sql_qry)).mappings().all()
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
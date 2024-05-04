from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

# TESTED
@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    print("resetting")
    sql_command =   """                    
                    DELETE FROM gold_ledger;
                    DELETE FROM ml_ledger;
                    DELETE FROM potion_ledger;
                    DELETE FROM global_ledger;
                    """
    
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(sql_command))
        result = connection.execute(sqlalchemy.text("INSERT INTO global_ledger (gold_delta) VALUES (100) RETURNING id AS init_ledger_id")).first()
        global_ledger_id = result.init_ledger_id
        connection.execute(sqlalchemy.text("INSERT INTO gold_ledger (ledger_id, gold_delta) VALUES (:l_id, 100)"), {"l_id": global_ledger_id})
        
    return "OK"


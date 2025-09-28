
from pydantic import BaseModel

class HoldingUpdateRequest(BaseModel):
    quantity: float
    average_cost: float

class AssetSellRequest(BaseModel):
    ticker: str
    quantity: float
    price: float

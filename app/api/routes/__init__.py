from .customer import router as customer_router
from .orders import router as orders_router
from .billing import router as billing_router
from .support import router as support_router

__all__ = [
    "customer_router",
    "orders_router",
    "billing_router",
    "support_router"
]
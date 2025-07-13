from .api import router
from .core.config import settings
from .core.setup import create_application

app = create_application(router=router, settings=settings, create_tables_on_start=True)

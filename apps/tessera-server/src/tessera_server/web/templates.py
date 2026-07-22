import os

from fastapi.templating import Jinja2Templates

from tessera_server.constants import PROJECT_ROOT

templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "templates"))

from config import Config
from db_setup import get_engine

Config.validate()
engine = get_engine()
print("✅ Conexión exitosa!")
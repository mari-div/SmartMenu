"""Configuracion de la aplicacion (lee variables del archivo .env)."""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/smartmenu",
    )
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-cambiar-en-produccion")
    # Cuantos platos puede preparar la cocina "en paralelo" (usado en las estimaciones)
    ESTACIONES_COCINA = int(os.getenv("ESTACIONES_COCINA", "3"))


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

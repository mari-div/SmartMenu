"""Punto de entrada: `python run.py` o `flask --app run <comando>`."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

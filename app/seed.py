"""Datos iniciales: menu del restaurante de ejemplo y mesas."""
from app.extensions import db
from app.models import Categoria, Ingrediente, Mesa, Plato, PlatoIngrediente

# (nombre, tipo, tiene_gluten, tiene_frutos_secos, stock, unidad)
INGREDIENTES = [
    ("Tortilla de maíz", "cereal", False, False, 40, "kg"),
    ("Pan", "cereal", True, False, 60, "kg"),
    ("Harina de trigo", "cereal", True, False, 80, "kg"),
    ("Arroz", "cereal", False, False, 100, "kg"),
    ("Pasta", "cereal", True, False, 50, "kg"),
    ("Cebada", "cereal", True, False, 30, "kg"),
    ("Carne de res", "carne", False, False, 40, "kg"),
    ("Pollo", "carne", False, False, 60, "kg"),
    ("Pepperoni", "carne", False, False, 15, "kg"),
    ("Camarón", "pescado", False, False, 20, "kg"),
    ("Queso", "lacteo", False, False, 25, "kg"),
    ("Mozzarella", "lacteo", False, False, 30, "kg"),
    ("Crema", "lacteo", False, False, 20, "l"),
    ("Leche", "lacteo", False, False, 40, "l"),
    ("Helado", "lacteo", False, False, 25, "l"),
    ("Huevo", "huevo", False, False, 300, "u"),
    ("Lechuga", "vegetal", False, False, 15, "kg"),
    ("Tomate", "vegetal", False, False, 30, "kg"),
    ("Aguacate", "vegetal", False, False, 20, "kg"),
    ("Limón", "vegetal", False, False, 20, "kg"),
    ("Garbanzos", "vegetal", False, False, 15, "kg"),
    ("Lentejas", "vegetal", False, False, 15, "kg"),
    ("Frijoles", "vegetal", False, False, 15, "kg"),
    ("Papas", "vegetal", False, False, 80, "kg"),
    ("Champiñones", "vegetal", False, False, 10, "kg"),
    ("Pimientos", "vegetal", False, False, 10, "kg"),
    ("Cebolla", "vegetal", False, False, 25, "kg"),
    ("Albahaca", "vegetal", False, False, 3, "kg"),
    ("Fruta", "vegetal", False, False, 40, "kg"),
    ("Salsa de tomate", "vegetal", False, False, 30, "l"),
    ("Nueces", "vegetal", False, True, 8, "kg"),
    ("Aceite", "otro", False, False, 40, "l"),
    ("Azúcar", "otro", False, False, 50, "kg"),
    ("Chocolate", "otro", False, False, 10, "kg"),
    ("Café", "otro", False, False, 10, "kg"),
    ("Agua", "otro", False, False, 500, "l"),
    ("Salsa BBQ", "otro", False, False, 10, "l"),
    ("Jarabe de gaseosa", "otro", False, False, 60, "l"),
]

# categoria -> lista de (nombre, descripcion, precio, costo, minutos, [ingredientes])
MENU = {
    "Entradas": [
        ("Nachos con queso", "Tortilla crujiente con queso fundido y frijoles", 6.50, 2.10, 8,
         ["Tortilla de maíz", "Queso", "Frijoles", "Tomate"]),
        ("Ensalada fresca", "Lechuga, tomate y aguacate con limón", 5.90, 1.80, 6,
         ["Lechuga", "Tomate", "Aguacate", "Limón", "Aceite"]),
        ("Hummus con pan pita", "Crema de garbanzos con aceite de oliva", 5.50, 1.70, 6,
         ["Garbanzos", "Aceite", "Limón", "Pan"]),
        ("Alitas BBQ", "Seis alitas de pollo con salsa BBQ", 8.90, 3.40, 15,
         ["Pollo", "Salsa BBQ"]),
    ],
    "Platos fuertes": [
        ("Hamburguesa clásica", "Carne de res, queso, lechuga y tomate", 9.90, 3.60, 14,
         ["Pan", "Carne de res", "Queso", "Lechuga", "Tomate"]),
        ("Hamburguesa vegana", "Medallón de lentejas con aguacate", 9.50, 3.10, 13,
         ["Pan", "Lentejas", "Lechuga", "Tomate", "Aguacate"]),
        ("Pollo a la parrilla", "Pechuga con arroz y ensalada", 10.50, 3.70, 18,
         ["Pollo", "Arroz", "Lechuga", "Limón"]),
        ("Pasta alfredo", "Pasta en salsa cremosa con champiñones", 10.90, 3.00, 15,
         ["Pasta", "Crema", "Queso", "Champiñones"]),
        ("Arroz con camarones", "Arroz salteado con camarones y pimientos", 12.50, 5.20, 20,
         ["Arroz", "Camarón", "Pimientos", "Cebolla"]),
        ("Papas fritas", "Porción grande de papas crocantes", 3.90, 0.80, 8,
         ["Papas", "Aceite"]),
    ],
    "Pizzas": [
        ("Pizza margarita", "Tomate, mozzarella y albahaca", 11.00, 3.20, 16,
         ["Harina de trigo", "Salsa de tomate", "Mozzarella", "Albahaca"]),
        ("Pizza pepperoni", "Mozzarella y abundante pepperoni", 12.50, 4.10, 17,
         ["Harina de trigo", "Salsa de tomate", "Mozzarella", "Pepperoni"]),
        ("Pizza vegetariana", "Champiñones, pimientos y mozzarella", 12.00, 3.50, 17,
         ["Harina de trigo", "Salsa de tomate", "Mozzarella", "Champiñones", "Pimientos"]),
    ],
    "Postres": [
        ("Brownie con helado", "Brownie tibio con nueces y helado", 5.50, 1.60, 7,
         ["Harina de trigo", "Chocolate", "Huevo", "Nueces", "Helado", "Azúcar"]),
        ("Flan de caramelo", "Flan casero con caramelo", 4.50, 1.10, 3,
         ["Huevo", "Leche", "Azúcar"]),
        ("Ensalada de frutas", "Fruta fresca de temporada", 4.00, 1.20, 4, ["Fruta"]),
    ],
    "Bebidas": [
        ("Limonada", "Limonada natural", 2.80, 0.50, 3, ["Limón", "Azúcar", "Agua"]),
        ("Jugo natural", "Jugo de fruta del día", 3.00, 0.80, 3, ["Fruta", "Agua"]),
        ("Cerveza artesanal", "Botella 330 ml", 4.50, 1.50, 1, ["Cebada", "Agua"]),
        ("Café", "Café americano", 2.20, 0.40, 3, ["Café", "Agua"]),
        ("Gaseosa", "Lata 355 ml", 2.00, 0.50, 1, ["Jarabe de gaseosa", "Agua"]),
    ],
}


def sembrar_menu() -> bool:
    """Crea categorias, ingredientes y platos. Devuelve False si ya existian."""
    if Categoria.query.first():
        return False

    ingredientes = {}
    for nombre, tipo, gluten, secos, stock, unidad in INGREDIENTES:
        ing = Ingrediente(nombre=nombre, tipo=tipo, tiene_gluten=gluten,
                          tiene_frutos_secos=secos, stock=stock, unidad=unidad)
        ingredientes[nombre] = ing
        db.session.add(ing)

    for orden, (cat_nombre, platos) in enumerate(MENU.items()):
        categoria = Categoria(nombre=cat_nombre, orden=orden)
        db.session.add(categoria)
        for nombre, desc, precio, costo, minutos, ings in platos:
            plato = Plato(nombre=nombre, descripcion=desc, precio=precio, costo=costo,
                          tiempo_prep_min=minutos, categoria=categoria)
            plato.ingredientes = [
                PlatoIngrediente(ingrediente=ingredientes[n], cantidad=0.15) for n in ings
            ]
            db.session.add(plato)
    db.session.commit()
    return True


def sembrar_mesas(cantidad: int = 10) -> int:
    """Crea mesas numeradas (cada una con su token para el QR). Devuelve cuantas creo."""
    existentes = {m.numero for m in Mesa.query.all()}
    nuevas = [Mesa(numero=n, capacidad=4 if n % 3 else 6)
              for n in range(1, cantidad + 1) if n not in existentes]
    db.session.add_all(nuevas)
    db.session.commit()
    return len(nuevas)

"""Datos iniciales: menu del restaurante de ejemplo y mesas."""
from app.extensions import db
from app.models import Categoria, Ingrediente, Mesa, Plato, PlatoIngrediente, Usuario

def _foto(id_unsplash: str) -> str:
    """Foto de internet (Unsplash) ya recortada y comprimida para la carta."""
    return f"https://images.unsplash.com/{id_unsplash}?w=640&q=70&auto=format&fit=crop"


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
    ("Pescado blanco", "pescado", False, False, 25, "kg"),
    ("Camote", "vegetal", False, False, 20, "kg"),
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

# categoria -> lista de (nombre, descripcion, precio S/, costo S/, minutos, [ingredientes], foto)
MENU = {
    "Entradas": [
        ("Nachos con queso", "Tortilla crujiente con queso fundido y frijoles", 18.00, 6.00, 8,
         ["Tortilla de maíz", "Queso", "Frijoles", "Tomate"], "photo-1513456852971-30c0b8199d4d"),
        ("Ensalada fresca", "Lechuga, tomate y palta con limón", 16.00, 5.00, 6,
         ["Lechuga", "Tomate", "Aguacate", "Limón", "Aceite"], "photo-1512621776951-a57141f2eefd"),
        ("Hummus con pan pita", "Crema de garbanzos con aceite de oliva", 15.00, 4.50, 6,
         ["Garbanzos", "Aceite", "Limón", "Pan"], "photo-1637949385162-e416fb15b2ce"),
        ("Alitas BBQ", "Seis alitas de pollo con salsa BBQ", 26.00, 10.00, 15,
         ["Pollo", "Salsa BBQ"], "photo-1544025162-d76694265947"),
        ("Ceviche clásico", "Pescado fresco en leche de tigre, camote y cebolla", 36.00, 13.00, 12,
         ["Pescado blanco", "Limón", "Cebolla", "Camote"], "photo-1535399831218-d5bd36d1a6b3"),
    ],
    "Platos fuertes": [
        ("Hamburguesa clásica", "Carne de res, queso, lechuga y tomate", 28.00, 10.50, 14,
         ["Pan", "Carne de res", "Queso", "Lechuga", "Tomate"], "photo-1568901346375-23c9450c58cd"),
        ("Hamburguesa vegana", "Medallón de lentejas con palta", 27.00, 9.00, 13,
         ["Pan", "Lentejas", "Lechuga", "Tomate", "Aguacate"], "photo-1520072959219-c595dc870360"),
        ("Pollo a la parrilla", "Pechuga con arroz y ensalada", 30.00, 11.00, 18,
         ["Pollo", "Arroz", "Lechuga", "Limón"], "photo-1532550907401-a500c9a57435"),
        ("Pasta alfredo", "Pasta en salsa cremosa con champiñones", 31.00, 9.00, 15,
         ["Pasta", "Crema", "Queso", "Champiñones"], "photo-1621996346565-e3dbc646d9a9"),
        ("Arroz con camarones", "Arroz salteado con camarones y pimientos", 38.00, 15.50, 20,
         ["Arroz", "Camarón", "Pimientos", "Cebolla"], "photo-1559847844-5315695dadae"),
        ("Lomo saltado", "Lomo de res salteado con cebolla, tomate, papas y arroz", 34.00, 12.50, 16,
         ["Carne de res", "Cebolla", "Tomate", "Papas", "Arroz", "Aceite"],
         "photo-1600891964092-4316c288032e"),
        ("Papas fritas", "Porción grande de papas crocantes", 12.00, 2.50, 8,
         ["Papas", "Aceite"], "photo-1573080496219-bb080dd4f877"),
    ],
    "Pizzas": [
        ("Pizza margarita", "Tomate, mozzarella y albahaca", 32.00, 9.50, 16,
         ["Harina de trigo", "Salsa de tomate", "Mozzarella", "Albahaca"],
         "photo-1574071318508-1cdbab80d002"),
        ("Pizza pepperoni", "Mozzarella y abundante pepperoni", 36.00, 12.00, 17,
         ["Harina de trigo", "Salsa de tomate", "Mozzarella", "Pepperoni"],
         "photo-1604382354936-07c5d9983bd3"),
        ("Pizza vegetariana", "Champiñones, pimientos y mozzarella", 35.00, 10.50, 17,
         ["Harina de trigo", "Salsa de tomate", "Mozzarella", "Champiñones", "Pimientos"],
         "photo-1565299624946-b28f40a0ae38"),
    ],
    "Postres": [
        ("Brownie con helado", "Brownie tibio con nueces y helado", 16.00, 4.80, 7,
         ["Harina de trigo", "Chocolate", "Huevo", "Nueces", "Helado", "Azúcar"],
         "photo-1606313564200-e75d5e30476c"),
        ("Flan de caramelo", "Flan casero con caramelo", 12.00, 3.30, 3,
         ["Huevo", "Leche", "Azúcar"], "photo-1488477181946-6428a0291777"),
        ("Ensalada de frutas", "Fruta fresca de temporada", 11.00, 3.50, 4, ["Fruta"],
         "photo-1490474418585-ba9bad8fd0ea"),
    ],
    "Bebidas": [
        ("Limonada", "Limonada natural", 8.00, 1.50, 3, ["Limón", "Azúcar", "Agua"],
         "photo-1621263764928-df1444c5e859"),
        ("Jugo natural", "Jugo de fruta del día", 9.00, 2.40, 3, ["Fruta", "Agua"],
         "photo-1600271886742-f049cd451bba"),
        ("Cerveza artesanal", "Botella 330 ml", 14.00, 4.50, 1, ["Cebada", "Agua"],
         "photo-1535958636474-b021ee887b13"),
        ("Café", "Café americano", 7.00, 1.20, 3, ["Café", "Agua"],
         "photo-1495474472287-4d71bcdd2085"),
        ("Gaseosa", "Botella 500 ml", 6.00, 1.50, 1, ["Jarabe de gaseosa", "Agua"],
         "photo-1554866585-cd94860890b7"),
    ],
}

# (usuario, nombre, rol, clave) - claves de DESARROLLO; cambiarlas antes de usar en serio
USUARIOS = [
    ("admin", "Administrador", "admin", "admin123"),
    ("mozo1", "Carlos Quispe", "mozo", "mozo123"),
    ("mozo2", "Lucía Ramos", "mozo", "mozo123"),
    ("cocina1", "Chef Marco", "cocina", "cocina123"),
]


def sembrar_menu() -> bool:
    """Crea categorias, ingredientes y platos. Devuelve False si ya existian."""
    if Categoria.query.first():
        return False

    ingredientes = {}
    for nombre, tipo, gluten, secos, stock, unidad in INGREDIENTES:
        ing = Ingrediente(nombre=nombre, tipo=tipo, tiene_gluten=gluten,
                          tiene_frutos_secos=secos, stock=stock, unidad=unidad,
                          stock_minimo=round(stock * 0.2, 1))
        ingredientes[nombre] = ing
        db.session.add(ing)

    for orden, (cat_nombre, platos) in enumerate(MENU.items()):
        categoria = Categoria(nombre=cat_nombre, orden=orden)
        db.session.add(categoria)
        for nombre, desc, precio, costo, minutos, ings, foto in platos:
            plato = Plato(nombre=nombre, descripcion=desc, precio=precio, costo=costo,
                          tiempo_prep_min=minutos, categoria=categoria, imagen_url=_foto(foto))
            plato.ingredientes = [
                PlatoIngrediente(ingrediente=ingredientes[n], cantidad=0.15) for n in ings
            ]
            db.session.add(plato)
    db.session.commit()
    return True


def sembrar_mesas(cantidad: int = 10) -> int:
    """Crea mesas numeradas (cada una con su token). Devuelve cuantas creo."""
    existentes = {m.numero for m in Mesa.query.all()}
    nuevas = [Mesa(numero=n, capacidad=4 if n % 3 else 6)
              for n in range(1, cantidad + 1) if n not in existentes]
    db.session.add_all(nuevas)
    db.session.commit()
    return len(nuevas)


def sembrar_usuarios() -> int:
    """Crea los usuarios de ejemplo (uno por rol, dos mozos). Devuelve cuantos creo."""
    existentes = {u.username for u in Usuario.query.all()}
    creados = 0
    for username, nombre, rol, clave in USUARIOS:
        if username in existentes:
            continue
        usuario = Usuario(username=username, nombre=nombre, rol=rol)
        usuario.set_password(clave)
        db.session.add(usuario)
        creados += 1
    db.session.commit()
    return creados

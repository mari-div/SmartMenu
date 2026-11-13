"""Comandos de terminal:  flask --app run <comando>"""
import click

from app.extensions import db


def registrar_comandos(app):
    @app.cli.command("init-db")
    def init_db():
        """Crea las tablas en la base de datos."""
        db.create_all()
        click.echo("Tablas creadas.")

    @app.cli.command("reset-db")
    @click.confirmation_option(prompt="Esto BORRA todos los datos. ¿Continuar?")
    def reset_db():
        """Borra y vuelve a crear todas las tablas."""
        db.drop_all()
        db.create_all()
        click.echo("Base de datos reiniciada.")

    @app.cli.command("sembrar")
    @click.option("--mesas", default=10, show_default=True, help="Cantidad de mesas")
    def sembrar(mesas):
        """Carga el menu de ejemplo, las mesas y los usuarios de prueba."""
        from app.seed import sembrar_menu, sembrar_mesas, sembrar_usuarios
        db.create_all()
        click.echo("Menú creado." if sembrar_menu() else "El menú ya existía.")
        click.echo(f"Mesas nuevas: {sembrar_mesas(mesas)}")
        click.echo(f"Usuarios nuevos: {sembrar_usuarios()}  (admin/admin123, mozo1/mozo123, cocina1/cocina123)")

    @app.cli.command("generar-datos")
    @click.option("--dias", default=45, show_default=True)
    @click.option("--semilla", default=42, show_default=True)
    def generar_datos(dias, semilla):
        """Simula un historial de pedidos para el analisis."""
        from analisis.generador import generar_historial
        n = generar_historial(dias=dias, semilla=semilla)
        click.echo(f"Pedidos simulados: {n}")

    @app.cli.command("reporte")
    def reporte():
        """Imprime el analisis y guarda los graficos en docs/graficos."""
        from analisis.reporte import generar_reporte
        generar_reporte(db.engine)

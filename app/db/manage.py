#!/usr/bin/env python
import os
import sys

def main():
    """Punto de entrada principal para ejecutar comandos de Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', './app/db/settings.py')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Está instalado y disponible en tu entorno virtual?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()

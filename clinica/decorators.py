from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def roles_permitidos(*roles):
    def decorador(vista):
        @wraps(vista)
        @login_required
        def protegida(request, *args, **kwargs):
            perfil = getattr(request.user, "perfil", None)
            if perfil is None or perfil.rol not in roles:
                messages.error(request, "No tienes permiso para acceder a esa sección.")
                return redirect("inicio")
            return vista(request, *args, **kwargs)
        return protegida
    return decorador

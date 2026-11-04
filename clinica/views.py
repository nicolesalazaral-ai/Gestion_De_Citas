from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import roles_permitidos
from .forms import CitaForm, EspecialidadForm, HistoriaClinicaForm, HorarioForm, MedicoForm, PacienteForm, UsuarioForm
from .models import Cita, Especialidad, HistoriaClinica, Horario, Medico, Paciente, Perfil, RegistroConsulta

User = get_user_model()
ROLES_CLINICOS = [Perfil.Rol.ADMINISTRADOR, Perfil.Rol.MEDICO]
ROLES_CITAS = [Perfil.Rol.ADMINISTRADOR, Perfil.Rol.RECEPCION, Perfil.Rol.MEDICO, Perfil.Rol.PACIENTE]


def enviar_aviso(cita, asunto, mensaje):
    if cita.paciente.correo:
        send_mail(asunto, mensaje, None, [cita.paciente.correo], fail_silently=True)


def inicio(request):
    if not request.user.is_authenticated:
        return redirect("login")
    perfil = getattr(request.user, "perfil", None)
    if not perfil:
        messages.error(request, "Tu usuario no tiene un perfil asignado. Contacta al administrador.")
        return redirect("login")
    return redirect({
        Perfil.Rol.ADMINISTRADOR: "reportes",
        Perfil.Rol.RECEPCION: "citas",
        Perfil.Rol.MEDICO: "citas",
        Perfil.Rol.PACIENTE: "citas",
    }[perfil.rol])


@roles_permitidos(*ROLES_CITAS)
def lista_citas(request):
    perfil = request.user.perfil
    citas = Cita.objects.select_related("paciente", "medico__usuario", "medico__especialidad")
    if perfil.rol == Perfil.Rol.PACIENTE:
        paciente = get_object_or_404(Paciente, usuario=request.user)
        citas = citas.filter(paciente=paciente)
    elif perfil.rol == Perfil.Rol.MEDICO:
        medico = get_object_or_404(Medico, usuario=request.user)
        citas = citas.filter(medico=medico)
    return render(request, "clinica/citas.html", {"citas": citas, "rol": perfil.rol})


def guardar_cita(request, form, cita=None, reprogramar=False):
    if form.is_valid():
        try:
            with transaction.atomic():
                if reprogramar:
                    cita.estado = Cita.Estado.REPROGRAMADA
                    cita.save(update_fields=["estado"])
                    objeto = Cita(
                        paciente=form.cleaned_data["paciente"],
                        medico=form.cleaned_data["medico"],
                        fecha=form.cleaned_data["fecha"],
                        hora=form.cleaned_data["hora"],
                    )
                else:
                    objeto = form.save(commit=False)
                    objeto.estado = Cita.Estado.PROGRAMADA
                objeto.full_clean()
                objeto.save()
            accion = "reprogramada" if reprogramar else "agendada"
            enviar_aviso(objeto, f"Cita médica {accion}", f"Su cita quedó {accion} para el {objeto.fecha:%d/%m/%Y} a las {objeto.hora:%H:%M}.")
            if cita and reprogramar:
                enviar_aviso(cita, "Cita médica reprogramada", f"Su cita original del {cita.fecha:%d/%m/%Y} fue reprogramada.")
            messages.success(request, f"Cita {accion} correctamente.")
            return redirect("citas")
        except IntegrityError:
            form.add_error(None, "El médico ya tiene una cita en esa fecha y hora.")
        except ValidationError as error:
            form.add_error(None, error)
    return None


@roles_permitidos(Perfil.Rol.ADMINISTRADOR, Perfil.Rol.RECEPCION)
def crear_cita(request):
    form = CitaForm(request.POST or None)
    if request.method == "POST":
        response = guardar_cita(request, form)
        if response:
            return response
    return render(request, "clinica/formulario.html", {"form": form, "titulo": "Agendar cita"})


@roles_permitidos(Perfil.Rol.ADMINISTRADOR, Perfil.Rol.RECEPCION)
def reprogramar_cita(request, cita_id):
    cita = get_object_or_404(Cita, pk=cita_id, estado=Cita.Estado.PROGRAMADA)
    form = CitaForm(request.POST or None, instance=cita)
    if request.method == "POST":
        response = guardar_cita(request, form, cita=cita, reprogramar=True)
        if response:
            return response
    return render(request, "clinica/formulario.html", {"form": form, "titulo": "Reprogramar cita"})


@roles_permitidos(Perfil.Rol.ADMINISTRADOR, Perfil.Rol.RECEPCION)
def cancelar_cita(request, cita_id):
    if request.method == "POST":
        cita = get_object_or_404(Cita, pk=cita_id, estado=Cita.Estado.PROGRAMADA)
        cita.estado = Cita.Estado.CANCELADA
        cita.save(update_fields=["estado"])
        enviar_aviso(cita, "Cita médica cancelada", f"Su cita del {cita.fecha:%d/%m/%Y} a las {cita.hora:%H:%M} fue cancelada.")
        messages.success(request, "Cita cancelada correctamente.")
    return redirect("citas")


@roles_permitidos(Perfil.Rol.ADMINISTRADOR, Perfil.Rol.RECEPCION)
def crear_paciente(request):
    form = PacienteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Paciente registrado correctamente.")
        return redirect("crear_paciente")
    return render(request, "clinica/formulario.html", {"form": form, "titulo": "Registrar paciente"})


@roles_permitidos(*ROLES_CLINICOS)
def lista_historias(request):
    perfil = request.user.perfil
    historias = HistoriaClinica.objects.select_related("paciente", "cita__medico__usuario")
    if perfil.rol == Perfil.Rol.MEDICO:
        historias = historias.filter(cita__medico__usuario=request.user)
    RegistroConsulta.objects.create(usuario=request.user, accion="Abrió el listado de historias clínicas")
    return render(request, "clinica/historias.html", {"historias": historias})


@roles_permitidos(*ROLES_CLINICOS)
def editar_historia(request, cita_id):
    cita = get_object_or_404(
        Cita.objects.select_related("paciente", "medico__usuario"),
        pk=cita_id, estado__in=[Cita.Estado.PROGRAMADA, Cita.Estado.ATENDIDA],
    )
    if request.user.perfil.rol == Perfil.Rol.MEDICO and cita.medico.usuario_id != request.user.id:
        messages.error(request, "Solo puedes consultar historias de tus propios pacientes.")
        return redirect("citas")
    historia = HistoriaClinica.objects.filter(cita=cita).first()
    RegistroConsulta.objects.create(usuario=request.user, accion=f"Abrió la historia clínica de {cita.paciente}")
    form = HistoriaClinicaForm(request.POST or None, instance=historia)
    if request.method == "POST" and form.is_valid():
        objeto = form.save(commit=False)
        objeto.cita = cita
        objeto.paciente = cita.paciente
        objeto.full_clean()
        objeto.save()
        cita.estado = Cita.Estado.ATENDIDA
        cita.save(update_fields=["estado"])
        RegistroConsulta.objects.create(usuario=request.user, accion=f"Modificó la historia clínica de {cita.paciente}")
        messages.success(request, "Consulta registrada correctamente.")
        return redirect("historias")
    return render(request, "clinica/formulario.html", {"form": form, "titulo": f"Historia clínica · {cita.paciente}", "cita": cita})


@roles_permitidos(Perfil.Rol.ADMINISTRADOR)
def usuarios(request):
    form = UsuarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Usuario creado correctamente.")
        return redirect("usuarios")
    lista = User.objects.filter(perfil__rol__in=[Perfil.Rol.ADMINISTRADOR, Perfil.Rol.RECEPCION]).select_related("perfil")
    return render(request, "clinica/usuarios.html", {"form": form, "usuarios": lista})


@roles_permitidos(Perfil.Rol.ADMINISTRADOR)
def medicos(request):
    form = MedicoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Médico creado correctamente.")
        return redirect("medicos")
    lista = Medico.objects.select_related("usuario", "especialidad")
    return render(request, "clinica/medicos.html", {"form": form, "medicos": lista})


@roles_permitidos(Perfil.Rol.ADMINISTRADOR)
def editar_medico(request, medico_id):
    medico = get_object_or_404(Medico.objects.select_related("usuario"), pk=medico_id)
    form = MedicoForm(request.POST or None, instance=medico)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Médico actualizado.")
        return redirect("medicos")
    return render(request, "clinica/formulario.html", {"form": form, "titulo": "Editar médico"})


@roles_permitidos(Perfil.Rol.ADMINISTRADOR)
def eliminar_medico(request, medico_id):
    if request.method == "POST":
        medico = get_object_or_404(Medico, pk=medico_id)
        try:
            with transaction.atomic():
                usuario = medico.usuario
                medico.delete()
                usuario.delete()
            messages.success(request, "Médico eliminado.")
        except IntegrityError:
            messages.error(request, "No se puede eliminar un médico que tiene citas registradas.")
    return redirect("medicos")


@roles_permitidos(Perfil.Rol.ADMINISTRADOR)
def especialidades(request):
    form = EspecialidadForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Especialidad agregada.")
        return redirect("especialidades")
    return render(request, "clinica/especialidades.html", {"form": form, "especialidades": Especialidad.objects.annotate(total_medicos=Count("medicos"))})


@roles_permitidos(Perfil.Rol.ADMINISTRADOR)
def editar_especialidad(request, especialidad_id):
    especialidad = get_object_or_404(Especialidad, pk=especialidad_id)
    form = EspecialidadForm(request.POST or None, instance=especialidad)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Especialidad actualizada.")
        return redirect("especialidades")
    return render(request, "clinica/formulario.html", {"form": form, "titulo": "Editar especialidad"})


@roles_permitidos(Perfil.Rol.ADMINISTRADOR)
def eliminar_especialidad(request, especialidad_id):
    if request.method == "POST":
        especialidad = get_object_or_404(Especialidad, pk=especialidad_id)
        try:
            especialidad.delete()
            messages.success(request, "Especialidad eliminada.")
        except IntegrityError:
            messages.error(request, "No se puede eliminar una especialidad asignada a médicos.")
    return redirect("especialidades")


@roles_permitidos(Perfil.Rol.ADMINISTRADOR)
def horarios(request):
    form = HorarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Horario agregado.")
        return redirect("horarios")
    lista = Horario.objects.select_related("medico__usuario", "medico__especialidad")
    return render(request, "clinica/horarios.html", {"form": form, "horarios": lista})


@roles_permitidos(Perfil.Rol.ADMINISTRADOR)
def editar_horario(request, horario_id):
    horario = get_object_or_404(Horario, pk=horario_id)
    form = HorarioForm(request.POST or None, instance=horario)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Horario actualizado.")
        return redirect("horarios")
    return render(request, "clinica/formulario.html", {"form": form, "titulo": "Editar horario"})


@roles_permitidos(Perfil.Rol.ADMINISTRADOR)
def eliminar_horario(request, horario_id):
    if request.method == "POST":
        get_object_or_404(Horario, pk=horario_id).delete()
        messages.success(request, "Horario eliminado.")
    return redirect("horarios")


@roles_permitidos(Perfil.Rol.ADMINISTRADOR)
def reportes(request):
    por_medico = Medico.objects.select_related("usuario", "especialidad").annotate(
        total_citas=Count("citas"), atendidas=Count("citas", filter=Q(citas__estado=Cita.Estado.ATENDIDA)),
    )
    ausencias = Cita.objects.filter(fecha__lt=timezone.localdate(), estado=Cita.Estado.PROGRAMADA).select_related(
        "paciente", "medico__usuario",
    )
    registros = RegistroConsulta.objects.select_related("usuario")[:30]
    return render(request, "clinica/reportes.html", {"por_medico": por_medico, "ausencias": ausencias, "registros": registros})

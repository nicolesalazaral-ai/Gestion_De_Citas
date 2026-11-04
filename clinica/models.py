from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Perfil(models.Model):
    class Rol(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        RECEPCION = "recepcion", "Recepción"
        MEDICO = "medico", "Médico"
        PACIENTE = "paciente", "Paciente"

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    rol = models.CharField(max_length=20, choices=Rol.choices)

    def __str__(self):
        return f"{self.usuario.username} ({self.get_rol_display()})"


class Paciente(models.Model):
    documento = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=30)
    correo = models.EmailField(blank=True)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="paciente",
    )

    def __str__(self):
        return f"{self.nombre} ({self.documento})"


class Especialidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "especialidades"

    def __str__(self):
        return self.nombre


class Horario(models.Model):
    class Dia(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    medico = models.ForeignKey("Medico", on_delete=models.CASCADE, related_name="horarios")
    dia_semana = models.IntegerField(choices=Dia.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        ordering = ["dia_semana", "hora_inicio"]
        constraints = [
            models.UniqueConstraint(fields=["medico", "dia_semana", "hora_inicio"], name="horario_medico_unico"),
        ]

    def clean(self):
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError("La hora de fin debe ser posterior a la hora de inicio.")

    def __str__(self):
        return f"{self.medico} · {self.get_dia_semana_display()} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}"


class Medico(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="medico")
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT, related_name="medicos")

    class Meta:
        ordering = ["usuario__last_name", "usuario__first_name"]

    def __str__(self):
        nombre = self.usuario.get_full_name() or self.usuario.username
        return f"Dr./Dra. {nombre} · {self.especialidad}"


class Cita(models.Model):
    class Estado(models.TextChoices):
        PROGRAMADA = "programada", "Programada"
        CANCELADA = "cancelada", "Cancelada"
        REPROGRAMADA = "reprogramada", "Reprogramada"
        ATENDIDA = "atendida", "Atendida"

    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name="citas")
    medico = models.ForeignKey(Medico, on_delete=models.PROTECT, related_name="citas")
    fecha = models.DateField()
    hora = models.TimeField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PROGRAMADA)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "hora"]
        constraints = [
            models.UniqueConstraint(
                fields=["medico", "fecha", "hora"],
                condition=models.Q(estado__in=["programada", "atendida"]),
                name="cita_medico_fecha_hora_activa_unica",
            ),
        ]

    def clean(self):
        if self.estado in (self.Estado.PROGRAMADA, self.Estado.ATENDIDA):
            existe = Cita.objects.filter(
                medico=self.medico, fecha=self.fecha, hora=self.hora,
                estado__in=[self.Estado.PROGRAMADA, self.Estado.ATENDIDA],
            ).exclude(pk=self.pk).exists()
            if existe:
                raise ValidationError("El médico ya tiene una cita en esa fecha y hora.")

    def __str__(self):
        return f"{self.paciente} · {self.fecha} {self.hora:%H:%M}"


class HistoriaClinica(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name="historias")
    cita = models.OneToOneField(Cita, on_delete=models.PROTECT, related_name="historia")
    motivo = models.TextField()
    diagnostico = models.TextField()
    tratamiento = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name_plural = "historias clínicas"

    def clean(self):
        if self.cita_id and self.paciente_id and self.cita.paciente_id != self.paciente_id:
            raise ValidationError("La cita debe pertenecer al paciente de la historia.")

    def __str__(self):
        return f"Consulta de {self.paciente} · {self.fecha:%d/%m/%Y}"


class RegistroConsulta(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="registros_clinicos")
    accion = models.CharField(max_length=200)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_hora"]

    def __str__(self):
        return f"{self.usuario} · {self.accion} · {self.fecha_hora:%d/%m/%Y %H:%M}"

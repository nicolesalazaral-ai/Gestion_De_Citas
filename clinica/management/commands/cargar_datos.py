from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from clinica.models import Cita, Especialidad, Horario, Medico, Paciente, Perfil

User = get_user_model()


class Command(BaseCommand):
    help = "Crea usuarios, pacientes, médicos y citas de demostración."

    def handle(self, *args, **options):
        admin = self.crear_usuario("admin", "admin12345", "Ana", "Administradora", Perfil.Rol.ADMINISTRADOR, "admin@clinica.local")
        self.crear_usuario("recepcion", "recepcion123", "Rosa", "Recepción", Perfil.Rol.RECEPCION, "recepcion@clinica.local")

        cardiologia, _ = Especialidad.objects.get_or_create(nombre="Cardiología", defaults={"descripcion": "Salud cardiovascular"})
        pediatria, _ = Especialidad.objects.get_or_create(nombre="Pediatría", defaults={"descripcion": "Atención infantil"})
        medico1 = self.crear_medico("medico1", "medico123", "Carlos", "Soto", "carlos@clinica.local", cardiologia)
        medico2 = self.crear_medico("medico2", "medico123", "Elena", "Ríos", "elena@clinica.local", pediatria)

        usuarios_pacientes = [
            ("paciente1", "paciente123", "María López", "P-1001", "555-0101", "maria@correo.local"),
            (None, None, "José Hernández", "P-1002", "555-0102", "jose@correo.local"),
            (None, None, "Lucía García", "P-1003", "555-0103", "lucia@correo.local"),
        ]
        pacientes = []
        for username, password, nombre, documento, telefono, correo in usuarios_pacientes:
            usuario = None
            if username:
                usuario = self.crear_usuario(username, password, nombre.split()[0], " ".join(nombre.split()[1:]), Perfil.Rol.PACIENTE, correo)
            paciente, _ = Paciente.objects.update_or_create(
                documento=documento,
                defaults={"nombre": nombre, "telefono": telefono, "correo": correo, "usuario": usuario},
            )
            pacientes.append(paciente)

        hoy = date.today()
        citas_demo = [
            (pacientes[0], medico1, hoy + timedelta(days=1), time(9, 0)),
            (pacientes[1], medico2, hoy + timedelta(days=2), time(10, 0)),
            (pacientes[2], medico1, hoy - timedelta(days=2), time(11, 0)),
            (pacientes[0], medico2, hoy + timedelta(days=4), time(12, 0)),
        ]
        for paciente, medico, fecha, hora in citas_demo:
            Cita.objects.get_or_create(
                paciente=paciente, medico=medico, fecha=fecha, hora=hora,
                defaults={"estado": Cita.Estado.PROGRAMADA},
            )
        for medico in (medico1, medico2):
            Horario.objects.get_or_create(
                medico=medico, dia_semana=hoy.weekday(), hora_inicio=time(8, 0),
                defaults={"hora_fin": time(16, 0)},
            )

        self.stdout.write(self.style.SUCCESS("Datos de prueba cargados correctamente."))
        self.stdout.write("Usuarios: admin/admin12345, recepcion/recepcion123, medico1/medico123, medico2/medico123, paciente1/paciente123")

    def crear_usuario(self, username, password, first_name, last_name, rol, email):
        usuario, creado = User.objects.get_or_create(
            username=username,
            defaults={"first_name": first_name, "last_name": last_name, "email": email},
        )
        if creado:
            usuario.set_password(password)
            usuario.save()
        else:
            usuario.first_name = first_name
            usuario.last_name = last_name
            usuario.email = email
            usuario.save()
        perfil, _ = Perfil.objects.get_or_create(usuario=usuario, defaults={"rol": rol})
        if perfil.rol != rol:
            perfil.rol = rol
            perfil.save(update_fields=["rol"])
        return usuario

    def crear_medico(self, username, password, first_name, last_name, email, especialidad):
        usuario = self.crear_usuario(username, password, first_name, last_name, Perfil.Rol.MEDICO, email)
        medico, _ = Medico.objects.update_or_create(usuario=usuario, defaults={"especialidad": especialidad})
        return medico

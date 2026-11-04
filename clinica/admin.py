from django.contrib import admin

from .models import Cita, Especialidad, HistoriaClinica, Horario, Medico, Paciente, Perfil, RegistroConsulta

admin.site.register([Perfil, Paciente, Especialidad, Medico, Horario, Cita, HistoriaClinica, RegistroConsulta])

from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("citas/", views.lista_citas, name="citas"),
    path("citas/nueva/", views.crear_cita, name="crear_cita"),
    path("citas/<int:cita_id>/cancelar/", views.cancelar_cita, name="cancelar_cita"),
    path("citas/<int:cita_id>/reprogramar/", views.reprogramar_cita, name="reprogramar_cita"),
    path("pacientes/nuevo/", views.crear_paciente, name="crear_paciente"),
    path("historias/", views.lista_historias, name="historias"),
    path("historias/cita/<int:cita_id>/", views.editar_historia, name="editar_historia"),
    path("administracion/usuarios/", views.usuarios, name="usuarios"),
    path("administracion/medicos/", views.medicos, name="medicos"),
    path("administracion/medicos/<int:medico_id>/editar/", views.editar_medico, name="editar_medico"),
    path("administracion/medicos/<int:medico_id>/eliminar/", views.eliminar_medico, name="eliminar_medico"),
    path("administracion/especialidades/", views.especialidades, name="especialidades"),
    path("administracion/especialidades/<int:especialidad_id>/editar/", views.editar_especialidad, name="editar_especialidad"),
    path("administracion/especialidades/<int:especialidad_id>/eliminar/", views.eliminar_especialidad, name="eliminar_especialidad"),
    path("administracion/horarios/", views.horarios, name="horarios"),
    path("administracion/horarios/<int:horario_id>/editar/", views.editar_horario, name="editar_horario"),
    path("administracion/horarios/<int:horario_id>/eliminar/", views.eliminar_horario, name="eliminar_horario"),
    path("administracion/reportes/", views.reportes, name="reportes"),
]

# Sistema de gestión de citas médicas y expedientes clínicos

Aplicación web universitaria construida con Python, Django 5, SQLite y plantillas HTML. La interfaz utiliza Bootstrap 5 e íconos por CDN. Los correos de notificación se muestran en la consola.

## Ejecutar en Windows

Desde esta carpeta, en PowerShell:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py cargar_datos
python manage.py runserver
```

Abre <http://127.0.0.1:8000/>. La sesión se cierra tras 15 minutos sin actividad.

## Usuarios de prueba

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | `admin` | `admin12345` |
| Recepción | `recepcion` | `recepcion123` |
| Médico (Cardiología) | `medico1` | `medico123` |
| Médico (Pediatría) | `medico2` | `medico123` |
| Paciente | `paciente1` | `paciente123` |

El comando `cargar_datos` puede ejecutarse nuevamente sin duplicar los datos de demostración.

## Pruebas manuales

1. Inicia sesión como recepción y registra un paciente nuevo.
2. Agenda dos citas para el mismo médico, fecha y hora; la segunda debe rechazarse.
3. Reprograma una cita y confirma que se conserva el historial de la cita anterior.
4. Cancela una cita y revisa el aviso de correo en la consola.
5. Inicia sesión como médico y abre una cita propia para registrar motivo, diagnóstico y tratamiento.
6. Comprueba que el médico puede ver el registro de historias y que recepción no puede abrir esas páginas.
7. Inicia sesión como paciente y confirma que solo ve sus propias citas; intenta abrir una página administrativa.
8. Cierra sesión, vuelve atrás o abre una página protegida y confirma que se solicita iniciar sesión.

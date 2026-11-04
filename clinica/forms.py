from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Cita, Especialidad, HistoriaClinica, Horario, Medico, Paciente, Perfil

User = get_user_model()


class EstiloFormulario(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.Select):
                campo.widget.attrs["class"] = "form-select"
            else:
                campo.widget.attrs["class"] = "form-control"


class CitaForm(EstiloFormulario):
    class Meta:
        model = Cita
        fields = ["paciente", "medico", "fecha", "hora"]
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"}), "hora": forms.TimeInput(attrs={"type": "time"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["medico"].queryset = Medico.objects.select_related("usuario", "especialidad")


class PacienteForm(EstiloFormulario):
    class Meta:
        model = Paciente
        fields = ["documento", "nombre", "telefono", "correo"]


class HistoriaClinicaForm(EstiloFormulario):
    class Meta:
        model = HistoriaClinica
        fields = ["motivo", "diagnostico", "tratamiento"]
        widgets = {
            "motivo": forms.Textarea(attrs={"rows": 3}),
            "diagnostico": forms.Textarea(attrs={"rows": 3}),
            "tratamiento": forms.Textarea(attrs={"rows": 3}),
        }


class EspecialidadForm(EstiloFormulario):
    class Meta:
        model = Especialidad
        fields = ["nombre", "descripcion"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 2})}


class MedicoForm(forms.Form):
    username = forms.CharField(label="Usuario", max_length=150)
    first_name = forms.CharField(label="Nombre", max_length=150)
    last_name = forms.CharField(label="Apellido", max_length=150)
    email = forms.EmailField(label="Correo")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput, required=False)
    especialidad = forms.ModelChoiceField(label="Especialidad", queryset=Especialidad.objects.all())

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "form-select" if isinstance(campo, forms.Select) else "form-control"
        if instance:
            self.fields["username"].initial = instance.usuario.username
            self.fields["first_name"].initial = instance.usuario.first_name
            self.fields["last_name"].initial = instance.usuario.last_name
            self.fields["email"].initial = instance.usuario.email
            self.fields["especialidad"].initial = instance.especialidad
            self.fields["password"].help_text = "Deja en blanco para conservar la contraseña."

    def clean_username(self):
        username = self.cleaned_data["username"]
        usuarios = User.objects.filter(username=username)
        if self.instance:
            usuarios = usuarios.exclude(pk=self.instance.usuario_id)
        if usuarios.exists():
            raise forms.ValidationError("Ese nombre de usuario ya está registrado.")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.instance and not password:
            raise forms.ValidationError("La contraseña es obligatoria al crear un médico.")
        return password

    def save(self):
        datos = self.cleaned_data
        if self.instance:
            usuario = self.instance.usuario
            usuario.username = datos["username"]
            usuario.first_name = datos["first_name"]
            usuario.last_name = datos["last_name"]
            usuario.email = datos["email"]
            if datos["password"]:
                usuario.set_password(datos["password"])
            usuario.save()
            medico = self.instance
            medico.especialidad = datos["especialidad"]
            medico.save()
        else:
            usuario = User.objects.create_user(
                username=datos["username"], password=datos["password"], email=datos["email"],
                first_name=datos["first_name"], last_name=datos["last_name"],
            )
            usuario.perfil.rol = Perfil.Rol.MEDICO
            usuario.perfil.save()
            medico = Medico.objects.create(usuario=usuario, especialidad=datos["especialidad"])
        return medico


class HorarioForm(EstiloFormulario):
    class Meta:
        model = Horario
        fields = ["medico", "dia_semana", "hora_inicio", "hora_fin"]
        widgets = {"hora_inicio": forms.TimeInput(attrs={"type": "time"}), "hora_fin": forms.TimeInput(attrs={"type": "time"})}

    def clean(self):
        datos = super().clean()
        inicio, fin = datos.get("hora_inicio"), datos.get("hora_fin")
        if inicio and fin and fin <= inicio:
            self.add_error("hora_fin", "La hora de fin debe ser posterior al inicio.")
        return datos


class UsuarioForm(forms.Form):
    username = forms.CharField(label="Usuario", max_length=150)
    first_name = forms.CharField(label="Nombre", max_length=150)
    last_name = forms.CharField(label="Apellido", max_length=150, required=False)
    email = forms.EmailField(label="Correo", required=False)
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    rol = forms.ChoiceField(label="Rol", choices=[(Perfil.Rol.ADMINISTRADOR, "Administrador"), (Perfil.Rol.RECEPCION, "Recepción")])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "form-control" if not isinstance(campo.widget, forms.Select) else "form-select"

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ese nombre de usuario ya está registrado.")
        return username

    def save(self):
        datos = self.cleaned_data
        usuario = User.objects.create_user(
            username=datos["username"], password=datos["password"], first_name=datos["first_name"],
            last_name=datos["last_name"], email=datos["email"],
        )
        usuario.perfil.rol = datos["rol"]
        usuario.perfil.save()
        return usuario

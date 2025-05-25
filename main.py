from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import os
from collections import defaultdict
from datetime import datetime, timedelta
from flask import make_response
import pdfkit
from flask import jsonify
from werkzeug.utils import secure_filename
from flask_login import LoginManager
from flask_login import login_user
from flask_login import login_user, current_user
from flask_login import login_required
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import logout_user
from flask_login import current_user
from functools import wraps
from flask import redirect, flash
from flask import Flask, render_template, request, redirect, flash
from datetime import datetime, timedelta


def requiere_suscripcion(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.en_periodo_prueba():
            flash("🚫 Tu suscripción ha expirado. Renueva para seguir usando la app.")
            return redirect("/pago")
        return f(*args, **kwargs)
    return decorated_function



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///peluqueria.db'
app.secret_key = "tu_clave_secreta"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/fotos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def archivo_permitido(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Ruta absoluta al ejecutable wkhtmltopdf
PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=os.environ.get("WKHTMLTOPDF_PATH", "/usr/bin/wkhtmltopdf"))



db = SQLAlchemy(app)

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    fecha_alta = db.Column(db.Date, default=datetime.utcnow)
    subscripcion_id = db.Column(db.String(100), nullable=True)  # Asegúrate de incluir esto si estás usando suscripciones

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def en_periodo_prueba(self):
        return datetime.utcnow().date() <= self.fecha_alta + timedelta(days=30)
    
login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# MODELOS
class Mascota(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    tamano = db.Column(db.String(20)) 
    raza = db.Column(db.String(100))
    fecha_nacimiento = db.Column(db.Date, nullable=True)
    duenio = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    caracter = db.Column(db.Text)
    tipo_corte = db.Column(db.String(100))
    precio = db.Column(db.Float)  # Precio estándar por cita
    foto_antes = db.Column(db.String(200), nullable=True)
    foto_despues = db.Column(db.String(200), nullable=True)
    
    # ✅ relación con usuario
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    usuario = db.relationship("Usuario", backref="mascotas")


class Cita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mascota_id = db.Column(db.Integer, db.ForeignKey('mascota.id'))
    fecha = db.Column(db.Date)
    hora = db.Column(db.Time)
    tamano = db.Column(db.String(10))
    duracion = db.Column(db.Integer)
    notas = db.Column(db.Text)
    precio = db.Column(db.Float)  # Precio cobrado esa vez
    metodo_pago = db.Column(db.String(20), nullable=True)  # "efectivo", "tarjeta", etc.

    # ✅ relaciones
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    usuario = db.relationship("Usuario", backref="citas")
    mascota = db.relationship("Mascota", backref="citas")

# RUTAS
from flask_login import current_user

@app.route("/")
def inicio():
    if current_user.is_authenticated:
        return redirect("/dashboard")  # ✅ Ya está logueado → dashboard
    return render_template("index.html")  # Portada con video


@app.route("/registrar", methods=["GET", "POST"])
def registrar():
    if request.method == "POST":
        # 📸 Obtener archivos de imagen
        foto_antes = request.files.get("foto_antes")
        foto_despues = request.files.get("foto_despues")

        filename_antes = None
        filename_despues = None

        if foto_antes and archivo_permitido(foto_antes.filename):
            filename_antes = secure_filename(foto_antes.filename)
            foto_antes.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_antes))

        if foto_despues and archivo_permitido(foto_despues.filename):
            filename_despues = secure_filename(foto_despues.filename)
            foto_despues.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_despues))

        # 📅 Convertir fecha opcional
        fecha = request.form.get("edad")
        fecha_nacimiento = datetime.strptime(fecha, "%Y-%m-%d").date() if fecha else None

        # ✅ Crear nueva mascota
        nueva_mascota = Mascota(
            nombre=request.form["nombre"],
            tamano=request.form["tamano"],
            raza=request.form["raza"],
            fecha_nacimiento=fecha_nacimiento,
            duenio=request.form["duenio"],
            telefono=request.form["telefono"],
            caracter=request.form["caracter"],
            tipo_corte=request.form["tipo_corte"],
            precio=request.form.get("precio") or 0,
            foto_antes=filename_antes,
            foto_despues=filename_despues,
            user_id=current_user.id
        )

        db.session.add(nueva_mascota)
        db.session.commit()
        return redirect("/")
    return render_template("registrar.html",
        nombre=request.args.get("nombre", ""),
        telefono=request.args.get("telefono", ""),
        raza=request.args.get("raza", ""),
        tamano=request.args.get("tamano", "")
    )  
@app.route("/mascotas")
@login_required
@requiere_suscripcion
def ver_mascotas():
    q = request.args.get("q")
    if q:
        mascotas = Mascota.query.filter(
            (Mascota.nombre.ilike(f"%{q}%")) | (Mascota.telefono.ilike(f"%{q}%"))
        ).all()
    else:
          mascotas = Mascota.query.filter_by(user_id=current_user.id).all()
    return render_template("mascotas.html", mascotas=mascotas)

@app.route("/buscar-mascota", methods=["GET", "POST"])
def buscar_mascota():
    if request.method == "POST":
        nombre = request.form["nombre"].strip().lower()
        mascota = Mascota.query.filter(db.func.lower(Mascota.nombre) == nombre).first()
        if mascota:
            return redirect(f"/ficha/{mascota.id}")
        else:
            return redirect(f"/registrar?nombre={nombre}")
    return render_template("buscar_mascota.html")

@app.route("/cita", methods=["GET", "POST"])
def agendar_cita():
    if request.method == "POST":
        nombre_input = request.form["nombre_mascota"].strip().lower()
        mascota = Mascota.query.filter(db.func.lower(Mascota.nombre) == nombre_input).first()

        if not mascota:
            return redirect(f"/registrar?nombre={nombre_input}&telefono={request.form.get('telefono', '')}&raza={request.form.get('raza', '')}&tamano={request.form.get('tamano', '')}")

        # Obtener los datos del formulario
        fecha = datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()
        hora = datetime.strptime(request.form["hora"], "%H:%M").time()
        tamano = request.form["tamano"]
        notas = request.form["notas"]
        metodo_pago = request.form.get("metodo_pago")
        precio = request.form.get("precio")

        try:
            precio = float(precio.replace(",", ".")) if precio else 0.0
        except ValueError:
            precio = 0.0

        # Determinar duración según el tamaño
        if tamano == "pequeno":
            duracion = 60
        elif tamano == "mediano":
            duracion = 75
        elif tamano == "grande":
            duracion = 90
        else:
            duracion = 60  # Por defecto

        hora_inicio = datetime.combine(fecha, hora)
        hora_fin = hora_inicio + timedelta(minutes=duracion)

        # Verificar solapamiento de citas existentes
        citas = Cita.query.filter_by(fecha=fecha).all()
        for c in citas:
            c_inicio = datetime.combine(c.fecha, c.hora)
            c_fin = c_inicio + timedelta(minutes=c.duracion)
            if hora_inicio < c_fin and hora_fin > c_inicio:
                return "❌ Ya hay una cita en ese horario."

        # Guardar nueva cita
        nueva_cita = Cita(
            mascota_id=mascota.id,
            fecha=fecha,
            hora=hora,
            tamano=tamano,
            duracion=duracion,
            notas=notas,
            metodo_pago=metodo_pago,
            precio=precio,
            user_id=current_user.id
        )
        db.session.add(nueva_cita)
        db.session.commit()

        return redirect("/agenda")


    # GET (mostrar formulario con fecha y hora si vienen en la URL)
    fecha = request.args.get("fecha", "")
    hora = request.args.get("hora", "")
    return render_template("agendar_cita.html", fecha=fecha, hora=hora)




def generar_horarios(base_hora, fin_hora, paso_min=30):
    horarios = []
    actual = datetime.combine(datetime.today(), base_hora)
    fin = datetime.combine(datetime.today(), fin_hora)

    while actual <= fin:
        horarios.append(actual.time())
        actual += timedelta(minutes=paso_min)
    return horarios

def dia_semana_espanol(fecha):
    dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
    return dias[fecha.weekday()]



@app.route("/agenda")
@login_required
@requiere_suscripcion
def ver_agenda():
    dias_mostrar = 7
    hoy = datetime.today().date()
    
    # Excluir domingos
    dias_agenda = [
        hoy + timedelta(days=i)
        for i in range(dias_mostrar)
        if (hoy + timedelta(days=i)).weekday() != 6
    ]

    citas = Cita.query.filter_by(user_id=current_user.id).order_by(Cita.fecha, Cita.hora)

    # Agrupar citas por fecha
    citas_por_fecha = defaultdict(list)
    for cita in citas:
        citas_por_fecha[cita.fecha].append(cita)

    agenda_completa = []

    for dia in dias_agenda:
        bloques_dia = []

        if dia.weekday() == 5:  # Sábado
            bloques_dia = generar_bloques(
                dia,
                datetime.strptime("10:00", "%H:%M").time(),
                datetime.strptime("12:00", "%H:%M").time(),
                citas_por_fecha
            )
        else:  # Lunes a viernes
            bloques_manana = generar_bloques(
                dia,
                datetime.strptime("10:00", "%H:%M").time(),
                datetime.strptime("12:00", "%H:%M").time(),
                citas_por_fecha
            )
            bloques_tarde = generar_bloques(
                dia,
                datetime.strptime("17:00", "%H:%M").time(),
                datetime.strptime("19:30", "%H:%M").time(),
                citas_por_fecha
            )
            bloques_dia = bloques_manana + bloques_tarde

        agenda_completa.append((dia, dia_semana_espanol(dia), bloques_dia))

    return render_template("agenda.html", agenda=agenda_completa)

def generar_bloques(dia, hora_inicio, hora_fin, citas_por_fecha, paso_min=30):
    bloques = []
    hora_actual = datetime.combine(dia, hora_inicio)
    fin = datetime.combine(dia, hora_fin)
    citas_dia = citas_por_fecha.get(dia, [])
    ocupados = []

    for cita in citas_dia:
        inicio = datetime.combine(dia, cita.hora)
        fin_cita = inicio + timedelta(minutes=cita.duracion)
        ocupados.append((inicio, fin_cita, cita))

    while hora_actual < fin:
        bloque_ocupado = False

        for inicio, fin_cita, cita in ocupados:
            if inicio == hora_actual:
                if cita.metodo_pago == "efectivo":
                    icono_pago = "💵"
                elif cita.metodo_pago == "tarjeta":
                    icono_pago = "💳"
                else:
                    icono_pago = "❓"

                bloques.append({
                    "hora": hora_actual.strftime("%H:%M"),
                    "texto": f"{hora_actual.strftime('%H:%M')} - OCUPADO: {cita.mascota.nombre} ({cita.tamano}) {icono_pago}",
                    "enlace": None,
                    "cita_id": cita.id
                })
                hora_actual = fin_cita
                bloque_ocupado = True
                break

        if not bloque_ocupado:
            bloques.append({
                "hora": hora_actual.strftime("%H:%M"),
                "texto": f"{hora_actual.strftime('%H:%M')} - Libre",
                "enlace": f"/cita?fecha={dia}&hora={hora_actual.strftime('%H:%M')}",
                "cita_id": None
            })
            hora_actual += timedelta(minutes=paso_min)

    return bloques


@app.route("/anular_cita/<int:cita_id>", methods=["POST"])
def anular_cita(cita_id):
    cita = Cita.query.get_or_404(cita_id)
    db.session.delete(cita)
    db.session.commit()
    return redirect("/agenda")

@app.route("/editar_cita/<int:cita_id>", methods=["GET", "POST"])
def editar_cita(cita_id):
    cita = Cita.query.get_or_404(cita_id)

    if request.method == "POST":
        cita.precio = float(request.form["precio"])
        cita.notas = request.form.get("notas")
        db.session.commit()
        return redirect(f"/ficha/{cita.mascota.id}")

    return render_template("editar_cita.html", cita=cita)
@app.route("/ficha_pdf/<int:mascota_id>")
def ficha_pdf(mascota_id):
    mascota = Mascota.query.get_or_404(mascota_id)
    rendered = render_template("ficha_pdf.html", mascota=mascota)

    pdf = pdfkit.from_string(rendered, False, configuration=PDFKIT_CONFIG)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=ficha_{mascota.nombre}.pdf'
    return response
@app.route("/editar/<int:mascota_id>", methods=["GET", "POST"])
def editar_mascota(mascota_id):
    mascota = Mascota.query.get_or_404(mascota_id)

    if request.method == "POST":
        mascota.nombre = request.form["nombre"]
        mascota.raza = request.form["raza"]
        mascota.duenio = request.form["duenio"]
        mascota.telefono = request.form["telefono"]
        mascota.caracter = request.form["caracter"]
        mascota.tipo_corte = request.form["tipo_corte"]
        mascota.precio = request.form.get("precio") or 0

        fecha = request.form.get("edad")
        mascota.fecha_nacimiento = datetime.strptime(fecha, "%Y-%m-%d").date() if fecha else None

        db.session.commit()
        return redirect(f"/ficha/{mascota.id}")

    return render_template("editar_mascota.html", mascota=mascota)

@app.route("/arqueo")
def arqueo():
    hoy = datetime.today().date()
    citas_hoy = Cita.query.filter_by(fecha=hoy).all()

    total_efectivo = sum(c.precio for c in citas_hoy if c.metodo_pago == "efectivo")
    total_tarjeta = sum(c.precio for c in citas_hoy if c.metodo_pago == "tarjeta")
    total = total_efectivo + total_tarjeta

    return render_template("arqueo.html", total_efectivo=total_efectivo, total_tarjeta=total_tarjeta, total=total, hoy=hoy)



@app.route("/api/mascota")
def api_mascota():
    nombre = request.args.get("nombre", "").strip().lower()
    mascota = Mascota.query.filter(db.func.lower(Mascota.nombre) == nombre).first()

    if mascota:
        return {
            "tamano": mascota.tamano,
            "telefono": mascota.telefono
        }
    return jsonify({})
@app.route("/api/mascotas_sugerencia")
def mascotas_sugerencia():
    nombre = request.args.get("nombre", "").strip().lower()
    mascotas = Mascota.query.filter(Mascota.nombre.ilike(f"{nombre}%")).all()
    return jsonify([
        {
            "id": m.id,
            "nombre": m.nombre,
            "telefono": m.telefono,
            "raza": m.raza,
            "tamano": m.tamano
        }
        for m in mascotas
    ])
@app.route("/ficha/<int:mascota_id>", methods=["GET", "POST"])
@login_required
@requiere_suscripcion
def ficha_mascota(mascota_id):
    mascota = Mascota.query.get_or_404(mascota_id)

    if mascota.user_id != current_user.id:
        return "⛔ Acceso no autorizado", 403

    if request.method == "POST":
        mascota.raza = request.form["raza"]
        mascota.duenio = request.form["duenio"]
        mascota.telefono = request.form["telefono"]
        mascota.caracter = request.form["caracter"]
        mascota.tipo_corte = request.form["tipo_corte"]
        db.session.commit()


        # Manejo de fotos
        foto_antes = request.files.get("foto_antes")
        foto_despues = request.files.get("foto_despues")

        if foto_antes and foto_antes.filename:
            filename_antes = secure_filename(foto_antes.filename)
            foto_antes.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_antes))
            mascota.foto_antes = filename_antes

        if foto_despues and foto_despues.filename:
            filename_despues = secure_filename(foto_despues.filename)
            foto_despues.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_despues))
            mascota.foto_despues = filename_despues

        db.session.commit()
        return redirect(f"/ficha/{mascota_id}")

    return render_template("ficha_mascota.html", mascota=mascota)
@app.route("/arqueo/pdf")
def arqueo_pdf():
    hoy = datetime.today().date()
    citas_hoy = Cita.query.filter_by(fecha=hoy).all()

    total_efectivo = sum(c.precio for c in citas_hoy if c.metodo_pago == "efectivo")
    total_tarjeta = sum(c.precio for c in citas_hoy if c.metodo_pago == "tarjeta")
    total = total_efectivo + total_tarjeta

    html = render_template("arqueo_pdf.html", hoy=hoy, citas=citas_hoy,
                           total_efectivo=total_efectivo, total_tarjeta=total_tarjeta, total=total)

    pdf = pdfkit.from_string(html, False, configuration=PDFKIT_CONFIG)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=arqueo.pdf'
    return response

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre_usuario"]
        email = request.form["email"]
        password = request.form["password"]

        # Verificar si el nombre de usuario o email ya existen
        if Usuario.query.filter((Usuario.nombre_usuario == nombre) | (Usuario.email == email)).first():
            flash("⚠️ El usuario o email ya está registrado.")
            return redirect("/registro")

        nuevo = Usuario(nombre_usuario=nombre, email=email)
        nuevo.set_password(password)
        db.session.add(nuevo)
        db.session.commit()
        login_user(nuevo)
        return redirect("/agenda")
    
    return render_template("registro.html")

from flask import flash

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre = request.form["nombre_usuario"]
        password = request.form["password"]
        user = Usuario.query.filter_by(nombre_usuario=nombre).first()

        if not user or not user.check_password(password):
            flash("❌ Usuario o contraseña incorrectos")
            return redirect("/login")

        if not user.en_periodo_prueba():
            flash("⚠️ Tu periodo de prueba ha caducado. Por favor, activa tu cuenta.")
            return redirect("/pago")

        login_user(user)
        return redirect("/dashboard")

    return render_template("login.html")


@app.route("/pago")
def pago():
    return render_template("pago.html")

from flask_login import login_required, current_user



@app.route("/logout")
@login_required
@requiere_suscripcion
def logout():
    logout_user()
    return redirect("/")


@app.route("/dashboard")
@login_required
@requiere_suscripcion
def agenda():
    dias_mostrar = 7
    hoy = datetime.today().date()
    
    # Excluir domingos
    dias_agenda = [
        hoy + timedelta(days=i)
        for i in range(dias_mostrar)
        if (hoy + timedelta(days=i)).weekday() != 6
    ]

    citas = Cita.query.filter_by(user_id=current_user.id).order_by(Cita.fecha, Cita.hora).all()

    citas_por_fecha = defaultdict(list)
    for cita in citas:
        citas_por_fecha[cita.fecha].append(cita)

    agenda_completa = []
    for dia in dias_agenda:
        if dia.weekday() == 5:  # Sábado
            bloques_dia = generar_bloques(
                dia,
                datetime.strptime("10:00", "%H:%M").time(),
                datetime.strptime("12:00", "%H:%M").time(),
                citas_por_fecha
            )
        else:
            bloques_manana = generar_bloques(
                dia,
                datetime.strptime("10:00", "%H:%M").time(),
                datetime.strptime("14:00", "%H:%M").time(),
                citas_por_fecha
            )
            bloques_tarde = generar_bloques(
                dia,
                datetime.strptime("17:00", "%H:%M").time(),
                datetime.strptime("20:30", "%H:%M").time(),
                citas_por_fecha
            )
            bloques_dia = bloques_manana + bloques_tarde

        agenda_completa.append((dia, dia_semana_espanol(dia), bloques_dia))

    # 🕒 Fecha fin de prueba para el contador
    fecha_fin_prueba = current_user.fecha_alta + timedelta(days=30)

    return render_template(
        "dashboard.html",
        agenda=agenda_completa,
        fecha_fin_prueba=fecha_fin_prueba.isoformat()
    )

@app.route("/agenda")
@login_required
@requiere_suscripcion
def agenda():
    dias_mostrar = 7
    hoy = datetime.today().date()
    
    # Excluir domingos
    dias_agenda = [
        hoy + timedelta(days=i)
        for i in range(dias_mostrar)
        if (hoy + timedelta(days=i)).weekday() != 6
    ]

    citas = Cita.query.filter_by(user_id=current_user.id).order_by(Cita.fecha, Cita.hora).all()

    citas_por_fecha = defaultdict(list)
    for cita in citas:
        citas_por_fecha[cita.fecha].append(cita)

    agenda_completa = []
    for dia in dias_agenda:
        if dia.weekday() == 5:  # Sábado
            bloques_dia = generar_bloques(
                dia,
                datetime.strptime("10:00", "%H:%M").time(),
                datetime.strptime("12:00", "%H:%M").time(),
                citas_por_fecha
            )
        else:
            bloques_manana = generar_bloques(
                dia,
                datetime.strptime("10:00", "%H:%M").time(),
                datetime.strptime("14:00", "%H:%M").time(),
                citas_por_fecha
            )
            bloques_tarde = generar_bloques(
                dia,
                datetime.strptime("17:00", "%H:%M").time(),
                datetime.strptime("20:30", "%H:%M").time(),
                citas_por_fecha
            )
            bloques_dia = bloques_manana + bloques_tarde

        agenda_completa.append((dia, dia_semana_espanol(dia), bloques_dia))

    # 🕒 Fecha fin de prueba para el contador
    fecha_fin_prueba = current_user.fecha_alta + timedelta(days=30)

    return render_template(
        "agenda.html",
        agenda=agenda_completa,
        fecha_fin_prueba=fecha_fin_prueba.isoformat()
    )




@app.route("/actualizar_pago/<int:cita_id>", methods=["POST"])
@login_required
def actualizar_pago(cita_id):
    cita = Cita.query.get_or_404(cita_id)

    metodo_pago = request.form.get("metodo_pago")
    precio = request.form.get("precio")

    if metodo_pago:
        cita.metodo_pago = metodo_pago

    if precio:
        try:
            cita.precio = float(precio)
        except ValueError:
            pass  # Puedes mostrar un error si prefieres

    db.session.commit()
    return redirect("/agenda")

@app.route("/suscripcion_exitosa")
@login_required
def suscripcion_exitosa():
    sub_id = request.args.get("sub_id")
    current_user.subscripcion_id = sub_id
    current_user.fecha_suscripcion = datetime.utcnow().date()
    db.session.commit()
    flash("✅ Suscripción activada con éxito.")
    return redirect("/dashboard")




# INICIO APP
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))


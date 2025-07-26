from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import os
import requests
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
from datetime import datetime, timedelta, timezone
import smtplib
from itsdangerous import URLSafeTimedSerializer
from flask import url_for
from sqlalchemy import text
from flask_migrate import Migrate




def requiere_suscripcion(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.en_periodo_prueba():
            flash("🚫 Tu suscripción ha expirado. Renueva para seguir usando la app.")
            return redirect("/pago")
        return f(*args, **kwargs)
    return decorated_function



app = Flask(__name__, static_folder='static', static_url_path='')

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://tpv_peluqueria_db_user:D368Z6HYZEuiyYZamD7rZrNhBhtLXdsh@dpg-d1mloiu3jp1c73dr6smg-a.oregon-postgres.render.com/tpv_peluqueria_db'
app.secret_key = "tu_clave_secreta"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/fotos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def archivo_permitido(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Ruta absoluta al ejecutable wkhtmltopdf
PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=os.environ.get("WKHTMLTOPDF_PATH", "/usr/bin/wkhtmltopdf"))
#PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")



db = SQLAlchemy(app)
try:
    with app.app_context():
        print("✅ Probando conexión a la base de datos...")
        db.session.execute(text("SELECT 1"))
        print("✅ Conexión exitosa")
except Exception as e:
    print("❌ Error de conexión a la base de datos:", e)

login_manager = LoginManager(app)
login_manager.login_view = "login"

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(300), nullable=False)
    fecha_alta = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    subscripcion_id = db.Column(db.String(100), nullable=True)
    nombre_empresa = db.Column(db.String(150))
    cif = db.Column(db.String(20))
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.String(200))
    codigo_postal = db.Column(db.String(10))
    token_recuperacion = db.Column(db.String(200), nullable=True)
    cortes_ocultos = db.relationship("CorteOculto", backref="usuario", lazy=True)
    cortes_personales = db.relationship("CorteRaza", backref="usuario", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)



    def en_periodo_prueba(self):
        ahora = datetime.now(timezone.utc)

        if self.fecha_alta.tzinfo is None:
            fecha_alta = self.fecha_alta.replace(tzinfo=timezone.utc)
        else:
            fecha_alta = self.fecha_alta

        return ahora <= fecha_alta + timedelta(days=30)

     #return False  # Fuerza a que siempre termine el periodo de prueba


import smtplib
from email.mime.text import MIMEText

def enviar_email(destinatario, asunto, contenido_html):
    remitente = "techinclusiondigital@gmail.com"
    password = "mbgo lqoh fjha xbdu"  # Generada en tu cuenta Gmail (contraseña de aplicación)

    msg = MIMEText(contenido_html, "html")
    msg["Subject"] = asunto
    msg["From"] = remitente
    msg["To"] = destinatario

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())


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
    tipo_servicio = db.Column(db.String(100))  # baño, corte, etc
    precio = db.Column(db.Float)  # Precio estándar por cita
    foto_antes = db.Column(db.String(200), nullable=True)
    foto_despues = db.Column(db.String(200), nullable=True)
    
    # ✅ relación con usuario
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    usuario = db.relationship("Usuario", backref="mascotas")


class Cita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    duracion = db.Column(db.Integer, default=60)  # en minutos
    tipo_servicio = db.Column(db.String(100))  # baño, corte, etc.
    precio = db.Column(db.Float)
    metodo_pago = db.Column(db.String(20))
    notas = db.Column(db.Text)
    mascota_id = db.Column(db.Integer, db.ForeignKey("mascota.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    tamano = db.Column(db.String(20))
    mascota = db.relationship("Mascota", backref="citas")



    # ✅ relaciones
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    usuario = db.relationship("Usuario", backref="citas")
    mascota = db.relationship("Mascota", backref="citas")

class CorteRaza(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_raza = db.Column(db.String(100), nullable=False)
    imagen_url = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    es_publico = db.Column(db.Boolean, default=False)
    cortes_ocultos = db.relationship("CorteOculto", backref="corte", cascade="all, delete-orphan")
    orden = db.Column(db.Integer, default=0)


class CorteOculto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    corte_id = db.Column(db.Integer, db.ForeignKey('corte_raza.id'))


class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    comprado = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))  # si quieres que cada usuario tenga los suyos

class OrdenCorte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    corte_id = db.Column(db.Integer, db.ForeignKey("corte_raza.id"))
    posicion = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint("usuario_id", "corte_id", name="unique_user_corte"),)


# RUTAS
from flask_login import current_user

@app.route("/")
def inicio():
    if current_user.is_authenticated:
        return redirect("/dashboard")  # ✅ Ya está logueado → dashboard
    return render_template("index.html")  # Portada con video


@app.route("/registrar", methods=["GET", "POST"])
@login_required
def registrar():
    if request.method == "POST":
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

        fecha = request.form.get("edad")
        fecha_nacimiento = datetime.strptime(fecha, "%Y-%m-%d").date() if fecha else None

        nueva_mascota = Mascota(
            nombre=request.form["nombre"],
            tamano=request.form["tamano"],
            raza=request.form["raza"],
            fecha_nacimiento=fecha_nacimiento,
            duenio=request.form["duenio"],
            telefono=request.form["telefono"],
            caracter=request.form["caracter"],
            precio=request.form.get("precio") or 0,
            foto_antes=filename_antes,
            foto_despues=filename_despues,
            

            user_id=current_user.id
        )

        db.session.add(nueva_mascota)
        db.session.commit()

        datos_cita = session.pop("datos_cita_pendiente", None)
        if datos_cita:
            try:
                fecha_dt = datetime.strptime(datos_cita["fecha"], "%Y-%m-%d").date()
                hora_dt = datetime.strptime(datos_cita["hora"], "%H:%M").time()
                duracion = int(datos_cita.get("duracion", 60))
                tipo_servicio = datos_cita.get("tipo_servicio", "")
                metodo_pago = datos_cita.get("metodo_pago", "")
                precio = float(datos_cita.get("precio", 0) or 0.0)
                notas = datos_cita.get("notas", "")
                tamano = datos_cita.get("tamano", nueva_mascota.tamano)

                nueva_cita = Cita(
                    mascota_id=nueva_mascota.id,
                    fecha=fecha_dt,
                    hora=hora_dt,
                    duracion=duracion,
                    tipo_servicio=tipo_servicio,
                    metodo_pago=metodo_pago,
                    precio=precio,
                    notas=notas,
                    user_id=current_user.id,
                    tamano=tamano
                )
                db.session.add(nueva_cita)
                db.session.commit()
            except Exception as e:
                print(f"❌ Error al crear cita automática: {e}")

        return redirect("/dashboard")
    RAZAS = [
        "Affenpinscher", "Akita Inu", "Alaskan Malamute", "American Bully", "American Staffordshire Terrier",
        "Basenji", "Basset Hound", "Beagle", "Bearded Collie", "Bedlington Terrier", "Bichón Frisé", "Bichón Maltés",
        "Bloodhound", "Bobtail", "Bóxer", "Boston Terrier", "Border Collie", "Borzoi", "Braco Alemán", "Braco de Weimar",
        "Bulldog Francés", "Bulldog Inglés", "Bullmastiff", "Cairn Terrier", "Caniche (Poodle)", "Caniche Toy",
        "Cane Corso", "Cavalier King Charles Spaniel", "Chihuahua", "Chow Chow", "Cocker Americano", "Cocker Spaniel Inglés",
        "Collie", "Dálmata", "Doberman", "Dogo Argentino", "Dogo de Burdeos", "Dogue Alemán (Gran Danés)", "Fox Terrier",
        "Galgo Español", "Golden Retriever", "Gos d’Atura Català", "Gran Pirineo", "Husky Siberiano", "Jack Russell Terrier",
        "Labrador Retriever", "Lhasa Apso", "Maltés", "Mastín Español", "Mastín Napolitano", "Papillón", "Pastor Alemán",
        "Pastor Australiano", "Pastor Belga", "Pastor Blanco Suizo", "Pekinés", "Perro de Agua Español", "Pinscher Miniatura",
        "Pitbull", "Podenco Ibicenco", "Pointer", "Pomerania", "Presa Canario", "Pug (Carlino)", "Rottweiler", "Samoyedo",
        "San Bernardo", "Schnauzer", "Scottish Terrier", "Setter Irlandés", "Shar Pei", "Shiba Inu", "Shih Tzu",
        "Staffordshire Bull Terrier", "Teckel (Dachshund)", "Terranova", "Vizsla", "Weimaraner", "Welsh Corgi", "West Highland White Terrier",
        "Whippet", "Yorkshire Terrier",
        "Gato común", "Gato abisinio", "Gato angora turco", "Gato azul ruso", "Gato balinés", "Gato bengalí", "Gato bombay",
        "Gato bosque de Noruega", "Gato británico de pelo corto", "Gato burmés", "Gato cartujo (Chartreux)", "Gato cornish rex",
        "Gato devon rex", "Gato egipcio mau", "Gato esfinge (Sphynx)", "Gato exótico de pelo corto", "Gato habana brown",
        "Gato himalayo", "Gato japonés bobtail", "Gato laPerm", "Gato maine coon", "Gato manx", "Gato munchkin",
        "Gato oriental de pelo corto", "Gato persa", "Gato ragdoll", "Gato savannah", "Gato siamés", "Gato siberiano",
        "Gato singapura", "Gato somalí", "Gato tonquinés", "Gato turco van"
    ]
    datos = session.get("datos_cita_pendiente", {})
    return render_template("registrar.html",
    nombre=request.args.get("nombre", ""),
    telefono=datos.get("telefono", ""),
    raza=datos.get("raza", ""),
    tamano=datos.get("tamano", ""),
    duenio=datos.get("duenio", ""),
    fecha=datos.get("fecha", ""),
    hora=datos.get("hora", ""),
    notas=datos.get("notas", ""),
    metodo_pago=datos.get("metodo_pago", ""),
    precio=datos.get("precio", ""),
    tipo_servicio=datos.get("tipo_servicio", ""),
    RAZAS=RAZAS
)

@app.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        email = request.form["email"]
        user = Usuario.query.filter_by(email=email).first()
        if user:
            s = URLSafeTimedSerializer(app.secret_key)
            token = s.dumps(user.email, salt="recuperar-clave")
            user.token_recuperacion = token
            db.session.commit()

            enlace = url_for("reset_password", token=token, _external=True)
            cuerpo = f"""
            <h3>Restablecer contraseña</h3>
            <p>Haz clic en el siguiente enlace para restablecer tu contraseña:</p>
            <a href="{enlace}">Restablecer contraseña</a>
            """
            enviar_email(user.email, "Recuperación de contraseña - Petshappy", cuerpo)
            flash("📧 Se ha enviado un enlace de recuperación a tu correo.")
        else:
            flash("❌ No se encontró un usuario con ese correo.")
        return redirect("/login")

    return render_template("recuperar.html")

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    s = URLSafeTimedSerializer(app.secret_key)
    try:
        email = s.loads(token, salt="recuperar-clave", max_age=3600)
    except Exception:
        flash("⚠️ El enlace ha expirado o es inválido.")
        return redirect("/login")

    user = Usuario.query.filter_by(email=email).first()

    if request.method == "POST":
        nueva = request.form["password"]
        user.set_password(nueva)
        user.token_recuperacion = None
        db.session.commit()
        flash("✅ Contraseña actualizada correctamente.")
        return redirect("/login")

    return render_template("reset_password.html")


import smtplib
from email.mime.text import MIMEText

def enviar_email(destinatario, asunto, contenido_html):
    remitente = "techinclusiondigital@gmail.com"
    password = "mbgo lqoh fjha xbdu"  # usa una contraseña de aplicación

    msg = MIMEText(contenido_html, "html")
    msg["Subject"] = asunto
    msg["From"] = remitente
    msg["To"] = destinatario

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())

@app.route("/politica")
def politica():
    return render_template("politica.html", ocultar_menu=True)

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
        mascota = Mascota.query.filter(
    db.func.lower(Mascota.nombre) == nombre,
    Mascota.user_id == current_user.id
).first()


        if mascota:
            return redirect(f"/ficha/{mascota.id}")
        else:
            return redirect(f"/registrar?nombre={nombre}")
    return render_template("buscar_mascota.html")

from flask import session
@app.route("/cita", methods=["GET", "POST"])
@login_required
def agendar_cita():
    if request.method == "POST":
        nombre_input = request.form["nombre_mascota"].strip().lower()

        mascota = Mascota.query.filter(
            db.func.lower(Mascota.nombre) == nombre_input,
            Mascota.user_id == current_user.id
        ).first()

        if not mascota:
            # ✅ Guardar los datos de la cita temporalmente en sesión
            session["datos_cita_pendiente"] = {
                "fecha": request.form.get("fecha"),
                "hora": request.form.get("hora"),
                "duracion": request.form.get("duracion"),
                "tipo_servicio": request.form.get("tipo_servicio"),
                "precio": request.form.get("precio"),
                "metodo_pago": request.form.get("metodo_pago"),
                "notas": request.form.get("notas"),
                "tamano": request.form.get("tamano"),
                "telefono": request.form.get("telefono"),
                "raza": request.form.get("raza"),
                "duenio": request.form.get("duenio"),

            }
            return redirect(url_for("registrar", nombre=request.form.get("nombre_mascota")))

        # Mascota existe: crear cita normalmente
        fecha = datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()
        hora = datetime.strptime(request.form["hora"], "%H:%M").time()
        tamano = request.form["tamano"]
        notas = request.form["notas"]
        metodo_pago = request.form.get("metodo_pago")
        tipo_servicio = request.form.get("tipo_servicio")
        precio = request.form.get("precio")

        try:
            precio = float(precio.replace(",", ".")) if precio else 0.0
        except ValueError:
            precio = 0.0

        duracion = int(request.form.get("duracion", 60))

        nueva_cita = Cita(
            mascota_id=mascota.id,
            fecha=fecha,
            hora=hora,
            duracion=duracion,
            notas=notas,
            tipo_servicio=tipo_servicio,
            metodo_pago=metodo_pago,
            precio=precio,
            user_id=current_user.id,
            tamano=tamano
        )
        db.session.add(nueva_cita)
        db.session.commit()

        return redirect("/dashboard")

    # GET: mostrar el formulario
    fecha = request.args.get("fecha", "")
    hora = request.args.get("hora", "")
    nombre = request.args.get("nombre", "")
    telefono = request.args.get("telefono", "")
    raza = request.args.get("raza", "")
    tamano = request.args.get("tamano", "")
    tipo_servicio = request.args.get("tipo_servicio", "")

    return render_template(
        "agendar_cita.html",
        nombre=nombre,
        telefono=telefono,
        raza=raza,
        tamano=tamano,
        tipo_servicio=tipo_servicio,
        fecha=fecha,
        hora=hora
    )







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

@app.route("/pedidos", methods=["GET", "POST"])
@login_required
def pedidos():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        if nombre:
            nuevo = Pedido(nombre=nombre, user_id=current_user.id)
            db.session.add(nuevo)
            db.session.commit()
        return redirect("/pedidos")

    lista = Pedido.query.filter_by(user_id=current_user.id).order_by(Pedido.comprado, Pedido.nombre).all()
    return render_template("pedidos.html", pedidos=lista)

@app.route("/pedido/<int:id>/toggle", methods=["POST"])
@login_required
def marcar_comprado(id):
    pedido = Pedido.query.get_or_404(id)
    pedido.comprado = not pedido.comprado
    db.session.commit()
    return redirect("/pedidos")

@app.route("/pedido/<int:id>/eliminar", methods=["POST"])
@login_required
def eliminar_pedido(id):
    pedido = Pedido.query.get_or_404(id)
    db.session.delete(pedido)
    db.session.commit()
    return redirect("/pedidos")



@app.route("/cortes")
@login_required
def galeria_cortes():
    raza_seleccionada = request.args.get("raza")
    ocultos_ids = [o.corte_id for o in current_user.cortes_ocultos]

    # Query base: cortes visibles para el usuario
    cortes_query = CorteRaza.query.filter(
        ((CorteRaza.es_publico == True) & (~CorteRaza.id.in_(ocultos_ids))) |
        (CorteRaza.user_id == current_user.id)
    )

    # Filtrar por raza si se ha seleccionado
    if raza_seleccionada:
        cortes_query = cortes_query.filter(CorteRaza.nombre_raza == raza_seleccionada)

    cortes = cortes_query.all()

    # Obtener orden personalizado del usuario (si existe)
    orden_usuario = {
        orden.corte_id: orden.posicion
        for orden in OrdenCorte.query.filter_by(usuario_id=current_user.id).all()
    }

    # Ordenar según el orden guardado, los no encontrados van al final
    cortes.sort(key=lambda c: orden_usuario.get(c.id, 9999))

    # Cortes ocultos por usuario y raza
    cortes_ocultos = CorteRaza.query.join(CorteOculto).filter(
        CorteOculto.usuario_id == current_user.id
    )
    if raza_seleccionada:
        cortes_ocultos = cortes_ocultos.filter(CorteRaza.nombre_raza == raza_seleccionada)
    cortes_ocultos = cortes_ocultos.all()

    RAZAS = [
        "Affenpinscher", "Akita Inu", "Alaskan Malamute", "American Bully", "American Staffordshire Terrier",
        "Basenji", "Basset Hound", "Beagle", "Bearded Collie", "Bedlington Terrier", "Bichón Frisé", "Bichón Maltés",
        "Bloodhound", "Bobtail", "Bóxer", "Boston Terrier", "Border Collie", "Borzoi", "Braco Alemán", "Braco de Weimar",
        "Bulldog Francés", "Bulldog Inglés", "Bullmastiff", "Cairn Terrier", "Caniche (Poodle)", "Caniche Toy",
        "Cane Corso", "Cavalier King Charles Spaniel", "Chihuahua", "Chow Chow", "Cocker Americano", "Cocker Spaniel Inglés",
        "Collie", "Dálmata", "Doberman", "Dogo Argentino", "Dogo de Burdeos", "Dogue Alemán (Gran Danés)", "Fox Terrier",
        "Galgo Español", "Golden Retriever", "Gos d’Atura Català", "Gran Pirineo", "Husky Siberiano", "Jack Russell Terrier",
        "Labrador Retriever", "Lhasa Apso", "Maltés", "Mastín Español", "Mastín Napolitano", "Papillón", "Pastor Alemán",
        "Pastor Australiano", "Pastor Belga", "Pastor Blanco Suizo", "Pekinés", "Perro de Agua Español", "Pinscher Miniatura",
        "Pitbull", "Podenco Ibicenco", "Pointer", "Pomerania", "Presa Canario", "Pug (Carlino)", "Rottweiler", "Samoyedo",
        "San Bernardo", "Schnauzer", "Scottish Terrier", "Setter Irlandés", "Shar Pei", "Shiba Inu", "Shih Tzu",
        "Staffordshire Bull Terrier", "Teckel (Dachshund)", "Terranova", "Vizsla", "Weimaraner", "Welsh Corgi", "West Highland White Terrier",
        "Whippet", "Yorkshire Terrier",
        "Gato común", "Gato abisinio", "Gato angora turco", "Gato azul ruso", "Gato balinés", "Gato bengalí", "Gato bombay",
        "Gato bosque de Noruega", "Gato británico de pelo corto", "Gato burmés", "Gato cartujo (Chartreux)", "Gato cornish rex",
        "Gato devon rex", "Gato egipcio mau", "Gato esfinge (Sphynx)", "Gato exótico de pelo corto", "Gato habana brown",
        "Gato himalayo", "Gato japonés bobtail", "Gato laPerm", "Gato maine coon", "Gato manx", "Gato munchkin",
        "Gato oriental de pelo corto", "Gato persa", "Gato ragdoll", "Gato savannah", "Gato siamés", "Gato siberiano",
        "Gato singapura", "Gato somalí", "Gato tonquinés", "Gato turco van"
    ]

    return render_template("galeria_cortes.html",
                           cortes=cortes,
                           cortes_ocultos=cortes_ocultos,
                           razas=RAZAS,
                           raza_seleccionada=raza_seleccionada)


import os
from werkzeug.utils import secure_filename

@app.route("/admin/subir-corte", methods=["GET", "POST"])
@login_required
def subir_corte_admin():
    if current_user.email != "techinclusiondigital@gmail.com":
        abort(403)  # Solo el administrador puede subir fotos públicas

    RAZAS = [ "Affenpinscher", "Akita Inu", "Alaskan Malamute", "American Bully", "American Staffordshire Terrier",
    "Basenji", "Basset Hound", "Beagle", "Bearded Collie", "Bedlington Terrier", "Bichón Frisé", "Bichón Maltés",
    "Bloodhound", "Bobtail", "Bóxer", "Boston Terrier", "Border Collie", "Borzoi", "Braco Alemán", "Braco de Weimar",
    "Bulldog Francés", "Bulldog Inglés", "Bullmastiff", "Cairn Terrier", "Caniche (Poodle)", "Caniche Toy",
    "Cane Corso", "Cavalier King Charles Spaniel", "Chihuahua", "Chow Chow", "Cocker Americano", "Cocker Spaniel Inglés",
    "Collie", "Dálmata", "Doberman", "Dogo Argentino", "Dogo de Burdeos", "Dogue Alemán (Gran Danés)", "Fox Terrier",
    "Galgo Español", "Golden Retriever", "Gos d’Atura Català", "Gran Pirineo", "Husky Siberiano", "Jack Russell Terrier",
    "Labrador Retriever", "Lhasa Apso", "Maltés", "Mastín Español", "Mastín Napolitano", "Papillón", "Pastor Alemán",
    "Pastor Australiano", "Pastor Belga", "Pastor Blanco Suizo", "Pekinés", "Perro de Agua Español", "Pinscher Miniatura",
    "Pitbull", "Podenco Ibicenco", "Pointer", "Pomerania", "Presa Canario", "Pug (Carlino)", "Rottweiler", "Samoyedo",
    "San Bernardo", "Schnauzer", "Scottish Terrier", "Setter Irlandés", "Shar Pei", "Shiba Inu", "Shih Tzu",
    "Staffordshire Bull Terrier", "Teckel (Dachshund)", "Terranova", "Vizsla", "Weimaraner", "Welsh Corgi", "West Highland White Terrier",
    "Whippet", "Yorkshire Terrier",
    "Gato común", "Gato abisinio", "Gato angora turco", "Gato azul ruso", "Gato balinés", "Gato bengalí", "Gato bombay",
    "Gato bosque de Noruega", "Gato británico de pelo corto", "Gato burmés", "Gato cartujo (Chartreux)", "Gato cornish rex",
    "Gato devon rex", "Gato egipcio mau", "Gato esfinge (Sphynx)", "Gato exótico de pelo corto", "Gato habana brown",
    "Gato himalayo", "Gato japonés bobtail", "Gato laPerm", "Gato maine coon", "Gato manx", "Gato munchkin",
    "Gato oriental de pelo corto", "Gato persa", "Gato ragdoll", "Gato savannah", "Gato siamés", "Gato siberiano",
    "Gato singapura", "Gato somalí", "Gato tonquinés", "Gato turco van"]  # Pega aquí tu lista de razas

    if request.method == "POST":
        raza = request.form.get("raza")
        imagen = request.files.get("imagen")

        if imagen:
            filename = secure_filename(imagen.filename)
            ruta = os.path.join("static", "uploads", filename)
            imagen.save(ruta)

            nuevo_corte = CorteRaza(
                nombre_raza=raza,
                imagen_url=filename,  # guardamos solo el nombre
                es_publico=True
            )
            db.session.add(nuevo_corte)
            db.session.commit()
            flash("✅ Corte público subido correctamente.")
            return redirect("/admin/subir-corte")


    # 👇 obtenemos cortes públicos para mostrarlos
    cortes_publicos = CorteRaza.query.filter_by(es_publico=True).all()

    return render_template("admin_subir_corte.html", razas=RAZAS, cortes_publicos=cortes_publicos)



@app.route("/admin/corte/<int:corte_id>/eliminar", methods=["POST"])
@login_required
def eliminar_corte_publico(corte_id):
    if current_user.email != "techinclusiondigital@gmail.com":
        abort(403)

    corte = CorteRaza.query.get_or_404(corte_id)

    # Borrar archivo físico
    if corte.imagen_url:
       ruta_imagen = os.path.join(app.root_path, "static", "uploads", corte.imagen_url)

    if os.path.exists(ruta_imagen):
            os.remove(ruta_imagen)

    # Eliminar de la base de datos
    db.session.delete(corte)
    db.session.commit()
    flash("🗑 Corte eliminado correctamente.")
    return redirect("/admin/subir-corte")





@app.route("/ocultar_corte/<int:corte_id>", methods=["POST"])
@login_required
def ocultar_corte(corte_id):
    corte = CorteRaza.query.get_or_404(corte_id)

    # Asegura que la imagen es pública y no es del usuario
    if corte.es_publico is not True or corte.user_id == current_user.id:
        abort(403)

    # Verificar si ya está oculto
    ya_oculto = CorteOculto.query.filter_by(usuario_id=current_user.id, corte_id=corte_id).first()
    if not ya_oculto:
        oculto = CorteOculto(usuario_id=current_user.id, corte_id=corte_id)
        db.session.add(oculto)
        db.session.commit()

    flash("🔒 Imagen oculta correctamente.")

    # Redirigir con la raza original del corte
    return redirect(f"/cortes?raza={corte.nombre_raza}")

@app.route("/mostrar_corte/<int:corte_id>", methods=["POST"])
@login_required
def mostrar_corte(corte_id):
    corte_oculto = CorteOculto.query.filter_by(usuario_id=current_user.id, corte_id=corte_id).first()
    if corte_oculto:
        db.session.delete(corte_oculto)
        db.session.commit()
        flash("✅ Imagen visible nuevamente.")

    raza = request.form.get("raza")
    if raza:
        return redirect(f"/cortes?raza={raza}")
    return redirect("/cortes")



@app.route("/guardar_orden_cortes", methods=["POST"])
@login_required
def guardar_orden_cortes():
    data = request.get_json()
    orden_ids = data.get("orden", [])

    for idx, corte_id in enumerate(orden_ids):
        corte_id = int(corte_id)
        orden = OrdenCorte.query.filter_by(usuario_id=current_user.id, corte_id=corte_id).first()

        if orden:
            orden.posicion = idx
        else:
            nueva_orden = OrdenCorte(usuario_id=current_user.id, corte_id=corte_id, posicion=idx)
            db.session.add(nueva_orden)

    db.session.commit()
    return jsonify({"mensaje": "Orden guardado correctamente"})


@app.route("/cortes_ocultos")
@login_required
def ver_cortes_ocultos():
    ocultos = CorteOculto.query.filter_by(usuario_id=current_user.id).all()
    cortes_ocultos = [CorteRaza.query.get(oculto.corte_id) for oculto in ocultos]

    return render_template("cortes_ocultos.html", cortes_ocultos=cortes_ocultos)



@app.route("/subir_corte", methods=["POST"])
@login_required
def subir_corte():
    archivo = request.files.get("imagen")
    nombre_raza = request.form.get("nombre_raza")

    if archivo and nombre_raza:
        filename = secure_filename(archivo.filename)
        ruta = os.path.join(app.root_path, "static", "uploads", filename)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        archivo.save(ruta)

        nuevo = CorteRaza(
            nombre_raza=nombre_raza,
            imagen_url=filename,  # o imagen=filename si tu modelo lo usa así
            user_id=current_user.id,
            es_publico=False
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("✅ Corte subido correctamente.")
        return redirect(f"/cortes?raza={nombre_raza}")
    
    flash("❌ Debes seleccionar una imagen y una raza.")
    return redirect("/cortes")

@app.route("/subir_corte_formulario", methods=["GET"])
@login_required
def formulario_subir_corte():
    RAZAS = ["Affenpinscher", "Akita Inu", "Alaskan Malamute", "American Bully", "American Staffordshire Terrier",
    "Basenji", "Basset Hound", "Beagle", "Bearded Collie", "Bedlington Terrier", "Bichón Frisé", "Bichón Maltés",
    "Bloodhound", "Bobtail", "Bóxer", "Boston Terrier", "Border Collie", "Borzoi", "Braco Alemán", "Braco de Weimar",
    "Bulldog Francés", "Bulldog Inglés", "Bullmastiff", "Cairn Terrier", "Caniche (Poodle)", "Caniche Toy",
    "Cane Corso", "Cavalier King Charles Spaniel", "Chihuahua", "Chow Chow", "Cocker Americano", "Cocker Spaniel Inglés",
    "Collie", "Dálmata", "Doberman", "Dogo Argentino", "Dogo de Burdeos", "Dogue Alemán (Gran Danés)", "Fox Terrier",
    "Galgo Español", "Golden Retriever", "Gos d’Atura Català", "Gran Pirineo", "Husky Siberiano", "Jack Russell Terrier",
    "Labrador Retriever", "Lhasa Apso", "Maltés", "Mastín Español", "Mastín Napolitano", "Papillón", "Pastor Alemán",
    "Pastor Australiano", "Pastor Belga", "Pastor Blanco Suizo", "Pekinés", "Perro de Agua Español", "Pinscher Miniatura",
    "Pitbull", "Podenco Ibicenco", "Pointer", "Pomerania", "Presa Canario", "Pug (Carlino)", "Rottweiler", "Samoyedo",
    "San Bernardo", "Schnauzer", "Scottish Terrier", "Setter Irlandés", "Shar Pei", "Shiba Inu", "Shih Tzu",
    "Staffordshire Bull Terrier", "Teckel (Dachshund)", "Terranova", "Vizsla", "Weimaraner", "Welsh Corgi", "West Highland White Terrier",
    "Whippet", "Yorkshire Terrier",
    "Gato común", "Gato abisinio", "Gato angora turco", "Gato azul ruso", "Gato balinés", "Gato bengalí", "Gato bombay",
    "Gato bosque de Noruega", "Gato británico de pelo corto", "Gato burmés", "Gato cartujo (Chartreux)", "Gato cornish rex",
    "Gato devon rex", "Gato egipcio mau", "Gato esfinge (Sphynx)", "Gato exótico de pelo corto", "Gato habana brown",
    "Gato himalayo", "Gato japonés bobtail", "Gato laPerm", "Gato maine coon", "Gato manx", "Gato munchkin",
    "Gato oriental de pelo corto", "Gato persa", "Gato ragdoll", "Gato savannah", "Gato siamés", "Gato siberiano",
    "Gato singapura", "Gato somalí", "Gato tonquinés", "Gato turco van" ]  # tu lista de razas
    raza_seleccionada = request.args.get("raza")
    return render_template("formulario_subir_corte.html", razas=RAZAS, raza_seleccionada=raza_seleccionada)

@app.route("/corte_usuario/<int:corte_id>/eliminar", methods=["POST"])
@login_required
def eliminar_corte_usuario(corte_id):
    corte = CorteRaza.query.get_or_404(corte_id)

    # Asegúrate de que el corte pertenece al usuario
    if corte.user_id != current_user.id:
        abort(403)

    # Borrar archivo físico
    if corte.imagen_url:
        ruta = os.path.join(app.root_path, "static", "uploads_cortes", corte.imagen_url)
        if os.path.exists(ruta):
            os.remove(ruta)

    db.session.delete(corte)
    db.session.commit()
    flash("🗑 Imagen eliminada correctamente.")
    return redirect(f"/cortes?raza={corte.nombre_raza}")




RECAPTCHA_SECRET_KEY = "6LfjNX0rAAAAAHnB0abPdA9WOZoyFT-e6wW0xJlu"

@app.route("/contacto", methods=["POST"])
def contacto():
    # Verificación reCAPTCHA
    captcha_respuesta = request.form.get("g-recaptcha-response")
    if not captcha_respuesta:
        flash("❌ Verifica que no eres un robot.")
        return redirect("/")

    validacion = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={
            "secret": RECAPTCHA_SECRET_KEY,
            "response": captcha_respuesta
        }
    ).json()

    if not validacion.get("success"):
        flash("❌ reCAPTCHA no válido. Inténtalo de nuevo.")
        return redirect("/")

    # Si pasó reCAPTCHA, procesamos mensaje
    nombre = request.form["nombre"]
    email = request.form["email"]
    mensaje = request.form["mensaje"]

    contenido = f"""
    <h3>📩 Nuevo mensaje desde el formulario de contacto</h3>
    <p><strong>Nombre:</strong> {nombre}</p>
    <p><strong>Email:</strong> {email}</p>
    <p><strong>Mensaje:</strong><br>{mensaje}</p>
    """
    enviar_email("techinclusiondigital@gmail.com", "📬 Nuevo mensaje de contacto", contenido)

    flash("✅ ¡Mensaje enviado correctamente!")
    return redirect("/")



@app.route("/agenda")
@login_required
@requiere_suscripcion
def redirigir_agenda():
    return redirect("/dashboard")

@app.route("/mascota/<int:id>")
@login_required
def ver_mascota(id):
    mascota = Mascota.query.get_or_404(id)
    return render_template("ficha_mascota.html", mascota=mascota)



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
@login_required
@requiere_suscripcion
def arqueo():
    fecha_str = request.args.get("fecha")
    
    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            flash("⚠️ Fecha inválida.")
            return redirect("/arqueo")
    else:
        fecha = datetime.today().date()

    citas = Cita.query.filter_by(fecha=fecha, user_id=current_user.id).all()

    total_efectivo = sum(c.precio for c in citas if c.metodo_pago == "efectivo")
    total_tarjeta = sum(c.precio for c in citas if c.metodo_pago == "tarjeta")
    total = total_efectivo + total_tarjeta

    return render_template("arqueo.html", 
        total_efectivo=total_efectivo,
        total_tarjeta=total_tarjeta,
        total=total,
        hoy=fecha
    )



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
@login_required
def mascotas_sugerencia():
    nombre = request.args.get("nombre", "").strip().lower()
    mascotas = Mascota.query.filter(
        db.func.lower(Mascota.nombre).ilike(f"{nombre}%"),
        Mascota.user_id == current_user.id
    ).all()

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



RECAPTCHA_SECRET_KEY = "6LfjNX0rAAAAAHnB0abPdA9WOZoyFT-e6wW0xJlu"

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        # Validación de reCAPTCHA
        captcha_respuesta = request.form.get("g-recaptcha-response")
        if not captcha_respuesta:
            flash("❌ Verifica que no eres un robot.")
            return redirect("/registro")

        validacion = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": RECAPTCHA_SECRET_KEY,
                "response": captcha_respuesta
            }
        ).json()

        if not validacion.get("success"):
            flash("❌ reCAPTCHA no válido. Inténtalo de nuevo.")
            return redirect("/registro")

        try:
            # Datos del formulario
            nombre = request.form["nombre_usuario"]
            email = request.form["email"]
            password = request.form["password"]
            nombre_empresa = request.form["nombre_empresa"]
            direccion = request.form["direccion"]
            cif = request.form["cif"]
            telefono = request.form["telefono"]
            codigo_postal = request.form["codigo_postal"]

            # Verificar si ya existe el usuario o email
            if Usuario.query.filter((Usuario.nombre_usuario == nombre) | (Usuario.email == email)).first():
             flash("⚠️ El usuario o el correo ya están registrados. Inicia sesión.", "warning")
             return redirect("/login")


            # Crear nuevo usuario
            nuevo = Usuario(
                nombre_usuario=nombre,
                email=email,
                nombre_empresa=nombre_empresa,
                direccion=direccion,
                cif=cif,
                telefono=telefono,
                codigo_postal=codigo_postal
            )
            nuevo.set_password(password)
            nuevo.fecha_alta = datetime.now(timezone.utc)

            db.session.add(nuevo)
            db.session.commit()

            # ✅ Enviar correo al administrador
            admin_msg = f"""
            <h2>📥 Nuevo registro en HappyPets</h2>
            <p><strong>Empresa:</strong> {nombre_empresa}</p>
            <p><strong>Usuario:</strong> {nombre}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Dirección:</strong> {direccion}</p>
            <p><strong>Código Postal:</strong> {codigo_postal}</p>
            <p><strong>Teléfono:</strong> {telefono}</p>
            """
            enviar_email("techinclusiondigital@gmail.com", "📬 Nuevo registro en HappyPets", admin_msg)

            # ✅ Enviar correo de bienvenida al usuario
            user_msg = f"""
            <h2>🎉 Bienvenido a HappyPets</h2>
            <p>Hola <strong>{nombre}</strong>, gracias por registrarte.</p>
            <p>Tu empresa <strong>{nombre_empresa}</strong> ya puede comenzar a usar el sistema de gestión de peluquería canina.</p>
            <p>Recuerda que tienes 1 mes de prueba gratuito.</p>
            <br>
            <p>Si tienes dudas, contáctanos en: techinclusiondigital@gmail.com</p>
            """
            enviar_email(email, "🎉 Bienvenido a HappyPets", user_msg)

            # Login automático y redirección
            login_user(nuevo)
            flash("✅ Registro exitoso. ¡Bienvenido!")
            return redirect("/dashboard")

        except Exception as e:
            print("❌ Error al registrar usuario:", e)
            flash("❌ Ocurrió un error al registrar. Revisa los datos.")
            return redirect("/registro")

    return render_template("registro.html")


from flask import flash
from functools import wraps
from flask import abort
from flask_login import current_user

def solo_admin(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if not current_user.is_authenticated or current_user.email != "techinclusiondigital@gmail.com":
            abort(403)  # Prohibido
        return f(*args, **kwargs)
    return decorador


@app.route("/login", methods=["GET", "POST"], endpoint='login')
def login():
    if request.method == "POST":
        nombre = request.form["nombre_usuario"]
        password = request.form["password"]
        user = Usuario.query.filter_by(nombre_usuario=nombre).first()

        if not user or not user.check_password(password):
            flash("❌ Usuario o contraseña incorrectos")
            return redirect("/login")

        # ✅ Excluir al admin del chequeo de periodo de prueba
        if user.email != "techinclusiondigital@gmail.com" and not user.en_periodo_prueba():
            flash("⚠️ Tu periodo de prueba ha caducado. Por favor, activa tu cuenta.")
            return redirect("/pago")

        login_user(user)

        # ✅ Redirigir según tipo de usuario
        if user.email == "techinclusiondigital@gmail.com":
            return redirect("/admin/usuarios")
        else:
            return redirect("/dashboard")

    return render_template("login.html")

from flask import abort

@app.route("/admin/usuarios", methods=["GET", "POST"])
@login_required
def administrar_usuarios():
    # Solo el admin puede ver esta página
    if current_user.email != "techinclusiondigital@gmail.com":
        abort(403)

    q = request.args.get("q", "").lower()
    if q:
        usuarios = Usuario.query.filter(
            (Usuario.nombre_usuario.ilike(f"%{q}%")) | (Usuario.email.ilike(f"%{q}%"))
        ).all()
    else:
        usuarios = Usuario.query.all()

    return render_template("admin_usuarios.html", usuarios=usuarios)

@app.route("/admin/usuarios/<int:usuario_id>/eliminar", methods=["POST"])
@login_required
def eliminar_usuario(usuario_id):
    if current_user.email != "techinclusiondigital@gmail.com":
        abort(403)

    usuario = Usuario.query.get_or_404(usuario_id)
    db.session.delete(usuario)
    db.session.commit()
    flash("✅ Usuario eliminado correctamente.")
    return redirect("/admin/usuarios")

@app.route("/admin/usuarios/<int:id>/editar", methods=["GET", "POST"])
@login_required
@solo_admin
def editar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    if request.method == "POST":
        usuario.nombre_usuario = request.form["nombre_usuario"]
        usuario.email = request.form["email"]
        usuario.nombre_empresa = request.form["nombre_empresa"]
        usuario.telefono = request.form["telefono"]
        usuario.direccion = request.form["direccion"]
        usuario.codigo_postal = request.form["codigo_postal"]
        db.session.commit()
        flash("✅ Usuario actualizado correctamente")
        return redirect("/admin/usuarios")
    return render_template("admin_editar_usuario.html", usuario=usuario)

@app.route("/admin/usuarios/nuevo", methods=["GET", "POST"])
@login_required
@solo_admin
def nuevo_usuario():
    if request.method == "POST":
        nombre = request.form["nombre_usuario"]
        email = request.form["email"]
        password = request.form["password"]
        nombre_empresa = request.form["nombre_empresa"]

        if Usuario.query.filter((Usuario.nombre_usuario == nombre) | (Usuario.email == email)).first():
            flash("⚠️ Usuario o email ya existente.")
            return redirect("/admin/usuarios/nuevo")

        nuevo = Usuario(
            nombre_usuario=nombre,
            email=email,
            nombre_empresa=nombre_empresa,
            fecha_alta=datetime.now(timezone.utc)
        )
        nuevo.set_password(password)
        db.session.add(nuevo)
        db.session.commit()
        flash("✅ Usuario creado correctamente.")
        return redirect("/admin/usuarios")

    return render_template("admin_nuevo_usuario.html")

@app.route("/admin/usuarios")
@login_required
@solo_admin
def admin_usuarios():
    usuarios = Usuario.query.all()
    return render_template("admin_usuarios.html", usuarios=usuarios)

@app.route("/pago")
def pago():
    return render_template("pago.html")

from flask_login import login_required, current_user



@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

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
        hora_formateada = hora_actual.strftime("%H:%M")

        # Buscar citas que comienzan exactamente a esta hora
        citas_en_esta_hora = [
            (inicio, fin_cita, cita)
            for inicio, fin_cita, cita in ocupados
            if inicio == hora_actual
        ]

        # Buscar si esta hora está ocupada por alguna cita en curso
        en_curso = any(
            inicio < hora_actual < fin_cita
            for inicio, fin_cita, _ in ocupados
        )

        if citas_en_esta_hora:
            for inicio, fin_cita, cita in citas_en_esta_hora:
                icono_pago = {
                    "efectivo": "💵",
                    "tarjeta": "💳"
                }.get(cita.metodo_pago, "")

                bloques.append({
                    "hora": hora_formateada,
                    "texto": f"{hora_formateada} {cita.mascota.nombre} - {cita.tipo_servicio or 'Sin servicio'} {icono_pago}",
                    "enlace": None,
                    "cita_id": cita.id,
                    "metodo_pago": cita.metodo_pago,
                    "precio": cita.precio,
                    "mascota": cita.mascota,
                    "tipo_servicio": cita.tipo_servicio
                })

        elif en_curso:
            # Hay una cita en curso, pero no comienza exactamente en este bloque → no mostrar nada
            pass

        else:
            # Bloque libre
            bloques.append({
                "hora": hora_formateada,
                "texto": f"{hora_formateada} - Libre",
                "enlace": f"/cita?fecha={dia}&hora={hora_formateada}",
                "cita_id": None,
                "metodo_pago": None,
                "precio": None,
                "mascota": None,
                "tipo_servicio": None
            })

        hora_actual += timedelta(minutes=paso_min)

    return bloques





from datetime import datetime, timedelta, timezone

@app.route("/dashboard")
@login_required
@requiere_suscripcion
def dashboard():
    semana = int(request.args.get("semana", 0))
    fecha_param = request.args.get("fecha")

    if fecha_param:
        try:
            fecha_base = datetime.strptime(fecha_param, "%Y-%m-%d").date()
        except ValueError:
            fecha_base = datetime.today().date()
    else:
        fecha_base = datetime.today().date()

    hoy = fecha_base + timedelta(days=7 * semana)
    dias_mostrar = 7

    # Excluir domingos
    dias_agenda = [
        hoy + timedelta(days=i)
        for i in range(dias_mostrar)
        if (hoy + timedelta(days=i)).weekday() != 6
    ]

    # Obtener citas
    citas = Cita.query.filter_by(user_id=current_user.id).order_by(Cita.fecha, Cita.hora).all()
    citas_por_fecha = defaultdict(list)
    for cita in citas:
        citas_por_fecha[cita.fecha].append(cita)

    # Generar agenda
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

    # Calcular fin del periodo de prueba
    fecha_alta = current_user.fecha_alta
    if fecha_alta.tzinfo is None:
        fecha_alta = fecha_alta.replace(tzinfo=timezone.utc)
    fecha_fin_prueba = fecha_alta + timedelta(days=30)

    return render_template(
        "dashboard.html",
        agenda=agenda_completa,
        fecha_fin_prueba=fecha_fin_prueba
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
        print("Rutas registradas:")
        print(app.url_map)
        migrate = Migrate(app, db)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


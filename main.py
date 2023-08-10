from flask import Flask, render_template, request, flash, redirect, url_for
import pandas as pd
from database import read_ivr_table
from dotenv import load_dotenv
import os
import mysql.connector
from flask_login import LoginManager, UserMixin, login_user, login_required
from flask_caching import Cache
from delete_database import delete_all_credentials
from sqlalchemy.sql import text


config = {
    "DEBUG": True,
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 2419200

}

load_dotenv()
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/"
app.secret_key = os.getenv('C_SECRECT')


cache = Cache(app, config={
    "CACHE_TYPE": "simple",  
    "CACHE_DEFAULT_TIMEOUT": 60 * 60 * 24 * 28  
})

cache = Cache(app, config=config)

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)



#Funciones para validacion

def validar_identificacion(id):
    return len(str(id)) <= 11


def validar_operador(operador):
    valid_operators = read_ivr_table()
    return operador in valid_operators
    

host = os.getenv('DB_HOST')
user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_DATABASE')


def validar_credenciales(correo, contrasena):
    try:
        
        connection = mysql.connector.connect(host=host, user=user, password=password, database=database)

        cursor = connection.cursor()

        query = "SELECT * FROM credenciales WHERE user = %s AND password = %s"
        cursor.execute(query, (correo, contrasena))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            return True
        else:
            return False

    except Exception as e:
        print("Error al validar las credenciales:", e)
        return False
    
  #Agregar nuevos usuarios  
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_DATABASE')
}
    
def validar_admin(correo, contrasena):
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        query = "SELECT * FROM admin WHERE user = %s AND password = %s"
        cursor.execute(query, (correo, contrasena))
        result = cursor.fetchone()

        cursor.close()
        connection.close()

        if result:
            return User(result[0]) 
        else:
            return None

    except Exception as e:
        print("Error al validar las credenciales:", e)
        return None

@app.route('/')
def index():
    return render_template('login.html')


@app.route('/', methods=['POST'])
def login():
    correo = request.form['correo']
    contrasena = request.form['contrasena']

    if validar_credenciales(correo, contrasena):
        return render_template('index.html')
    else:
        return "Credenciales incorrectas"


@app.route("/upload", methods=["POST"])
def upload():
    try:
        #Lectura de archivo
        file = request.files["file"]
        df = pd.read_excel(file)
        errores = []

        #Validaciones de info
        for i, row in df.iterrows():
            if not validar_identificacion(row["Id_Cliente__c"]):
                errores.append((i, "Id_Cliente__c", row["Id_Cliente__c"]))
            if not validar_operador(row["Operado_Por__c"]):
                errores.append((i, "Operado_Por__c", row["Operado_Por__c"]))
        if errores:
            for error in errores:
                flash(
                    (
                        "Error en:",
                        f"Fila: {error[0]+2}, campo: {error[1]}, valor: {error[2]}",
                    )
                )
        else:
            flash("Success, Todos los datos son correctos.")
            
            delete_all_credentials()

            import sqlalchemy
            host = os.getenv('SQ_HOST')
            username = os.getenv('SQ_USER')
            password = os.getenv('SQ_PASSWORD')
            database = os.getenv('SQ_DATABASE')
            port = os.getenv('SQ_PORT')

            def load_data_ivr():
                try:
                    url = f'''mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database}'''

                    engine = sqlalchemy.create_engine(url.format(url))

                    df.to_sql('validator_ivr', engine, if_exists='append', index=False)
                    flash("Se cargo correctamente a la base de datos")
                except Exception as e:
                    flash("Error en el cargue a la base de datos", e)
            
            load_data_ivr()
    except Exception as e:
        flash(f"Error: {str(e)}")

    return render_template("index.html")


#Validar usuarios admin
@app.route('/admin', methods=['GET'])
def login2():
    return render_template('login_admin.html')

@app.route('/admin', methods=['POST', 'GET'])
def login_admin():
    if request.method == 'POST':
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        
        user = validar_admin(correo, contrasena)
        if user:
            login_user(user)
            return redirect(url_for('add_user'))
        else:
            return "Credenciales incorrectas"

    return render_template('login_admin.html')

@app.route('/admin/add_user', methods=['GET'])
@login_required
def add_user():
    return render_template('admin.html')


@app.route('/admin/add_user', methods=['POST'])
@login_required
def admin_superadmin():
    correo = request.form['username']
    contrasena = request.form['password']
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = "INSERT INTO credenciales (user, password) VALUES (%s, %s)"
        values = (correo, contrasena)
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        print("Se agrego correctamente")
        return "Usuario agregado correctamente"

    except Exception as e:
        print('Error al guardar usuario', e)
        return "Error al guardar usuario: " + str(e)


if __name__ == "__main__":
    app.run(debug=True)

import mysql.connector
from dotenv import load_dotenv
import os
from flask import Flask, render_template, request, flash, redirect, url_for
load_dotenv()

host = os.getenv('DB_HOST')
user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_DATABASE')

def delete_all_credentials():
    try:
        connection = mysql.connector.connect(host=host, user=user, password=password, database=database)
        if connection.is_connected():
            cursor = connection.cursor()

            query = "DELETE FROM validator_ivr"

            cursor.execute(query)
            connection.commit()

            cursor.close()
            connection.close()

            flash("Registros eliminados correctamente de la tabla.")
        else:
            flash("No se pudo conectar a la base de datos.")

    except Exception as e:
        print("Error al eliminar los registros:", e)



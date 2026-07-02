from db_config import *
import mysql.connector
from datetime import datetime
import matplotlib.pyplot as plt

class MysqlHandler:
    def __init__(self):
        self.host = HOST
        self.user = USER
        self.password = PASSWORD
        self.database = DATABASE

        self.conexao = mysql.connector.connect(
            host=HOST,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
        )

        self.cursor = self.conexao.cursor()

        self.cursor.execute("SHOW DATABASES LIKE %s", (DATABASE,))
        resultado = self.cursor.fetchone()

        if resultado is None:
            self.cursor.execute(f"CREATE DATABASE {DATABASE}")

        self.cursor.execute(f"USE {DATABASE}")

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id_usuario INT AUTO_INCREMENT PRIMARY KEY,
                usuario VARCHAR(100) NOT NULL
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tipos_valores (
                id_tipo INT AUTO_INCREMENT PRIMARY KEY,
                id_usuario INT NOT NULL,
                titulo VARCHAR(100) NOT NULL,
                descricao VARCHAR(255) NOT NULL,
                FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS medicoes (
                id_medicao INT AUTO_INCREMENT PRIMARY KEY,
                id_tipo INT NOT NULL,
                data_medicao DATETIME NOT NULL,
                valor FLOAT NOT NULL,
                FOREIGN KEY (id_tipo) REFERENCES tipos_valores(id_tipo)
            )
            """
        )

        self.cursor.execute("SHOW COLUMNS FROM tipos_valores LIKE 'titulo'")
        if self.cursor.fetchone() is None:
            self.cursor.execute(
                "ALTER TABLE tipos_valores ADD COLUMN titulo VARCHAR(100) NOT NULL DEFAULT '' AFTER id_usuario"
            )

        self.cursor.execute("SHOW COLUMNS FROM tipos_valores LIKE 'descricao'")
        if self.cursor.fetchone() is None:
            self.cursor.execute(
                "ALTER TABLE tipos_valores ADD COLUMN descricao VARCHAR(255) NOT NULL DEFAULT '' AFTER titulo"
            )

        self.conexao.commit()

    def __exit__(self, exc_type, exc, tb):
        self.cursor.close()
        self.conexao.close()

    def get_users(self):
        self.cursor.execute("SELECT * FROM usuarios")
        return self.cursor.fetchall()

    def insert_user(self, usuario):
        self.cursor.execute("INSERT INTO usuarios (usuario) VALUES (%s)", (usuario,))
        self.conexao.commit()

    def delete_user(self, id_usuario):
        self.cursor.execute("DELETE FROM usuarios WHERE id_usuario = %s", (id_usuario,))
        self.conexao.commit()

    def get_tipos_valores(self, id_usuario=None):
        if id_usuario is None:
            self.cursor.execute(
                """
                SELECT tv.id_tipo, u.usuario, tv.titulo, tv.descricao
                FROM tipos_valores tv
                JOIN usuarios u ON tv.id_usuario = u.id_usuario
                ORDER BY u.usuario, tv.titulo
                """
            )
        else:
            self.cursor.execute(
                "SELECT tv.id_tipo, tv.titulo, tv.descricao FROM tipos_valores tv WHERE tv.id_usuario = %s ORDER BY tv.titulo",
                (id_usuario,),
            )
        return self.cursor.fetchall()

    def insert_tipo_valor(self, id_usuario, titulo, descricao):
        self.cursor.execute(
            "INSERT INTO tipos_valores (id_usuario, titulo, descricao) VALUES (%s, %s, %s)",
            (id_usuario, titulo, descricao),
        )
        self.conexao.commit()
        return self.cursor.lastrowid

    def delete_tipo_valor(self, id_tipo):
        self.cursor.execute("DELETE FROM tipos_valores WHERE id_tipo = %s", (id_tipo,))
        self.conexao.commit()

    def insert_altitudes_measurements(self, id_tipo, altitudes_list):
        for altitude in altitudes_list:
            self.cursor.execute(
                "INSERT INTO medicoes (id_tipo, data_medicao, valor) VALUES (%s, %s, %s)",
                (id_tipo, datetime.now(), altitude),
            )

        self.conexao.commit() 

    def get_altitudes_measurements(self, id_tipo):
        self.cursor.execute(
            "SELECT data_medicao, valor FROM medicoes WHERE id_tipo = %s ORDER BY data_medicao",
            (id_tipo,),
        )
        return self.cursor.fetchall()


if __name__ == "__main__":
    mysql_handler = MysqlHandler()

    print(mysql_handler.get_users())
    
    altitudes = mysql_handler.get_altitudes_measurements(2)
    altitudes = [altitude[1] for altitude in altitudes]
    
    time_stamps = []
    moment = 0
    for i in range(0, len(altitudes)):
        time_stamps.append(moment)
        moment += 1 / 20

    plt.plot(time_stamps, altitudes)
    plt.xlabel("Tempo (s)")
    plt.ylabel("Altitude (m)")
    plt.title("Altitude x Tempo")
    plt.grid(True)
    plt.show()
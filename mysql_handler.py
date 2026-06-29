from db_config import *
import mysql.connector


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

        print("Resultado:", resultado)

        if resultado is None:
            print(f"Criando banco '{DATABASE}'...")

            self.cursor.execute(f"CREATE DATABASE {DATABASE}")
            self.cursor.execute(f"USE {DATABASE}")

            self.cursor.execute(
                """
                CREATE TABLE usuarios (
                    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
                    usuario VARCHAR(100) NOT NULL
                )
                """
            )

            self.cursor.execute(
                """
                CREATE TABLE tipos_valores (
                    id_tipo INT AUTO_INCREMENT PRIMARY KEY,
                    id_usuario INT NOT NULL,
                    descricao VARCHAR(100) NOT NULL,
                    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
                )
                """
            )

            self.cursor.execute(
                """
                CREATE TABLE medicoes (
                    id_medicao INT AUTO_INCREMENT PRIMARY KEY,
                    id_tipo INT NOT NULL,
                    data_medicao DATETIME NOT NULL,
                    valor FLOAT NOT NULL,
                    FOREIGN KEY (id_tipo) REFERENCES tipos_valores(id_tipo)
                )
                """
            )

            print("Banco e tabelas criados com sucesso!")

        else:
            print(f"O banco '{DATABASE}' já existe.")

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
                SELECT tv.id_tipo, u.usuario, tv.descricao
                FROM tipos_valores tv
                JOIN usuarios u ON tv.id_usuario = u.id_usuario
                ORDER BY u.usuario, tv.descricao
                """
            )
        else:
            self.cursor.execute(
                "SELECT tv.id_tipo, tv.descricao FROM tipos_valores tv WHERE tv.id_usuario = %s ORDER BY tv.descricao",
                (id_usuario,),
            )
        return self.cursor.fetchall()

    def insert_tipo_valor(self, id_usuario, descricao):
        self.cursor.execute(
            "INSERT INTO tipos_valores (id_usuario, descricao) VALUES (%s, %s)",
            (id_usuario, descricao),
        )
        self.conexao.commit()

    def delete_tipo_valor(self, id_tipo):
        self.cursor.execute("DELETE FROM tipos_valores WHERE id_tipo = %s", (id_tipo,))
        self.conexao.commit()


if __name__ == "__main__":
    mysql_handler = MysqlHandler()

    print(mysql_handler.get_users())
    print(mysql_handler.delete_user(5))
    print(mysql_handler.get_users())
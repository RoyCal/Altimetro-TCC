import sys
import threading

from textual.app import App, ComposeResult
from textual.widgets import Button, Static, Input, Select, Log
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from mysql_handler import MysqlHandler
from serial_eeprom import SerialEEPROM, plot_altitude
from serial.tools import list_ports

mysql_handler = MysqlHandler()
serial_eeprom = SerialEEPROM()

class LogRedirect:
    def __init__(self, app: App):
        self.app = app

    def write(self, message: str) -> int:
        if not message:
            return 0

        try:
            screen = self.app.screen
            if hasattr(screen, "write_log"):
                try:
                    # Schedule UI update on the app's thread so the Textual
                    # event loop can render the log in real time.
                    self.app.call_from_thread(screen.write_log, message)
                except Exception:
                    # Fallback if call_from_thread is unavailable.
                    screen.write_log(message)
                return len(message)
        except Exception:
            pass

        try:
            sys.__stdout__.write(message)
        except Exception:
            pass
        return len(message)

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False

# -------- MENU --------
class MenuScreen(Screen):
    CSS = """
    Screen {
        align: center middle;
        content-align: center middle;
    }

    Vertical {
        content-align: center middle;
    }

    Static {
        margin: 1;
    }

    Button {
        width: 30;
        margin: 1;
    }
    """

    def on_mount(self):
        self.query_one("#btn_dados").focus()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("MENU PRINCIPAL", id="title")
            yield Button("Recuperar dados de voo", id="btn_dados")
            yield Button("Usuários", id="btn_usuario")
            yield Button("Tipos de valores", id="btn_tipo")
            yield Button("Encerrar aplicação", id="btn_sair", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn_dados":
                self.app.push_screen("retrieve_data_screen")

            case "btn_usuario":
                self.app.push_screen("users_screen")

            case "btn_tipo":
                self.app.push_screen("value_types_screen")

            case "btn_sair":
                self.app.exit()

# -------- USERS --------
class UsersScreen(Screen):
    CSS = """
    Screen {
        content-align: center middle;
    }

    #title {
        margin: 1;
    }

    #subtitle {
        margin-left: 3;
        margin-bottom: 1;
    }

    Button {
        margin: 1;
    }
    """

    def load_users(self):
        self.users = mysql_handler.get_users()

    def on_mount(self):
        self.query_one("#btn_add").focus()

    def compose(self) -> ComposeResult:
        self.load_users()

        with VerticalScroll():
            yield Static("USUÁRIOS", id="title")
            yield Static("ID - NOME", id="subtitle")
            
            if not self.users:
                yield Static("Nenhum usuário cadastrado")
            else:
                for u in self.users:
                    yield Static(f"👤 {u[0]} - {u[1]}")

            yield Button("Adicionar usuário", id="btn_add")
            yield Button("Voltar", id="btn_back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_back":
            self.app.pop_screen()

        elif event.button.id == "btn_add":
            self.app.push_screen("add_user_screen")


class AddUserScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("ADICIONAR USUÁRIO")
            yield Input(placeholder="Nome do usuário", id="input_name")
            yield Button("Adicionar", id="btn_add", variant="success")
            yield Button("Voltar", id="btn_back", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_back":
            self.app.pop_screen()

        elif event.button.id == "btn_add":
            name = self.query_one("#input_name", Input).value.strip()

            if not name:
                self.notify("Digite um nome válido")
                return

            mysql_handler.insert_user(name)

            self.notify(f"Usuário '{name}' adicionado!")
            self.query_one("#input_name", Input).value = ""
            self.app.get_screen("users_screen", UsersScreen).refresh(recompose=True)


# -------- VALUE TYPES --------
class ValueTypesScreen(Screen):
    CSS = """
    Screen {
        content-align: center middle;
    }

    #title {
        margin: 1;
    }

    #subtitle {
        margin-left: 3;
        margin-bottom: 1;
    }

    Button {
        margin: 1;
    }
    """

    def load_value_types(self):
        self.value_types = mysql_handler.get_tipos_valores()

    def on_mount(self):
        self.query_one("#btn_add").focus()

    def compose(self) -> ComposeResult:
        self.load_value_types()

        with VerticalScroll():
            yield Static("TIPOS DE VALORES", id="title")
            yield Static("ID - USUÁRIO - DESCRIÇÃO", id="subtitle")

            if not self.value_types:
                yield Static("Nenhum tipo de valor cadastrado")
            else:
                for item in self.value_types:
                    yield Static(f"📊 {item[0]} - {item[1]} - {item[2]}")

            yield Button("Adicionar tipo", id="btn_add")
            yield Button("Voltar", id="btn_back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_back":
            self.app.pop_screen()

        elif event.button.id == "btn_add":
            self.app.push_screen("add_value_type_screen")


class AddValueTypeScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("ADICIONAR TIPO DE VALOR")
            yield Input(placeholder="ID do usuário", id="input_user_id")
            yield Input(placeholder="Descrição do tipo", id="input_description")
            yield Button("Adicionar", id="btn_add", variant="success")
            yield Button("Voltar", id="btn_back", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_back":
            self.app.pop_screen()

        elif event.button.id == "btn_add":
            user_id_text = self.query_one("#input_user_id", Input).value.strip()
            description = self.query_one("#input_description", Input).value.strip()

            if not user_id_text or not description:
                self.notify("Preencha todos os campos")
                return

            try:
                user_id = int(user_id_text)
            except ValueError:
                self.notify("Digite um ID de usuário válido")
                return

            users = mysql_handler.get_users()
            if not any(user[0] == user_id for user in users):
                self.notify("Usuário não encontrado")
                return

            mysql_handler.insert_tipo_valor(user_id, description)

            self.notify(f"Tipo '{description}' adicionado!")
            self.query_one("#input_user_id", Input).value = ""
            self.query_one("#input_description", Input).value = ""
            self.app.get_screen("value_types_screen", ValueTypesScreen).refresh(recompose=True)

# -------- RECUPERAR DADOS --------

class RetrieveDataScreen(Screen):
    CSS = """
    Screen {
        content-align: center middle;
    }

    Static {
        margin: 1;
    }

    Log {
        margin: 1;
    }

    #button_container {
        height: 6;
    }

    Button {
        margin: 1;
    }
    """

    def on_mount(self):
        self.query_one("#serial_port_select").focus()

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("RECUPERAR DADOS DE VOO")
            yield Select(
                options=[(f"{port.device} - {port.description}", port.device) for port in list_ports.comports()],
                prompt="Selecione a porta serial",
                id="serial_port_select",
            )
            
            with Horizontal(id="button_container"):
                yield Button("Reload page", id="btn_reload", variant="primary")
                yield Button("Iniciar recuperação", id="btn_retrieve", variant="success")

            yield Log(id="log_output", highlight=True, auto_scroll=True)
            yield Button("Voltar", id="btn_back", variant="error")

    def write_log(self, message: str) -> None:
        log_output = self.query_one("#log_output", Log)
        log_output.write(message)

    def get_data(self):
        result = serial_eeprom.retrieve_data()
        if not result:
            return
        time_stamps, altitudes = result
        try:
            import multiprocessing

            p = multiprocessing.Process(target=plot_altitude, args=(time_stamps, altitudes))
            p.daemon = True
            p.start()
        except Exception as e:
            print("Erro ao iniciar plot:", e)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_back":
            self.app.pop_screen()

        elif event.button.id == "btn_retrieve":
            selected_port = self.query_one("#serial_port_select", Select).value

            if not selected_port or selected_port == Select.NULL:
                self.notify("Selecione uma porta serial antes de iniciar a recuperação")
                return
            
            serial_eeprom.SERIAL_PORT = selected_port
            # Run retrieval in a background thread so the Textual UI can
            # update the log in real time while matplotlib shows plots.
            threading.Thread(target=self.get_data, daemon=True).start()

        elif event.button.id == "btn_reload":
            self.app.get_screen("retrieve_data_screen", RetrieveDataScreen).refresh(recompose=True)

# -------- APP --------
class MyApp(App):
    SCREENS = {
        "menu_screen": MenuScreen,
        "users_screen": UsersScreen,
        "add_user_screen": AddUserScreen,
        "value_types_screen": ValueTypesScreen,
        "add_value_type_screen": AddValueTypeScreen,
        "retrieve_data_screen": RetrieveDataScreen,
    }

    def __init__(self):
        super().__init__()
        self._stdout_redirect = LogRedirect(self)
        self._stderr_redirect = LogRedirect(self)
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr

    def on_mount(self):
        sys.stdout = self._stdout_redirect
        sys.stderr = self._stderr_redirect
        self.push_screen("menu_screen")

    def on_unmount(self):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr


if __name__ == "__main__":
    MyApp().run()
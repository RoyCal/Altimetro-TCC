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
            yield Button("Encerrar aplicação", id="btn_sair", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn_dados":
                self.app.push_screen("retrieve_data_screen")

            case "btn_usuario":
                self.app.push_screen("users_screen")

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
        match event.button.id:

            case "btn_back":
                self.app.pop_screen()

            case "btn_add":
                name = self.query_one("#input_name", Input).value.strip()

                if not name:
                    self.notify("Digite um nome válido")
                    return

                mysql_handler.insert_user(name)

                self.notify(f"Usuário '{name}' adicionado!")
                self.query_one("#input_name", Input).value = ""
                self.app.get_screen("users_screen", UsersScreen).refresh(recompose=True)
                self.app.pop_screen()

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
        content-align: center middle;
        height: auto;
    }

    #button_container2 {
        content-align: center middle;
        height: auto;
        margin-bottom: 2;
    }

    Button {
        margin: 1;
        margin-bottom: 0;
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
                yield Button("Clear log", id="btn_clr_log", variant="primary")
                yield Button("Device info", id="btn_info", variant="primary")
                yield Button("Enable flight", id="btn_enable", variant="primary")
                yield Button("Test BMP", id="btn_test_bmp", variant="primary")
                yield Button("Test EEPROM", id="btn_test_eeprom", variant="primary")
                yield Button("Iniciar recuperação", id="btn_retrieve", variant="success")

            yield Log(id="log_output", highlight=True, auto_scroll=True)
            with Horizontal(id="button_container2"):
                yield Button("Visualizar gráfico", id="btn_visualize", variant="primary")
                yield Button("Recortar gráfico", id="btn_crop", variant="primary")
                yield Button("Cadastrar no banco", id="btn_save", variant="success")
                yield Button("Voltar", id="btn_back", variant="error")
                yield Button("Reload page", id="btn_reload", variant="primary")

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
            self.notify("Erro ao iniciar plot")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:

            case "btn_back":
                self.app.pop_screen()

            case "btn_retrieve":
                selected_port = self.query_one("#serial_port_select", Select).value

                if not selected_port or selected_port == Select.NULL:
                    self.notify("Selecione uma porta serial antes de iniciar a recuperação")
                    return
                
                serial_eeprom.SERIAL_PORT = selected_port
                # Run retrieval in a background thread so the Textual UI can
                # update the log in real time while matplotlib shows plots.
                threading.Thread(target=self.get_data, daemon=True).start()

            case "btn_reload":
                self.app.get_screen("retrieve_data_screen", RetrieveDataScreen).refresh(recompose=True)

            case "btn_clr_log":
                self.query_one("#log_output", Log).clear()

            case "btn_save":
                if not serial_eeprom.altitudes:
                    self.notify("Nenhuma medição disponível para cadastrar")
                    return
                
                self.app.push_screen("save_measurement_screen")
            
            case "btn_info":
                selected_port = self.query_one("#serial_port_select", Select).value

                if not selected_port or selected_port == Select.NULL:
                    self.notify("Selecione uma porta serial antes de obter as infomações do dispositivo")
                    return
                
                serial_eeprom.SERIAL_PORT = selected_port

                serial_eeprom.get_alt_infos()
            
            case "btn_enable":
                selected_port = self.query_one("#serial_port_select", Select).value

                if not selected_port or selected_port == Select.NULL:
                    self.notify("Selecione uma porta serial antes de habilitar o voo")
                    return
                
                serial_eeprom.SERIAL_PORT = selected_port

                serial_eeprom.enable_flight()
            
            case "btn_test_bmp":
                selected_port = self.query_one("#serial_port_select", Select).value

                if not selected_port or selected_port == Select.NULL:
                    self.notify("Selecione uma porta serial antes de testar o BMP")
                    return
                
                serial_eeprom.SERIAL_PORT = selected_port

                serial_eeprom.test_bmp()

            case "btn_test_eeprom":
                selected_port = self.query_one("#serial_port_select", Select).value

                if not selected_port or selected_port == Select.NULL:
                    self.notify("Selecione uma porta serial antes de testar a EEPROM")
                    return
                
                serial_eeprom.SERIAL_PORT = selected_port

                serial_eeprom.test_eeprom()

            case "btn_visualize":
                if not serial_eeprom.altitudes:
                    self.notify("Nenhum gráfico para visualizar")
                    return
                
                altitudes = serial_eeprom.altitudes
                time_stamps = serial_eeprom.time_stamps

                try:
                    import multiprocessing

                    p = multiprocessing.Process(target=plot_altitude, args=(time_stamps, altitudes))
                    p.daemon = True
                    p.start()
                except Exception as e:
                    self.notify("Erro ao iniciar plot")
            
            case "btn_crop":
                if not serial_eeprom.altitudes:
                    self.notify("Nenhum gráfico para recortar")
                    return
                
                self.app.push_screen("crop_graph_screen")

# ------ RECORTAR GRÁFICO ------

class CropGraphScreen(Screen):
    CSS = """
    Screen {
        content-align: center middle;
    }

    Static {
        margin: 1;
    }

    Button {
        margin: 1;
    }
    """

    def on_mount(self):
        self.query_one("#input_amount").focus()

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("Tempo máximo do gráfico (s)", id="title")
            yield Input(placeholder="Quantidade para recorte", id="input_amount")
            with Horizontal(id="button_container"):
                yield Button("Recortar", id="btn_crop", variant="primary")
                yield Button("Confirmar recorte", id="btn_confirm_crop", variant="success")
                yield Button("Voltar", id="btn_back", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn_back":
                self.app.pop_screen()
            
            case "btn_crop":
                amount_str = self.query_one("#input_amount", Input).value.strip()
                try:
                    amount = float(amount_str)
                except ValueError:
                    self.notify("Digite um número válido")
                    return
                
                if amount <= 0:
                    self.notify("Digite um número maior que zero")
                    return
                
                if amount*serial_eeprom.ALT_FREQ >= len(serial_eeprom.altitudes):
                    self.notify(f"Digite um número menor que {len(serial_eeprom.altitudes)/serial_eeprom.ALT_FREQ}")
                    return

                serial_eeprom.crop_graph_end(amount)
                self.notify(f"Gráfico recortado em {amount} segundos")

                try:
                    import multiprocessing

                    p = multiprocessing.Process(target=plot_altitude, args=(serial_eeprom.croppedTimestamps, serial_eeprom.croppedAltitudes))
                    p.daemon = True
                    p.start()
                except Exception as e:
                    self.notify("Erro ao iniciar plot")
            
            case "btn_confirm_crop":
                serial_eeprom.confirm_crop()
                self.notify("Gráfico recortado!")

# ------ CADASTRAR NO BANCO ------
class SaveMeasurementScreen(Screen):
    CSS = """
    Screen {
        content-align: center middle;
    }

    Static {
        margin: 1;
    }

    Button {
        margin: 1;
    }
    """

    def load_users(self):
        self.users = mysql_handler.get_users()

    def on_mount(self):
        self.query_one("#input_title").focus()

    def compose(self) -> ComposeResult:
        self.load_users()

        with VerticalScroll():
            yield Static("CADASTRAR MEDIÇÃO", id="title")
            yield Input(placeholder="Título da medição", id="input_title")
            yield Input(placeholder="Descrição da medição", id="input_description")
            yield Select(
                options=[(u[1], u[0]) for u in self.users],
                prompt="Selecione o usuário",
                id="select_user",
            )
            with Horizontal(id="button_container"):
                yield Button("Cadastrar", id="btn_register", variant="success")
                yield Button("Voltar", id="btn_back", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn_back":
                self.app.pop_screen()

            case "btn_register":
                title = self.query_one("#input_title", Input).value.strip()
                description = self.query_one("#input_description", Input).value.strip()
                user_id = self.query_one("#select_user", Select).value

                if not title:
                    self.notify("Digite um título válido")
                    return

                if not description:
                    self.notify("Digite uma descrição válida")
                    return

                if not user_id:
                    self.notify("Selecione um usuário")
                    return

                try:
                    id_tipo = mysql_handler.insert_tipo_valor(user_id, title, description)
                    mysql_handler.insert_altitudes_measurements(id_tipo, serial_eeprom.altitudes)
                    self.notify("Medição cadastrada com sucesso")
                    self.app.pop_screen()
                except Exception as e:
                    self.notify(f"Erro ao cadastrar: {e}")


# -------- APP --------
class MyApp(App):
    SCREENS = {
        "menu_screen": MenuScreen,
        "users_screen": UsersScreen,
        "add_user_screen": AddUserScreen,
        "retrieve_data_screen": RetrieveDataScreen,
        "save_measurement_screen": SaveMeasurementScreen,
        "crop_graph_screen": CropGraphScreen,
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
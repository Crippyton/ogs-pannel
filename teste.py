import flet as ft
import os
import json
import importlib.util
from pathlib import Path

# Configurações do sistema
APP_NAME = "Hub de TI"
SETTINGS_FILE = "settings.json"
MODULES_DIR = "modules"
USERS_FILE = "users.json"

class AuthManager:
    def __init__(self):
        self.users = self._load_users()

    def _load_users(self):
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, "r") as f:
                    return json.load(f)
            # Usuário padrão para teste
            default_users = {"admin": "admin123"}
            self._save_users(default_users)
            return default_users
        except Exception as e:
            print(f"Erro ao carregar usuários: {e}")
            return {"admin": "admin123"}

    def _save_users(self, users):
        try:
            with open(USERS_FILE, "w") as f:
                json.dump(users, f)
        except Exception as e:
            print(f"Erro ao salvar usuários: {e}")

    def authenticate(self, username, password):
        return self.users.get(username) == password

class ThemeManager:
    def __init__(self):
        self.current_theme = self._load_theme()

    def _load_theme(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                    return settings.get("theme", "light")
            return "light"
        except Exception as e:
            print(f"Erro ao carregar tema: {e}")
            return "light"

    def save_theme(self, theme):
        try:
            settings = self._load_settings()
            settings["theme"] = theme
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f)
            self.current_theme = theme
        except Exception as e:
            print(f"Erro ao salvar tema: {e}")

    def _load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        return {}

    def toggle_theme(self):
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.save_theme(new_theme)
        return new_theme

class ModuleLoader:
    def __init__(self):
        self.modules = {}
        self._ensure_modules_dir()
        self._load_modules()

    def _ensure_modules_dir(self):
        os.makedirs(MODULES_DIR, exist_ok=True)

    def _load_modules(self):
        module_path = Path(MODULES_DIR)
        for py_file in module_path.glob("*.py"):
            self._load_module_from_file(py_file)

    def _load_module_from_file(self, py_file):
        module_name = py_file.stem
        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._register_module(module_name, module)
        except Exception as e:
            print(f"Erro ao carregar módulo {module_name}: {e}")

    def _register_module(self, module_name, module):
        if hasattr(module, "Module"):
            module_instance = module.Module()
            if hasattr(module_instance, "get_module_info") and hasattr(module_instance, "get_view"):
                self.modules[module_name] = module_instance
                print(f"Módulo carregado: {module_name}")

    def get_modules(self):
        return self.modules

class TIHubApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.auth_manager = AuthManager()
        self.theme_manager = ThemeManager()
        self.module_loader = ModuleLoader()
        self.is_authenticated = False
        self.current_module = None
        self.module_index_map = {"home": 0}
        self.module_content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        
        # Configuração inicial da página
        self.page.title = APP_NAME
        self.page.theme_mode = ft.ThemeMode.LIGHT if self.theme_manager.current_theme == "light" else ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.window.width = 1100  # Atualizado para a nova propriedade
        self.page.window.height = 800  # Atualizado para a nova propriedade
        self.page.window.min_width = 400  # Atualizado para a nova propriedade
        self.page.window.min_height = 600  # Atualizado para a nova propriedade
        self.page.theme = ft.Theme(color_scheme_seed=ft.colors.BLUE)
        
        # Inicializa a interface
        self._init_ui()

    def _init_ui(self):
        if not self.is_authenticated:
            self._show_login_view()
        else:
            self._show_main_view()

    def _show_login_view(self):
        self.page.views.clear()
        self.username_field = self._create_text_field("Usuário", False)
        self.password_field = self._create_text_field("Senha", True)
        
        # Mensagem de erro
        self.login_error_text = ft.Text(color=ft.colors.RED_500, size=12, visible=False)

        # Logo placeholder
        logo = ft.Container(
            content=ft.Image(src="assets/log.jpg", width=200, height=100, fit=ft.ImageFit.CONTAIN),
            alignment=ft.alignment.center,
        )
        
        login_button = ft.ElevatedButton(text="Entrar", width=320, on_click=self._handle_login)

        # Tela de login
        login_view = ft.View(
            route="/login",
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[logo, ft.Container(height=40), self._create_login_card(login_button)],
        )
        
        self.page.views.append(login_view)
        self.page.go("/login")

    def _create_text_field(self, label, password):
        return ft.TextField(
            label=label,
            password=password,
            can_reveal_password=password,
            border=ft.InputBorder.OUTLINE,
            width=320,
        )

    def _create_login_card(self, login_button):
        return ft.Card(
            elevation=4,
            content=ft.Container(
                width=400,
                padding=20,
                content=ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Login", size=22, weight=ft.FontWeight.BOLD),
                        ft.Container(height=20),
                        self.username_field,
                        ft.Container(height=10),
                        self.password_field,
                        ft.Container(height=5),
                        self.login_error_text,
                        ft.Container(height=20),
                        login_button,
                    ],
                ),
            ),
        )

    def _handle_login(self, e):
        username = self.username_field.value
        password = self.password_field.value
        
        if not username or not password:
            self.login_error_text.value = "Preencha todos os campos"
            self.login_error_text.visible = True
            self.page.update()
            return
        
        if self.auth_manager.authenticate(username, password):
            self.is_authenticated = True
            self._show_main_view()
        else:
            self.login_error_text.value = "Usuário ou senha inválidos"
            self.login_error_text.visible = True
            self.page.update()

    def _show_main_view(self):
        self.page.views.clear()
        self.module_index_map = {"home": 0}
        
        # Barra lateral com os módulos
        modules_rail = self._create_modules_rail()

        # Botão para alternar o tema
        theme_switch = ft.IconButton(
            icon=ft.icons.DARK_MODE if self.theme_manager.current_theme == "light" else ft.icons.LIGHT_MODE,
            tooltip="Alternar tema",
            on_click=self._toggle_theme,
        )

        # Layout principal
        main_content = ft.Row(
            spacing=0,
            controls=[self._create_sidebar(modules_rail, theme_switch), self.module_content],
            expand=True,
        )

        main_view = ft.View(route="/main", controls=[main_content], padding=0, bgcolor=self._get_main_bgcolor())
        self.page.views.append(main_view)
        self.page.go("/main")

        # Exibir a tela inicial do módulo
        self._show_home_view()

    def _create_modules_rail(self):
        modules_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            extended=True,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.HOME_OUTLINED,
                    selected_icon=ft.icons.HOME,
                    label="Início",
                ),
            ],
            on_change=self._handle_rail_change,
        )

        # Adicionar módulos carregados ao rail
        for module_name, module in self.module_loader.get_modules().items():
            module_info = module.get_module_info()
            modules_rail.destinations.append(
                ft.NavigationRailDestination(
                    icon=ft.icons.EXTENSION_OUTLINED,
                    selected_icon=ft.icons.EXTENSION,
                    label=module_info.get("name", module_name),
                )
            )

        return modules_rail

    def _handle_rail_change(self, e):
        selected_index = e.control.selected_index
        if selected_index == 0:
            self._show_home_view()
        else:
            module_name = list(self.module_loader.get_modules().keys())[selected_index - 1]
            self._show_module_view(module_name)

    def _show_home_view(self):
        self.module_content.controls.clear()
        
        # Mensagem de boas-vindas
        welcome_message = ft.Text("Bem-vindo ao Hub de TI!", size=24, weight=ft.FontWeight.BOLD)
        
        # Botão para encerrar sessão
        logout_button = ft.ElevatedButton(
            text="Encerrar Sessão",
            icon=ft.icons.LOGOUT,
            on_click=self._handle_logout,
        )
        
        # Adiciona os controles à tela inicial
        self.module_content.controls.append(welcome_message)
        self.module_content.controls.append(ft.Container(height=20))  # Espaçamento
        self.module_content.controls.append(logout_button)
        
        self.page.update()

    def _handle_logout(self, e):
        # Redefine o estado de autenticação
        self.is_authenticated = False
        
        # Redireciona para a tela de login
        self._show_login_view()

    def _show_module_view(self, module_name):
        module = self.module_loader.get_modules().get(module_name)
        if module:
            self.module_content.controls.clear()
            self.module_content.controls.append(module.get_view())
            self.page.update()

    def _create_sidebar(self, modules_rail, theme_switch):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Image(src="assets/log.jpg", width=80, height=40, fit=ft.ImageFit.CONTAIN),
                        padding=10,
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(
                        content=modules_rail,
                        expand=True,  # Garante que o NavigationRail ocupe o espaço disponível
                    ),
                    ft.Column(expand=True),  # Espaço flexível
                    ft.Container(content=theme_switch, padding=10, alignment=ft.alignment.center),
                ],
                spacing=0,
                tight=True,
                expand=True,
            ),
            bgcolor=ft.colors.SURFACE,
            border=ft.border.only(right=ft.BorderSide(1, ft.colors.OUTLINE)),
        )

    def _get_main_bgcolor(self):
        return ft.colors.SURFACE_VARIANT if self.theme_manager.current_theme == "light" else ft.colors.SURFACE_TINT

    def _toggle_theme(self, e):
        new_theme = self.theme_manager.toggle_theme()
        self.page.theme_mode = ft.ThemeMode.LIGHT if new_theme == "light" else ft.ThemeMode.DARK
        
        # Atualiza o ícone do botão
        theme_switch = e.control
        theme_switch.icon = ft.icons.DARK_MODE if new_theme == "light" else ft.icons.LIGHT_MODE
        
        self.page.update()

def main(page: ft.Page):
    app = TIHubApp(page)

if __name__ == "__main__":
    ft.app(target=main)
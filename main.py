import flet as ft
import os
import sys
import json
import importlib.util
import hashlib
import base64
from pathlib import Path
from datetime import datetime


if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

zabbix_path = os.path.join(BASE_DIR, "modules", "Pacs", "assets", "zabbix.png")
pixeon_path = os.path.join(BASE_DIR, "modules", "Pacs", "assets", "pixeon.jpeg")

img = ft.Image(src=zabbix_path)
img = ft.Image(src=pixeon_path)

# Configurações do sistema
APP_NAME = "God's action"
SETTINGS_FILE = "settings.json"
MODULES_DIR = "modules"
USERS_FILE = "users.json"
LOGS_FILE = "system_logs.json"
LINKS_FILE = "useful_links.json"
# Adicionar constante para o arquivo de configurações de contato
CONTACT_FILE = "contact_info.json"

class Logger:
    """Sistema de logs para rastrear atividades e erros"""
    
    @staticmethod
    def log(action, details, user=None, level="INFO"):
        try:
            logs = []
            if os.path.exists(LOGS_FILE):
                try:
                    with open(LOGS_FILE, "r") as f:
                        content = f.read().strip()
                        if content:  # Verifica se o arquivo não está vazio
                            logs = json.loads(content)
                except json.JSONDecodeError:
                    # Arquivo existe mas não é um JSON válido
                    logs = []
            
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "details": details,
                "user": user,
                "level": level
            })
            
            with open(LOGS_FILE, "w") as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"Erro ao registrar log: {e}")

class AuthManager:
    """Gerencia autenticação e usuários do sistema"""
    
    def __init__(self):
        self.users = self._load_users()
        self.current_user = None

    def _load_users(self):
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, "r") as f:
                    users_data = json.load(f)
                    
                    # Verifica se precisa migrar do formato antigo para o novo
                    migrated_users = {}
                    migration_needed = False
                    
                    for username, data in users_data.items():
                        if isinstance(data, str):  # Formato antigo: {"username": "password"}
                            migration_needed = True
                            migrated_users[username] = {
                                "password": self._hash_password(data),
                                "role": "admin" if username == "admin" else "user",
                                "name": username.capitalize(),
                                "created_at": datetime.now().isoformat()
                            }
                        else:
                            # Já está no formato novo
                            migrated_users[username] = data
                    
                    if migration_needed:
                        print("Migrando formato de usuários...")
                        self._save_users(migrated_users)
                        Logger.log("users_migrated", "Formato de usuários migrado para o novo formato")
                        return migrated_users
                    
                    return users_data
                    
            # Usuário padrão para teste
            default_users = {
                "admin": {
                    "password": self._hash_password("admin123"),
                    "role": "admin",
                    "name": "Administrador",
                    "created_at": datetime.now().isoformat()
                }
            }
            self._save_users(default_users)
            return default_users
        except Exception as e:
            Logger.log("load_users_error", str(e), level="ERROR")
            return {
                "admin": {
                    "password": self._hash_password("admin123"),
                    "role": "admin",
                    "name": "Administrador",
                    "created_at": datetime.now().isoformat()
                }
            }

    def _save_users(self, users):
        try:
            with open(USERS_FILE, "w") as f:
                json.dump(users, f, indent=2)
        except Exception as e:
            Logger.log("save_users_error", str(e), level="ERROR")

    def _hash_password(self, password):
        """Cria um hash seguro da senha"""
        salt = "TIHubSalt"  # Em produção, use um salt único por usuário
        hash_obj = hashlib.sha256((password + salt).encode())
        return base64.b64encode(hash_obj.digest()).decode()

    def authenticate(self, username, password):
        """Autentica um usuário"""
        if username not in self.users:
            return False
            
        hashed_password = self._hash_password(password)
        if self.users[username]["password"] == hashed_password:
            self.current_user = username
            Logger.log("login_success", f"Login bem-sucedido", username)
            return True
            
        Logger.log("login_failed", f"Tentativa de login falhou", username)
        return False
        
    def add_user(self, username, password, name, role="user"):
        """Adiciona um novo usuário"""
        if username in self.users:
            return False, "Usuário já existe"
            
        self.users[username] = {
            "password": self._hash_password(password),
            "role": role,
            "name": name,
            "created_at": datetime.now().isoformat()
        }
        self._save_users(self.users)
        Logger.log("user_added", f"Usuário {username} adicionado", self.current_user)
        return True, "Usuário adicionado com sucesso"
    
    def update_user(self, username, name=None, role=None, password=None):
        """Atualiza um usuário existente"""
        if username not in self.users:
            return False, "Usuário não encontrado"
            
        if username == "admin" and role and role != "admin":
            return False, "Não é possível alterar a função do administrador"
            
        if name:
            self.users[username]["name"] = name
            
        if role:
            self.users[username]["role"] = role
            
        if password:
            self.users[username]["password"] = self._hash_password(password)
            
        self._save_users(self.users)
        Logger.log("user_updated", f"Usuário {username} atualizado", self.current_user)
        return True, "Usuário atualizado com sucesso"
        
    def remove_user(self, username):
        """Remove um usuário"""
        if username not in self.users:
            return False, "Usuário não encontrado"
            
        if username == "admin":
            return False, "Não é possível remover o usuário administrador"
            
        if username == self.current_user:
            return False, "Não é possível remover o usuário atual"
            
        del self.users[username]
        self._save_users(self.users)
        Logger.log("user_removed", f"Usuário {username} removido", self.current_user)
        return True, "Usuário removido com sucesso"
        
    def get_users(self):
        """Retorna a lista de usuários"""
        return self.users
        
    def is_admin(self):
        """Verifica se o usuário atual é administrador"""
        if not self.current_user:
            return False
        return self.users[self.current_user]["role"] == "admin"
        
    def get_current_user_info(self):
        """Retorna informações do usuário atual"""
        if not self.current_user:
            return None
        user_info = self.users[self.current_user].copy()
        user_info.pop("password", None)  # Remove a senha por segurança
        user_info["username"] = self.current_user
        return user_info

class ThemeManager:
    """Gerencia o tema da aplicação"""
    
    def __init__(self):
        self.current_theme = self._load_theme()
        self.accent_color = self._load_accent_color()

    def _load_theme(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                    return settings.get("theme", "light")
            return "light"
        except Exception as e:
            Logger.log("load_theme_error", str(e), level="ERROR")
            return "light"
            
    def _load_accent_color(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                    return settings.get("accent_color", ft.colors.BLUE)
            return ft.colors.BLUE
        except Exception as e:
            Logger.log("load_accent_color_error", str(e), level="ERROR")
            return ft.colors.BLUE

    def save_theme(self, theme):
        try:
            settings = self._load_settings()
            settings["theme"] = theme
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=2)
            self.current_theme = theme
            Logger.log("theme_changed", f"Tema alterado para {theme}")
        except Exception as e:
            Logger.log("save_theme_error", str(e), level="ERROR")
            
    def save_accent_color(self, color):
        try:
            settings = self._load_settings()
            settings["accent_color"] = color
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=2)
            self.accent_color = color
            Logger.log("accent_color_changed", f"Cor de destaque alterada para {color}")
        except Exception as e:
            Logger.log("save_accent_color_error", str(e), level="ERROR")

    def _load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def toggle_theme(self):
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.save_theme(new_theme)
        return new_theme

class ModuleLoader:
    """Carrega módulos dinâmicos do sistema"""
    
    def __init__(self):
        self.modules = {}
        self._ensure_modules_dir()
        self._load_modules()

    def _ensure_modules_dir(self):
        os.makedirs(MODULES_DIR, exist_ok=True)
        
        # Cria um módulo de exemplo se não existir nenhum
        example_module_path = os.path.join(MODULES_DIR, "example_module.py")
        if not os.listdir(MODULES_DIR) and not os.path.exists(example_module_path):
            self._create_example_module(example_module_path)

    def _create_example_module(self, path):
        """Cria um módulo de exemplo para demonstração"""
        example_code = '''
import flet as ft

class Module:
    def get_module_info(self):
        return {
            "name": "Calculadora",
            "description": "Uma calculadora simples",
            "version": "1.0.0",
            "icon": ft.icons.CALCULATE,
            "color": ft.colors.GREEN,
        }
        
    def get_view(self):
        self.result = ft.Text("0", size=32, text_align=ft.TextAlign.RIGHT)
        
        def button_clicked(e):
            data = e.control.data
            
            if data == "C":
                self.result.value = "0"
            elif data == "=":
                try:
                    self.result.value = str(eval(self.result.value))
                except:
                    self.result.value = "Erro"
            else:
                if self.result.value == "0" or self.result.value == "Erro":
                    self.result.value = data
                else:
                    self.result.value += data
                    
            e.page.update()
        
        buttons = [
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["C", "0", "=", "+"]
        ]
        
        button_rows = []
        for row in buttons:
            button_row = []
            for button in row:
                btn = ft.ElevatedButton(
                    text=button,
                    data=button,
                    width=60,
                    height=60,
                    on_click=button_clicked,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                    )
                button_row.append(btn)
            button_rows.append(ft.Row(button_row, alignment=ft.MainAxisAlignment.CENTER))
        
        return ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Calculadora", size=24, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=self.result,
                                bgcolor=ft.colors.BLACK12,
                                border_radius=10,
                                padding=10,
                                width=280,
                                height=60,
                                alignment=ft.alignment.center_right,
                            ),
                            ft.Container(height=20),
                            *button_rows
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=20,
                    border_radius=10,
                    bgcolor=ft.colors.SURFACE,
                    width=320,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
'''
        with open(path, "w") as f:
            f.write(example_code)
        Logger.log("example_module_created", "Módulo de exemplo criado")

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
            Logger.log("module_load_error", f"Erro ao carregar módulo {module_name}: {e}", level="ERROR")

    def _register_module(self, module_name, module):
        if hasattr(module, "Module"):
            module_instance = module.Module()
            if hasattr(module_instance, "get_module_info") and hasattr(module_instance, "get_view"):
                self.modules[module_name] = module_instance
                Logger.log("module_loaded", f"Módulo carregado: {module_name}")

    def get_modules(self):
        return self.modules

class LinksManager:
    """Gerencia os links úteis do sistema"""
    
    def __init__(self):
        self.links = self._load_links()
    
    def _load_links(self):
        try:
            if os.path.exists(LINKS_FILE):
                with open(LINKS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except Exception as e:
            Logger.log("load_links_error", str(e), level="ERROR")
            return []
    
    def get_links(self):
        return self.links

class TIHubApp:
    """Aplicação principal do Hub de TI"""
    
    # Adicionar método para carregar informações de contato na classe TIHubApp
    def _load_contact_info(self):
        """Carrega as informações de contato do desenvolvedor"""
        try:
            if os.path.exists(CONTACT_FILE):
                with open(CONTACT_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            # Informações padrão
            default_info = {
                "email": "suporte@hubti.com",
                "phone": "(11) 99999-9999",
                "name": "Equipe de Suporte",
                "description": "Entre em contato para obter ajuda com o sistema."
            }
            # Salva as informações padrão
            with open(CONTACT_FILE, "w", encoding="utf-8") as f:
                json.dump(default_info, f, ensure_ascii=False, indent=2)
            return default_info
        except Exception as e:
            Logger.log("load_contact_error", str(e), level="ERROR")
            return {
                "email": "suporte@hubti.com",
                "phone": "(11) 99999-9999",
                "name": "Equipe de Suporte",
                "description": "Entre em contato para obter ajuda com o sistema."
            }

    # Adicionar método para salvar informações de contato na classe TIHubApp
    def _save_contact_info(self, contact_info):
        """Salva as informações de contato do desenvolvedor"""
        try:
            with open(CONTACT_FILE, "w", encoding="utf-8") as f:
                json.dump(contact_info, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            Logger.log("save_contact_error", str(e), level="ERROR")
            return False

    # Adicionar método para exibir a tela de contato na classe TIHubApp
    def _show_contact_view(self):
        """Exibe a tela de informações de contato"""
        self.module_content.controls.clear()
        
        # Carrega as informações de contato
        contact_info = self._load_contact_info()
        
        # Título
        title = ft.Text("Contato para Suporte", size=24, weight=ft.FontWeight.BOLD)
        
        # Card com informações de contato
        contact_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.icons.SUPPORT_AGENT, size=40, color=ft.colors.BLUE),
                                ft.Container(width=20),
                                ft.Column(
                                    [
                                        ft.Text(contact_info.get("name", "Equipe de Suporte"), 
                                                size=20, 
                                                weight=ft.FontWeight.BOLD),
                                        ft.Text(contact_info.get("description", ""), 
                                                size=14, 
                                                color=ft.colors.BLACK54),
                                    ],
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        ft.Divider(),
                        ft.Container(height=10),
                        ft.Row(
                            [
                                ft.Icon(ft.icons.EMAIL, color=ft.colors.BLUE),
                                ft.Container(width=10),
                                ft.Text(f"E-mail: {contact_info.get('email', '')}", 
                                        size=16, 
                                        selectable=True),
                            ],
                        ),
                        ft.Container(height=10),
                        ft.Row(
                            [
                                ft.Icon(ft.icons.PHONE, color=ft.colors.BLUE),
                                ft.Container(width=10),
                                ft.Text(f"Telefone: {contact_info.get('phone', '')}", 
                                        size=16, 
                                        selectable=True),
                            ],
                        ),
                    ],
                    spacing=10,
                ),
                padding=30,
                width=600,
            ),
            elevation=4,
        )
    
        # Botão para editar informações (apenas para admin)
        edit_button = ft.ElevatedButton(
            "Editar Informações de Contato",
            icon=ft.icons.EDIT,
            on_click=self._show_edit_contact_dialog,
            visible=self.auth_manager.is_admin(),
        )
    
        # Layout principal
        self.module_content.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        title,
                        ft.Container(height=20),
                        contact_card,
                        ft.Container(height=20),
                        edit_button,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=20,
                expand=True,
            )
        )
    
        self.page.update()

    # Adicionar método para exibir o diálogo de edição de contato na classe TIHubApp
    def _show_edit_contact_dialog(self, e):
        """Exibe o diálogo para editar informações de contato"""
        if not self.auth_manager.is_admin():
            return
            
        # Carrega as informações atuais
        contact_info = self._load_contact_info()
        
        # Campos do formulário
        name_field = ft.TextField(
            label="Nome",
            value=contact_info.get("name", ""),
            width=400,
        )
        
        email_field = ft.TextField(
            label="E-mail",
            value=contact_info.get("email", ""),
            width=400,
        )
        
        phone_field = ft.TextField(
            label="Telefone",
            value=contact_info.get("phone", ""),
            width=400,
        )
        
        description_field = ft.TextField(
            label="Descrição",
            value=contact_info.get("description", ""),
            width=400,
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        
        # Função para salvar as alterações
        def save_contact_info(e):
            new_contact_info = {
                "name": name_field.value,
                "email": email_field.value,
                "phone": phone_field.value,
                "description": description_field.value,
            }
            
            success = self._save_contact_info(new_contact_info)
            
            # Fecha o diálogo
            edit_dialog.open = False
            self.page.update()
            
            # Exibe mensagem de sucesso ou erro
            if success:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("Informações de contato atualizadas com sucesso"),
                        bgcolor=ft.colors.GREEN,
                        action="OK",
                    )
                )
                # Atualiza a tela de contato
                self._show_contact_view()
            else:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("Erro ao atualizar informações de contato"),
                        bgcolor=ft.colors.RED,
                        action="OK",
                    )
                )
        
        # Cria o diálogo
        edit_dialog = ft.AlertDialog(
            title=ft.Text("Editar Informações de Contato"),
            content=ft.Column(
                [
                    name_field,
                    email_field,
                    phone_field,
                    description_field,
                ],
                spacing=20,
                width=400,
                height=300,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(edit_dialog, "open", False)),
                ft.ElevatedButton("Salvar", on_click=save_contact_info),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        self.page.dialog = edit_dialog
        edit_dialog.open = True
        self.page.update()

    # Adicionar método para mostrar a tela do PACS
    def _show_pacs_view(self):
        """Exibe a tela do módulo PACS"""
        self.module_content.controls.clear()

        try:
            # Caminho para o módulo PACS (na pasta modules/Pacs)
            pacs_module_path = os.path.join(MODULES_DIR, "Pacs", "pacs.py")
        
            # Verifica se o módulo existe
            if os.path.exists(pacs_module_path):
                # Adiciona o diretório modules ao sys.path temporariamente para resolver importações
                import sys
                original_path = sys.path.copy()
                
                # Adiciona os diretórios necessários ao sys.path
                if MODULES_DIR not in sys.path:
                    sys.path.insert(0, MODULES_DIR)
                
                # Adiciona também o diretório Pacs ao sys.path
                pacs_dir = os.path.join(MODULES_DIR, "Pacs")
                if os.path.exists(pacs_dir) and pacs_dir not in sys.path:
                    sys.path.insert(0, pacs_dir)
                
                try:
                    # Carrega o módulo usando importlib diretamente na thread principal
                    import importlib
                    
                    # Usa uma abordagem mais direta para importar o módulo
                    if os.path.exists(pacs_dir):
                        # Se o diretório Pacs existe, importa como um pacote
                        pacs_module = importlib.import_module("Pacs.pacs")
                    else:
                        # Tenta importar diretamente
                        spec = importlib.util.spec_from_file_location("pacs", pacs_module_path)
                        pacs_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(pacs_module)
                
                    # Instancia o módulo
                    pacs_instance = pacs_module.Module()
                
                    # Adiciona a visualização do módulo
                    self.module_content.controls.append(pacs_instance.get_view())
                
                    # Configura a página para o módulo se tiver o método did_mount
                    if hasattr(pacs_instance, "did_mount"):
                        pacs_instance.did_mount(self.page)
                    
                except ImportError as e:
                    # Erro específico de importação
                    missing_module = str(e).split()[-1].strip("'") if "No module named" in str(e) else ""
                
                    self.module_content.controls.append(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "Erro ao carregar o módulo PACS",
                                        size=24,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.colors.RED,
                                    ),
                                    ft.Text(
                                        f"Erro de importação: {str(e)}",
                                        size=16,
                                        color=ft.colors.RED,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            f"Módulo não encontrado: '{missing_module}'",
                                            size=14,
                                            color=ft.colors.WHITE,
                                        ),
                                        padding=10,
                                        bgcolor=ft.colors.RED,
                                        border_radius=5,
                                    ),
                                    ft.Container(height=20),
                                    ft.Text(
                                        "Solução: Verifique se o módulo está disponível na pasta 'modules/Pacs'",
                                        size=16,
                                        color=ft.colors.BLUE,
                                    ),
                                    ft.Container(height=20),
                                    ft.ElevatedButton(
                                        "Voltar para a tela inicial",
                                        icon=ft.icons.HOME,
                                        on_click=lambda e: self._show_home_view(),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            alignment=ft.alignment.center,
                            expand=True,
                        )
                    )
                except Exception as e:
                    # Captura erros específicos relacionados a threads e sinais
                    error_message = str(e)
                    if "signal" in error_message and "thread" in error_message:
                        error_message = "Erro de thread: O módulo PACS utiliza recursos que só funcionam na thread principal."
                    
                    self.module_content.controls.append(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "Erro ao carregar o módulo PACS",
                                        size=24,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.colors.RED,
                                    ),
                                    ft.Text(
                                        error_message,
                                        size=16,
                                        color=ft.colors.RED,
                                    ),
                                    ft.Container(height=20),
                                    ft.Text(
                                        "Solução: Verifique se o módulo PACS está implementado corretamente para funcionar com o Flet.",
                                        size=16,
                                        color=ft.colors.BLUE,
                                    ),
                                    ft.Container(height=20),
                                    ft.ElevatedButton(
                                        "Voltar para a tela inicial",
                                        icon=ft.icons.HOME,
                                        on_click=lambda e: self._show_home_view(),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            alignment=ft.alignment.center,
                            expand=True,
                        )
                    )
                finally:
                    # Restaura o sys.path original
                    sys.path = original_path
            else:
                # Se o módulo não existir, exibe uma mensagem
                self.module_content.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Módulo PACS não encontrado",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.colors.RED,
                                ),
                                ft.Text(
                                    f"O arquivo {pacs_module_path} não foi encontrado. Verifique se o módulo existe na pasta 'modules/Pacs'.",
                                    size=16,
                                    color=ft.colors.BLACK54,
                                ),
                                ft.Container(height=20),
                                ft.ElevatedButton(
                                    "Voltar para a tela inicial",
                                    icon=ft.icons.HOME,
                                    on_click=lambda e: self._show_home_view(),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        alignment=ft.alignment.center,
                        expand=True,
                    )
                )
        except Exception as e:
            # Em caso de erro, exibe uma mensagem
            self.module_content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "Erro ao carregar o módulo PACS",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.RED,
                            ),
                            ft.Text(
                                str(e),
                                size=16,
                                color=ft.colors.RED,
                            ),
                            ft.Container(height=20),
                            ft.ElevatedButton(
                                "Voltar para a tela inicial",
                                icon=ft.icons.HOME,
                                on_click=lambda e: self._show_home_view(),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )

        self.page.update()

    # Método para criar o card do PACS
    def _create_pacs_card(self):
        """Cria um card para o módulo PACS"""
        # Botão de ação
        action_button = ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Text("Abrir", size=14, weight=ft.FontWeight.BOLD),
                    ft.Icon(ft.icons.ARROW_FORWARD, size=16),
                ],
                spacing=5,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                color={
                    ft.ControlState.HOVERED: ft.colors.WHITE,
                    ft.ControlState.DEFAULT: ft.colors.WHITE,
                },
                bgcolor={
                    ft.ControlState.HOVERED: ft.colors.PURPLE,
                    ft.ControlState.DEFAULT: ft.colors.BLACK45,
                },
                elevation={"pressed": 0, "": 1},
                animation_duration=200,
            ),
            on_click=lambda e: self._show_pacs_view(),
        )
        
        # Card com layout flexível e responsivo
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        # Cabeçalho do card com ícone e título
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Icon(
                                        ft.icons.IMAGE,
                                        size=32,
                                        color=ft.colors.PURPLE,
                                    ),
                                    padding=10,
                                    bgcolor="#00000012",
                                    border_radius=8,
                                ),
                                ft.Container(width=10),
                                ft.Column(
                                    [
                                        ft.Text(
                                            "PACS",
                                            size=18,
                                            weight=ft.FontWeight.BOLD,
                                            no_wrap=False,
                                            max_lines=2,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                        ft.Text(
                                            "Sistema de Comunicação e Arquivamento de Imagens",
                                            size=12,
                                            color=ft.colors.BLACK54,
                                            no_wrap=False,
                                            max_lines=2,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        
                        # Espaçador flexível
                        ft.Container(
                            expand=True,
                            height=10,
                        ),
                        
                        # Botão de ação
                        ft.Container(
                            content=action_button,
                            alignment=ft.alignment.center_right,
                        ),
                    ],
                    spacing=10,
                    expand=True,
                ),
                padding=15,
                expand=True,
                height=160,  # Altura fixa para manter consistência
            ),
            elevation=2,
            surface_tint_color=ft.colors.SURFACE_VARIANT,
        )

    # Modificar o método __init__ da classe TIHubApp para inicializar as informações de contato
    def __init__(self, page: ft.Page):
        self.page = page
        self.auth_manager = AuthManager()
        self.theme_manager = ThemeManager()
        self.module_loader = ModuleLoader()
        self.links_manager = LinksManager()
        self.is_authenticated = False
        self.current_module = None
        self.module_index_map = {"home": 0, "links": 1}
        self.module_content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self.contact_info = self._load_contact_info()  # Carrega as informações de contato
        
        # Configuração inicial da página
        self.page.title = APP_NAME
        self.page.theme_mode = ft.ThemeMode.LIGHT if self.theme_manager.current_theme == "light" else ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.window.width = 1100
        self.page.window.height = 800
        self.page.window.min_width = 400
        self.page.window.min_height = 600
        self.page.theme = ft.Theme(color_scheme_seed=self.theme_manager.accent_color)
        self.page.on_resized = self._handle_resize  # Usando on_resized em vez de on_resize
        
        # Inicializa a interface
        self._init_ui()

    def _handle_resize(self, e):
        # Atualiza a interface quando a janela é redimensionada
        if self.is_authenticated:
            self.page.update()
        else:
            # Se estiver na tela de login, atualiza a visualização para ajustar a imagem
            if self.page.route == "/login":
                # Força a atualização completa da tela para ajustar a imagem de fundo
                self._show_login_view()

    def _init_ui(self):
        if not self.is_authenticated:
            self._show_login_view()
        else:
            self._show_main_view()

    # Modificar o método _show_login_view para adicionar suporte a background de imagem/vídeo
    def _show_login_view(self):
        self.page.views.clear()
        self.username_field = self._create_text_field("Usuário", False)
        self.password_field = self._create_text_field("Senha", True)
        
        # Mensagem de erro
        self.login_error_text = ft.Text(color=ft.colors.RED_500, size=12, visible=False)

        # Verifica se a pasta assets existe
        if not os.path.exists("assets"):
            os.makedirs("assets", exist_ok=True)
        
        # Verifica se o logo existe
        logo_path = "assets/log.jpg"
        if not os.path.exists(logo_path):
            # Usa um placeholder se o logo não existir
            logo = ft.Container(
                content=ft.Text("HUB DE TI", size=32, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE),
                alignment=ft.alignment.center,
                height=100,
                border_radius=50,  # Torna o container arredondado
                border=ft.border.all(1, ft.colors.WHITE24),  # Adiciona borda sutil
            )
        else:
            # Usa o logo se existir com formato arredondado
            # Container para a imagem com borda e recorte circular
            logo = ft.Container(
                content=ft.Image(
                    src=logo_path, 
                    width=120, 
                    height=120, 
                    fit=ft.ImageFit.COVER
                ),
                width=120,
                height=120,
                border_radius=60,  # Metade da largura/altura para tornar circular
                border=ft.border.all(2, ft.colors.WHITE24),  # Adiciona borda sutil diretamente no container da imagem
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,  # Suaviza as bordas
                bgcolor=ft.colors.BLACK12,  # Fundo sutil para destacar o logo
            )
        
        login_button = ft.ElevatedButton(
            text="Entrar", 
            width=320, 
            on_click=self._handle_login,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
            )
        )

        # Verifica se existe uma imagem de background
        bg_image_path = "assets/banner.jpg"
        bg_video_path = "assets/login_bg.mp4"
        
        # Container para o conteúdo de login
        login_content = ft.Container(
            content=ft.Column(
                [
                    logo, 
                    ft.Container(height=40), 
                    self._create_login_card(login_button)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.alignment.center,
        )
        
        # Verifica se existe um vídeo de background
        if os.path.exists(bg_video_path):
            # Usa vídeo como background (implementação básica, pois o Flet não suporta vídeo de background diretamente)
            login_view = ft.View(
                route="/login",
                controls=[
                    ft.Stack([
                        ft.Container(
                            content=ft.Text("", size=1),  # Container vazio para o vídeo (seria implementado com JavaScript)
                            expand=True,
                            bgcolor=ft.colors.BLACK,
                        ),
                        ft.Container(
                            content=login_content,
                            expand=True,
                            bgcolor=ft.colors.with_opacity(0.7, ft.colors.BLACK),
                        ),
                    ]),
                ],
            )
        # Verifica se existe uma imagem de background
        elif os.path.exists(bg_image_path):
            # Usa imagem como background com ajustes para responsividade e correção do corte
            login_view = ft.View(
                route="/login",
                controls=[
                    ft.Container(
                        content=ft.Stack([
                            # Container para a imagem de fundo com posicionamento responsivo
                            ft.Container(
                                content=ft.Image(
                                    src=bg_image_path,
                                    fit=ft.ImageFit.COVER,  # Garante que a imagem cubra todo o container
                                    width=None,  # Permite que a largura seja determinada pelo container pai
                                    height=None,  # Permite que a altura seja determinada pelo container pai
                                    scale=1.1,   # Escala a imagem para evitar cortes nas bordas
                            ),
                            expand=True,  # Expande para preencher o espaço disponível
                            border_radius=12,  # Arredonda levemente as bordas da imagem
                            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,  # Suaviza as bordas
                            margin=0,  # Remove margens para evitar espaços em branco
                        ),
                        # Container para o conteúdo de login com fundo semi-transparente
                        ft.Container(
                            content=login_content,
                            expand=True,
                            bgcolor=ft.colors.with_opacity(0.7, ft.colors.BLACK),
                            border_radius=12,  # Arredonda levemente as bordas
                        ),
                    ]),
                    expand=True,  # Garante que o container ocupe toda a tela
                    padding=0,  # Remove o padding para evitar espaços indesejados
                ),
            ],
            padding=0,  # Remove o padding para evitar espaços indesejados
        )
        else:
            # Usa o layout padrão sem background
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
            border_radius=8,  # Arredonda as bordas do campo
            border_color=ft.colors.WHITE24,  # Cor da borda mais suave
            focused_border_color=ft.colors.WHITE,  # Cor da borda quando focado
            focused_border_width=2,  # Largura da borda quando focado
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
            border=ft.border.all(1, ft.colors.WHITE24),  # Movido para o Container
            border_radius=16,  # Movido para o Container
        ),
        # Removido: border e border_radius do Card
        surface_tint_color=ft.colors.SURFACE_VARIANT,
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
        self.module_index_map = {"home": 0, "links": 1}
        
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
                # Removido o item Links Úteis da barra de navegação
            ],
            on_change=self._handle_rail_change,
        )

        # Adicionar módulos carregados ao rail
        for module_name, module in self.module_loader.get_modules().items():
            # Pula o módulo de Links Úteis para não aparecer na barra lateral
            if module_name == "useful_links":
                continue
            
            module_info = module.get("module_info") if hasattr(module, "get") else module.get_module_info()
            icon = module_info.get("icon", ft.icons.EXTENSION_OUTLINED)
            selected_icon = module_info.get("icon", ft.icons.EXTENSION)
            
            modules_rail.destinations.append(
                ft.NavigationRailDestination(
                    icon=icon,
                    selected_icon=selected_icon,
                    label=module_info.get("name", module_name),
                )
            )
            # Mapeia o índice do módulo
            self.module_index_map[module_name] = len(modules_rail.destinations) - 1

        # Adicionar opção de administração para usuários admin
        if self.auth_manager.is_admin():
            modules_rail.destinations.append(
                ft.NavigationRailDestination(
                    icon=ft.icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                    selected_icon=ft.icons.ADMIN_PANEL_SETTINGS,
                    label="Administração",
                )
            )
            self.module_index_map["admin"] = len(modules_rail.destinations) - 1

        return modules_rail

    # Modificar o método _handle_rail_change para incluir a opção de contato
    def _handle_rail_change(self, e):
        selected_index = e.control.selected_index
        if selected_index == 0:
            self._show_home_view()
        elif selected_index == self.module_index_map.get("admin", -1):
            self._show_admin_view()
        else:
            # Encontra o nome do módulo pelo índice
            module_name = None
            for name, index in self.module_index_map.items():
                if index == selected_index and name != "home" and name != "admin" and name != "links":
                    module_name = name
                    break
            
            if module_name:
                self._show_module_view(module_name)

    def _show_home_view(self):
        self.module_content.controls.clear()
    
        # Container principal com padding responsivo
        main_container = ft.Container(
            content=ft.Column(
                [
                    # Cabeçalho com mensagem de boas-vindas
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    f"Bem-vindo, {self.auth_manager.get_current_user_info()['name']}!",
                                    size=28,
                                    weight=ft.FontWeight.BOLD,
                                    no_wrap=False,
                                ),
                                ft.Text(
                                    "Selecione um módulo para começar:",
                                    size=16,
                                    color=ft.colors.BLACK54,
                                ),
                            ],
                            spacing=5,
                        ),
                        margin=ft.margin.only(bottom=20),
                    ),
                
                    # Container adaptativo para os cards
                    ft.Container(
                        content=ft.ResponsiveRow(
                            [
                                # Card para Links Úteis
                                ft.Container(
                                    content=self._create_links_card(),
                                    col={"xs": 12, "sm": 12, "md": 6, "lg": 4, "xl": 3},
                                    padding=10,
                                ),
                                # Card para PACS
                                ft.Container(
                                    content=self._create_pacs_card(),
                                    col={"xs": 12, "sm": 12, "md": 6, "lg": 4, "xl": 3},
                                    padding=10,
                                ),
                                # Cards para os módulos carregados
                                *[
                                    ft.Container(
                                        content=self._create_module_card(module_name, module),
                                        col={"xs": 12, "sm": 12, "md": 6, "lg": 4, "xl": 3},
                                        padding=10,
                                    )
                                    for module_name, module in self.module_loader.get_modules().items()
                                    if module_name != "useful_links"  # Pula o módulo de Links Úteis para não duplicar
                                ]
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        expand=True,
                    ),
                ],
                spacing=0,
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.padding.all(20),
            expand=True,
        )
    
        self.module_content.controls.append(main_container)
        self.current_module = None  # Marca que estamos na tela inicial
        self.page.update()

    def _create_links_card(self):
        """Cria um card para o módulo de Links Úteis"""
        # Botão de ação melhorado
        action_button = ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Text("Abrir", size=14, weight=ft.FontWeight.BOLD),
                    ft.Icon(ft.icons.ARROW_FORWARD, size=16),
                ],
                spacing=5,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                color={
                    ft.ControlState.HOVERED: ft.colors.WHITE,
                    ft.ControlState.DEFAULT: ft.colors.WHITE,
                },
                bgcolor={
                    ft.ControlState.HOVERED: ft.colors.INDIGO,
                    ft.ControlState.DEFAULT: ft.colors.BLACK45,
                },
                elevation={"pressed": 0, "": 1},
                animation_duration=200,
            ),
            on_click=lambda e: self._open_links_from_card(e),
        )
        
        # Card com layout flexível e responsivo
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        # Cabeçalho do card com ícone e título
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Icon(
                                        ft.icons.LINK,
                                        size=32,
                                        color=ft.colors.INDIGO,
                                    ),
                                    padding=10,
                                    bgcolor="#00000012",
                                    border_radius=8,
                                ),
                                ft.Container(width=10),
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Links Úteis",
                                            size=18,
                                            weight=ft.FontWeight.BOLD,
                                            no_wrap=False,
                                            max_lines=2,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                        ft.Text(
                                            "Gerenciador de links úteis para a equipe OGS",
                                            size=12,
                                            color=ft.colors.BLACK54,
                                            no_wrap=False,
                                            max_lines=2,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        
                        # Espaçador flexível
                        ft.Container(
                            expand=True,
                            height=10,
                        ),
                        
                        # Botão de ação
                        ft.Container(
                            content=action_button,
                            alignment=ft.alignment.center_right,
                        ),
                    ],
                    spacing=10,
                    expand=True,
                ),
                padding=15,
                expand=True,
                height=160,  # Altura fixa para manter consistência
            ),
            elevation=2,
            surface_tint_color=ft.colors.SURFACE_VARIANT,
        )

    def _open_links_from_card(self, e):
        # Não precisa mais atualizar o índice selecionado no NavigationRail
        # já que removemos o item Links Úteis da barra lateral
    
        # Mostra a tela de links diretamente
        self._show_links_view()
        self.page.update()

    def _show_links_view(self):
        """Exibe a tela de Links Úteis"""
        self.module_content.controls.clear()
        
        # Carrega o módulo de links úteis
        try:
            # Verifica se o módulo já existe
            module_path = os.path.join(MODULES_DIR, "useful_links.py")
            if not os.path.exists(module_path):
                # Se não existir, cria o diretório e o arquivo
                os.makedirs(MODULES_DIR, exist_ok=True)
                
                # Importa o módulo
                spec = importlib.util.spec_from_file_location("useful_links", module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Instancia o módulo
                links_module = module.Module()
            else:
                # Se já existir, carrega normalmente
                spec = importlib.util.spec_from_file_location("useful_links", module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Instancia o módulo
                links_module = module.Module()
            
            # Adiciona a visualização do módulo
            self.module_content.controls.append(links_module.get_view())
            
            # Configura a página para o módulo
            links_module.did_mount(self.page)
            
        except Exception as e:
            # Em caso de erro, exibe uma mensagem
            self.module_content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "Erro ao carregar o módulo de Links Úteis",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.RED,
                            ),
                            ft.Text(
                                str(e),
                                size=14,
                                color=ft.colors.RED,
                            ),
                        ],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )
        
        self.page.update()

    def _create_module_card(self, module_name, module):
        """Cria um card de módulo com layout melhorado e responsivo"""
        module_info = module.get("module_info") if hasattr(module, "get") else module.get_module_info()
        
        # Botão de ação melhorado
        action_button = ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Text("Abrir", size=14, weight=ft.FontWeight.BOLD),
                    ft.Icon(ft.icons.ARROW_FORWARD, size=16),
                ],
                spacing=5,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                color={
                    ft.ControlState.HOVERED: ft.colors.WHITE,
                    ft.ControlState.DEFAULT: ft.colors.WHITE,
                },
                bgcolor={
                    ft.ControlState.HOVERED: module_info.get("color", ft.colors.BLUE),
                    ft.ControlState.DEFAULT: ft.colors.BLACK45,
                },
                elevation={"pressed": 0, "": 1},
                animation_duration=200,
            ),
            on_click=lambda e, name=module_name: self._open_module_from_card(e, name),
        )
    
        # Card com layout flexível e responsivo
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        # Cabeçalho do card com ícone e título
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Icon(
                                        module_info.get("icon", ft.icons.EXTENSION),
                                        size=32,
                                        color=module_info.get("color", ft.colors.BLUE),
                                    ),
                                    padding=10,
                                    bgcolor="#00000012",
                                    border_radius=8,
                                ),
                                ft.Container(width=10),
                                ft.Column(
                                    [
                                        ft.Text(
                                            module_info.get("name", module_name),
                                            size=18,
                                            weight=ft.FontWeight.BOLD,
                                            no_wrap=False,
                                            max_lines=2,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                        ft.Text(
                                            module_info.get("description", ""),
                                            size=12,
                                            color=ft.colors.BLACK54,
                                            no_wrap=False,
                                            max_lines=2,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        
                        # Espaçador flexível
                        ft.Container(
                            expand=True,
                            height=10,
                        ),
                        
                        # Botão de ação
                        ft.Container(
                            content=action_button,
                            alignment=ft.alignment.center_right,
                        ),
                    ],
                    spacing=10,
                    expand=True,
                ),
                padding=15,
                expand=True,
                height=160,  # Altura fixa para manter consistência
            ),
            elevation=2,
            surface_tint_color=ft.colors.SURFACE_VARIANT,
        )

    def _open_module_from_card(self, e, module_name):
        # Atualiza o índice selecionado no NavigationRail
        for control in self.page.views[0].controls[0].controls[0].content.controls:
            # Aqui estava o erro de indentação - corrigido
            if isinstance(control, ft.NavigationRail):
                control.selected_index = self.module_index_map.get(module_name, 0)
                break
                
        # Mostra o módulo
        self._show_module_view(module_name)
        self.page.update()

    def _show_admin_view(self):
        """Exibe a tela de administração"""
        self.module_content.controls.clear()
        
        # Título
        title = ft.Text("Painel de Administração", size=24, weight=ft.FontWeight.BOLD)
        
        # Seção de gerenciamento de usuários
        users_title = ft.Text("Gerenciamento de Usuários", size=18, weight=ft.FontWeight.BOLD)
        
        # Campos para adicionar usuário
        self.new_username = ft.TextField(label="Nome de usuário", width=250)
        self.new_password = ft.TextField(label="Senha", password=True, can_reveal_password=True, width=250)
        self.new_name = ft.TextField(label="Nome completo", width=250)
        self.new_role = ft.Dropdown(
            label="Função",
            width=250,
            options=[
                ft.dropdown.Option("user", "Usuário"),
                ft.dropdown.Option("admin", "Administrador"),
            ],
            value="user",
        )
        
        # Botão para adicionar usuário
        add_user_button = ft.ElevatedButton(
            "Adicionar Usuário",
            icon=ft.icons.PERSON_ADD,
            on_click=self._handle_add_user,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )
        
        # Mensagem de status
        self.admin_status_message = ft.Text(visible=False, size=14)
        
        # Lista de usuários
        users = self.auth_manager.get_users()
        user_list = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Usuário")),
                ft.DataColumn(ft.Text("Nome")),
                ft.DataColumn(ft.Text("Função")),
                ft.DataColumn(ft.Text("Criado em")),
                ft.DataColumn(ft.Text("Ações")),
            ],
            rows=[],
            border_radius=10,
        )
        
        # Diálogo para editar usuário
        self.edit_user_dialog = ft.AlertDialog(
            title=ft.Text("Editar Usuário"),
            content=ft.Column(
                [
                    ft.Text("Carregando...", size=14),
                ],
                tight=True,
                spacing=20,
                width=400,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._close_edit_dialog),
                ft.ElevatedButton("Salvar", on_click=self._handle_save_user_edit),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        for username, user_data in users.items():
            # Formata a data de criação
            created_at = user_data.get("created_at", "")
            try:
                dt = datetime.fromisoformat(created_at)
                formatted_date = dt.strftime("%d/%m/%Y %H:%M")
            except:
                formatted_date = created_at
                
            # Botões de ação
            action_row = ft.Row([
                # Botão de editar
                ft.IconButton(
                    icon=ft.icons.EDIT,
                    tooltip="Editar usuário",
                    on_click=lambda e, u=username: self._show_edit_user_dialog(e, u),
                    disabled=username == "admin" and not self.auth_manager.is_admin(),
                ),
                # Botão de remover
                ft.IconButton(
                    icon=ft.icons.DELETE,
                    tooltip="Remover usuário",
                    on_click=lambda e, u=username: self._handle_remove_user(e, u),
                    disabled=username == "admin",
                ),
            ], spacing=0)
            
            user_list.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(username)),
                        ft.DataCell(ft.Text(user_data.get("name", ""))),
                        ft.DataCell(ft.Text("Administrador" if user_data.get("role") == "admin" else "Usuário")),
                        ft.DataCell(ft.Text(formatted_date)),
                        ft.DataCell(action_row),
                    ]
                )
            )
        
        # Seção de configurações do sistema
        system_title = ft.Text("Configurações do Sistema", size=18, weight=ft.FontWeight.BOLD)
        
        # Seletor de cor de destaque
        color_options = [
            ft.dropdown.Option(ft.colors.BLUE, "Azul"),
            ft.dropdown.Option(ft.colors.RED, "Vermelho"),
            ft.dropdown.Option(ft.colors.GREEN, "Verde"),
            ft.dropdown.Option(ft.colors.PURPLE, "Roxo"),
            ft.dropdown.Option(ft.colors.ORANGE, "Laranja"),
            ft.dropdown.Option(ft.colors.TEAL, "Turquesa"),
        ]
        
        self.accent_color_dropdown = ft.Dropdown(
            label="Cor de destaque",
            width=250,
            options=color_options,
            value=self.theme_manager.accent_color,
            on_change=self._handle_accent_color_change,
        )
        
        # Layout responsivo para a tela de administração
        admin_layout = ft.ResponsiveRow([
            # Coluna de formulário
            ft.Container(
                content=ft.Column(
                    [
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("Adicionar Novo Usuário", weight=ft.FontWeight.BOLD, size=16),
                                        ft.Divider(),
                                        self.new_username,
                                        self.new_password,
                                        self.new_name,
                                        self.new_role,
                                        ft.Container(
                                            content=add_user_button,
                                            alignment=ft.alignment.center_right,
                                            margin=ft.margin.only(top=10),
                                        ),
                                    ],
                                    spacing=10,
                                ),
                                padding=20,
                            ),
                            elevation=2,
                        ),
                    ],
                ),
                col={"xs": 12, "sm": 12, "md": 4, "lg": 3},
                padding=10,
            ),
            
            # Coluna de lista de usuários
            ft.Container(
                content=ft.Column(
                    [
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("Usuários Cadastrados", weight=ft.FontWeight.BOLD, size=16),
                                        ft.Divider(),
                                        user_list,
                                    ],
                                    spacing=10,
                                ),
                                padding=20,
                            ),
                            elevation=2,
                        ),
                    ],
                ),
                col={"xs": 12, "sm": 12, "md": 8, "lg": 9},
                padding=10,
            ),
        ])
        
        # Adiciona os controles à tela de administração
        self.module_content.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        # Cabeçalho
                        ft.Container(
                            content=title,
                            margin=ft.margin.only(bottom=20),
                        ),
                        
                        # Seção de usuários
                        ft.Container(
                            content=users_title,
                            margin=ft.margin.only(bottom=10),
                        ),
                        admin_layout,
                        self.admin_status_message,
                        
                        # Seção de configurações
                        ft.Container(
                            content=system_title,
                            margin=ft.margin.only(top=30, bottom=10),
                        ),
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("Aparência do Sistema", weight=ft.FontWeight.BOLD, size=16),
                                        ft.Divider(),
                                        self.accent_color_dropdown,
                                    ],
                                    spacing=10,
                                ),
                                padding=20,
                            ),
                            elevation=2,
                        ),
                    ],
                    spacing=0,
                ),
                padding=20,
                expand=True,
            )
        )
        
        self.page.update()
    
    def _show_edit_user_dialog(self, e, username):
        """Exibe o diálogo para editar um usuário"""
        user_data = self.auth_manager.get_users().get(username, {})
        
        # Campos para editar usuário
        self.edit_username_field = ft.TextField(
            label="Nome de usuário",
            value=username,
            read_only=True,
            width=400,
        )
        
        self.edit_name_field = ft.TextField(
            label="Nome completo",
            value=user_data.get("name", ""),
            width=400,
        )
        
        self.edit_role_field = ft.Dropdown(
            label="Função",
            width=400,
            options=[
                ft.dropdown.Option("user", "Usuário"),
                ft.dropdown.Option("admin", "Administrador"),
            ],
            value=user_data.get("role", "user"),
            disabled=username == "admin",  # Não permite alterar a função do admin
        )
        
        self.edit_password_field = ft.TextField(
            label="Nova senha (deixe em branco para manter a atual)",
            password=True,
            can_reveal_password=True,
            width=400,
        )
        
        # Atualiza o conteúdo do diálogo
        self.edit_user_dialog.content = ft.Column(
            [
                self.edit_username_field,
                self.edit_name_field,
                self.edit_role_field,
                self.edit_password_field,
            ],
            tight=True,
            spacing=20,
            width=400,
        )
        
        # Exibe o diálogo
        self.page.dialog = self.edit_user_dialog
        self.edit_user_dialog.open = True
        self.page.update()
    
    def _close_edit_dialog(self, e):
        """Fecha o diálogo de edição de usuário"""
        self.edit_user_dialog.open = False
        self.page.update()
    
    def _handle_save_user_edit(self, e):
        """Salva as alterações do usuário"""
        username = self.edit_username_field.value
        name = self.edit_name_field.value
        role = self.edit_role_field.value
        password = self.edit_password_field.value if self.edit_password_field.value else None
        
        if not name:
            self.admin_status_message.value = "O nome não pode ficar em branco"
            self.admin_status_message.color = ft.colors.RED
            self.admin_status_message.visible = True
            self._close_edit_dialog(e)
            self.page.update()
            return
        
        success, message = self.auth_manager.update_user(username, name, role, password)
        
        self.admin_status_message.value = message
        self.admin_status_message.color = ft.colors.GREEN if success else ft.colors.RED
        self.admin_status_message.visible = True
        
        # Fecha o diálogo
        self._close_edit_dialog(e)
        
        # Atualiza a tela
        if success:
            self._show_admin_view()
        else:
            self.page.update()
        
    def _handle_add_user(self, e):
        """Adiciona um novo usuário"""
        username = self.new_username.value
        password = self.new_password.value
        name = self.new_name.value
        role = self.new_role.value
        
        if not username or not password or not name:
            self.admin_status_message.value = "Preencha todos os campos"
            self.admin_status_message.color = ft.colors.RED
            self.admin_status_message.visible = True
            self.page.update()
            return
            
        success, message = self.auth_manager.add_user(username, password, name, role)
        
        self.admin_status_message.value = message
        self.admin_status_message.color = ft.colors.GREEN if success else ft.colors.RED
        self.admin_status_message.visible = True
        
        if success:
            # Limpa os campos
            self.new_username.value = ""
            self.new_password.value = ""
            self.new_name.value = ""
            self.new_role.value = "user"
            
            # Atualiza a tela
            self._show_admin_view()
        else:
            self.page.update()
            
    def _handle_remove_user(self, e, username):
        """Remove um usuário"""
        success, message = self.auth_manager.remove_user(username)
        
        self.admin_status_message.value = message
        self.admin_status_message.color = ft.colors.GREEN if success else ft.colors.RED
        self.admin_status_message.visible = True
        
        # Atualiza a tela
        if success:
            self._show_admin_view()
        else:
            self.page.update()
            
    def _handle_accent_color_change(self, e):
        """Altera a cor de destaque do sistema"""
        color = self.accent_color_dropdown.value
        self.theme_manager.save_accent_color(color)
        
        # Atualiza o tema da página
        self.page.theme = ft.Theme(color_scheme_seed=color)
        self.page.update()

    def _handle_logout(self, e):
        # Redefine o estado de autenticação
        self.is_authenticated = False
        self.auth_manager.current_user = None
        
        # Redireciona para a tela de login
        self._show_login_view()

    def _show_module_view(self, module_name):
        module = self.module_loader.get_modules().get(module_name)
        if module:
            self.module_content.controls.clear()
            self.module_content.controls.append(module.get_view())
            self.page.update()

    # Modificar o método _create_sidebar para adicionar o botão de suporte
    def _create_sidebar(self, modules_rail, theme_switch):
        """Cria a barra lateral com layout melhorado e responsivo"""
        # Verifica se o logo existe
        logo_path = "assets/log.jpg"
        if not os.path.exists(logo_path):
            # Usa um placeholder se o logo não existir
            logo = ft.Container(
                content=ft.Text(
                    "HUB DE TI",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.BLUE,
                ),
                padding=ft.padding.all(20),
                alignment=ft.alignment.center,
            )
        else:
            # Usa o logo se existir
            logo = ft.Container(
                content=ft.Image(
                    src=logo_path,
                    width=200,  # Aumentado para ocupar mais espaço
                    height=80,   # Aumentado para ocupar mais espaço
                    fit=ft.ImageFit.CONTAIN,
                ),
                padding=ft.padding.all(20),
                alignment=ft.alignment.center,
            )
        
        # Botão de encerrar sessão melhorado
        logout_button = ft.TextButton(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.icons.LOGOUT,
                        color=ft.colors.ERROR,
                        size=18,
                    ),
                    ft.Text(
                        "Encerrar Sessão",
                        size=14,
                        color=ft.colors.ERROR,
                    ),
                ],
                spacing=5,
            ),
            on_click=self._handle_logout,
            style=ft.ButtonStyle(
                padding=ft.padding.all(15),
                shape=ft.RoundedRectangleBorder(radius=8),
                overlay_color={"hovered": "#FF000020"},
            ),
        )
        
        # Botão de suporte
        support_button = ft.TextButton(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.icons.SUPPORT_AGENT,
                        color=ft.colors.BLUE,
                        size=18,
                    ),
                    ft.Text(
                        "Contato para Suporte",
                        size=14,
                        color=ft.colors.BLUE,
                    ),
                ],
                spacing=5,
            ),
            on_click=lambda e: self._show_contact_view(),
            style=ft.ButtonStyle(
                padding=ft.padding.all(15),
                shape=ft.RoundedRectangleBorder(radius=8),
                overlay_color={"hovered": "#0000FF20"},
            ),
        )
            
        return ft.Container(
            content=ft.Column(
                controls=[
                    # Logo no topo
                    logo,
                    
                    # Divisor após o logo
                    ft.Divider(height=1, color="#CCCCCC20"),
                    
                    # NavigationRail com padding uniforme
                    ft.Container(
                        content=modules_rail,
                        expand=True,
                        padding=ft.padding.symmetric(vertical=10),
                    ),
                    
                    # Divisor antes dos botões
                    ft.Divider(height=1, color="#CCCCCC20"),
                    
                    # Botões de ação no rodapé
                    ft.Container(
                        content=ft.Column(
                            [
                                support_button,  # Botão de suporte adicionado
                                logout_button,
                                ft.Container(
                                    content=theme_switch,
                                    padding=10,
                                    alignment=ft.alignment.center,
                                ),
                            ],
                            spacing=0,
                        ),
                        padding=ft.padding.only(bottom=10),
                    ),
                ],
                spacing=0,
                tight=True,
            ),
            width=250,  # Largura fixa para o sidebar
            bgcolor=ft.colors.SURFACE,
            border=ft.border.only(right=ft.BorderSide(1, "#CCCCCC20")),
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


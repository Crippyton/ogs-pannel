import flet as ft
import subprocess
import platform
import os
import json
from pathlib import Path
import webbrowser
import sys
import requests
import zipfile
import tarfile
import shutil
from typing import List, Dict, Optional, Tuple
import re

# Configurações
CONFIG_FILE = "ssh_manager_config.json"
DEFAULT_GROUP = "Default"
ICON_PATH = os.path.join(os.path.dirname(__file__), "assets")

class ConnectionType:
    SSH = "SSH"
    RDP = "RDP"

class SSHClient:
    def __init__(self):
        self.install_dir = os.path.join(str(Path.home()), "ssh_manager_clients")
        os.makedirs(self.install_dir, exist_ok=True)
        
        # Cria diretório para ícones se não existir
        os.makedirs(ICON_PATH, exist_ok=True)
        
        self.clients = {
            "Windows": {
                "OpenSSH": {
                    "command": "ssh",
                    "install": self.install_openssh_windows,
                    "icon": "terminal.png"
                },
                "PuTTY": {
                    "command": "putty",
                    "download_url": "https://the.earth.li/~sgtatham/putty/latest/w64/putty.exe",
                    "install": self.install_putty,
                    "icon": "putty.png"
                },
                "KiTTY": {
                    "command": "kitty",
                    "download_url": "https://www.fosshub.com/KiTTY.html",
                    "install": self.install_kitty,
                    "icon": "kitty.png"
                },
                "MobaXterm": {
                    "command": "mobaxterm",
                    "download_url": "https://download.mobatek.net/2312022023112-38/MobaXterm_Portable_v23.1.zip",
                    "executable": "MobaXterm.exe",
                    "install": self.install_mobaxterm,
                    "icon": "mobaxterm.png"
                },
                "RDP": {
                    "command": "mstsc",
                    "install": self.install_rdp_windows,
                    "icon": "rdp.png"
                }
            },
            "Linux": {
                "OpenSSH": {
                    "command": "ssh",
                    "install": self.install_openssh_linux,
                    "icon": "terminal.png"
                },
                "Remmina": {
                    "command": "remmina",
                    "install": self.install_remmina_linux,
                    "icon": "rdp.png"
                }
            },
            "Darwin": {
                "OpenSSH": {
                    "command": "ssh",
                    "install": self.install_openssh_mac,
                    "icon": "terminal.png"
                },
                "Microsoft Remote Desktop": {
                    "command": "open -a 'Microsoft Remote Desktop'",
                    "install": self.install_rdp_mac,
                    "icon": "rdp.png"
                }
            }
        }
    
    def get_platform_clients(self) -> Dict:
        system = platform.system()
        return self.clients.get(system, {})
    
    def get_clients_by_type(self, connection_type: str) -> Dict:
        """Retorna os clientes disponíveis para um tipo de conexão específico"""
        all_clients = self.get_platform_clients()
        if connection_type == ConnectionType.SSH:
            return {k: v for k, v in all_clients.items() if k != "RDP" and k != "Remmina" and k != "Microsoft Remote Desktop"}
        elif connection_type == ConnectionType.RDP:
            rdp_clients = {}
            if "RDP" in all_clients:
                rdp_clients["RDP"] = all_clients["RDP"]
            if "Remmina" in all_clients:
                rdp_clients["Remmina"] = all_clients["Remmina"]
            if "Microsoft Remote Desktop" in all_clients:
                rdp_clients["Microsoft Remote Desktop"] = all_clients["Microsoft Remote Desktop"]
            return rdp_clients
        return all_clients
    
    def is_client_installed(self, client_name: str) -> bool:
        """Verifica se o cliente já está instalado"""
        clients = self.get_platform_clients()
        if client_name not in clients:
            return False
        
        # Verifica se o comando está disponível no PATH
        try:
            if platform.system() == "Windows":
                # Verificação especial para MobaXterm
                if client_name == "MobaXterm":
                    # Verifica nos locais comuns de instalação
                    common_paths = [
                        os.path.join(os.environ.get("ProgramFiles", ""), ""),
                        os.path.join(os.environ.get("ProgramFiles(x86)", ""), ""),
                        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
                        self.install_dir
                    ]
                    
                    for path in common_paths:
                        for root, dirs, files in os.walk(path):
                            if "MobaXterm.exe" in files:
                                return True
                    return False
                
                # Verificação especial para RDP (sempre instalado no Windows)
                if client_name == "RDP":
                    return True
                
                result = subprocess.run(
                    f"where {clients[client_name]['command']}", 
                    shell=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                return result.returncode == 0
            else:
                # Verificação especial para Microsoft Remote Desktop no Mac
                if client_name == "Microsoft Remote Desktop" and platform.system() == "Darwin":
                    result = subprocess.run(
                        "ls /Applications/Microsoft\\ Remote\\ Desktop.app 2>/dev/null || ls ~/Applications/Microsoft\\ Remote\\ Desktop.app 2>/dev/null",
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    return result.returncode == 0
                
                result = subprocess.run(
                    f"which {clients[client_name]['command'].split()[0]}", 
                    shell=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                return result.returncode == 0
        except Exception:
            return False
    
    def get_client_icon(self, client_name: str) -> str:
        """Retorna o caminho para o ícone do cliente"""
        clients = self.get_platform_clients()
        icon_name = clients.get(client_name, {}).get("icon", "terminal.png")
        return os.path.join(ICON_PATH, icon_name)
    
    def install_client(self, client_name: str, progress_callback=None) -> bool:
        """Instala o cliente especificado"""
        clients = self.get_platform_clients()
        if client_name not in clients:
            raise Exception(f"Cliente {client_name} não suportado neste sistema")
        
        if self.is_client_installed(client_name):
            if progress_callback:
                progress_callback(f"{client_name} já está instalado")
            return True
        
        if "install" in clients[client_name]:
            return clients[client_name]["install"](progress_callback)
        else:
            raise Exception(f"Método de instalação não definido para {client_name}")
    
    def install_openssh_windows(self, progress_callback=None) -> bool:
        """Instala o OpenSSH no Windows"""
        try:
            if progress_callback:
                progress_callback("Verificando OpenSSH...")
            
            # Verifica se o OpenSSH já está instalado
            result = subprocess.run(
                "Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Client*'",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if "Installed" in result.stdout:
                if progress_callback:
                    progress_callback("OpenSSH já está instalado")
                return True
            
            if progress_callback:
                progress_callback("Instalando OpenSSH...")
            
            # Instala o OpenSSH Client
            subprocess.run(
                "Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0",
                shell=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"Falha ao instalar OpenSSH: {e.stderr}")
    
    def install_putty(self, progress_callback=None) -> bool:
        """Instala o PuTTY"""
        try:
            url = self.clients["Windows"]["PuTTY"]["download_url"]
            exe_path = os.path.join(self.install_dir, "putty.exe")
            
            if progress_callback:
                progress_callback("Baixando PuTTY...")
            
            # Download do PuTTY
            response = requests.get(url, stream=True)
            with open(exe_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Adiciona ao PATH do usuário
            self._add_to_path(self.install_dir)
            return True
        except Exception as e:
            raise Exception(f"Falha ao instalar PuTTY: {str(e)}")
    
    def install_kitty(self, progress_callback=None) -> bool:
        """Instala o KiTTY"""
        try:
            if progress_callback:
                progress_callback("Abrindo site do KiTTY...")
            
            # KiTTY precisa ser baixado manualmente devido ao fosshub
            webbrowser.open("https://www.fosshub.com/KiTTY.html")
            raise Exception("Por favor, baixe e instale o KiTTY manualmente do site oficial")
        except Exception as e:
            raise Exception(f"Falha ao instalar KiTTY: {str(e)}")
    
    def install_mobaxterm(self, progress_callback=None) -> bool:
        """Instala o MobaXterm"""
        try:
            # Primeiro verifica se já está instalado em outros locais
            common_paths = [
                os.path.join(os.environ.get("ProgramFiles", ""), ""),
                os.path.join(os.environ.get("ProgramFiles(x86)", ""), ""),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
                self.install_dir
            ]
            
            for path in common_paths:
                if not path:
                    continue
                    
                for root, dirs, files in os.walk(path):
                    if "MobaXterm.exe" in files:
                        if progress_callback:
                            progress_callback("MobaXterm encontrado em: " + root)
                        # Cria um atalho no diretório de instalação
                        src_path = os.path.join(root, "MobaXterm.exe")
                        dest_path = os.path.join(self.install_dir, "mobaxterm.exe")
                        
                        if not os.path.exists(dest_path):
                            shutil.copy(src_path, dest_path)
                        
                        self._add_to_path(self.install_dir)
                        return True
            
            # Se não encontrou, procede com a instalação
            url = self.clients["Windows"]["MobaXterm"]["download_url"]
            zip_path = os.path.join(self.install_dir, "MobaXterm.zip")
            extract_dir = os.path.join(self.install_dir, "MobaXterm")
            
            if progress_callback:
                progress_callback("Baixando MobaXterm...")
            
            # Download do MobaXterm
            response = requests.get(url, stream=True, verify=False)  # Desativa verificação SSL
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if progress_callback:
                progress_callback("Extraindo MobaXterm...")
            
            # Extrai o arquivo ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Encontra o executável
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.lower() == "mobaxterm.exe":
                        exe_path = os.path.join(root, file)
                        # Cria um atalho no diretório de instalação
                        dest_path = os.path.join(self.install_dir, "mobaxterm.exe")
                        if not os.path.exists(dest_path):
                            shutil.copy(exe_path, dest_path)
                        break
            
            # Adiciona ao PATH do usuário
            self._add_to_path(self.install_dir)
            return True
        except Exception as e:
            raise Exception(f"Falha ao instalar MobaXterm: {str(e)}")
    
    def install_rdp_windows(self, progress_callback=None) -> bool:
        """Verifica o RDP no Windows (já vem instalado por padrão)"""
        if progress_callback:
            progress_callback("RDP já está instalado no Windows")
        return True
    
    def install_openssh_linux(self, progress_callback=None) -> bool:
        """Instala o OpenSSH no Linux"""
        try:
            if progress_callback:
                progress_callback("Instalando OpenSSH...")
            
            # Detecta o gerenciador de pacotes
            if subprocess.run(["which", "apt-get"], capture_output=True).returncode == 0:
                subprocess.run(["sudo", "apt-get", "install", "-y", "openssh-client"], check=True)
            elif subprocess.run(["which", "yum"], capture_output=True).returncode == 0:
                subprocess.run(["sudo", "yum", "install", "-y", "openssh-clients"], check=True)
            elif subprocess.run(["which", "dnf"], capture_output=True).returncode == 0:
                subprocess.run(["sudo", "dnf", "install", "-y", "openssh-clients"], check=True)
            elif subprocess.run(["which", "pacman"], capture_output=True).returncode == 0:
                subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "openssh"], check=True)
            else:
                raise Exception("Gerenciador de pacotes não reconhecido")
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"Falha ao instalar OpenSSH: {e.stderr}")
    
    def install_remmina_linux(self, progress_callback=None) -> bool:
        """Instala o Remmina no Linux"""
        try:
            if progress_callback:
                progress_callback("Instalando Remmina...")
            
            # Detecta o gerenciador de pacotes
            if subprocess.run(["which", "apt-get"], capture_output=True).returncode == 0:
                subprocess.run(["sudo", "apt-get", "install", "-y", "remmina"], check=True)
            elif subprocess.run(["which", "yum"], capture_output=True).returncode == 0:
                subprocess.run(["sudo", "yum", "install", "-y", "remmina"], check=True)
            elif subprocess.run(["which", "dnf"], capture_output=True).returncode == 0:
                subprocess.run(["sudo", "dnf", "install", "-y", "remmina"], check=True)
            elif subprocess.run(["which", "pacman"], capture_output=True).returncode == 0:
                subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "remmina"], check=True)
            else:
                raise Exception("Gerenciador de pacotes não reconhecido")
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"Falha ao instalar Remmina: {e.stderr}")
    
    def install_openssh_mac(self, progress_callback=None) -> bool:
        """Instala o OpenSSH no Mac"""
        try:
            if progress_callback:
                progress_callback("Verificando Homebrew...")
            
            # Verifica se o Homebrew está instalado
            if subprocess.run(["which", "brew"], capture_output=True).returncode != 0:
                if progress_callback:
                    progress_callback("Instalando Homebrew...")
                
                # Instala o Homebrew
                subprocess.run(
                    '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
                    shell=True,
                    check=True
                )
            
            if progress_callback:
                progress_callback("Instalando OpenSSH...")
            
            # Instala o OpenSSH
            subprocess.run(["brew", "install", "openssh"], check=True)
            return True
        except subprocess.CalledProcessError as e:
            raise Exception(f"Falha ao instalar OpenSSH: {e.stderr}")
    
    def install_rdp_mac(self, progress_callback=None) -> bool:
        """Instala o Microsoft Remote Desktop no Mac"""
        try:
            if progress_callback:
                progress_callback("Abrindo App Store para instalar Microsoft Remote Desktop...")
            
            # Abre a App Store na página do Microsoft Remote Desktop
            webbrowser.open("macappstore://apps.apple.com/app/microsoft-remote-desktop/id1295203466")
            
            if progress_callback:
                progress_callback("Por favor, instale o Microsoft Remote Desktop da App Store")
            
            return False  # Retorna falso para que o usuário precise confirmar a instalação
        except Exception as e:
            raise Exception(f"Falha ao abrir App Store: {str(e)}")
    
    def _add_to_path(self, directory: str) -> None:
        """Adiciona um diretório ao PATH do usuário"""
        if platform.system() == "Windows":
            # Adiciona ao PATH do usuário no Windows
            import winreg
            
            with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as hkey:
                with winreg.OpenKey(hkey, "Environment", 0, winreg.KEY_ALL_ACCESS) as sub_key:
                    try:
                        path_value = winreg.QueryValueEx(sub_key, "Path")[0]
                    except WindowsError:
                        path_value = ""
                    
                    if directory not in path_value:
                        new_path = f"{path_value};{directory}" if path_value else directory
                        winreg.SetValueEx(sub_key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            
            # Notifica o sistema sobre a mudança no PATH
            subprocess.run(
                'powershell -Command "[Environment]::SetEnvironmentVariable(\'Path\', [Environment]::GetEnvironmentVariable(\'Path\', \'User\'), \'User\')"',
                shell=True
            )

class SSHSavedHost:
    def __init__(self, name: str, host: str, username: str, password: str, port: str, client: str, 
                 group: str = DEFAULT_GROUP, connection_type: str = ConnectionType.SSH):
        self.name = name
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.client = client
        self.group = group
        self.connection_type = connection_type

class SSHManager:
    def __init__(self):
        self.ssh_client = SSHClient()
        self.saved_hosts: List[SSHSavedHost] = []
        self.load_config()
    
    def load_config(self) -> None:
        """Carrega a configuração salva do arquivo JSON"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.saved_hosts = [
                        SSHSavedHost(
                            name=host["name"],
                            host=host["host"],
                            username=host["username"],
                            password=host["password"],
                            port=host["port"],
                            client=host["client"],
                            group=host.get("group", DEFAULT_GROUP),
                            connection_type=host.get("connection_type", ConnectionType.SSH)
                        )
                        for host in data.get("hosts", [])
                    ]
        except Exception as e:
            print(f"Erro ao carregar configuração: {str(e)}")
    
    def save_config(self) -> None:
        """Salva a configuração atual no arquivo JSON"""
        try:
            data = {
                "hosts": [
                    {
                        "name": host.name,
                        "host": host.host,
                        "username": host.username,
                        "password": host.password,
                        "port": host.port,
                        "client": host.client,
                        "group": host.group,
                        "connection_type": host.connection_type
                    }
                    for host in self.saved_hosts
                ]
            }
            
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar configuração: {str(e)}")
    
    def add_host(self, host: SSHSavedHost) -> None:
        """Adiciona um novo host à lista"""
        self.saved_hosts.append(host)
        self.save_config()
    
    def remove_host(self, host_name: str) -> None:
        """Remove um host da lista"""
        self.saved_hosts = [h for h in self.saved_hosts if h.name != host_name]
        self.save_config()
    
    def get_groups(self) -> List[str]:
        """Retorna a lista de grupos únicos"""
        groups = {host.group for host in self.saved_hosts}
        if not groups:
            groups = {DEFAULT_GROUP}
        return sorted(groups)
    
    def get_hosts_by_group(self, group: str) -> List[SSHSavedHost]:
        """Retorna os hosts de um grupo específico"""
        return [host for host in self.saved_hosts if host.group == group]
    
    def get_host(self, host_name: str) -> Optional[SSHSavedHost]:
        """Retorna um host específico pelo nome"""
        for host in self.saved_hosts:
            if host.name == host_name:
                return host
        return None
    
    def add_group(self, group_name: str) -> None:
        """Adiciona um novo grupo"""
        # Grupos são criados implicitamente ao adicionar hosts
        # Esta função é mantida para compatibilidade
        self.save_config()
    
    def rename_group(self, old_name: str, new_name: str) -> None:
        """Renomeia um grupo"""
        for host in self.saved_hosts:
            if host.group == old_name:
                host.group = new_name
        self.save_config()
    
    def remove_group(self, group_name: str) -> None:
        """Remove um grupo (move hosts para o grupo padrão)"""
        for host in self.saved_hosts:
            if host.group == group_name:
                host.group = DEFAULT_GROUP
        self.save_config()

def main(page: ft.Page):
    # Configuração da página
    page.title = "SSH & RDP Manager Pro"
    
    # Configuração responsiva
    def page_resize(e):
        # Ajusta o layout com base no tamanho da janela
        if page.window_width < 800:
            # Layout para telas pequenas
            main_content.horizontal = False
            left_panel.width = None
            left_panel.expand = True
            right_panel.expand = True
        else:
            # Layout para telas maiores
            main_content.horizontal = True
            left_panel.width = 350
            left_panel.expand = False
            right_panel.expand = True
        page.update()
    
    # Configura o evento de redimensionamento
    page.on_resize = page_resize
    
    # Usa as novas propriedades de janela
    page.window.width = 1000
    page.window.height = 750
    page.window.min_width = 800
    page.window.min_height = 600
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10
    page.fonts = {
        "Roboto": "https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap"
    }
    page.theme = ft.Theme(font_family="Roboto")
    
    # Inicializa o gerenciador SSH
    ssh_manager = SSHManager()
    
    # Variáveis de estado
    selected_group = ft.Text(DEFAULT_GROUP)
    selected_host = ft.Text("Nenhum host selecionado", style=ft.TextStyle(size=14))
    installation_progress = ft.Text("", style=ft.TextStyle(size=12))
    installation_progress_bar = ft.ProgressBar(width=300, visible=False, color=ft.colors.BLUE_400)
    
    # Cores personalizadas
    primary_color = ft.colors.BLUE_700
    secondary_color = ft.colors.BLUE_400
    accent_color = ft.colors.AMBER_600
    bg_color = ft.colors.GREY_900
    card_color = ft.colors.GREY_800
    
    # Elementos da UI
    def create_input_field(label: str, value: str = "", password: bool = False, width: int = 300):
        return ft.TextField(
            label=label,
            value=value,
            password=password,
            can_reveal_password=password,
            width=width,
            border_color=secondary_color,
            focused_border_color=accent_color,
            text_size=14,
            content_padding=10,
            cursor_color=accent_color,
            label_style=ft.TextStyle(color=ft.colors.WHITE),
            text_style=ft.TextStyle(color=ft.colors.WHITE),
            expand=True
        )
    
    # Campos de entrada
    host_name = create_input_field("Nome do Host")
    host_address = create_input_field("Host/IP")
    username = create_input_field("Usuário")
    password = create_input_field("Senha", password=True)
    port = create_input_field("Porta", "22")
    
    # Dropdown para tipo de conexão
    connection_type_dropdown = ft.Dropdown(
        label="Tipo de Conexão",
        options=[
            ft.dropdown.Option(ConnectionType.SSH),
            ft.dropdown.Option(ConnectionType.RDP)
        ],
        value=ConnectionType.SSH,
        width=300,
        border_color=secondary_color,
        focused_border_color=accent_color,
        text_size=14,
        content_padding=10,
        expand=True,
        on_change=lambda e: update_client_dropdown(e.control.value)
    )
    
    # Dropdown para grupos
    group_dropdown = ft.Dropdown(
        label="Grupo",
        value=DEFAULT_GROUP,
        width=300,
        border_color=secondary_color,
        focused_border_color=accent_color,
        text_size=14,
        content_padding=10,
        options=[ft.dropdown.Option(group) for group in ssh_manager.get_groups()],
        expand=True
    )
    
    # Dropdown para clientes SSH/RDP
    client_dropdown = ft.Dropdown(
        label="Cliente",
        options=[],
        width=300,
        border_color=secondary_color,
        focused_border_color=accent_color,
        text_size=14,
        content_padding=10,
        expand=True
    )
    
    # Atualiza a lista de clientes SSH/RDP disponíveis
    def update_client_dropdown(connection_type=ConnectionType.SSH):
        clients = ssh_manager.ssh_client.get_clients_by_type(connection_type)
        client_dropdown.options = [
            ft.dropdown.Option(
                text=client,
                data=ssh_manager.ssh_client.get_client_icon(client)
            ) 
            for client in clients.keys()
        ]
        
        if client_dropdown.options:
            client_dropdown.value = client_dropdown.options[0].text
        page.update()
    
    # Atualiza a lista de grupos
    def update_groups():
        groups = ssh_manager.get_groups()
        group_dropdown.options = [
            ft.dropdown.Option(group) 
            for group in groups
        ]
        
        if not group_dropdown.options:
            group_dropdown.options.append(ft.dropdown.Option(DEFAULT_GROUP))
            group_dropdown.value = DEFAULT_GROUP
        
        page.update()
    
    # Lista de hosts
    hosts_list = ft.ListView(expand=True, spacing=10, padding=10)
    
    # Atualiza a lista de hosts
    def update_hosts_list(group: str = None):
        hosts_list.controls.clear()
        
        group_to_show = group or selected_group.value
        hosts = ssh_manager.get_hosts_by_group(group_to_show)
        
        for host in hosts:
            icon_path = ssh_manager.ssh_client.get_client_icon(host.client)
            
            # Ícone baseado no tipo de conexão
            connection_icon = ft.icons.TERMINAL
            if host.connection_type == ConnectionType.RDP:
                connection_icon = ft.icons.DESKTOP_WINDOWS
            
            hosts_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.ListTile(
                            title=ft.Text(host.name, weight=ft.FontWeight.BOLD, size=14),
                            subtitle=ft.Column([
                                ft.Text(
                                    f"{host.username}@{host.host}:{host.port}",
                                    size=12,
                                    color=ft.colors.GREY_400
                                ),
                                ft.Text(
                                    f"Tipo: {host.connection_type} | Cliente: {host.client}",
                                    size=10,
                                    color=ft.colors.GREY_500
                                )
                            ], spacing=2, tight=True),
                            leading=ft.Row([
                                ft.Icon(connection_icon, color=accent_color, size=16),
                                ft.Image(
                                    src=icon_path,
                                    width=30,
                                    height=30,
                                    fit=ft.ImageFit.CONTAIN,
                                    error_content=ft.Icon(ft.icons.COMPUTER)
                                )
                            ], spacing=5),
                            trailing=ft.PopupMenuButton(
                                icon=ft.icons.MORE_VERT,
                                items=[
                                    ft.PopupMenuItem(
                                        text="Conectar",
                                        icon=ft.icons.CONNECT_WITHOUT_CONTACT,
                                        on_click=lambda e, h=host: connect_to_host(h)
                                    ),
                                    ft.PopupMenuItem(
                                        text="Editar",
                                        icon=ft.icons.EDIT,
                                        on_click=lambda e, h=host: edit_host(h)
                                    ),
                                    ft.PopupMenuItem(
                                        text="Excluir",
                                        icon=ft.icons.DELETE,
                                        on_click=lambda e, h=host: delete_host(h)
                                    ),
                                ]
                            ),
                            on_click=lambda e, h=host: select_host(h),
                            data=host
                        ),
                        padding=10,
                        border_radius=10,
                        bgcolor=card_color,
                    ),
                    elevation=5,
                    margin=5,
                )
            )
        
        page.update()
    
    # Seleciona um host
    def select_host(host: SSHSavedHost):
        selected_host.value = host.name
        host_name.value = host.name
        host_address.value = host.host
        username.value = host.username
        password.value = host.password
        port.value = host.port
        connection_type_dropdown.value = host.connection_type
        update_client_dropdown(host.connection_type)
        client_dropdown.value = host.client
        group_dropdown.value = host.group
        
        save_button.text = "Atualizar"
        page.update()
    
    # Conecta a um host
    def connect_to_host(host: SSHSavedHost = None):
        if not host:
            host = SSHSavedHost(
                name=host_name.value,
                host=host_address.value,
                username=username.value,
                password=password.value,
                port=port.value,
                client=client_dropdown.value,
                group=group_dropdown.value,
                connection_type=connection_type_dropdown.value
            )
        
        if not host.host:
            show_error("Por favor, informe o host ou IP")
            return
        
        # Verifica se o cliente está instalado
        if not ssh_manager.ssh_client.is_client_installed(host.client):
            # Se não estiver instalado, instala
            install_client(host.client, on_success=lambda: connect_to_host(host))
            return
        
        try:
            client_name = host.client
            clients = ssh_manager.ssh_client.get_platform_clients()
            client_cmd = clients[client_name]["command"]
            
            if host.connection_type == ConnectionType.SSH:
                # Conexão SSH
                if platform.system() == "Windows":
                    if client_cmd == "ssh":
                        command = f"start cmd /k ssh {host.username}@{host.host} -p {host.port}"
                    elif client_cmd in ["putty", "kitty"]:
                        command = f"{client_cmd}.exe -ssh {host.username}@{host.host} -P {host.port}"
                        if host.password:
                            command += f" -pw {host.password}"
                    elif client_cmd == "mobaxterm":
                        # Verifica o caminho completo do MobaXterm
                        mobaxterm_path = find_mobaxterm()
                        if mobaxterm_path:
                            command = f'start "" "{mobaxterm_path}" /ssh {host.username}@{host.host} /port={host.port}'
                        else:
                            command = f"start mobaxterm.exe /ssh {host.username}@{host.host} /port={host.port}"
                    else:
                        command = f"start {client_cmd}.exe"
                    
                    subprocess.Popen(command, shell=True)
                else:
                    command = ["ssh", f"{host.username}@{host.host}", "-p", host.port]
                    subprocess.Popen(command)
            else:
                # Conexão RDP
                if platform.system() == "Windows":
                    # Usa o cliente RDP nativo do Windows
                    command = f"mstsc /v:{host.host}"
                    if host.username:
                        command += f" /u:{host.username}"
                    if host.password:
                        # Não é possível passar a senha diretamente para o mstsc
                        pass
                    subprocess.Popen(command, shell=True)
                elif platform.system() == "Linux":
                    # Usa o Remmina no Linux
                    if client_cmd == "remmina":
                        # Cria um arquivo de configuração temporário para o Remmina
                        config_content = f"""[remmina]
                        name={host.name}
                        server={host.host}
                        username={host.username}
                        password={host.password}
                        protocol=RDP
                        """
                        temp_file = os.path.join(os.path.expanduser("~"), f".remmina_temp_{host.name}.remmina")
                        with open(temp_file, "w") as f:
                            f.write(config_content)
                        
                        command = f"remmina -c {temp_file}"
                        subprocess.Popen(command, shell=True)
                elif platform.system() == "Darwin":
                    # Usa o Microsoft Remote Desktop no macOS
                    # Não há uma forma direta de abrir o MRD com parâmetros via linha de comando
                    # Então apenas abrimos o aplicativo
                    command = "open -a 'Microsoft Remote Desktop'"
                    subprocess.Popen(command, shell=True)
                    show_info(f"Por favor, conecte-se manualmente a {host.host} usando Microsoft Remote Desktop")
            
            show_success(f"Conexão iniciada com {host.host}")
        except Exception as e:
            show_error(f"Erro ao conectar: {str(e)}")
    
    def find_mobaxterm() -> Optional[str]:
        """Encontra o caminho completo do MobaXterm no sistema"""
        search_paths = [
            os.path.join(os.environ.get("ProgramFiles", ""), ""),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), ""),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
            ssh_manager.ssh_client.install_dir
        ]
        
        for path in search_paths:
            if not path:
                continue
                
            for root, dirs, files in os.walk(path):
                if "MobaXterm.exe" in files:
                    return os.path.join(root, "MobaXterm.exe")
        
        return None
    
    # Instala um cliente SSH/RDP
    def install_client(client_name: str, on_success=None):
        def update_progress(message: str):
            installation_progress.value = message
            page.update()
        
        installation_progress_bar.visible = True
        installation_progress.value = f"Verificando {client_name}..."
        page.update()
        
        try:
            # Verifica novamente se já está instalado (pode ter sido instalado manualmente)
            if ssh_manager.ssh_client.is_client_installed(client_name):
                installation_progress.value = f"{client_name} já está instalado!"
                installation_progress_bar.visible = False
                page.update()
                
                if on_success:
                    on_success()
                return
            
            installation_progress.value = f"Instalando {client_name}..."
            page.update()
            
            ssh_manager.ssh_client.install_client(client_name, update_progress)
            
            installation_progress.value = f"{client_name} instalado com sucesso!"
            installation_progress_bar.visible = False
            show_success(f"{client_name} instalado com sucesso!")
            
            if on_success:
                on_success()
        except Exception as e:
            installation_progress.value = f"Erro ao instalar {client_name}: {str(e)}"
            installation_progress_bar.visible = False
            show_error(f"Erro ao instalar {client_name}: {str(e)}")
        
        page.update()
    
    # Salva um host
    def save_host():
        if not host_name.value:
            show_error("Por favor, informe um nome para o host")
            return
        
        if not host_address.value:
            show_error("Por favor, informe o host ou IP")
            return
        
        # Verifica se o grupo é novo
        new_group = group_dropdown.value
        existing_groups = ssh_manager.get_groups()
        if new_group not in existing_groups and new_group != DEFAULT_GROUP:
            ssh_manager.add_group(new_group)
            update_groups()
        
        host = SSHSavedHost(
            name=host_name.value,
            host=host_address.value,
            username=username.value,
            password=password.value,
            port=port.value,
            client=client_dropdown.value,
            group=new_group,
            connection_type=connection_type_dropdown.value
        )
        
        # Verifica se já existe um host com esse nome
        existing_host = ssh_manager.get_host(host.name)
        if existing_host:
            # Atualiza o host existente
            ssh_manager.remove_host(host.name)
        
        ssh_manager.add_host(host)
        update_groups()
        update_hosts_list()
        show_success(f"Host '{host.name}' salvo com sucesso!")
        clear_fields()
    
    # Edita um host
    def edit_host(host: SSHSavedHost):
        select_host(host)
        save_button.text = "Atualizar"
        page.update()
    
    # Exclui um host
    def delete_host(host: SSHSavedHost):
        def confirm_delete(e):
            ssh_manager.remove_host(host.name)
            update_groups()
            update_hosts_list()
            dlg.open = False
            page.update()
            show_success(f"Host '{host.name}' excluído com sucesso!")
            clear_fields()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar exclusão"),
            content=ft.Text(f"Tem certeza que deseja excluir o host '{host.name}'?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, "open", False)),
                ft.TextButton("Excluir", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.colors.RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        page.dialog = dlg
        dlg.open = True
        page.update()
    
    # Gerencia grupos
    def manage_groups(e):
        groups = ssh_manager.get_groups()
        
        # Campo para adicionar novo grupo
        new_group_field = ft.TextField(
            label="Nome do novo grupo",
            width=300,
            border_color=secondary_color,
            focused_border_color=accent_color
        )
        
        def add_new_group(e):
            new_group_name = new_group_field.value.strip()
            if not new_group_name:
                show_error("Por favor, informe um nome para o novo grupo")
                return
            
            if new_group_name in groups:
                show_error("Já existe um grupo com esse nome")
                return
            
            # Adiciona o novo grupo à lista
            groups.append(new_group_name)
            group_list_view.controls.append(
                ft.Text(new_group_name, size=14)
            )
            new_group_field.value = ""
            page.update()
            show_success(f"Grupo '{new_group_name}' adicionado")
        
        def rename_group(e):
            if not hasattr(group_list_view, "selected_index") or group_list_view.selected_index is None:
                show_error("Por favor, selecione um grupo para renomear")
                return
                
            old_name = group_list_view.controls[group_list_view.selected_index].value
            new_name = rename_field.value.strip()
            
            if not new_name:
                show_error("Por favor, informe um novo nome para o grupo")
                return
            
            if new_name in groups and new_name != old_name:
                show_error("Já existe um grupo com esse nome")
                return
            
            ssh_manager.rename_group(old_name, new_name)
            update_groups()
            update_hosts_list()
            group_dialog.open = False
            page.update()
            show_success(f"Grupo '{old_name}' renomeado para '{new_name}'")
        
        def delete_group(e):
            if not hasattr(group_list_view, "selected_index") or group_list_view.selected_index is None:
                show_error("Por favor, selecione um grupo para excluir")
                return
                
            group_name = group_list_view.controls[group_list_view.selected_index].value
            
            if group_name == DEFAULT_GROUP:
                show_error("Não é possível excluir o grupo padrão")
                return
            
            def confirm_group_delete(e):
                ssh_manager.remove_group(group_name)
                update_groups()
                update_hosts_list()
                confirm_dlg.open = False
                group_dialog.open = False
                page.update()
                show_success(f"Grupo '{group_name}' excluído")
            
            confirm_dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirmar exclusão"),
                content=ft.Text(f"Tem certeza que deseja excluir o grupo '{group_name}'?\nTodos os hosts serão movidos para o grupo padrão."),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: setattr(confirm_dlg, "open", False)),
                    ft.TextButton("Excluir", on_click=confirm_group_delete, style=ft.ButtonStyle(color=ft.colors.RED)),
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )
            
            page.dialog = confirm_dlg
            confirm_dlg.open = True
            page.update()
        
        # Lista de grupos com seleção
        group_list_view = ft.ListView(
            expand=True,
            spacing=5,
            auto_scroll=True
        )
        
        for group in groups:
            group_list_view.controls.append(
                ft.Text(group, size=14, selectable=True)
            )
        
        rename_field = ft.TextField(
            label="Novo nome",
            width=300,
            border_color=secondary_color,
            focused_border_color=accent_color
        )
        
        group_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Gerenciar Grupos"),
            content=ft.Column([
                ft.Text("Adicionar novo grupo:", weight=ft.FontWeight.BOLD),
                ft.Row([
                    new_group_field,
                    ft.IconButton(
                        icon=ft.icons.ADD,
                        tooltip="Adicionar grupo",
                        on_click=add_new_group
                    )
                ]),
                ft.Divider(),
                ft.Text("Grupos existentes:", weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=group_list_view,
                    width=300,
                    height=200,
                    border=ft.border.all(1, ft.colors.GREY_600),
                    border_radius=5,
                    padding=10
                ),
                ft.Text("Selecione um grupo para editar ou excluir", size=12, italic=True, color=ft.colors.GREY_400),
                ft.Divider(),
                ft.Text("Renomear grupo selecionado:", weight=ft.FontWeight.BOLD),
                rename_field,
            ], spacing=10),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: setattr(group_dialog, "open", False)),
                ft.TextButton("Excluir", on_click=delete_group, style=ft.ButtonStyle(color=ft.colors.RED)),
                ft.TextButton("Renomear", on_click=rename_group),
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        page.dialog = group_dialog
        group_dialog.open = True
        page.update()
    
    # Limpa os campos
    def clear_fields():
        host_name.value = ""
        host_address.value = ""
        username.value = ""
        password.value = ""
        port.value = "22"
        connection_type_dropdown.value = ConnectionType.SSH
        update_client_dropdown(ConnectionType.SSH)
        client_dropdown.value = client_dropdown.options[0].text if client_dropdown.options else ""
        group_dropdown.value = DEFAULT_GROUP
        selected_host.value = "Nenhum host selecionado"
        save_button.text = "Salvar"
        page.update()
    
    # Mostra uma mensagem de erro
    def show_error(message: str):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.colors.WHITE),
            bgcolor=ft.colors.RED_700,
            duration=3000,
            behavior=ft.SnackBarBehavior.FLOATING,
            shape=ft.RoundedRectangleBorder(radius=10)
        )
        page.snack_bar.open = True
        page.update()
    
    # Mostra uma mensagem de sucesso
    def show_success(message: str):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.colors.WHITE),
            bgcolor=ft.colors.GREEN_700,
            duration=3000,
            behavior=ft.SnackBarBehavior.FLOATING,
            shape=ft.RoundedRectangleBorder(radius=10)
        )
        page.snack_bar.open = True
        page.update()
    
    # Mostra uma mensagem informativa
    def show_info(message: str):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.colors.WHITE),
            bgcolor=ft.colors.BLUE_700,
            duration=5000,
            behavior=ft.SnackBarBehavior.FLOATING,
            shape=ft.RoundedRectangleBorder(radius=10)
        )
        page.snack_bar.open = True
        page.update()
    
    # Botões
    save_button = ft.ElevatedButton(
        "Salvar",
        icon=ft.icons.SAVE,
        on_click=lambda e: save_host(),
        width=150,
        height=45,
        style=ft.ButtonStyle(
            bgcolor=primary_color,
            color=ft.colors.WHITE,
            padding=10,
            shape=ft.RoundedRectangleBorder(radius=10)
        )
    )
    
    connect_button = ft.ElevatedButton(
        "Conectar",
        icon=ft.icons.CONNECT_WITHOUT_CONTACT,
        on_click=lambda e: connect_to_host(),
        width=150,
        height=45,
        style=ft.ButtonStyle(
            bgcolor=accent_color,
            color=ft.colors.WHITE,
            padding=10,
            shape=ft.RoundedRectangleBorder(radius=10)
        )
    )
    
    clear_button = ft.ElevatedButton(
        "Limpar",
        icon=ft.icons.CLEAR,
        on_click=lambda e: clear_fields(),
        width=150,
        height=45,
        style=ft.ButtonStyle(
            bgcolor=ft.colors.GREY_700,
            color=ft.colors.WHITE,
            padding=10,
            shape=ft.RoundedRectangleBorder(radius=10)
        )
    )
    
    manage_groups_button = ft.TextButton(
        "Gerenciar Grupos",
        icon=ft.icons.GROUP_WORK,
        on_click=manage_groups,
        style=ft.ButtonStyle(color=secondary_color)
    )
    
    # Layout principal - agora com design responsivo
    left_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Hosts Salvos", size=18, weight=ft.FontWeight.BOLD),
                manage_groups_button
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([
                ft.Text("Grupo:", weight=ft.FontWeight.BOLD, size=14),
                ft.Dropdown(
                    options=[ft.dropdown.Option(group) for group in ssh_manager.get_groups()],
                    value=DEFAULT_GROUP,
                    on_change=lambda e: update_hosts_list(e.control.value),
                    expand=True,
                    border_color=secondary_color,
                    content_padding=10,
                    text_size=14
                )
            ]),
            hosts_list
        ], spacing=15, expand=True),
        width=350,
        padding=15,
        bgcolor=card_color,
        border_radius=15,
    )
    
    right_panel = ft.Container(
        content=ft.Column([
            ft.Text("Gerenciar Conexão", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(height=10, color=ft.colors.TRANSPARENT),
            ft.Text("Host selecionado:", size=14),
            ft.Container(
                content=selected_host,
                padding=10,
                bgcolor=ft.colors.GREY_800,
                border_radius=10,
                width=300
            ),
            ft.Divider(height=20),
            # Layout responsivo para os campos de entrada
            ft.ResponsiveRow([
                ft.Column([host_name], col={"sm": 12, "md": 6, "lg": 6}, expand=True),
                ft.Column([host_address], col={"sm": 12, "md": 6, "lg": 6}, expand=True),
            ]),
            ft.ResponsiveRow([
                ft.Column([username], col={"sm": 12, "md": 6, "lg": 6}, expand=True),
                ft.Column([password], col={"sm": 12, "md": 6, "lg": 6}, expand=True),
            ]),
            ft.ResponsiveRow([
                ft.Column([port], col={"sm": 12, "md": 4, "lg": 4}, expand=True),
                ft.Column([connection_type_dropdown], col={"sm": 12, "md": 8, "lg": 8}, expand=True),
            ]),
            ft.ResponsiveRow([
                ft.Column([group_dropdown], col={"sm": 12, "md": 6, "lg": 6}, expand=True),
                ft.Column([client_dropdown], col={"sm": 12, "md": 6, "lg": 6}, expand=True),
            ]),
            ft.Divider(height=20),
            ft.Row([save_button, connect_button, clear_button], 
                  spacing=15, 
                  alignment=ft.MainAxisAlignment.CENTER,
                  wrap=True),
            ft.Divider(height=20),
            installation_progress,
            installation_progress_bar,
            ft.Text("Clientes disponíveis:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Se o cliente desejado não estiver instalado, ele será baixado automaticamente ao conectar.",
                size=12,
                color=ft.colors.GREY_400
            )
        ], spacing=10, expand=True),
        expand=True,
        padding=20,
        bgcolor=card_color,
        border_radius=15,
    )
    
    main_content = ft.Row([left_panel, right_panel], spacing=20, expand=True)
    
    # Barra de status
    status_bar = ft.Container(
        content=ft.Row([
            ft.Text(f"SSH & RDP Manager Pro | {platform.system()} {platform.release()}", size=12),
            ft.Text("Desenvolvido com Python e Flet", size=12, style=ft.TextStyle(italic=True))
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=10,
        bgcolor=primary_color,
        border_radius=10
    )
    
    # Adiciona tudo à página
    page.add(
        ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.TERMINAL, size=30, color=accent_color),
                    ft.Icon(ft.icons.DESKTOP_WINDOWS, size=30, color=secondary_color),
                    ft.Text("SSH & RDP Manager Pro", size=24, weight=ft.FontWeight.BOLD),
                ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                padding=15,
                alignment=ft.alignment.center,
                bgcolor=bg_color,
                border_radius=15,
                margin=ft.margin.only(bottom=10)
            ),
            main_content,
            status_bar
        ], spacing=10, expand=True)
    )
    
    # Inicializa os dados
    update_client_dropdown(ConnectionType.SSH)
    update_groups()
    update_hosts_list()
    
    # Chama o redimensionamento inicial para configurar o layout
    page_resize(None)

if __name__ == "__main__":
    ft.app(target=main)
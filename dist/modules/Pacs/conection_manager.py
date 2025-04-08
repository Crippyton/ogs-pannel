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
SCRIPTS_FILE = "ssh_manager_scripts.json"
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
                        if not path:
                            continue
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

class Script:
    def __init__(self, name: str, content: str, description: str = "", platform: str = "all"):
        self.name = name
        self.content = content
        self.description = description
        self.platform = platform  # "windows", "linux", "darwin" ou "all"

class SSHManager:
    def __init__(self):
        self.ssh_client = SSHClient()
        self.saved_hosts: List[SSHSavedHost] = []
        self.scripts: List[Script] = []
        self.load_config()
        self.load_scripts()
    
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
    
    def load_scripts(self) -> None:
        """Carrega os scripts salvos do arquivo JSON"""
        try:
            if os.path.exists(SCRIPTS_FILE):
                with open(SCRIPTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.scripts = [
                        Script(
                            name=script["name"],
                            content=script["content"],
                            description=script.get("description", ""),
                            platform=script.get("platform", "all")
                        )
                        for script in data.get("scripts", [])
                    ]
            else:
                # Cria alguns scripts de exemplo
                self.scripts = [
                    Script(
                        name="Verificar Espaço em Disco",
                        content="df -h",
                        description="Verifica o espaço em disco disponível",
                        platform="linux"
                    ),
                    Script(
                        name="Listar Processos",
                        content="ps aux | sort -nrk 3,3 | head -n 10",
                        description="Lista os 10 processos que mais consomem CPU",
                        platform="linux"
                    ),
                    Script(
                        name="Verificar Memória",
                        content="free -h",
                        description="Verifica a memória disponível",
                        platform="linux"
                    ),
                    Script(
                        name="Verificar Espaço em Disco (Windows)",
                        content="wmic logicaldisk get deviceid, volumename, name, description, size, freespace",
                        description="Verifica o espaço em disco disponível no Windows",
                        platform="windows"
                    )
                ]
                self.save_scripts()
        except Exception as e:
            print(f"Erro ao carregar scripts: {str(e)}")
    
    def save_scripts(self) -> None:
        """Salva os scripts no arquivo JSON"""
        try:
            data = {
                "scripts": [
                    {
                        "name": script.name,
                        "content": script.content,
                        "description": script.description,
                        "platform": script.platform
                    }
                    for script in self.scripts
                ]
            }
            
            with open(SCRIPTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar scripts: {str(e)}")
    
    def add_script(self, script: Script) -> None:
        """Adiciona um novo script à lista"""
        # Verifica se já existe um script com esse nome
        for i, s in enumerate(self.scripts):
            if s.name == script.name:
                # Substitui o script existente
                self.scripts[i] = script
                self.save_scripts()
                return
        
        self.scripts.append(script)
        self.save_scripts()
    
    def remove_script(self, script_name: str) -> None:
        """Remove um script da lista"""
        self.scripts = [s for s in self.scripts if s.name != script_name]
        self.save_scripts()
    
    def get_scripts_by_platform(self, platform_name: str = None) -> List[Script]:
        """Retorna os scripts compatíveis com a plataforma especificada"""
        if not platform_name:
            platform_name = platform.system().lower()
        
        return [s for s in self.scripts if s.platform == "all" or s.platform.lower() == platform_name.lower()]
    
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
    
    def search_hosts(self, query: str) -> List[SSHSavedHost]:
        """Pesquisa hosts pelo nome, endereço ou usuário"""
        query = query.lower()
        return [
            host for host in self.saved_hosts 
            if query in host.name.lower() or 
               query in host.host.lower() or 
               query in host.username.lower() or
               query in host.group.lower()
        ]
    
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
            page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        else:
            # Layout para telas maiores
            page.horizontal_alignment = ft.CrossAxisAlignment.START
        
        # Atualiza a grade de hosts
        update_host_grid()
        page.update()
    
    # Configura o evento de redimensionamento
    page.on_resize = page_resize
    
    # Usa as novas propriedades de janela
    page.window.width = 1200
    page.window.height = 800
    page.window.min_width = 800
    page.window.min_height = 600
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 15
    page.fonts = {
        "Roboto": "https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap"
    }
    page.theme = ft.Theme(font_family="Roboto")
    
    # Cores personalizadas
    primary_color = ft.colors.BLUE_700
    secondary_color = ft.colors.BLUE_400
    accent_color = ft.colors.AMBER_600
    bg_color = ft.colors.GREY_900
    card_color = ft.colors.GREY_800
    
    # Inicializa o gerenciador SSH
    ssh_manager = SSHManager()
    
    # Variáveis de estado
    selected_group = ft.Text(DEFAULT_GROUP)
    selected_host = None
    selected_script = None
    installation_progress = ft.Text("", style=ft.TextStyle(size=12))
    installation_progress_bar = ft.ProgressBar(width=300, visible=False, color=ft.colors.BLUE_400)
    
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
    
    # Campos de entrada para o modal de cadastro
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
    
    # Dropdown para scripts
    script_dropdown = ft.Dropdown(
        label="Script para executar após conexão (opcional)",
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
    
    # Atualiza a lista de scripts
    def update_script_dropdown():
        current_platform = platform.system().lower()
        scripts = ssh_manager.get_scripts_by_platform(current_platform)
        
        script_dropdown.options = [
            ft.dropdown.Option(text="Nenhum", data=None)
        ] + [
            ft.dropdown.Option(text=script.name, data=script.name)
            for script in scripts
        ]
        
        script_dropdown.value = "Nenhum"
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
        
        # Garante que o valor atual está nas opções
        if group_dropdown.value not in groups:
            group_dropdown.value = DEFAULT_GROUP
        
        # Atualiza também o dropdown de filtro de grupos
        filter_group_dropdown.options = [
            ft.dropdown.Option("Todos os grupos")
        ] + [
            ft.dropdown.Option(group) 
            for group in groups
        ]
        
        page.update()
    
    # Barra de pesquisa
    search_field = ft.TextField(
        hint_text="Pesquisar hosts...",
        prefix_icon=ft.icons.SEARCH,
        border_color=secondary_color,
        focused_border_color=accent_color,
        text_size=14,
        content_padding=10,
        expand=True,
        on_change=lambda e: search_hosts(e.control.value)
    )
    
    # Dropdown para filtrar por grupo
    filter_group_dropdown = ft.Dropdown(
        label="Filtrar por grupo",
        options=[
            ft.dropdown.Option("Todos os grupos")
        ] + [
            ft.dropdown.Option(group) 
            for group in ssh_manager.get_groups()
        ],
        value="Todos os grupos",
        width=200,
        border_color=secondary_color,
        focused_border_color=accent_color,
        text_size=14,
        content_padding=10,
        on_change=lambda e: filter_hosts_by_group(e.control.value)
    )
    
    # Container para a grade de hosts
    host_grid = ft.GridView(
        expand=True,
        runs_count=3,
        max_extent=350,
        spacing=10,
        run_spacing=10,
        padding=20,
        child_aspect_ratio=1.2
    )
    
    # Função para pesquisar hosts
    def search_hosts(query: str):
        if not query:
            # Se a pesquisa estiver vazia, mostra todos os hosts ou filtra pelo grupo selecionado
            if filter_group_dropdown.value == "Todos os grupos":
                hosts_to_show = ssh_manager.saved_hosts
            else:
                hosts_to_show = ssh_manager.get_hosts_by_group(filter_group_dropdown.value)
        else:
            # Pesquisa por hosts que correspondem à consulta
            hosts_to_show = ssh_manager.search_hosts(query)
            # Se um grupo estiver selecionado, filtra ainda mais
            if filter_group_dropdown.value != "Todos os grupos":
                hosts_to_show = [h for h in hosts_to_show if h.group == filter_group_dropdown.value]
        
        update_host_grid(hosts_to_show)
    
    # Função para filtrar hosts por grupo
    def filter_hosts_by_group(group: str):
        if group == "Todos os grupos":
            hosts_to_show = ssh_manager.saved_hosts
        else:
            hosts_to_show = ssh_manager.get_hosts_by_group(group)
        
        # Se houver uma pesquisa ativa, filtra ainda mais
        if search_field.value:
            hosts_to_show = [h for h in hosts_to_show if 
                            search_field.value.lower() in h.name.lower() or 
                            search_field.value.lower() in h.host.lower() or 
                            search_field.value.lower() in h.username.lower()]
        
        update_host_grid(hosts_to_show)
    
    # Atualiza a grade de hosts
    def update_host_grid(hosts_to_show=None):
        host_grid.controls.clear()
        
        if hosts_to_show is None:
            if filter_group_dropdown.value == "Todos os grupos":
                hosts_to_show = ssh_manager.saved_hosts
            else:
                hosts_to_show = ssh_manager.get_hosts_by_group(filter_group_dropdown.value)
        
        for host in hosts_to_show:
            # Verifica se o cliente existe na plataforma atual
            client_exists = host.client in ssh_manager.ssh_client.get_platform_clients()
            icon_path = ssh_manager.ssh_client.get_client_icon(host.client) if client_exists else None
            
            # Ícone baseado no tipo de conexão
            connection_icon = ft.icons.TERMINAL
            if host.connection_type == ConnectionType.RDP:
                connection_icon = ft.icons.DESKTOP_WINDOWS
            
            # Cria um card para o host
            host_card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(connection_icon, color=accent_color, size=20),
                            ft.Text(host.name, weight=ft.FontWeight.BOLD, size=16, expand=True),
                            ft.Container(
                                content=ft.Text(host.group, size=12),
                                bgcolor=primary_color,
                                border_radius=15,
                                padding=ft.padding.only(left=10, right=10, top=5, bottom=5)
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(height=1, color=ft.colors.GREY_700),
                        ft.Container(height=10),
                        ft.Row([
                            ft.Image(
                                src=icon_path,
                                width=40,
                                height=40,
                                fit=ft.ImageFit.CONTAIN,
                                error_content=ft.Icon(ft.icons.COMPUTER)
                            ),
                            ft.Column([
                                ft.Text(f"Host: {host.host}", size=14),
                                ft.Text(f"Usuário: {host.username}", size=14),
                                ft.Text(f"Porta: {host.port}", size=14),
                                ft.Text(f"Cliente: {host.client}", size=14)
                            ], spacing=2, expand=True)
                        ], alignment=ft.MainAxisAlignment.START),
                        ft.Container(height=10),
                        ft.Row([
                            ft.ElevatedButton(
                                "Conectar",
                                icon=ft.icons.CONNECT_WITHOUT_CONTACT,
                                style=ft.ButtonStyle(
                                    bgcolor=accent_color,
                                    color=ft.colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=10)
                                ),
                                on_click=lambda e, h=host: connect_to_host(h)
                            ),
                            ft.PopupMenuButton(
                                icon=ft.icons.MORE_VERT,
                                tooltip="Mais opções",
                                items=[
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
                                    ft.PopupMenuItem(
                                        text="Conectar com script",
                                        icon=ft.icons.CODE,
                                        on_click=lambda e, h=host: show_script_selection(h)
                                    )
                                ]
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ], spacing=5),
                    padding=15,
                    border_radius=10,
                    bgcolor=card_color,
                ),
                elevation=5,
                margin=5,
            )
            
            host_grid.controls.append(host_card)
        
        # Mensagem se não houver hosts
        if not host_grid.controls:
            host_grid.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.SEARCH_OFF, size=50, color=ft.colors.GREY_500),
                        ft.Text("Nenhum host encontrado", size=16, color=ft.colors.GREY_500),
                        ft.Text("Adicione um novo host ou altere os filtros de pesquisa", 
                               size=14, color=ft.colors.GREY_500)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    expand=True
                )
            )
        
        page.update()
    
    # Seleciona um host
    def select_host(host: SSHSavedHost):
        nonlocal selected_host
        selected_host = host
        host_name.value = host.name
        host_address.value = host.host
        username.value = host.username
        password.value = host.password
        port.value = host.port
        connection_type_dropdown.value = host.connection_type
        update_client_dropdown(host.connection_type)
        
        # Verifica se o cliente existe na plataforma atual
        clients = ssh_manager.ssh_client.get_clients_by_type(host.connection_type)
        if host.client in clients:
            client_dropdown.value = host.client
        elif client_dropdown.options:
            client_dropdown.value = client_dropdown.options[0].text
            
        group_dropdown.value = host.group
        
        page.update()
    
    # Mostra o modal de seleção de script
    def show_script_selection(host: SSHSavedHost):
        nonlocal selected_host
        selected_host = host
        
        # Atualiza a lista de scripts disponíveis
        current_platform = platform.system().lower()
        scripts = ssh_manager.get_scripts_by_platform(current_platform)
        
        script_list = ft.ListView(
            expand=True,
            spacing=10,
            padding=10,
            auto_scroll=True
        )
        
        for script in scripts:
            script_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.icons.CODE, color=accent_color),
                            ft.Text(script.name, weight=ft.FontWeight.BOLD, size=16)
                        ]),
                        ft.Text(script.description, size=14, color=ft.colors.GREY_400),
                        ft.Container(
                            content=ft.Text(script.content, size=12, selectable=True),
                            bgcolor=ft.colors.GREY_900,
                            border_radius=5,
                            padding=10,
                            width=500
                        ),
                        ft.ElevatedButton(
                            "Executar este script",
                            icon=ft.icons.PLAY_ARROW,
                            on_click=lambda e, s=script: connect_with_script(host, s)
                        )
                    ], spacing=10),
                    padding=10,
                    border_radius=10,
                    bgcolor=card_color
                )
            )
        
        # Se não houver scripts, mostra uma mensagem
        if not script_list.controls:
            script_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.CODE_OFF, size=50, color=ft.colors.GREY_500),
                        ft.Text("Nenhum script disponível para esta plataforma", size=16, color=ft.colors.GREY_500),
                        ft.Text("Adicione scripts no gerenciador de scripts", size=14, color=ft.colors.GREY_500)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    expand=True
                )
            )
        
        # Cria o modal
        script_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Selecione um script para executar em {host.name}"),
            content=ft.Column([
                ft.Text("Selecione um script para executar após a conexão:"),
                ft.Container(
                    content=script_list,
                    height=400,
                    width=550
                )
            ], scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(script_dialog, "open", False)),
                ft.TextButton("Conectar sem script", on_click=lambda e: connect_to_host(host))
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            content_padding=ft.padding.all(20),
            inset_padding=ft.padding.all(10)
        )
        
        page.dialog = script_dialog
        script_dialog.open = True
        page.update()
    
    # Conecta com um script
    def connect_with_script(host: SSHSavedHost, script: Script):
        # Fecha o diálogo
        if page.dialog and page.dialog.open:
            page.dialog.open = False
            page.update()
        
        # Conecta ao host
        try:
            client_name = host.client
            clients = ssh_manager.ssh_client.get_platform_clients()
            client_cmd = clients[client_name]["command"]
            
            if host.connection_type == ConnectionType.SSH:
                # Conexão SSH
                if platform.system() == "Windows":
                    if client_cmd == "ssh":
                        # Cria um arquivo de script temporário
                        script_file = os.path.join(os.environ.get("TEMP", ""), f"ssh_script_{host.name}.bat")
                        with open(script_file, "w") as f:
                            f.write(f"@echo off\n")
                            f.write(f"echo Conectando a {host.name}...\n")
                            f.write(f"ssh {host.username}@{host.host} -p {host.port}\n")
                            f.write(f"echo Executando script: {script.name}\n")
                            f.write(f"{script.content}\n")
                            f.write(f"pause\n")
                        
                        command = f"start cmd /k {script_file}"
                    elif client_cmd in ["putty", "kitty"]:
                        # Não é possível executar scripts diretamente com PuTTY/KiTTY
                        # Então apenas conectamos normalmente
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
                    # Cria um arquivo de script temporário
                    script_file = os.path.join("/tmp", f"ssh_script_{host.name}.sh")
                    with open(script_file, "w") as f:
                        f.write("#!/bin/bash\n")
                        f.write(f"echo 'Conectando a {host.name}...'\n")
                        f.write(f"ssh {host.username}@{host.host} -p {host.port}\n")
                        f.write(f"echo 'Executando script: {script.name}'\n")
                        f.write(f"{script.content}\n")
                        f.write("read -p 'Pressione Enter para continuar...'\n")
                    
                    # Torna o script executável
                    os.chmod(script_file, 0o755)
                    
                    # Executa o script em um terminal
                    if platform.system() == "Darwin":  # macOS
                        command = f"open -a Terminal {script_file}"
                    else:  # Linux
                        # Tenta encontrar um terminal disponível
                        terminals = ["gnome-terminal", "xterm", "konsole", "terminator"]
                        for term in terminals:
                            if subprocess.run(["which", term], capture_output=True).returncode == 0:
                                command = f"{term} -e {script_file}"
                                break
                        else:
                            command = f"x-terminal-emulator -e {script_file}"
                    
                    subprocess.Popen(command, shell=True)
            else:
                # Para conexões RDP, não podemos executar scripts facilmente
                # Então apenas conectamos normalmente
                connect_to_host(host)
            
            show_success(f"Conexão iniciada com {host.host} e script '{script.name}' será executado")
        except Exception as e:
            show_error(f"Erro ao conectar com script: {str(e)}")
    
    # Conecta a um host
    def connect_to_host(host: SSHSavedHost = None):
        # Fecha o diálogo se estiver aberto
        if page.dialog and page.dialog.open:
            page.dialog.open = False
            page.update()
        
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
        update_host_grid()
        
        # Fecha o modal
        add_host_dialog.open = False
        page.update()
        
        show_success(f"Host '{host.name}' salvo com sucesso!")
        clear_fields()
    
    # Edita um host
    def edit_host(host: SSHSavedHost):
        select_host(host)
        
        # Abre o modal de edição
        add_host_dialog.title = ft.Text("Editar Host")
        add_host_dialog.content = ft.Column([
            ft.Text("Edite as informações do host:"),
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
            ft.Row([
                ft.TextButton(
                    "Adicionar Novo Grupo",
                    icon=ft.icons.ADD,
                    on_click=lambda e: show_add_group_dialog()
                )
            ], alignment=ft.MainAxisAlignment.END)
        ], scroll=ft.ScrollMode.AUTO, spacing=20)
        
        add_host_dialog.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: setattr(add_host_dialog, "open", False)),
            ft.TextButton("Salvar", on_click=lambda e: save_host())
        ]
        
        add_host_dialog.open = True
        page.update()
    
    # Exclui um host
    def delete_host(host: SSHSavedHost):
        def confirm_delete(e):
            ssh_manager.remove_host(host.name)
            update_groups()
            update_host_grid()
            dlg.open = False
            page.update()
            show_success(f"Host '{host.name}' excluído com sucesso!")
        
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
    
    # Mostra o diálogo para adicionar um novo grupo
    def show_add_group_dialog():
        new_group_field = ft.TextField(
            label="Nome do novo grupo",
            border_color=secondary_color,
            focused_border_color=accent_color,
            width=300
        )
        
        def add_new_group(e):
            new_group_name = new_group_field.value.strip()
            if not new_group_name:
                show_error("Por favor, informe um nome para o novo grupo")
                return
            
            existing_groups = ssh_manager.get_groups()
            if new_group_name in existing_groups:
                show_error("Já existe um grupo com esse nome")
                return
            
            # Adiciona o grupo ao dropdown
            group_dropdown.options.append(ft.dropdown.Option(new_group_name))
            group_dropdown.value = new_group_name
            
            # Adiciona o grupo ao dropdown de filtro
            filter_group_dropdown.options.append(ft.dropdown.Option(new_group_name))
            
            # Fecha o diálogo
            group_dialog.open = False
            page.update()
            show_success(f"Grupo '{new_group_name}' adicionado com sucesso!")
        
        group_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Adicionar Novo Grupo"),
            content=ft.Column([
                ft.Text("Digite o nome do novo grupo:"),
                new_group_field
            ], spacing=10),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(group_dialog, "open", False)),
                ft.TextButton("Adicionar", on_click=add_new_group)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        page.dialog = group_dialog
        group_dialog.open = True
        page.update()
    
    # Gerencia grupos
    def manage_groups(e):
        groups = ssh_manager.get_groups()
        selected_group_index = None
        
        # Lista de grupos com seleção
        group_list = ft.ListView(
            expand=True,
            spacing=5,
            auto_scroll=True,
            height=300
        )
        
        # Função para selecionar um grupo na lista
        def select_group(e):
            nonlocal selected_group_index
            selected_group_index = e.control.data
            # Atualiza a aparência dos itens da lista
            for i, item in enumerate(group_list.controls):
                if i == selected_group_index:
                    item.bgcolor = ft.colors.BLUE_800
                else:
                    item.bgcolor = None
            rename_field.value = groups[selected_group_index]
            page.update()
        
        # Adiciona os grupos à lista
        for i, group in enumerate(groups):
            group_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.GROUP, color=accent_color),
                        ft.Text(group, size=16, weight=ft.FontWeight.BOLD)
                    ], spacing=10),
                    padding=15,
                    border_radius=10,
                    bgcolor=None,
                    data=i,
                    on_click=select_group
                )
            )
        
        # Campo para adicionar novo grupo
        new_group_field = ft.TextField(
            label="Nome do novo grupo",
            border_color=secondary_color,
            focused_border_color=accent_color,
            expand=True
        )
        
        # Campo para renomear grupo
        rename_field = ft.TextField(
            label="Novo nome",
            border_color=secondary_color,
            focused_border_color=accent_color,
            expand=True
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
            
            # Adiciona o novo grupo à lista visual
            index = len(group_list.controls)
            group_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.GROUP, color=accent_color),
                        ft.Text(new_group_name, size=16, weight=ft.FontWeight.BOLD)
                    ], spacing=10),
                    padding=15,
                    border_radius=10,
                    bgcolor=None,
                    data=index,
                    on_click=select_group
                )
            )
            
            # Adiciona o grupo aos dropdowns
            group_dropdown.options.append(ft.dropdown.Option(new_group_name))
            filter_group_dropdown.options.append(ft.dropdown.Option(new_group_name))
            
            # Cria um host fictício para salvar o grupo
            dummy_host = SSHSavedHost(
                name=f"_dummy_{new_group_name}",
                host="localhost",
                username="dummy",
                password="",
                port="22",
                client="OpenSSH",
                group=new_group_name,
                connection_type=ConnectionType.SSH
            )
            
            # Adiciona e remove o host fictício para salvar o grupo
            ssh_manager.add_host(dummy_host)
            ssh_manager.remove_host(dummy_host.name)
            
            new_group_field.value = ""
            page.update()
            show_success(f"Grupo '{new_group_name}' adicionado")
        
        def rename_group_action(e):
            nonlocal selected_group_index
            if selected_group_index is None:
                show_error("Por favor, selecione um grupo para renomear")
                return
                
            old_name = groups[selected_group_index]
            new_name = rename_field.value.strip()
            
            if not new_name:
                show_error("Por favor, informe um novo nome para o grupo")
                return
            
            if new_name in groups and new_name != old_name:
                show_error("Já existe um grupo com esse nome")
                return
            
            ssh_manager.rename_group(old_name, new_name)
            
            # Atualiza a interface
            groups[selected_group_index] = new_name
            group_list.controls[selected_group_index].content.controls[1].value = new_name
            
            # Atualiza os dropdowns
            update_groups()
            update_host_grid()
            page.update()
            show_success(f"Grupo '{old_name}' renomeado para '{new_name}'")
        
        def delete_group_action(e):
            nonlocal selected_group_index
            if selected_group_index is None:
                show_error("Por favor, selecione um grupo para excluir")
                return
                
            group_name = groups[selected_group_index]
            
            if group_name == DEFAULT_GROUP:
                show_error("Não é possível excluir o grupo padrão")
                return
            
            def confirm_group_delete(e):
                ssh_manager.remove_group(group_name)
                
                # Atualiza a interface
                groups.pop(selected_group_index)
                group_list.controls.pop(selected_group_index)
                
                # Atualiza os índices dos itens restantes
                for i, item in enumerate(group_list.controls):
                    item.data = i
                
                update_groups()
                update_host_grid()
                confirm_dlg.open = False
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
        
        # Botão para fechar o diálogo
        def close_dialog(e):
            group_dialog.open = False
            page.update()
        
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
                ], spacing=10),
                ft.Divider(),
                ft.Text("Grupos existentes:", weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=group_list,
                    border=ft.border.all(1, ft.colors.GREY_600),
                    border_radius=10,
                    padding=10,
                    height=300
                ),
                ft.Text("Selecione um grupo para editar ou excluir", size=12, italic=True, color=ft.colors.GREY_400),
                ft.Divider(),
                ft.Text("Renomear grupo selecionado:", weight=ft.FontWeight.BOLD),
                rename_field,
            ], spacing=10, scroll=ft.ScrollMode.AUTO, height=600, width=500),
            actions=[
                ft.TextButton("Fechar", on_click=close_dialog),
                ft.TextButton("Excluir", on_click=delete_group_action, style=ft.ButtonStyle(color=ft.colors.RED)),
                ft.TextButton("Renomear", on_click=rename_group_action),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            # Ajusta o tamanho do diálogo para caber na tela
            content_padding=ft.padding.all(20),
            inset_padding=ft.padding.all(10)
        )
        
        page.dialog = group_dialog
        group_dialog.open = True
        page.update()
    
    # Gerencia scripts
    def manage_scripts(e):
        # Lista de scripts
        script_list = ft.ListView(
            expand=True,
            spacing=10,
            auto_scroll=True
        )
        
        # Atualiza a lista de scripts
        def update_script_list():
            script_list.controls.clear()
            
            for script in ssh_manager.scripts:
                script_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.icons.CODE, color=accent_color),
                                    ft.Text(script.name, weight=ft.FontWeight.BOLD, size=16, expand=True),
                                    ft.Container(
                                        content=ft.Text(script.platform, size=12),
                                        bgcolor=primary_color,
                                        border_radius=15,
                                        padding=ft.padding.only(left=10, right=10, top=5, bottom=5)
                                    )
                                ]),
                                ft.Text(script.description, size=14, color=ft.colors.GREY_400),
                                ft.Container(
                                    content=ft.Text(script.content, size=12, selectable=True),
                                    bgcolor=ft.colors.GREY_900,
                                    border_radius=5,
                                    padding=10
                                ),
                                ft.Row([
                                    ft.ElevatedButton(
                                        "Editar",
                                        icon=ft.icons.EDIT,
                                        on_click=lambda e, s=script: edit_script(s)
                                    ),
                                    ft.ElevatedButton(
                                        "Excluir",
                                        icon=ft.icons.DELETE,
                                        style=ft.ButtonStyle(color=ft.colors.RED),
                                        on_click=lambda e, s=script: delete_script(s)
                                    )
                                ], alignment=ft.MainAxisAlignment.END)
                            ], spacing=10),
                            padding=15,
                            border_radius=10,
                            bgcolor=card_color
                        ),
                        elevation=5,
                        margin=5
                    )
                )
            
            # Se não houver scripts, mostra uma mensagem
            if not script_list.controls:
                script_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.CODE_OFF, size=50, color=ft.colors.GREY_500),
                            ft.Text("Nenhum script cadastrado", size=16, color=ft.colors.GREY_500),
                            ft.Text("Adicione scripts para automatizar tarefas", size=14, color=ft.colors.GREY_500)
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        expand=True
                    )
                )
            
            page.update()
        
        # Edita um script
        def edit_script(script: Script):
            # Campos para edição
            script_name_field = ft.TextField(
                label="Nome do Script",
                value=script.name,
                border_color=secondary_color,
                focused_border_color=accent_color,
                expand=True
            )
            
            script_description_field = ft.TextField(
                label="Descrição",
                value=script.description,
                border_color=secondary_color,
                focused_border_color=accent_color,
                expand=True
            )
            
            script_content_field = ft.TextField(
                label="Conteúdo do Script",
                value=script.content,
                border_color=secondary_color,
                focused_border_color=accent_color,
                multiline=True,
                min_lines=5,
                max_lines=10,
                expand=True
            )
            
            script_platform_dropdown = ft.Dropdown(
                label="Plataforma",
                options=[
                    ft.dropdown.Option("all", "Todas as plataformas"),
                    ft.dropdown.Option("windows", "Windows"),
                    ft.dropdown.Option("linux", "Linux"),
                    ft.dropdown.Option("darwin", "macOS")
                ],
                value=script.platform,
                border_color=secondary_color,
                focused_border_color=accent_color,
                expand=True
            )
            
            def save_script_changes(e):
                # Valida os campos
                if not script_name_field.value:
                    show_error("Por favor, informe um nome para o script")
                    return
                
                if not script_content_field.value:
                    show_error("Por favor, informe o conteúdo do script")
                    return
                
                # Cria um novo script com os dados atualizados
                updated_script = Script(
                    name=script_name_field.value,
                    content=script_content_field.value,
                    description=script_description_field.value,
                    platform=script_platform_dropdown.value
                )
                
                # Atualiza o script
                ssh_manager.add_script(updated_script)
                
                # Fecha o diálogo
                edit_dialog.open = False
                
                # Atualiza a lista de scripts
                update_script_list()
                
                show_success(f"Script '{updated_script.name}' atualizado com sucesso!")
            
            edit_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Editar Script"),
                content=ft.Column([
                    script_name_field,
                    script_description_field,
                    script_platform_dropdown,
                    script_content_field
                ], spacing=10, scroll=ft.ScrollMode.AUTO, width=600),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: setattr(edit_dialog, "open", False)),
                    ft.TextButton("Salvar", on_click=save_script_changes)
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )
            
            page.dialog = edit_dialog
            edit_dialog.open = True
            page.update()
        
        # Exclui um script
        def delete_script(script: Script):
            def confirm_delete(e):
                ssh_manager.remove_script(script.name)
                update_script_list()
                confirm_dialog.open = False
                page.update()
                show_success(f"Script '{script.name}' excluído com sucesso!")
            
            confirm_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirmar exclusão"),
                content=ft.Text(f"Tem certeza que deseja excluir o script '{script.name}'?"),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: setattr(confirm_dialog, "open", False)),
                    ft.TextButton("Excluir", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.colors.RED))
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )
            
            page.dialog = confirm_dialog
            confirm_dialog.open = True
            page.update()
        
        # Adiciona um novo script
        def add_new_script(e):
            # Campos para o novo script
            script_name_field = ft.TextField(
                label="Nome do Script",
                border_color=secondary_color,
                focused_border_color=accent_color,
                expand=True
            )
            
            script_description_field = ft.TextField(
                label="Descrição",
                border_color=secondary_color,
                focused_border_color=accent_color,
                expand=True
            )
            
            script_content_field = ft.TextField(
                label="Conteúdo do Script",
                border_color=secondary_color,
                focused_border_color=accent_color,
                multiline=True,
                min_lines=5,
                max_lines=10,
                expand=True
            )
            
            script_platform_dropdown = ft.Dropdown(
                label="Plataforma",
                options=[
                    ft.dropdown.Option("all", "Todas as plataformas"),
                    ft.dropdown.Option("windows", "Windows"),
                    ft.dropdown.Option("linux", "Linux"),
                    ft.dropdown.Option("darwin", "macOS")
                ],
                value="all",
                border_color=secondary_color,
                focused_border_color=accent_color,
                expand=True
            )
            
            def save_new_script(e):
                # Valida os campos
                if not script_name_field.value:
                    show_error("Por favor, informe um nome para o script")
                    return
                
                if not script_content_field.value:
                    show_error("Por favor, informe o conteúdo do script")
                    return
                
                # Cria um novo script
                new_script = Script(
                    name=script_name_field.value,
                    content=script_content_field.value,
                    description=script_description_field.value,
                    platform=script_platform_dropdown.value
                )
                
                # Adiciona o script
                ssh_manager.add_script(new_script)
                
                # Fecha o diálogo
                add_script_dialog.open = False
                
                # Atualiza a lista de scripts
                update_script_list()
                
                show_success(f"Script '{new_script.name}' adicionado com sucesso!")
            
            add_script_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Adicionar Novo Script"),
                content=ft.Column([
                    script_name_field,
                    script_description_field,
                    script_platform_dropdown,
                    script_content_field
                ], spacing=10, scroll=ft.ScrollMode.AUTO, width=600),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: setattr(add_script_dialog, "open", False)),
                    ft.TextButton("Salvar", on_click=save_new_script)
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )
            
            page.dialog = add_script_dialog
            add_script_dialog.open = True
            page.update()
        
        # Atualiza a lista de scripts
        update_script_list()
        
        # Cria o diálogo de gerenciamento de scripts
        scripts_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Gerenciar Scripts"),
            content=ft.Column([
                ft.Row([
                    ft.Text("Scripts disponíveis", size=16, weight=ft.FontWeight.BOLD, expand=True),
                    ft.ElevatedButton(
                        "Adicionar Script",
                        icon=ft.icons.ADD,
                        on_click=add_new_script
                    )
                ]),
                ft.Container(
                    content=script_list,
                    height=500,
                    width=700
                )
            ], spacing=10),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: setattr(scripts_dialog, "open", False))
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            content_padding=ft.padding.all(20),
            inset_padding=ft.padding.all(10)
        )
        
        page.dialog = scripts_dialog
        scripts_dialog.open = True
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
    
    # Cria o modal para adicionar/editar hosts
    add_host_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Adicionar Novo Host"),
        content=ft.Column([
            ft.Text("Preencha as informações do host:"),
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
            ft.Row([
                ft.TextButton(
                    "Adicionar Novo Grupo",
                    icon=ft.icons.ADD,
                    on_click=lambda e: show_add_group_dialog()
                )
            ], alignment=ft.MainAxisAlignment.END)
        ], scroll=ft.ScrollMode.AUTO, spacing=20),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: setattr(add_host_dialog, "open", False)),
            ft.TextButton("Salvar", on_click=lambda e: save_host())
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )
    
    # Função para mostrar o diálogo de adicionar host
    def show_add_host_dialog(e=None):
        clear_fields()
        add_host_dialog.title = ft.Text("Adicionar Novo Host")
        add_host_dialog.open = True
        page.update()
    
    # Botão para adicionar novo host
    add_host_button = ft.ElevatedButton(
        "Adicionar Host",
        icon=ft.icons.ADD,
        style=ft.ButtonStyle(
            bgcolor=accent_color,
            color=ft.colors.WHITE,
            padding=15,
            shape=ft.RoundedRectangleBorder(radius=10)
        ),
        on_click=show_add_host_dialog
    )
    
    # Botão para gerenciar grupos
    manage_groups_button = ft.ElevatedButton(
        "Gerenciar Grupos",
        icon=ft.icons.GROUP_WORK,
        style=ft.ButtonStyle(
            bgcolor=primary_color,
            color=ft.colors.WHITE,
            padding=15,
            shape=ft.RoundedRectangleBorder(radius=10)
        ),
        on_click=manage_groups
    )
    
    # Botão para gerenciar scripts
    manage_scripts_button = ft.ElevatedButton(
        "Gerenciar Scripts",
        icon=ft.icons.CODE,
        style=ft.ButtonStyle(
            bgcolor=primary_color,
            color=ft.colors.WHITE,
            padding=15,
            shape=ft.RoundedRectangleBorder(radius=10)
        ),
        on_click=manage_scripts
    )
    
    # Barra de ferramentas
    toolbar = ft.Container(
        content=ft.Row([
            add_host_button,
            manage_groups_button,
            manage_scripts_button,
            ft.VerticalDivider(width=20, color=ft.colors.TRANSPARENT),
            ft.Column([
                search_field,
            ], expand=True),
            filter_group_dropdown
        ], spacing=10, alignment=ft.MainAxisAlignment.START),
        padding=10,
        border_radius=10,
        bgcolor=card_color
    )
    
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
    
    # Layout principal
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
            toolbar,
            ft.Divider(height=1, color=ft.colors.GREY_700),
            host_grid,
            status_bar
        ], spacing=10, expand=True)
    )
    
    # Inicializa os dados
    update_client_dropdown(ConnectionType.SSH)
    update_groups()
    update_script_dropdown()
    update_host_grid()
    
    # Chama o redimensionamento inicial para configurar o layout
    page_resize(None)

if __name__ == "__main__":
    ft.app(target=main)
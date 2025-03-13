import flet as ft
import subprocess
import os
import threading
import glob

class Module:
    def __init__(self):
        self.page = None
        self.process = None
        self.is_running = False
        self.selected_module = None
        self.modules_list = []
        
    def get_module_info(self):
        return {
            "name": "Programa Externo",
            "description": "Executa o programa externo enviado",
            "version": "1.0.0",
            "icon": ft.icons.PLAY_CIRCLE_OUTLINED,
            "color": ft.colors.PURPLE,
        }
    
    def _scan_modules(self):
        """Scans the current directory for Python modules"""
        # Get the directory where this module is located
        current_dir = os.path.dirname(__file__)
        
        # Look for Python files in the current directory
        module_files = glob.glob(os.path.join(current_dir, "*.py"))
        
        # Filter out this module itself
        module_files = [f for f in module_files if os.path.basename(f) != os.path.basename(__file__)]
        
        # Convert to module names for display
        self.modules_list = [os.path.basename(f) for f in module_files]
        
        return self.modules_list
    
    def _run_program(self):
        try:
            script_path = ""
            
            # If a specific module is selected, use that
            if self.selected_module:
                script_path = os.path.join(os.path.dirname(__file__), self.selected_module)
            else:
                # Use the original path for backward compatibility
                script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main-4iNxk42ZPyHPY4N4tvkHUpN76v5uXm.py")
            
            if not os.path.exists(script_path):
                if self.page:
                    self.status_text.value = f"Erro: Arquivo {script_path} não encontrado"
                    self.status_text.color = ft.colors.RED
                    self.page.update()
                return
            
            # Executa o programa em um processo separado
            self.process = subprocess.Popen(["python", script_path], 
                                           stdout=subprocess.PIPE, 
                                           stderr=subprocess.PIPE)
            
            self.is_running = True
            if self.page:
                self.status_text.value = f"Executando: {os.path.basename(script_path)}..."
                self.status_text.color = ft.colors.GREEN
                self.run_button.text = "Parar Programa"
                self.run_button.icon = ft.icons.STOP
                self.page.update()
            
            # Aguarda o término do processo
            stdout, stderr = self.process.communicate()
            
            if self.process.returncode == 0:
                if self.page:
                    self.status_text.value = "Programa concluído com sucesso"
                    self.status_text.color = ft.colors.GREEN
            else:
                if self.page:
                    self.status_text.value = f"Erro ao executar o programa: {stderr.decode('utf-8')}"
                    self.status_text.color = ft.colors.RED
            
            self.is_running = False
            if self.page:
                self.run_button.text = "Executar Programa"
                self.run_button.icon = ft.icons.PLAY_ARROW
                self.page.update()
                
        except Exception as e:
            if self.page:
                self.status_text.value = f"Erro: {str(e)}"
                self.status_text.color = ft.colors.RED
                self.run_button.text = "Executar Programa"
                self.run_button.icon = ft.icons.PLAY_ARROW
                self.is_running = False
                self.page.update()
    
    def _handle_run_button(self, e):
        if not self.is_running:
            # Inicia o programa em uma thread separada
            threading.Thread(target=self._run_program, daemon=True).start()
        else:
            # Tenta encerrar o programa se estiver em execução
            if self.process:
                try:
                    self.process.terminate()
                    self.status_text.value = "Programa interrompido"
                    self.status_text.color = ft.colors.ORANGE
                    self.run_button.text = "Executar Programa"
                    self.run_button.icon = ft.icons.PLAY_ARROW
                    self.is_running = False
                    self.page.update()
                except Exception as e:
                    self.status_text.value = f"Erro ao interromper o programa: {str(e)}"
                    self.status_text.color = ft.colors.RED
                    self.page.update()
    
    def _handle_module_selection(self, e):
        """Handle module selection from dropdown"""
        self.selected_module = e.data
        if self.page:  # Check if page exists before updating
            self.status_text.value = f"Módulo selecionado: {self.selected_module}"
            self.status_text.color = ft.colors.BLUE
            self.page.update()
    
    def _handle_refresh_button(self, e):
        """Refresh the list of available modules"""
        self._scan_modules()
        self.module_dropdown.options = [ft.dropdown.Option(module) for module in self.modules_list]
        if self.page:  # Check if page exists before updating
            self.status_text.value = f"Encontrados {len(self.modules_list)} módulos"
            self.status_text.color = ft.colors.BLUE
            self.page.update()
    
    def get_view(self):
        # Título
        title = ft.Text("Executar Programa Externo", size=24, weight=ft.FontWeight.BOLD)
        
        # Descrição
        description = ft.Text(
            "Este módulo permite executar o programa externo que foi enviado ou selecionar "
            "um módulo da pasta atual para executar. "
            "Selecione um módulo e clique no botão para iniciar ou parar a execução.",
            size=16,
        )
        
        # Status text must be initialized before scanning modules
        self.status_text = ft.Text("Pronto para executar", size=16, color=ft.colors.BLUE)
        
        # Scan for modules initially
        self._scan_modules()
        
        # Module selection dropdown
        self.module_dropdown = ft.Dropdown(
            label="Selecione um módulo",
            hint_text="Escolha o módulo para executar",
            options=[ft.dropdown.Option(module) for module in self.modules_list],
            width=400,
            on_change=self._handle_module_selection,
        )
        
        # Refresh button for module list
        refresh_button = ft.IconButton(
            icon=ft.icons.REFRESH,
            tooltip="Atualizar lista de módulos",
            on_click=self._handle_refresh_button,
        )
        
        # Module selection row
        module_selection_row = ft.Row([
            self.module_dropdown,
            refresh_button
        ])
        
        # Botão de execução
        self.run_button = ft.ElevatedButton(
            text="Executar Programa",
            icon=ft.icons.PLAY_ARROW,
            on_click=self._handle_run_button,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )
        
        # Container principal
        return ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            title,
                            ft.Divider(),
                            description,
                            ft.Container(height=20),
                            module_selection_row,
                            ft.Container(height=20),
                            self.status_text,
                            ft.Container(height=20),
                            self.run_button,
                        ],
                        spacing=10,
                    ),
                    padding=20,
                    border_radius=10,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                    width=600,
                    expand=True,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
    
    def did_mount(self, page):
        """Chamado quando o módulo é montado na página"""
        self.page = page
    
    def will_unmount(self):
        """Chamado quando o módulo é desmontado da página"""
        if self.is_running and self.process:
            try:
                self.process.terminate()
            except:
                pass
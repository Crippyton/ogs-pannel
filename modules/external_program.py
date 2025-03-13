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
        self.current_directory = None
        self.base_directory = None
        
    def get_module_info(self):
        return {
            "name": "Programa Externo",
            "description": "Executa o programa externo enviado",
            "version": "1.0.0",
            "icon": ft.icons.PLAY_CIRCLE_OUTLINED,
            "color": ft.colors.PURPLE,
        }
    
    def _scan_directories(self):
        """Scan for directories within the modules folder"""
        # Get the base modules directory
        self.base_directory = os.path.dirname(__file__)
        self.current_directory = self.base_directory
        
        # Find all directories in the modules folder
        directories = []
        for item in os.listdir(self.base_directory):
            full_path = os.path.join(self.base_directory, item)
            if os.path.isdir(full_path):
                directories.append(item)
        
        # Add the current directory as an option
        directories.insert(0, ".")
        
        return directories
    
    def _scan_modules(self, directory=None):
        """Scans the specified directory for Python modules"""
        if directory is None:
            directory = self.current_directory
        else:
            if directory == ".":
                self.current_directory = self.base_directory
            else:
                self.current_directory = os.path.join(self.base_directory, directory)
        
        # Look for Python files in the current directory
        module_files = glob.glob(os.path.join(self.current_directory, "*.py"))
        
        # Filter out this module itself if we're in the base directory
        if self.current_directory == self.base_directory:
            module_files = [f for f in module_files if os.path.basename(f) != os.path.basename(__file__)]
        
        # Convert to module names for display
        self.modules_list = [os.path.basename(f) for f in module_files]
        
        return self.modules_list
    
    def _run_program(self):
        try:
            script_path = ""
            
            # If a specific module is selected, use that
            if self.selected_module:
                script_path = os.path.join(self.current_directory, self.selected_module)
            else:
                # Use the original path for backward compatibility
                script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main-4iNxk42ZPyHPY4N4tvkHUpN76v5uXm.py")
            
            if not os.path.exists(script_path):
                if self.page:
                    self.status_text.value = f"Erro: Arquivo {script_path} não encontrado"
                    self.status_text.color = ft.colors.RED
                    self.page.update()
                return
            
            # Get working directory - use the directory of the script
            working_directory = os.path.dirname(script_path)
            
            # Executa o programa em um processo separado, usando a pasta do script como diretório de trabalho
            self.process = subprocess.Popen(
                ["python", script_path], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                cwd=working_directory  # Set working directory to the script's directory
            )
            
            self.is_running = True
            if self.page:
                relative_path = os.path.relpath(script_path, self.base_directory)
                self.status_text.value = f"Executando: {relative_path}..."
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
                    # Show output if available
                    if stdout:
                        output = stdout.decode('utf-8').strip()
                        if output:
                            self.status_text.value = f"Programa concluído com sucesso\nSaída: {output[:200]}{'...' if len(output) > 200 else ''}"
            else:
                if self.page:
                    error_msg = stderr.decode('utf-8').strip() if stderr else "Erro desconhecido"
                    self.status_text.value = f"Erro ao executar o programa: {error_msg[:200]}{'...' if len(error_msg) > 200 else ''}"
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
    
    def _handle_directory_selection(self, e):
        """Handle directory selection from dropdown"""
        selected_dir = e.data
        self._scan_modules(selected_dir)
        
        # Update module dropdown with new modules from selected directory
        if self.page:
            self.module_dropdown.options.clear()
            for module in self.modules_list:
                self.module_dropdown.options.append(ft.dropdown.Option(module))
            self.module_dropdown.value = None  # Reset selection
            self.selected_module = None
            
            # Get directory name for display
            display_dir = "pasta atual" if selected_dir == "." else selected_dir
            self.status_text.value = f"Diretório selecionado: {display_dir} ({len(self.modules_list)} módulos encontrados)"
            self.status_text.color = ft.colors.BLUE
            self.page.update()
    
    def _handle_module_selection(self, e):
        """Handle module selection from dropdown"""
        self.selected_module = e.data
        if self.page:  # Check if page exists before updating
            relative_path = os.path.join(os.path.relpath(self.current_directory, self.base_directory), self.selected_module)
            if relative_path.startswith('.\\') or relative_path.startswith('./'):
                relative_path = relative_path[2:]
            self.status_text.value = f"Módulo selecionado: {relative_path}"
            self.status_text.color = ft.colors.BLUE
            self.page.update()
    
    def _handle_refresh_button(self, e):
        """Refresh the list of available directories and modules"""
        # Refresh directories
        directories = self._scan_directories()
        self.directory_dropdown.options.clear()
        for directory in directories:
            display_name = "Pasta atual" if directory == "." else directory
            self.directory_dropdown.options.append(ft.dropdown.Option(key=directory, text=display_name))
        
        # Refresh modules in current directory
        self._scan_modules()
        self.module_dropdown.options.clear()
        for module in self.modules_list:
            self.module_dropdown.options.append(ft.dropdown.Option(module))
        
        if self.page:  # Check if page exists before updating
            self.status_text.value = f"Lista atualizada: {len(self.modules_list)} módulos encontrados"
            self.status_text.color = ft.colors.BLUE
            self.page.update()
    
    def get_view(self):
        # Título
        title = ft.Text("Executar Programa Externo", size=24, weight=ft.FontWeight.BOLD)
        
        # Descrição
        description = ft.Text(
            "Este módulo permite executar o programa externo que foi enviado ou selecionar "
            "um módulo da pasta atual ou subpastas para executar. "
            "Selecione uma pasta, escolha um módulo e clique no botão para iniciar ou parar a execução.",
            size=16,
        )
        
        # Status text must be initialized before scanning modules
        self.status_text = ft.Text("Pronto para executar", size=16, color=ft.colors.BLUE)
        
        # Initialize directory paths
        self.base_directory = os.path.dirname(__file__)
        self.current_directory = self.base_directory
        
        # Scan for directories
        directories = self._scan_directories()
        
        # Directory selection dropdown
        self.directory_dropdown = ft.Dropdown(
            label="Selecione uma pasta",
            hint_text="Escolha a pasta do módulo",
            options=[ft.dropdown.Option(key=d, text="Pasta atual" if d == "." else d) for d in directories],
            width=400,
            on_change=self._handle_directory_selection,
        )
        
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
        
        # Refresh button for directory/module lists
        refresh_button = ft.IconButton(
            icon=ft.icons.REFRESH,
            tooltip="Atualizar lista de pastas e módulos",
            on_click=self._handle_refresh_button,
        )
        
        # Selection rows
        directory_selection_row = ft.Row([
            self.directory_dropdown,
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
                            directory_selection_row,
                            ft.Container(height=10),
                            self.module_dropdown,
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
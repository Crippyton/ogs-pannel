import flet as ft
import subprocess
import os
import threading
import glob
import time
import platform
import psutil
import shutil

class Module:
    def __init__(self):
        self.page = None
        self.process = None
        self.is_running = False
        self.selected_module = None
        self.modules_list = []
        self.current_directory = None
        self.base_directory = None
        self.process_start_time = None
        self.execution_history = []
        self.max_history_items = 10
        self.output_text = None
        self.output_container = None
        self.process_monitor_thread = None
        self.should_monitor = False
        self.folder_browser = None
        self.breadcrumb_row = None
        self.current_path_parts = []
        
    def get_module_info(self):
        return {
            "name": "Programa Externo",
            "description": "Executa o programa externo enviado",
            "version": "1.2.0",
            "icon": ft.Icons.PLAY_CIRCLE_OUTLINED,
            "color": ft.Colors.PURPLE,
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
            if isinstance(directory, ft.ControlEvent):
                # If this is an event, extract the directory from data
                if hasattr(directory.control, 'data'):
                    directory = directory.control.data
        
            if directory == ".":
                self.current_directory = self.base_directory
            else:
                self.current_directory = directory if os.path.isabs(directory) else os.path.join(self.base_directory, directory)
    
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
                    self.status_text.color = ft.Colors.RED
                    self.page.update()
                return
            
            # Get working directory - use the directory of the script
            working_directory = os.path.dirname(script_path)
            
            # Verifica se é o módulo pacs.py e ajusta o caminho das imagens
            if self.selected_module and "pacs.py" in self.selected_module:
                # Define variáveis de ambiente para o caminho das imagens
                os.environ["PACS_ASSETS_PATH"] = os.path.abspath(os.path.join(os.path.dirname(script_path), "assets"))
                
                # Exibe informação sobre o caminho dos assets
                if self.page and self.output_text:
                    self.output_text.value += f"Configurando caminho de assets para: {os.environ['PACS_ASSETS_PATH']}\n"
                    self.page.update()

            # Executa o programa em um processo separado, usando a pasta do script como diretório de trabalho
            self.process = subprocess.Popen(
                ["python", script_path], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                cwd=working_directory,  # Set working directory to the script's directory
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=os.environ  # Passa as variáveis de ambiente para o processo filho
            )
            
            self.process_start_time = time.time()
            self.is_running = True
            
            # Start process monitoring
            self.should_monitor = True
            self.process_monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
            self.process_monitor_thread.start()
            
            if self.page:
                relative_path = os.path.relpath(script_path, self.base_directory)
                self.status_text.value = f"Executando: {relative_path}..."
                self.status_text.color = ft.Colors.GREEN
                self.run_button.text = "Parar Programa"
                self.run_button.icon = ft.Icons.STOP
                self.output_text.value = "Iniciando execução...\n"
                self.output_container.visible = True
                self.page.update()
            
            # Read output in real-time
            def read_output():
                while self.is_running and self.process:
                    try:
                        # Read stdout line by line
                        stdout_line = self.process.stdout.readline()
                        if stdout_line:
                            if self.page and self.output_text:
                                self.output_text.value += f"{stdout_line}"
                                self.page.update()
                        
                        # Read stderr line by line
                        stderr_line = self.process.stderr.readline()
                        if stderr_line:
                            if self.page and self.output_text:
                                self.output_text.value += f"ERRO: {stderr_line}"
                                self.page.update()
                        
                        # If both are empty and process is not running, break
                        if not stdout_line and not stderr_line and self.process.poll() is not None:
                            break
                            
                    except Exception as e:
                        if self.page and self.output_text:
                            self.output_text.value += f"Erro ao ler saída: {str(e)}\n"
                            self.page.update()
                        break
            
            # Start reading output in a separate thread
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()
            
            # Aguarda o término do processo
            self.process.wait()
            
            # Calculate execution time
            execution_time = time.time() - self.process_start_time
            
            # Add to history
            self._add_to_history(script_path, self.process.returncode, execution_time)
            
            if self.process.returncode == 0:
                if self.page:
                    self.status_text.value = f"Programa concluído com sucesso (tempo: {self._format_time(execution_time)})"
                    self.status_text.color = ft.Colors.GREEN
            else:
                if self.page:
                    self.status_text.value = f"Erro ao executar o programa (código: {self.process.returncode})"
                    self.status_text.color = ft.Colors.RED
            
            self.is_running = False
            self.should_monitor = False
            
            if self.page:
                self.run_button.text = "Executar Programa"
                self.run_button.icon = ft.Icons.PLAY_ARROW
                self.page.update()
                
        except Exception as e:
            if self.page:
                self.status_text.value = f"Erro: {str(e)}"
                self.status_text.color = ft.Colors.RED
                self.run_button.text = "Executar Programa"
                self.run_button.icon = ft.Icons.PLAY_ARROW
                self.is_running = False
                self.should_monitor = False
                self.page.update()
    
    def _monitor_process(self):
        """Monitor process resource usage"""
        try:
            if not self.process or not self.is_running:
                return
                
            process = psutil.Process(self.process.pid)
            
            while self.should_monitor and self.is_running and self.process:
                try:
                    # Get CPU and memory usage
                    cpu_percent = process.cpu_percent(interval=1)
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
                    
                    # Update resource usage display
                    if self.page and hasattr(self, 'resource_text'):
                        execution_time = time.time() - self.process_start_time
                        self.resource_text.value = (
                            f"Tempo: {self._format_time(execution_time)} | "
                            f"CPU: {cpu_percent:.1f}% | "
                            f"Memória: {memory_mb:.1f} MB"
                        )
                        self.page.update()
                    
                    time.sleep(1)  # Update every second
                except:
                    # Process might have ended
                    break
        except:
            # Process monitoring failed
            pass
    
    def _format_time(self, seconds):
        """Format time in seconds to a readable string"""
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def _add_to_history(self, script_path, return_code, execution_time):
        """Add an execution to history"""
        relative_path = os.path.relpath(script_path, self.base_directory)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        history_item = {
            "path": relative_path,
            "timestamp": timestamp,
            "status": "Sucesso" if return_code == 0 else f"Erro (código {return_code})",
            "execution_time": execution_time
        }
        
        self.execution_history.insert(0, history_item)
        
        # Limit history size
        if len(self.execution_history) > self.max_history_items:
            self.execution_history = self.execution_history[:self.max_history_items]
        
        # Update history display if available
        if self.page and hasattr(self, 'history_list'):
            self._update_history_display()
    
    def _update_history_display(self):
        """Update the history display with current execution history"""
        if not hasattr(self, 'history_list'):
            return
            
        self.history_list.controls.clear()
        
        for item in self.execution_history:
            status_color = ft.Colors.GREEN if item["status"] == "Sucesso" else ft.Colors.RED
            
            history_item = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(
                            name=ft.Icons.CHECK_CIRCLE if item["status"] == "Sucesso" else ft.Icons.ERROR,
                            color=status_color,
                            size=16
                        ),
                        ft.Text(
                            item["path"],
                            weight=ft.FontWeight.BOLD,
                            size=14,
                        ),
                    ]),
                    ft.Row([
                        ft.Text(
                            f"{item['timestamp']} | {item['status']} | Tempo: {self._format_time(item['execution_time'])}",
                            size=12,
                            color=ft.Colors.GREY_700,
                        ),
                    ]),
                ]),
                padding=10,
                margin=ft.margin.only(bottom=5),
                border_radius=5,
                bgcolor=ft.Colors.BLUE_50,
                border=ft.border.all(1, ft.Colors.BLUE_200),
            )
            
            self.history_list.controls.append(history_item)
        
        if not self.execution_history:
            self.history_list.controls.append(
                ft.Text("Nenhuma execução registrada", italic=True, color=ft.Colors.GREY_500)
            )
        
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
                    self.status_text.color = ft.Colors.ORANGE
                    self.run_button.text = "Executar Programa"
                    self.run_button.icon = ft.Icons.PLAY_ARROW
                    self.is_running = False
                    self.should_monitor = False
                    self.page.update()
                except Exception as e:
                    self.status_text.value = f"Erro ao interromper o programa: {str(e)}"
                    self.status_text.color = ft.Colors.RED
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
            self.status_text.color = ft.Colors.BLUE
            self.page.update()
    
    def _handle_module_selection(self, e):
        """Handle module selection from dropdown"""
        self.selected_module = e.data
        if self.page:  # Check if page exists before updating
            relative_path = os.path.join(os.path.relpath(self.current_directory, self.base_directory), self.selected_module)
            if relative_path.startswith('.\\') or relative_path.startswith('./'):
                relative_path = relative_path[2:]
            self.status_text.value = f"Módulo selecionado: {relative_path}"
            self.status_text.color = ft.Colors.BLUE
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
        
        # Update folder browser if it exists
        if hasattr(self, 'folder_browser') and self.folder_browser:
            self._update_folder_browser()
        
        if self.page:  # Check if page exists before updating
            self.status_text.value = f"Lista atualizada: {len(self.modules_list)} módulos encontrados"
            self.status_text.color = ft.Colors.BLUE
            self.page.update()
    
    def _handle_clear_output(self, e):
        """Clear the output text"""
        if self.output_text:
            self.output_text.value = ""
            self.page.update()
    
    def _handle_copy_output(self, e):
        """Copy output text to clipboard"""
        if self.output_text and self.output_text.value:
            self.page.set_clipboard(self.output_text.value)
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("Saída copiada para a área de transferência"),
                    action="OK",
                )
            )
    
    def _get_system_info(self):
        """Get system information"""
        info = []
        info.append(f"Sistema: {platform.system()} {platform.version()}")
        info.append(f"Python: {platform.python_version()}")
        info.append(f"Processador: {platform.processor()}")
        
        # Get memory info
        try:
            virtual_memory = psutil.virtual_memory()
            total_gb = virtual_memory.total / (1024**3)
            available_gb = virtual_memory.available / (1024**3)
            info.append(f"Memória: {available_gb:.1f} GB livre de {total_gb:.1f} GB")
        except:
            pass
            
        # Get disk info
        try:
            disk = psutil.disk_usage('/')
            total_gb = disk.total / (1024**3)
            free_gb = disk.free / (1024**3)
            info.append(f"Disco: {free_gb:.1f} GB livre de {total_gb:.1f} GB")
        except:
            pass
            
        return "\n".join(info)
    
    def _handle_show_system_info(self, e):
        """Show system information dialog"""
        system_info = self._get_system_info()
        
        info_dialog = ft.AlertDialog(
            title=ft.Text("Informações do Sistema"),
            content=ft.Container(
                content=ft.Text(system_info),
                width=400,
                padding=20,
            ),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: self._close_dialog(info_dialog)),
                ft.TextButton("Copiar", on_click=lambda e: self._copy_system_info(system_info, info_dialog)),
            ],
        )
        
        self.page.dialog = info_dialog
        info_dialog.open = True
        self.page.update()
    
    def _copy_system_info(self, info, dialog):
        """Copy system info to clipboard and close dialog"""
        self.page.set_clipboard(info)
        dialog.open = False
        self.page.update()
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text("Informações copiadas para a área de transferência"),
                action="OK",
            )
        )
    
    def _close_dialog(self, dialog):
        """Close a dialog"""
        dialog.open = False
        self.page.update()
    
    def _update_folder_browser(self):
        """Update the folder browser with current directory structure"""
        if not hasattr(self, 'folder_browser') or not self.folder_browser:
            return
        
        self.folder_browser.controls.clear()
        
        # Add parent directory option if not at base directory
        if self.current_directory != self.base_directory:
            parent_dir = os.path.dirname(self.current_directory)
            parent_item = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.FOLDER_OPEN, color=ft.Colors.BLUE),
                    ft.Text(".."),
                ]),
                padding=10,
                margin=5,
                border_radius=5,
                bgcolor=ft.Colors.BLUE_50,
                on_click=lambda e, p=parent_dir: self._navigate_to_directory(p),
                data=parent_dir,
            )
            self.folder_browser.controls.append(parent_item)
        
        # Add directories
        for item in sorted(os.listdir(self.current_directory)):
            full_path = os.path.join(self.current_directory, item)
            if os.path.isdir(full_path):
                dir_item = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.FOLDER, color=ft.Colors.AMBER),
                        ft.Text(item),
                    ]),
                    padding=10,
                    margin=5,
                    border_radius=5,
                    bgcolor=ft.Colors.AMBER_50,
                    on_click=lambda e, p=full_path: self._navigate_to_directory(p),
                    data=full_path,
                )
                self.folder_browser.controls.append(dir_item)
        
        # Add Python files only if we're not in the base directory
        if self.current_directory != self.base_directory:
            for item in sorted(os.listdir(self.current_directory)):
                full_path = os.path.join(self.current_directory, item)
                if os.path.isfile(full_path) and item.endswith('.py'):
                    # Skip this module itself if somehow we're in its directory
                    if item == os.path.basename(__file__):
                        continue
                    
                    file_item = ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.CODE, color=ft.Colors.GREEN),
                            ft.Text(item),
                        ]),
                        padding=10,
                        margin=5,
                        border_radius=5,
                        bgcolor=ft.Colors.GREEN_50,
                        on_click=lambda e, p=full_path: self._select_module_file(p),
                        data=full_path,
                    )
                    self.folder_browser.controls.append(file_item)
        
        # Update breadcrumb
        self._update_breadcrumb()
        
        if self.page:
            self.page.update()
    
    def _navigate_to_directory(self, directory):
        """Navigate to the specified directory"""
        # Ensure we're using the correct directory path
        if isinstance(directory, ft.ControlEvent):
            # If this is an event, extract the directory from data
            if hasattr(directory.control, 'data'):
                directory = directory.control.data
    
        self.current_directory = directory
        self._scan_modules(directory)
        self._update_folder_browser()
        
        # Update module dropdown
        self.module_dropdown.options.clear()
        for module in self.modules_list:
            self.module_dropdown.options.append(ft.dropdown.Option(module))
        self.module_dropdown.value = None
        self.selected_module = None
        
        # Update status
        rel_path = os.path.relpath(directory, self.base_directory)
        display_path = rel_path if rel_path != "." else "pasta atual"
        self.status_text.value = f"Diretório selecionado: {display_path} ({len(self.modules_list)} módulos encontrados)"
        self.status_text.color = ft.Colors.BLUE
        
        if self.page:
            self.page.update()
    
    def _select_module_file(self, file_path):
        """Select a module file from the browser"""
        # Get the module name (filename)
        module_name = os.path.basename(file_path)
        
        # Set as selected module
        self.selected_module = module_name
        self.module_dropdown.value = module_name
        
        # Update status
        rel_path = os.path.relpath(file_path, self.base_directory)
        self.status_text.value = f"Módulo selecionado: {rel_path}"
        self.status_text.color = ft.Colors.BLUE
        
        self.page.update()
    
    def _update_breadcrumb(self):
        """Update the breadcrumb navigation"""
        if not hasattr(self, 'breadcrumb_row') or not self.breadcrumb_row:
            return
            
        self.breadcrumb_row.controls.clear()
        
        # Create path parts
        rel_path = os.path.relpath(self.current_directory, self.base_directory)
        if rel_path == ".":
            parts = []
        else:
            parts = rel_path.split(os.sep)
            
        # Add root
        root_item = ft.TextButton(
            text="Raiz",
            icon=ft.Icons.HOME,
            on_click=lambda e: self._navigate_to_directory(self.base_directory),
        )
        self.breadcrumb_row.controls.append(root_item)
        
        # Add separator after root if there are parts
        if parts:
            self.breadcrumb_row.controls.append(
                ft.Text(" / ", color=ft.Colors.GREY_600)
            )
        
        # Add path parts
        current_path = self.base_directory
        for i, part in enumerate(parts):
            current_path = os.path.join(current_path, part)
            
            # Add part button
            part_button = ft.TextButton(
                text=part,
                on_click=lambda e, p=current_path: self._navigate_to_directory(p),
            )
            self.breadcrumb_row.controls.append(part_button)
            
            # Add separator if not the last part
            if i < len(parts) - 1:
                self.breadcrumb_row.controls.append(
                    ft.Text(" / ", color=ft.Colors.GREY_600)
                )
        
        if self.page:
            self.page.update()
    
    def _handle_theme_toggle(self, e):
        """Toggle between light and dark theme"""
        if self.theme_mode == "light":
            self.theme_mode = "dark"
            self.theme_button.icon = ft.Icons.LIGHT_MODE
            self.theme_button.tooltip = "Mudar para tema claro"
            self._apply_theme("dark")
        else:
            self.theme_mode = "light"
            self.theme_button.icon = ft.Icons.DARK_MODE
            self.theme_button.tooltip = "Mudar para tema escuro"
            self._apply_theme("light")
    
    def _apply_theme(self, theme):
        """Apply theme to components"""
        if not self.page:
            return
            
        if theme == "dark":
            # Apply dark theme
            self.main_container.bgcolor = ft.Colors.SURFACE_VARIANT_DARK
            self.output_container.bgcolor = ft.Colors.BLACK
            self.output_text.color = ft.Colors.GREEN
            self.history_container.bgcolor = ft.Colors.SURFACE_VARIANT_DARK
        else:
            # Apply light theme
            self.main_container.bgcolor = ft.Colors.SURFACE_VARIANT
            self.output_container.bgcolor = ft.Colors.BLACK
            self.output_text.color = ft.Colors.GREEN
            self.history_container.bgcolor = ft.Colors.SURFACE_VARIANT
        
        # Update history items with new theme
        self._update_history_display()
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
        self.status_text = ft.Text("Pronto para executar", size=16, color=ft.Colors.BLUE)
        
        # Resource usage text
        self.resource_text = ft.Text("", size=14, color=ft.Colors.GREY_700)
        
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
            icon=ft.Icons.REFRESH,
            tooltip="Atualizar lista de pastas e módulos",
            on_click=self._handle_refresh_button,
            icon_color=ft.Colors.BLUE,
        )
        
        # System info button
        system_info_button = ft.IconButton(
            icon=ft.Icons.INFO_OUTLINE,
            tooltip="Informações do sistema",
            on_click=self._handle_show_system_info,
            icon_color=ft.Colors.BLUE,
        )
        
        # Breadcrumb navigation
        self.breadcrumb_row = ft.Row(
            controls=[
                ft.TextButton(
                    text="Raiz",
                    icon=ft.Icons.HOME,
                    on_click=lambda e: self._navigate_to_directory(self.base_directory),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
        )
        
        # Folder browser
        self.folder_browser = ft.Column(
            controls=[],
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
            expand=True,  # Make it expand to fill available space
        )
        
        # Não atualize o navegador de pastas aqui, será atualizado no did_mount
        
        # Selection rows
        directory_selection_row = ft.Row([
            self.directory_dropdown,
            refresh_button
        ])
        
        # Botão de execução
        self.run_button = ft.ElevatedButton(
            text="Executar Programa",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._handle_run_button,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN,
            ),
        )
        
        # Output text area
        self.output_text = ft.Text(
            value="",
            size=12,
            color=ft.Colors.GREEN,
            selectable=True,
            no_wrap=False,
        )
        
        # Output container
        self.output_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Saída do programa:", weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        icon=ft.Icons.CONTENT_COPY,
                        tooltip="Copiar saída",
                        on_click=self._handle_copy_output,
                        icon_color=ft.Colors.BLUE,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLEAR_ALL,
                        tooltip="Limpar saída",
                        on_click=self._handle_clear_output,
                        icon_color=ft.Colors.RED,
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(
                    content=self.output_text,
                    bgcolor=ft.Colors.BLACK,
                    border_radius=5,
                    padding=10,
                    expand=True,
                    height=200,
                ),
            ]),
            padding=10,
            bgcolor=ft.Colors.BLACK,
            border_radius=5,
            visible=False,
            margin=ft.margin.only(top=10),
        )
        
        # History list
        self.history_list = ft.Column(
            controls=[
                ft.Text("Nenhuma execução registrada", italic=True, color=ft.Colors.GREY_500)
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
        )
        
        # History container
        self.history_container = ft.Container(
            content=ft.Column([
                ft.Text("Histórico de execuções:", weight=ft.FontWeight.BOLD),
                self.history_list,
            ]),
            padding=10,
            bgcolor=ft.Colors.SURFACE_VARIANT,
            border_radius=5,
            margin=ft.margin.only(top=10),
            expand=True,  # Make it expand to fill available space
        )
        
        # Folder browser container
        folder_browser_container = ft.Container(
            content=ft.Column([
                ft.Text("Navegador de arquivos:", weight=ft.FontWeight.BOLD),
                self.breadcrumb_row,
                ft.Container(height=5),
                self.folder_browser,
            ]),
            padding=10,
            bgcolor=ft.Colors.SURFACE_VARIANT,
            border_radius=5,
            margin=ft.margin.only(top=10),
        )
        
        # Main container
        self.main_container = ft.Container(
            content=ft.Column(
                [
                    ft.Row([
                        title,
                        system_info_button,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    description,
                    ft.Container(height=10),
                    folder_browser_container,
                    ft.Container(height=10),
                    directory_selection_row,
                    ft.Container(height=10),
                    self.module_dropdown,
                    ft.Container(height=10),
                    ft.Row([
                        self.status_text,
                        self.resource_text,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(height=10),
                    self.run_button,
                    self.output_container,
                    self.history_container,
                ],
                spacing=5,
                expand=True,  # Make the column expand
            ),
            padding=20,
            border_radius=10,
            bgcolor=ft.Colors.SURFACE_VARIANT,
            expand=True,  # Make the container expand
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                offset=ft.Offset(0, 2),
            ),
        )
        
        # Update the return statement to make the column expand
        return ft.Column(
            [
                self.main_container
            ],
            expand=True,  # Make the outer column expand
        )
    
    def did_mount(self, page):
        """Chamado quando o módulo é montado na página"""
        self.page = page
        # Agora que a página está disponível, atualize o navegador de pastas
        self._update_folder_browser()
    
    def will_unmount(self):
        """Chamado quando o módulo é desmontado da página"""
        if self.is_running and self.process:
            try:
                self.process.terminate()
                self.should_monitor = False
            except:
                pass


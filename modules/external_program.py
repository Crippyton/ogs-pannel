import flet as ft
import subprocess
import os
import threading

class Module:
    def __init__(self):
        self.page = None
        self.process = None
        self.is_running = False
        
    def get_module_info(self):
        return {
            "name": "Programa Externo",
            "description": "Executa o programa externo enviado",
            "version": "1.0.0",
            "icon": ft.icons.PLAY_CIRCLE_OUTLINED,
            "color": ft.colors.PURPLE,
        }
    
    def _run_program(self):
        try:
            # Caminho para o arquivo Python que foi enviado
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main-4iNxk42ZPyHPY4N4tvkHUpN76v5uXm.py")
            
            if not os.path.exists(script_path):
                if self.page:
                    self.status_text.value = "Erro: Arquivo não encontrado"
                    self.status_text.color = ft.colors.RED
                    self.page.update()
                return
            
            # Executa o programa em um processo separado
            self.process = subprocess.Popen(["python", script_path], 
                                           stdout=subprocess.PIPE, 
                                           stderr=subprocess.PIPE)
            
            self.is_running = True
            if self.page:
                self.status_text.value = "Programa em execução..."
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
    
    def get_view(self):
        # Título
        title = ft.Text("Executar Programa Externo", size=24, weight=ft.FontWeight.BOLD)
        
        # Descrição
        description = ft.Text(
            "Este módulo permite executar o programa externo que foi enviado. "
            "Clique no botão abaixo para iniciar ou parar a execução.",
            size=16,
        )
        
        # Status
        self.status_text = ft.Text("Pronto para executar", size=16, color=ft.colors.BLUE)
        
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
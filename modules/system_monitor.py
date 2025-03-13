import flet as ft
import psutil
import platform
import datetime
import threading
import time

class Module:
    def __init__(self):
        self.update_interval = 2  # segundos
        self.stop_thread = False
        self.update_thread = None
        self.cpu_usage = 0
        self.memory_usage = 0
        self.disk_usage = 0
        self.network_sent = 0
        self.network_recv = 0
        self.prev_net_io = psutil.net_io_counters()
        self.last_update = datetime.datetime.now()
        self.page = None
        
    def get_module_info(self):
        return {
            "name": "Monitor do Sistema",
            "description": "Monitora recursos do sistema como CPU, memória e disco",
            "version": "1.0.0",
            "icon": ft.icons.MONITOR_OUTLINED,
            "color": ft.colors.BLUE,
        }
    
    def _update_stats(self):
        while not self.stop_thread:
            try:
                # CPU
                self.cpu_usage = psutil.cpu_percent(interval=0.5)
                
                # Memória
                memory = psutil.virtual_memory()
                self.memory_usage = memory.percent
                
                # Disco
                disk = psutil.disk_usage('/')
                self.disk_usage = disk.percent
                
                # Rede
                current_net_io = psutil.net_io_counters()
                time_diff = (datetime.datetime.now() - self.last_update).total_seconds()
                
                self.network_sent = (current_net_io.bytes_sent - self.prev_net_io.bytes_sent) / time_diff
                self.network_recv = (current_net_io.bytes_recv - self.prev_net_io.bytes_recv) / time_diff
                
                self.prev_net_io = current_net_io
                self.last_update = datetime.datetime.now()
                
                # Atualiza a interface
                if hasattr(self, 'page') and self.page:
                    self.cpu_text.value = f"{self.cpu_usage:.1f}%"
                    self.cpu_progress.value = self.cpu_usage / 100
                    
                    self.memory_text.value = f"{self.memory_usage:.1f}%"
                    self.memory_progress.value = self.memory_usage / 100
                    
                    self.disk_text.value = f"{self.disk_usage:.1f}%"
                    self.disk_progress.value = self.disk_usage / 100
                    
                    self.network_sent_text.value = f"{self._format_bytes(self.network_sent)}/s"
                    self.network_recv_text.value = f"{self._format_bytes(self.network_recv)}/s"
                    
                    self.page.update()
            except Exception as e:
                print(f"Erro ao atualizar estatísticas: {e}")
            
            time.sleep(self.update_interval)
    
    def _format_bytes(self, bytes):
        """Formata bytes para uma representação legível"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} PB"
    
    def _start_monitoring(self):
        """Inicia o monitoramento em uma thread separada"""
        if self.update_thread is None or not self.update_thread.is_alive():
            self.stop_thread = False
            self.update_thread = threading.Thread(target=self._update_stats)
            self.update_thread.daemon = True
            self.update_thread.start()
    
    def _stop_monitoring(self):
        """Para o monitoramento"""
        self.stop_thread = True
        if self.update_thread:
            self.update_thread.join(timeout=1)
    
    def get_view(self):
        # Informações do sistema
        system_info = {
            "Sistema": platform.system(),
            "Versão": platform.version(),
            "Processador": platform.processor(),
            "Arquitetura": platform.machine(),
            "Hostname": platform.node(),
            "Python": platform.python_version(),
        }
        
        # Cria os controles para exibir as informações
        system_info_controls = []
        for key, value in system_info.items():
            system_info_controls.append(
                ft.Row([
                    ft.Text(f"{key}:", weight=ft.FontWeight.BOLD),
                    ft.Text(value),
                ])
            )
        
        # Cria os controles para monitoramento em tempo real
        self.cpu_text = ft.Text("0%", size=18, weight=ft.FontWeight.BOLD)
        self.cpu_progress = ft.ProgressBar(width=200, value=0)
        
        self.memory_text = ft.Text("0%", size=18, weight=ft.FontWeight.BOLD)
        self.memory_progress = ft.ProgressBar(width=200, value=0)
        
        self.disk_text = ft.Text("0%", size=18, weight=ft.FontWeight.BOLD)
        self.disk_progress = ft.ProgressBar(width=200, value=0)
        
        self.network_sent_text = ft.Text("0 B/s", size=18, weight=ft.FontWeight.BOLD)
        self.network_recv_text = ft.Text("0 B/s", size=18, weight=ft.FontWeight.BOLD)
        
        # Conteúdo principal
        content_column = ft.Column(
            [
                ft.Text("Monitor do Sistema", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                # Informações do sistema
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Informações do Sistema", size=18, weight=ft.FontWeight.BOLD),
                            *system_info_controls,
                        ],
                        spacing=10,
                    ),
                    padding=20,
                    border_radius=10,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                ),
                
                ft.Container(height=20),
                
                # Monitoramento em tempo real
                ft.Text("Monitoramento em Tempo Real", size=18, weight=ft.FontWeight.BOLD),
                
                # CPU
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.MEMORY, color=ft.colors.BLUE),
                                    ft.Text("CPU:", size=16),
                                    self.cpu_text,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            self.cpu_progress,
                        ],
                    ),
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                ),
                
                ft.Container(height=10),
                
                # Memória
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.STORAGE, color=ft.colors.GREEN),
                                    ft.Text("Memória:", size=16),
                                    self.memory_text,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            self.memory_progress,
                        ],
                    ),
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                ),
                
                ft.Container(height=10),
                
                # Disco
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.DISC_FULL, color=ft.colors.AMBER),
                                    ft.Text("Disco:", size=16),
                                    self.disk_text,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            self.disk_progress,
                        ],
                    ),
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                ),
                
                ft.Container(height=10),
                
                # Rede
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.UPLOAD, color=ft.colors.RED),
                                    ft.Text("Upload:", size=16),
                                    self.network_sent_text,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.DOWNLOAD, color=ft.colors.INDIGO),
                                    ft.Text("Download:", size=16),
                                    self.network_recv_text,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        ],
                    ),
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                ),
            ],
            spacing=10,
        )
        
        # Retorna um ScrollableControl para permitir rolagem
        return ft.Column(
            [
                ft.Container(
                    content=content_column,
                    padding=20,
                    expand=True,
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
    
    def did_mount(self, page):
        """Chamado quando o módulo é montado na página"""
        self.page = page
        self._start_monitoring()
    
    def will_unmount(self):
        """Chamado quando o módulo é desmontado da página"""
        self._stop_monitoring()
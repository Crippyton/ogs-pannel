import flet as ft
import platform
import psutil
import time
import threading

class Module:
    def get_module_info(self):
        return {
            "name": "Monitor",
            "description": "Monitore recursos do sistema",
            "version": "1.0.0",
            "icon": ft.icons.MONITOR_HEART,
            "color": ft.colors.ORANGE,
        }
        
    def get_view(self):
        self.page = None
        self.update_thread = None
        self.running = False
        
        # Informações do sistema
        system_info = self._get_system_info()
        
        # Gráficos de uso
        self.cpu_progress = ft.ProgressBar(width=400, value=0)
        self.cpu_text = ft.Text("CPU: 0%")
        
        self.memory_progress = ft.ProgressBar(width=400, value=0)
        self.memory_text = ft.Text("Memória: 0%")
        
        self.disk_progress = ft.ProgressBar(width=400, value=0)
        self.disk_text = ft.Text("Disco: 0%")
        
        # Botão para iniciar/parar monitoramento
        self.monitor_button = ft.ElevatedButton(
            "Iniciar Monitoramento",
            icon=ft.icons.PLAY_ARROW,
            on_click=self._toggle_monitoring,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )
        
        # Informações detalhadas
        self.details_text = ft.Text("", selectable=True)
        
        return ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Monitor do Sistema", size=24, weight=ft.FontWeight.BOLD),
                            ft.Container(height=20),
                            ft.Text("Informações do Sistema", size=18, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text(f"Sistema Operacional: {system_info['os']}"),
                                        ft.Text(f"Versão: {system_info['version']}"),
                                        ft.Text(f"Máquina: {system_info['machine']}"),
                                        ft.Text(f"Processador: {system_info['processor']}"),
                                        ft.Text(f"Núcleos: {system_info['cores']}"),
                                    ],
                                    spacing=5,
                                ),
                                padding=10,
                                border=ft.border.all(1, ft.colors.OUTLINE),
                                border_radius=8,
                            ),
                            ft.Container(height=20),
                            ft.Text("Uso de Recursos", size=18, weight=ft.FontWeight.BOLD),
                            ft.Container(height=10),
                            ft.Row([self.cpu_text]),
                            self.cpu_progress,
                            ft.Container(height=10),
                            ft.Row([self.memory_text]),
                            self.memory_progress,
                            ft.Container(height=10),
                            ft.Row([self.disk_text]),
                            self.disk_progress,
                            ft.Container(height=20),
                            self.monitor_button,
                            ft.Container(height=20),
                            ft.Text("Detalhes", size=18, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=self.details_text,
                                padding=10,
                                border=ft.border.all(1, ft.colors.OUTLINE),
                                border_radius=8,
                                height=200,
                                scroll=ft.ScrollMode.ALWAYS,
                            ),
                        ],
                    ),
                    padding=20,
                    expand=True,
                )
            ],
            expand=True,
        )
        
    def _get_system_info(self):
        return {
            "os": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cores": psutil.cpu_count(logical=True),
        }
        
    def _toggle_monitoring(self, e):
        self.page = e.page
        
        if not self.running:
            # Inicia o monitoramento
            self.running = True
            self.monitor_button.text = "Parar Monitoramento"
            self.monitor_button.icon = ft.icons.STOP
            
            # Inicia a thread de atualização
            self.update_thread = threading.Thread(target=self._update_stats)
            self.update_thread.daemon = True
            self.update_thread.start()
        else:
            # Para o monitoramento
            self.running = False
            self.monitor_button.text = "Iniciar Monitoramento"
            self.monitor_button.icon = ft.icons.PLAY_ARROW
            
        self.page.update()
        
    def _update_stats(self):
        while self.running:
            try:
                # CPU
                cpu_percent = psutil.cpu_percent()
                self.cpu_progress.value = cpu_percent / 100
                self.cpu_text.value = f"CPU: {cpu_percent:.1f}%"
                
                # Memória
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                self.memory_progress.value = memory_percent / 100
                self.memory_text.value = f"Memória: {memory_percent:.1f}% (Usado: {self._format_bytes(memory.used)} / Total: {self._format_bytes(memory.total)})"
                
                # Disco
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent
                self.disk_progress.value = disk_percent / 100
                self.disk_text.value = f"Disco: {disk_percent:.1f}% (Usado: {self._format_bytes(disk.used)} / Total: {self._format_bytes(disk.total)})"
                
                # Detalhes
                details = []
                details.append(f"Tempo de atividade: {self._format_uptime(psutil.boot_time())}")
                
                # Processos
                processes = []
                for proc in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent']), key=lambda p: p.info['cpu_percent'], reverse=True)[:5]:
                    try:
                        processes.append(f"PID: {proc.info['pid']}, Nome: {proc.info['name']}, CPU: {proc.info['cpu_percent']:.1f}%")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                details.append("\nProcessos com maior uso de CPU:")
                details.extend(processes)
                
                self.details_text.value = "\n".join(details)
                
                # Atualiza a UI
                if self.page:
                    self.page.update()
                    
                time.sleep(2)  # Atualiza a cada 2 segundos
                
            except Exception as e:
                print(f"Erro ao atualizar estatísticas: {e}")
                break
                
    def _format_bytes(self, bytes):
        """Formata bytes para uma representação legível"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} PB"
        
    def _format_uptime(self, boot_time):
        """Formata o tempo de atividade do sistema"""
        uptime_seconds = time.time() - boot_time
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        if days > 0:
            return f"{days} dias, {hours} horas, {minutes} minutos"
        elif hours > 0:
            return f"{hours} horas, {minutes} minutos"
        else:
            return f"{minutes} minutos"
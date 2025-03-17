import flet as ft
import psutil
import platform
import datetime
import threading
import time
import os
import socket
import json
from typing import Dict, List, Any

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
        self.cpu_history = []
        self.memory_history = []
        self.disk_history = []
        self.max_history_points = 60  # 2 minutos de histórico com intervalo de 2 segundos
        self.processes = []
        self.show_processes = True
        self.sort_by = "cpu"  # Ordenar processos por CPU por padrão
        self.sort_reverse = True  # Ordem decrescente por padrão
        self.max_processes = 10  # Número máximo de processos a exibir
        self.chart_height = 200
        self.chart_width = 600
        self.theme_mode = "light"
        self.history_data = {
            "cpu": [],
            "memory": [],
            "disk": [],
            "network_sent": [],
            "network_recv": []
        }
        self.alert_thresholds = {
            "cpu": 80,
            "memory": 80,
            "disk": 90
        }
        self.alerts_enabled = True
        self.last_alert_time = {}
        self.alert_cooldown = 60  # segundos entre alertas do mesmo tipo
        
    def get_module_info(self):
        return {
            "name": "Monitor do Sistema",
            "description": "Monitora recursos do sistema como CPU, memória e disco",
            "version": "2.0.0",
            "icon": ft.icons.MONITOR_OUTLINED,
            "color": ft.colors.BLUE,
        }
    
    def _update_stats(self):
        while not self.stop_thread:
            try:
                # CPU
                self.cpu_usage = psutil.cpu_percent(interval=0.5)
                cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
                
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
                
                # Atualiza histórico
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                
                self.history_data["cpu"].append({"time": timestamp, "value": self.cpu_usage})
                self.history_data["memory"].append({"time": timestamp, "value": self.memory_usage})
                self.history_data["disk"].append({"time": timestamp, "value": self.disk_usage})
                self.history_data["network_sent"].append({"time": timestamp, "value": self.network_sent})
                self.history_data["network_recv"].append({"time": timestamp, "value": self.network_recv})
                
                # Limita o tamanho do histórico
                for key in self.history_data:
                    if len(self.history_data[key]) > self.max_history_points:
                        self.history_data[key] = self.history_data[key][-self.max_history_points:]
                
                # Atualiza lista de processos
                if self.show_processes:
                    self.processes = []
                    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time', 'status']):
                        try:
                            pinfo = proc.info
                            pinfo['cpu_percent'] = proc.cpu_percent(interval=0.1)
                            self.processes.append(pinfo)
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            pass
                    
                    # Ordena processos
                    if self.sort_by == "cpu":
                        self.processes.sort(key=lambda x: x['cpu_percent'], reverse=self.sort_reverse)
                    elif self.sort_by == "memory":
                        self.processes.sort(key=lambda x: x['memory_percent'], reverse=self.sort_reverse)
                    elif self.sort_by == "pid":
                        self.processes.sort(key=lambda x: x['pid'], reverse=self.sort_reverse)
                    elif self.sort_by == "name":
                        self.processes.sort(key=lambda x: x['name'].lower(), reverse=self.sort_reverse)
                    
                    # Limita o número de processos
                    self.processes = self.processes[:self.max_processes]
                
                # Verifica alertas
                if self.alerts_enabled:
                    self._check_alerts()
                
                # Atualiza a interface
                if hasattr(self, 'page') and self.page:
                    self._update_ui()
            except Exception as e:
                print(f"Erro ao atualizar estatísticas: {e}")
            
            time.sleep(self.update_interval)
    
    def _check_alerts(self):
        """Verifica se algum recurso ultrapassou o limite e exibe alertas"""
        current_time = time.time()
        
        # Verifica CPU
        if self.cpu_usage > self.alert_thresholds["cpu"]:
            if "cpu" not in self.last_alert_time or (current_time - self.last_alert_time["cpu"]) > self.alert_cooldown:
                self.last_alert_time["cpu"] = current_time
                if self.page:
                    self.page.show_snack_bar(
                        ft.SnackBar(
                            content=ft.Text(f"Alerta: Uso de CPU acima de {self.alert_thresholds['cpu']}% (Atual: {self.cpu_usage:.1f}%)"),
                            bgcolor=ft.colors.RED_700,
                            action="OK",
                        )
                    )
        
        # Verifica Memória
        if self.memory_usage > self.alert_thresholds["memory"]:
            if "memory" not in self.last_alert_time or (current_time - self.last_alert_time["memory"]) > self.alert_cooldown:
                self.last_alert_time["memory"] = current_time
                if self.page:
                    self.page.show_snack_bar(
                        ft.SnackBar(
                            content=ft.Text(f"Alerta: Uso de Memória acima de {self.alert_thresholds['memory']}% (Atual: {self.memory_usage:.1f}%)"),
                            bgcolor=ft.colors.RED_700,
                            action="OK",
                        )
                    )
        
        # Verifica Disco
        if self.disk_usage > self.alert_thresholds["disk"]:
            if "disk" not in self.last_alert_time or (current_time - self.last_alert_time["disk"]) > self.alert_cooldown:
                self.last_alert_time["disk"] = current_time
                if self.page:
                    self.page.show_snack_bar(
                        ft.SnackBar(
                            content=ft.Text(f"Alerta: Uso de Disco acima de {self.alert_thresholds['disk']}% (Atual: {self.disk_usage:.1f}%)"),
                            bgcolor=ft.colors.RED_700,
                            action="OK",
                        )
                    )
    
    def _update_ui(self):
        """Atualiza todos os elementos da interface"""
        # Atualiza indicadores principais
        self.cpu_text.value = f"{self.cpu_usage:.1f}%"
        self.cpu_progress.value = self.cpu_usage / 100
        self.cpu_progress.color = self._get_status_color(self.cpu_usage, self.alert_thresholds["cpu"])
        
        self.memory_text.value = f"{self.memory_usage:.1f}%"
        self.memory_progress.value = self.memory_usage / 100
        self.memory_progress.color = self._get_status_color(self.memory_usage, self.alert_thresholds["memory"])
        
        self.disk_text.value = f"{self.disk_usage:.1f}%"
        self.disk_progress.value = self.disk_usage / 100
        self.disk_progress.color = self._get_status_color(self.disk_usage, self.alert_thresholds["disk"])
        
        self.network_sent_text.value = f"{self._format_bytes(self.network_sent)}/s"
        self.network_recv_text.value = f"{self._format_bytes(self.network_recv)}/s"
        
        # Atualiza gráficos
        self._update_charts()
        
        # Atualiza lista de processos
        if self.show_processes and hasattr(self, 'process_list'):
            self._update_process_list()
        
        # Atualiza a página
        self.page.update()
    
    def _update_charts(self):
        """Atualiza os gráficos com os dados históricos"""
        if hasattr(self, 'cpu_chart'):
            # Prepara dados para o gráfico de CPU
            cpu_data = [{"x": i, "y": point["value"]} for i, point in enumerate(self.history_data["cpu"][-30:])]
            self.cpu_chart.data = cpu_data
            
            # Prepara dados para o gráfico de memória
            memory_data = [{"x": i, "y": point["value"]} for i, point in enumerate(self.history_data["memory"][-30:])]
            self.memory_chart.data = memory_data
            
            # Prepara dados para o gráfico de rede
            network_sent_data = [{"x": i, "y": min(point["value"] / 1024 / 1024, 100)} for i, point in enumerate(self.history_data["network_sent"][-30:])]
            network_recv_data = [{"x": i, "y": min(point["value"] / 1024 / 1024, 100)} for i, point in enumerate(self.history_data["network_recv"][-30:])]
            
            self.network_chart.data_series = [
                ft.LineChartData(
                    data_points=[ft.LineChartDataPoint(x=p["x"], y=p["y"]) for p in network_sent_data],
                    stroke_width=2,
                    color=ft.colors.RED,
                    curved=True,
                    stroke_cap_round=True,
                ),
                ft.LineChartData(
                    data_points=[ft.LineChartDataPoint(x=p["x"], y=p["y"]) for p in network_recv_data],
                    stroke_width=2,
                    color=ft.colors.BLUE,
                    curved=True,
                    stroke_cap_round=True,
                ),
            ]
    
    def _update_process_list(self):
        """Atualiza a lista de processos"""
        self.process_list.controls.clear()
        
        # Adiciona cabeçalho
        header = ft.Row(
            [
                ft.Container(
                    content=ft.Text("PID", weight=ft.FontWeight.BOLD),
                    width=60,
                    on_click=lambda _: self._sort_processes("pid"),
                ),
                ft.Container(
                    content=ft.Text("Nome", weight=ft.FontWeight.BOLD),
                    expand=1,
                    on_click=lambda _: self._sort_processes("name"),
                ),
                ft.Container(
                    content=ft.Text("CPU %", weight=ft.FontWeight.BOLD),
                    width=80,
                    on_click=lambda _: self._sort_processes("cpu"),
                ),
                ft.Container(
                    content=ft.Text("Memória %", weight=ft.FontWeight.BOLD),
                    width=100,
                    on_click=lambda _: self._sort_processes("memory"),
                ),
                ft.Container(
                    content=ft.Text("Status", weight=ft.FontWeight.BOLD),
                    width=80,
                ),
                ft.Container(
                    content=ft.Text("Ações", weight=ft.FontWeight.BOLD),
                    width=80,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        self.process_list.controls.append(header)
        
        # Adiciona separador
        self.process_list.controls.append(ft.Divider(height=1))
        
        # Adiciona processos
        for proc in self.processes:
            # Define cores baseadas no uso de recursos
            cpu_color = self._get_status_color(proc['cpu_percent'], 50)
            memory_color = self._get_status_color(proc['memory_percent'], 50)
            
            # Define cor do status
            status_color = ft.colors.GREEN if proc['status'] == 'running' else ft.colors.ORANGE
            
            # Cria linha do processo
            process_row = ft.Row(
                [
                    ft.Container(
                        content=ft.Text(str(proc['pid'])),
                        width=60,
                    ),
                    ft.Container(
                        content=ft.Text(proc['name'], overflow=ft.TextOverflow.ELLIPSIS),
                        expand=1,
                        tooltip=proc['name'],
                    ),
                    ft.Container(
                        content=ft.Text(f"{proc['cpu_percent']:.1f}%", color=cpu_color),
                        width=80,
                    ),
                    ft.Container(
                        content=ft.Text(f"{proc['memory_percent']:.1f}%", color=memory_color),
                        width=100,
                    ),
                    ft.Container(
                        content=ft.Text(proc['status'], color=status_color),
                        width=80,
                    ),
                    ft.Container(
                        content=ft.IconButton(
                            icon=ft.icons.CLOSE,
                            icon_color=ft.colors.RED,
                            icon_size=18,
                            tooltip="Encerrar processo",
                            on_click=lambda e, pid=proc['pid']: self._terminate_process(pid),
                        ),
                        width=80,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
            self.process_list.controls.append(process_row)
    
    def _sort_processes(self, sort_key):
        """Altera a ordenação dos processos"""
        if self.sort_by == sort_key:
            # Inverte a ordem se já estiver ordenando por esta coluna
            self.sort_reverse = not self.sort_reverse
        else:
            # Define nova coluna de ordenação
            self.sort_by = sort_key
            # Define ordem padrão para cada tipo de coluna
            if sort_key in ["cpu", "memory"]:
                self.sort_reverse = True  # Decrescente para recursos
            else:
                self.sort_reverse = False  # Crescente para PID e nome
    
    def _terminate_process(self, pid):
        """Tenta encerrar um processo pelo PID"""
        try:
            process = psutil.Process(pid)
            process.terminate()
            
            # Exibe mensagem de sucesso
            if self.page:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"Processo {pid} encerrado com sucesso"),
                        bgcolor=ft.colors.GREEN,
                        action="OK",
                    )
                )
        except Exception as e:
            # Exibe mensagem de erro
            if self.page:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"Erro ao encerrar processo {pid}: {str(e)}"),
                        bgcolor=ft.colors.RED,
                        action="OK",
                    )
                )
    
    def _get_status_color(self, value, threshold):
        """Retorna uma cor baseada no valor em relação ao limite"""
        if value < threshold * 0.5:
            return ft.colors.GREEN
        elif value < threshold * 0.8:
            return ft.colors.AMBER
        else:
            return ft.colors.RED
    
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
    
    def _toggle_processes(self, e):
        """Alterna a exibição da lista de processos"""
        self.show_processes = not self.show_processes
        self.processes_container.visible = self.show_processes
        self.toggle_processes_button.icon = ft.icons.VISIBILITY_OFF if self.show_processes else ft.icons.VISIBILITY
        self.toggle_processes_button.tooltip = "Ocultar processos" if self.show_processes else "Mostrar processos"
        if self.page:
            self.page.update()
    
    def _toggle_alerts(self, e):
        """Alterna a ativação de alertas"""
        self.alerts_enabled = not self.alerts_enabled
        self.toggle_alerts_button.icon = ft.icons.NOTIFICATIONS_OFF if not self.alerts_enabled else ft.icons.NOTIFICATIONS_ACTIVE
        self.toggle_alerts_button.tooltip = "Ativar alertas" if not self.alerts_enabled else "Desativar alertas"
        
        # Exibe mensagem
        if self.page:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"Alertas {'desativados' if not self.alerts_enabled else 'ativados'}"),
                    bgcolor=ft.colors.BLUE,
                    action="OK",
                )
            )
            self.page.update()
    
    def _export_data(self, e):
        """Exporta os dados de monitoramento para um arquivo JSON"""
        try:
            # Cria diretório de exportação se não existir
            export_dir = os.path.join(os.path.dirname(__file__), "exports")
            os.makedirs(export_dir, exist_ok=True)
            
            # Cria nome de arquivo com timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(export_dir, f"system_monitor_export_{timestamp}.json")
            
            # Prepara dados para exportação
            export_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "system_info": {
                    "system": platform.system(),
                    "version": platform.version(),
                    "processor": platform.processor(),
                    "architecture": platform.machine(),
                    "hostname": platform.node(),
                    "python": platform.python_version(),
                },
                "current_stats": {
                    "cpu_usage": self.cpu_usage,
                    "memory_usage": self.memory_usage,
                    "disk_usage": self.disk_usage,
                    "network_sent": self.network_sent,
                    "network_recv": self.network_recv,
                },
                "history_data": self.history_data,
                "processes": self.processes,
            }
            
            # Salva arquivo
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            # Exibe mensagem de sucesso
            if self.page:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"Dados exportados para {filename}"),
                        bgcolor=ft.colors.GREEN,
                        action="OK",
                    )
                )
        except Exception as e:
            # Exibe mensagem de erro
            if self.page:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"Erro ao exportar dados: {str(e)}"),
                        bgcolor=ft.colors.RED,
                        action="OK",
                    )
                )
    
    def _show_settings_dialog(self, e):
        """Exibe diálogo de configurações"""
        # Campos para limites de alerta
        cpu_threshold_slider = ft.Slider(
            min=50,
            max=100,
            divisions=10,
            value=self.alert_thresholds["cpu"],
            label="{value}%",
        )
        
        memory_threshold_slider = ft.Slider(
            min=50,
            max=100,
            divisions=10,
            value=self.alert_thresholds["memory"],
            label="{value}%",
        )
        
        disk_threshold_slider = ft.Slider(
            min=50,
            max=100,
            divisions=10,
            value=self.alert_thresholds["disk"],
            label="{value}%",
        )
        
        # Campo para intervalo de atualização
        update_interval_slider = ft.Slider(
            min=1,
            max=10,
            divisions=9,
            value=self.update_interval,
            label="{value}s",
        )
        
        # Campo para número máximo de processos
        max_processes_slider = ft.Slider(
            min=5,
            max=50,
            divisions=9,
            value=self.max_processes,
            label="{value}",
        )
        
        # Função para salvar configurações
        def save_settings(e):
            self.alert_thresholds["cpu"] = cpu_threshold_slider.value
            self.alert_thresholds["memory"] = memory_threshold_slider.value
            self.alert_thresholds["disk"] = disk_threshold_slider.value
            self.update_interval = update_interval_slider.value
            self.max_processes = int(max_processes_slider.value)
            
            # Fecha o diálogo
            settings_dialog.open = False
            self.page.update()
            
            # Exibe mensagem de sucesso
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("Configurações salvas com sucesso"),
                    bgcolor=ft.colors.GREEN,
                    action="OK",
                )
            )
        
        # Cria diálogo
        settings_dialog = ft.AlertDialog(
            title=ft.Text("Configurações"),
            content=ft.Column(
                [
                    ft.Text("Limites de Alerta", weight=ft.FontWeight.BOLD),
                    ft.Text("CPU:"),
                    cpu_threshold_slider,
                    ft.Text("Memória:"),
                    memory_threshold_slider,
                    ft.Text("Disco:"),
                    disk_threshold_slider,
                    ft.Divider(),
                    ft.Text("Intervalo de Atualização (segundos):"),
                    update_interval_slider,
                    ft.Text("Número máximo de processos:"),
                    max_processes_slider,
                ],
                scroll=ft.ScrollMode.AUTO,
                height=400,
                width=400,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(settings_dialog, "open", False)),
                ft.TextButton("Salvar", on_click=save_settings),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        self.page.dialog = settings_dialog
        settings_dialog.open = True
        self.page.update()
    
    def get_view(self):
        # Informações do sistema
        system_info = {
            "Sistema": platform.system(),
            "Versão": platform.version(),
            "Processador": platform.processor(),
            "Arquitetura": platform.machine(),
            "Hostname": platform.node(),
            "Python": platform.python_version(),
            "IP Local": socket.gethostbyname(socket.gethostname()),
        }
        
        # Cria os controles para exibir as informações
        system_info_controls = []
        for key, value in system_info.items():
            system_info_controls.append(
                ft.Row([
                    ft.Text(f"{key}:", weight=ft.FontWeight.BOLD),
                    ft.Text(value, selectable=True),
                ])
            )
        
        # Cria os controles para monitoramento em tempo real
        self.cpu_text = ft.Text("0%", size=18, weight=ft.FontWeight.BOLD)
        self.cpu_progress = ft.ProgressBar(width=200, value=0, color=ft.colors.GREEN)
        
        self.memory_text = ft.Text("0%", size=18, weight=ft.FontWeight.BOLD)
        self.memory_progress = ft.ProgressBar(width=200, value=0, color=ft.colors.GREEN)
        
        self.disk_text = ft.Text("0%", size=18, weight=ft.FontWeight.BOLD)
        self.disk_progress = ft.ProgressBar(width=200, value=0, color=ft.colors.GREEN)
        
        self.network_sent_text = ft.Text("0 B/s", size=18, weight=ft.FontWeight.BOLD)
        self.network_recv_text = ft.Text("0 B/s", size=18, weight=ft.FontWeight.BOLD)
        
        # Cria gráficos
        self.cpu_chart = ft.LineChart(
            data_series=[
                ft.LineChartData(
                    data_points=[],
                    stroke_width=2,
                    color=ft.colors.BLUE,
                    curved=True,
                    stroke_cap_round=True,
                ),
            ],
            border=ft.border.all(1, ft.colors.GREY_400),
            horizontal_grid_lines=ft.ChartGridLines(interval=10, color=ft.colors.GREY_300, width=1),
            vertical_grid_lines=ft.ChartGridLines(interval=5, color=ft.colors.GREY_300, width=1),
            tooltip_bgcolor=ft.colors.with_opacity(0.8, ft.colors.GREY_800),
            left_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(value=0, label=ft.Text("0%")),
                    ft.ChartAxisLabel(value=50, label=ft.Text("50%")),
                    ft.ChartAxisLabel(value=100, label=ft.Text("100%")),
                ],
                labels_size=40,
            ),
            bottom_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(value=0, label=ft.Text("0")),
                    ft.ChartAxisLabel(value=15, label=ft.Text("15s")),
                    ft.ChartAxisLabel(value=30, label=ft.Text("30s")),
                ],
                labels_size=40,
            ),
            expand=True,
            min_y=0,
            max_y=100,
            min_x=0,
            max_x=30,
            height=200,
        )
        
        self.memory_chart = ft.LineChart(
            data_series=[
                ft.LineChartData(
                    data_points=[],
                    stroke_width=2,
                    color=ft.colors.GREEN,
                    curved=True,
                    stroke_cap_round=True,
                ),
            ],
            border=ft.border.all(1, ft.colors.GREY_400),
            horizontal_grid_lines=ft.ChartGridLines(interval=10, color=ft.colors.GREY_300, width=1),
            vertical_grid_lines=ft.ChartGridLines(interval=5, color=ft.colors.GREY_300, width=1),
            tooltip_bgcolor=ft.colors.with_opacity(0.8, ft.colors.GREY_800),
            left_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(value=0, label=ft.Text("0%")),
                    ft.ChartAxisLabel(value=50, label=ft.Text("50%")),
                    ft.ChartAxisLabel(value=100, label=ft.Text("100%")),
                ],
                labels_size=40,
            ),
            bottom_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(value=0, label=ft.Text("0")),
                    ft.ChartAxisLabel(value=15, label=ft.Text("15s")),
                    ft.ChartAxisLabel(value=30, label=ft.Text("30s")),
                ],
                labels_size=40,
            ),
            expand=True,
            min_y=0,
            max_y=100,
            min_x=0,
            max_x=30,
            height=200,
        )
        
        self.network_chart = ft.LineChart(
            data_series=[
                ft.LineChartData(
                    data_points=[],
                    stroke_width=2,
                    color=ft.colors.RED,
                    curved=True,
                    stroke_cap_round=True,
                ),
                ft.LineChartData(
                    data_points=[],
                    stroke_width=2,
                    color=ft.colors.BLUE,
                    curved=True,
                    stroke_cap_round=True,
                ),
            ],
            border=ft.border.all(1, ft.colors.GREY_400),
            horizontal_grid_lines=ft.ChartGridLines(interval=10, color=ft.colors.GREY_300, width=1),
            vertical_grid_lines=ft.ChartGridLines(interval=5, color=ft.colors.GREY_300, width=1),
            tooltip_bgcolor=ft.colors.with_opacity(0.8, ft.colors.GREY_800),
            left_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(value=0, label=ft.Text("0 MB/s")),
                    ft.ChartAxisLabel(value=50, label=ft.Text("50 MB/s")),
                    ft.ChartAxisLabel(value=100, label=ft.Text("100 MB/s")),
                ],
                labels_size=60,
            ),
            bottom_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(value=0, label=ft.Text("0")),
                    ft.ChartAxisLabel(value=15, label=ft.Text("15s")),
                    ft.ChartAxisLabel(value=30, label=ft.Text("30s")),
                ],
                labels_size=40,
            ),
            expand=True,
            min_y=0,
            max_y=100,
            min_x=0,
            max_x=30,
            height=200,
        )
        
        # Lista de processos
        self.process_list = ft.Column(
            controls=[
                ft.Text("Carregando processos...", italic=True),
            ],
            spacing=5,
            scroll=ft.ScrollMode.AUTO,
            height=300,
        )
        
        # Container para lista de processos
        self.processes_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Processos em Execução", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.IconButton(
                            icon=ft.icons.REFRESH,
                            tooltip="Atualizar lista",
                            on_click=lambda e: self._update_process_list(),
                        ),
                    ]),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.process_list,
            ]),
            padding=10,
            border_radius=10,
            bgcolor=ft.colors.SURFACE_VARIANT,
            visible=self.show_processes,
        )
        
        # Botões de ação
        self.toggle_processes_button = ft.IconButton(
            icon=ft.icons.VISIBILITY_OFF if self.show_processes else ft.icons.VISIBILITY,
            tooltip="Ocultar processos" if self.show_processes else "Mostrar processos",
            on_click=self._toggle_processes,
        )
        
        self.toggle_alerts_button = ft.IconButton(
            icon=ft.icons.NOTIFICATIONS_ACTIVE,
            tooltip="Desativar alertas",
            on_click=self._toggle_alerts,
        )
        
        export_button = ft.IconButton(
            icon=ft.icons.DOWNLOAD,
            tooltip="Exportar dados",
            on_click=self._export_data,
        )
        
        settings_button = ft.IconButton(
            icon=ft.icons.SETTINGS,
            tooltip="Configurações",
            on_click=self._show_settings_dialog,
        )
        
        # Conteúdo principal
        content_column = ft.Column(
            [
                # Cabeçalho com título e botões
                ft.Row(
                    [
                        ft.Text("Monitor do Sistema", size=24, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            [
                                self.toggle_processes_button,
                                self.toggle_alerts_button,
                                export_button,
                                settings_button,
                            ],
                            spacing=5,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
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
                
                ft.Container(height=20),
                
                # Gráficos
                ft.Text("Gráficos de Desempenho", size=18, weight=ft.FontWeight.BOLD),
                
                # Gráfico de CPU
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Uso de CPU ao longo do tempo", weight=ft.FontWeight.BOLD),
                            self.cpu_chart,
                        ],
                    ),
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                ),
                
                ft.Container(height=10),
                
                # Gráfico de Memória
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Uso de Memória ao longo do tempo", weight=ft.FontWeight.BOLD),
                            self.memory_chart,
                        ],
                    ),
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                ),
                
                ft.Container(height=10),
                
                # Gráfico de Rede
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Tráfego de Rede ao longo do tempo", weight=ft.FontWeight.BOLD),
                            ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Container(width=10, height=10, bgcolor=ft.colors.RED, border_radius=5),
                                            ft.Text("Upload"),
                                        ]),
                                        padding=5,
                                    ),
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Container(width=10, height=10, bgcolor=ft.colors.BLUE, border_radius=5),
                                            ft.Text("Download"),
                                        ]),
                                        padding=5,
                                    ),
                                ],
                            ),
                            self.network_chart,
                        ],
                    ),
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                ),
                
                ft.Container(height=20),
                
                # Lista de processos
                self.processes_container,
            ],
            spacing=10,
            expand=True,
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


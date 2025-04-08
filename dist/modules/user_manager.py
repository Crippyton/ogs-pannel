import flet as ft
import json
import os
from datetime import datetime

# Arquivo de usuários
USERS_FILE = "users.json"

class Module:
    def get_module_info(self):
        return {
            "name": "Painel de Usuários",
            "description": "Usuários do sistema",
            "version": "1.0.0",
            "icon": ft.icons.PEOPLE,
            "color": ft.colors.BLUE,
        }
        
    def get_view(self):
        self.users = self._load_users()
        self.status_text = ft.Text(visible=False, size=14)
        
        # Campos para filtrar usuários
        self.search_field = ft.TextField(
            label="Buscar usuário",
            prefix_icon=ft.icons.SEARCH,
            on_change=self._filter_users,
            expand=True
        )
        
        # Tabela de usuários
        self.user_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Usuário")),
                ft.DataColumn(ft.Text("Nome")),
                ft.DataColumn(ft.Text("Função")),
                ft.DataColumn(ft.Text("Criado em")),
                ft.DataColumn(ft.Text("Status")),
            ],
            rows=[]
        )
        
        # Preenche a tabela
        self._update_user_table()
        
        # Estatísticas
        total_users = len(self.users)
        admin_users = sum(1 for user in self.users.values() if user.get("role") == "admin")
        
        stats_row = ft.Row(
            [
                self._create_stat_card("Total de Usuários", total_users, ft.icons.PEOPLE, ft.colors.BLUE),
                self._create_stat_card("Administradores", admin_users, ft.icons.ADMIN_PANEL_SETTINGS, ft.colors.RED),
                self._create_stat_card("Usuários Padrão", total_users - admin_users, ft.icons.PERSON, ft.colors.GREEN),
            ],
            alignment=ft.MainAxisAlignment.START,
        )
        
        return ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Gerenciador de Usuários", size=24, weight=ft.FontWeight.BOLD),
                            ft.Container(height=20),
                            stats_row,
                            ft.Container(height=20),
                            ft.Row(
                                [
                                    self.search_field,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Container(height=10),
                            self.user_table,
                            self.status_text,
                        ],
                    ),
                    padding=20,
                    expand=True,
                )
            ],
            expand=True,
        )
        
    def _create_stat_card(self, title, value, icon, color):
        return ft.Card(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icon, size=40, color=color),
                        ft.Column(
                            [
                                ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
                                ft.Text(str(value), size=24, weight=ft.FontWeight.BOLD, color=color),
                            ],
                            spacing=5,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=15,
                ),
                width=200,
                padding=15,
            ),
        )
        
    def _load_users(self):
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, "r") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Erro ao carregar usuários: {e}")
            return {}
            
    def _update_user_table(self, filter_text=""):
        self.user_table.rows.clear()
        
        for username, user_data in self.users.items():
            # Aplica filtro se necessário
            if filter_text and filter_text.lower() not in username.lower() and filter_text.lower() not in user_data.get("name", "").lower():
                continue
                
            # Formata a data de criação
            created_at = user_data.get("created_at", "")
            try:
                dt = datetime.fromisoformat(created_at)
                formatted_date = dt.strftime("%d/%m/%Y %H:%M")
            except:
                formatted_date = created_at
                
            # Status do usuário (ativo/inativo)
            status = user_data.get("status", "active")
            status_text = "Ativo" if status == "active" else "Inativo"
            status_color = ft.colors.GREEN if status == "active" else ft.colors.RED
            
            self.user_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(username)),
                        ft.DataCell(ft.Text(user_data.get("name", ""))),
                        ft.DataCell(ft.Text("Administrador" if user_data.get("role") == "admin" else "Usuário")),
                        ft.DataCell(ft.Text(formatted_date)),
                        ft.DataCell(ft.Text(status_text, color=status_color)),
                    ]
                )
            )
            
    def _filter_users(self, e):
        filter_text = self.search_field.value
        self._update_user_table(filter_text)
        e.page.update()
import flet as ft
import json
import os
import webbrowser
import csv
import io
from datetime import datetime

class Module:
    def __init__(self):
        self.page = None
        self.links_file = "useful_links.json"
        self.links = []
        self.filtered_links = []
        self.search_term = ""
        
    def get_module_info(self):
        return {
            "name": "Links Úteis",
            "description": "Gerenciador de links úteis para a equipe OGS",
            "version": "1.0.0",
            "icon": ft.Icons.LINK,
            "color": ft.Colors.INDIGO,
        }
    
    def _load_links(self):
        """Carrega os links do arquivo JSON"""
        try:
            if os.path.exists(self.links_file):
                with open(self.links_file, "r", encoding="utf-8") as f:
                    self.links = json.load(f)
            else:
                # Cria alguns links de exemplo se o arquivo não existir
                self.links = [
                    {
                        "id": "1",
                        "title": "Portal OGS",
                        "description": "Portal interno da equipe OGS",
                        "url": "https://portal.ogs.com.br",
                        "created_at": datetime.now().isoformat(),
                        "category": "Interno"
                    },
                    {
                        "id": "2",
                        "title": "Documentação Técnica",
                        "description": "Base de conhecimento técnico da equipe",
                        "url": "https://docs.ogs.com.br",
                        "created_at": datetime.now().isoformat(),
                        "category": "Documentação"
                    }
                ]
                self._save_links()
        except Exception as e:
            print(f"Erro ao carregar links: {e}")
            self.links = []
        
        # Inicializa os links filtrados com todos os links
        self.filtered_links = self.links.copy()
    
    def _save_links(self):
        """Salva os links no arquivo JSON"""
        try:
            with open(self.links_file, "w", encoding="utf-8") as f:
                json.dump(self.links, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar links: {e}")
            if self.page:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"Erro ao salvar links: {e}"),
                        bgcolor=ft.Colors.RED_500,
                        action="OK",
                    )
                )
    
    def _open_link(self, e, url):
        """Abre o link no navegador padrão"""
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Erro ao abrir link: {e}")
            if self.page:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"Erro ao abrir link: {e}"),
                        bgcolor=ft.Colors.RED_500,
                        action="OK",
                    )
                )
    
    def _add_link(self, title, description, url, category="Geral"):
        """Adiciona um novo link à lista"""
        # Gera um ID único baseado no timestamp
        link_id = str(int(datetime.now().timestamp()))
        
        new_link = {
            "id": link_id,
            "title": title,
            "description": description,
            "url": url,
            "created_at": datetime.now().isoformat(),
            "category": category
        }
        
        self.links.append(new_link)
        self._save_links()
        self._filter_links()  # Atualiza os links filtrados
        self._update_links_view()
    
    def _edit_link(self, link_id, title, description, url, category):
        """Edita um link existente"""
        for i, link in enumerate(self.links):
            if link["id"] == link_id:
                self.links[i]["title"] = title
                self.links[i]["description"] = description
                self.links[i]["url"] = url
                self.links[i]["category"] = category
                break
        
        self._save_links()
        self._filter_links()  # Atualiza os links filtrados
        self._update_links_view()
    
    def _delete_link(self, link_id):
        """Remove um link da lista"""
        self.links = [link for link in self.links if link["id"] != link_id]
        self._save_links()
        self._filter_links()  # Atualiza os links filtrados
        self._update_links_view()
    
    def _filter_links(self):
        """Filtra os links com base no termo de pesquisa"""
        if not self.search_term:
            self.filtered_links = self.links.copy()
        else:
            term = self.search_term.lower()
            self.filtered_links = [
                link for link in self.links
                if term in link["title"].lower() or 
                   term in link["description"].lower() or 
                   term in link["url"].lower() or
                   term in link["category"].lower()
            ]
    
    def _handle_search(self, e):
        """Manipula a pesquisa de links"""
        self.search_term = e.control.value
        self._filter_links()
        self._update_links_view()
    
    def _update_links_view(self):
        """Atualiza a visualização dos links"""
        if not hasattr(self, 'links_list') or not self.links_list:
            return
            
        self.links_list.controls.clear()
        
        if not self.filtered_links:
            self.links_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.SEARCH_OFF,
                                size=64,
                                color=ft.Colors.GREY_400,
                            ),
                            ft.Text(
                                "Nenhum link encontrado",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREY_500,
                            ),
                            ft.Text(
                                "Tente uma pesquisa diferente ou adicione novos links",
                                size=14,
                                color=ft.Colors.GREY_400,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    alignment=ft.alignment.center,
                    padding=40,
                    expand=True,
                )
            )
        else:
            # Agrupa links por categoria
            links_by_category = {}
            for link in self.filtered_links:
                category = link.get("category", "Geral")
                if category not in links_by_category:
                    links_by_category[category] = []
                links_by_category[category].append(link)
            
            # Adiciona os links agrupados por categoria
            for category, links in sorted(links_by_category.items()):
                # Adiciona o cabeçalho da categoria
                self.links_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(
                                    content=ft.Icon(
                                        ft.Icons.FOLDER,
                                        color=ft.Colors.INDIGO,
                                        size=20,
                                    ),
                                    margin=ft.margin.only(right=8),
                                ),
                                ft.Text(
                                    category,
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.INDIGO,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        f"{len(links)}",
                                        size=12,
                                        color=ft.Colors.WHITE,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    bgcolor=ft.Colors.INDIGO,
                                    border_radius=12,
                                    padding=ft.padding.only(left=8, right=8, top=4, bottom=4),
                                    margin=ft.margin.only(left=8),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.padding.only(left=16, top=24, bottom=8),
                        border_radius=ft.border_radius.only(top_left=8, top_right=8),
                    )
                )
                
                # Adiciona os links da categoria em um grid responsivo
                grid_items = []
                for link in links:
                    grid_items.append(
                        ft.Container(
                            content=self._create_link_card(link),
                            col={"xs": 12, "sm": 6, "md": 4, "lg": 4, "xl": 3},
                            padding=8,
                        )
                    )
                
                self.links_list.controls.append(
                    ft.Container(
                        content=ft.ResponsiveRow(
                            grid_items,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        padding=ft.padding.only(left=8, right=8, bottom=16),
                    )
                )
                
                # Adiciona um divisor após cada categoria, exceto a última
                if category != list(sorted(links_by_category.keys()))[-1]:
                    self.links_list.controls.append(
                        ft.Container(
                            content=ft.Divider(
                                height=1,
                                color=ft.Colors.GREY_300,
                            ),
                            padding=ft.padding.only(left=16, right=16),
                        )
                    )
        
        if self.page:
            self.page.update()
    
    def _create_link_card(self, link):
        """Cria um card para exibir um link"""
        # Determina a cor do card com base na categoria
        category_colors = {
            "Interno": ft.Colors.BLUE,
            "Documentação": ft.Colors.GREEN,
            "Ferramentas": ft.Colors.ORANGE,
            "Suporte": ft.Colors.RED,
            "Geral": ft.Colors.PURPLE,
        }
        
        category = link.get("category", "Geral")
        card_color = category_colors.get(category, ft.Colors.INDIGO)
        
        # Cria um ícone com base na URL
        icon = ft.Icons.LINK
        if "docs" in link["url"].lower() or "documentacao" in link["url"].lower():
            icon = ft.Icons.DESCRIPTION
        elif "portal" in link["url"].lower() or "intranet" in link["url"].lower():
            icon = ft.Icons.BUSINESS
        elif "suporte" in link["url"].lower() or "help" in link["url"].lower():
            icon = ft.Icons.SUPPORT
        elif "ferramenta" in link["url"].lower() or "tool" in link["url"].lower():
            icon = ft.Icons.BUILD
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        # Cabeçalho do card com ícone e título
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Icon(
                                            icon,
                                            color=ft.Colors.WHITE,
                                            size=20,
                                        ),
                                        bgcolor=card_color,
                                        width=36,
                                        height=36,
                                        border_radius=18,
                                        alignment=ft.alignment.center,
                                    ),
                                    ft.Container(width=10),
                                    ft.Text(
                                        link["title"],
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=card_color,
                                        no_wrap=False,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        expand=True,
                                    ),
                                ],
                                spacing=0,
                                alignment=ft.MainAxisAlignment.START,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            margin=ft.margin.only(bottom=8),
                        ),
                        
                        # Descrição do link
                        ft.Container(
                            content=ft.Text(
                                link["description"],
                                size=14,
                                no_wrap=False,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                color=ft.Colors.BLACK87,
                            ),
                            margin=ft.margin.only(bottom=12),
                            height=40,  # Altura fixa para manter consistência
                        ),
                        
                        # URL do link
                        ft.Container(
                            content=ft.Text(
                                link["url"],
                                size=12,
                                color=ft.Colors.BLUE_400,
                                no_wrap=False,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                selectable=True,
                            ),
                            margin=ft.margin.only(bottom=12),
                        ),
                        
                        # Divisor
                        ft.Divider(height=1, color=ft.Colors.GREY_300),
                        
                        # Botões de ação
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    icon_color=ft.Colors.ORANGE,
                                    tooltip="Editar link",
                                    on_click=lambda e, l=link: self._show_edit_dialog(l),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    icon_color=ft.Colors.RED,
                                    tooltip="Excluir link",
                                    on_click=lambda e, l=link: self._show_delete_dialog(l),
                                ),
                                ft.Container(expand=True),  # Espaçador flexível
                                ft.ElevatedButton(
                                    content=ft.Row(
                                        [
                                            ft.Text("Abrir", size=14),
                                            ft.Icon(ft.Icons.OPEN_IN_NEW, size=14),
                                        ],
                                        spacing=4,
                                        alignment=ft.MainAxisAlignment.CENTER,
                                    ),
                                    on_click=lambda e, url=link["url"]: self._open_link(e, url),
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                        color=ft.Colors.WHITE,
                                        bgcolor=card_color,
                                    ),
                                    height=36,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END,
                            spacing=0,
                        ),
                    ],
                    spacing=0,
                ),
                padding=16,
                width=None,  # Permite que o card se ajuste à largura disponível
            ),
            elevation=2,
            surface_tint_color=ft.Colors.SURFACE_VARIANT,
        )
    
    def _show_add_dialog(self, e=None):
        """Exibe o diálogo para adicionar um novo link"""
        # Campos do formulário
        title_field = ft.TextField(
            label="Título",
            border=ft.InputBorder.OUTLINE,
            width=400,
            prefix_icon=ft.Icons.TITLE,
            focused_border_color=ft.Colors.INDIGO,
            focused_color=ft.Colors.INDIGO,
        )
        
        description_field = ft.TextField(
            label="Descrição",
            border=ft.InputBorder.OUTLINE,
            width=400,
            multiline=True,
            min_lines=2,
            max_lines=4,
            prefix_icon=ft.Icons.DESCRIPTION,
            focused_border_color=ft.Colors.INDIGO,
            focused_color=ft.Colors.INDIGO,
        )
        
        url_field = ft.TextField(
            label="URL",
            border=ft.InputBorder.OUTLINE,
            width=400,
            prefix_icon=ft.Icons.LINK,
            focused_border_color=ft.Colors.INDIGO,
            focused_color=ft.Colors.INDIGO,
        )
        
        # Dropdown para categorias predefinidas
        category_dropdown = ft.Dropdown(
            label="Categoria",
            width=400,
            options=[
                ft.dropdown.Option("Geral"),
                ft.dropdown.Option("Interno"),
                ft.dropdown.Option("Documentação"),
                ft.dropdown.Option("Ferramentas"),
                ft.dropdown.Option("Suporte"),
            ],
            value="Geral",
            prefix_icon=ft.Icons.CATEGORY,
            focused_border_color=ft.Colors.INDIGO,
            focused_color=ft.Colors.INDIGO,
        )
        
        # Função para adicionar o link
        def handle_add(e):
            title = title_field.value
            description = description_field.value
            url = url_field.value
            category = category_dropdown.value
            
            if not title or not url:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("Título e URL são obrigatórios"),
                        bgcolor=ft.Colors.RED_500,
                        action="OK",
                    )
                )
                return
            
            # Adiciona o protocolo http:// se não estiver presente
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "http://" + url
            
            self._add_link(title, description, url, category)
            
            # Fecha o diálogo
            add_dialog.open = False
            self.page.update()
            
            # Exibe mensagem de sucesso
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("Link adicionado com sucesso"),
                    bgcolor=ft.Colors.GREEN_500,
                    action="OK",
                )
            )
        
        # Cria o diálogo
        add_dialog = ft.AlertDialog(
            title=ft.Text("Adicionar Novo Link"),
            content=ft.Column(
                [
                    title_field,
                    description_field,
                    url_field,
                    category_dropdown,
                ],
                spacing=20,
                width=400,
                height=300,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar", 
                    on_click=lambda e: setattr(add_dialog, "open", False),
                    style=ft.ButtonStyle(color=ft.Colors.GREY_700),
                ),
                ft.ElevatedButton(
                    "Adicionar", 
                    on_click=handle_add,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.INDIGO,
                        color=ft.Colors.WHITE,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        self.page.dialog = add_dialog
        add_dialog.open = True
        self.page.update()
    
    def _show_edit_dialog(self, link):
        """Exibe o diálogo para editar um link existente"""
        # Campos do formulário
        title_field = ft.TextField(
            label="Título",
            value=link["title"],
            border=ft.InputBorder.OUTLINE,
            width=400,
            prefix_icon=ft.Icons.TITLE,
            focused_border_color=ft.Colors.INDIGO,
            focused_color=ft.Colors.INDIGO,
        )
        
        description_field = ft.TextField(
            label="Descrição",
            value=link["description"],
            border=ft.InputBorder.OUTLINE,
            width=400,
            multiline=True,
            min_lines=2,
            max_lines=4,
            prefix_icon=ft.Icons.DESCRIPTION,
            focused_border_color=ft.Colors.INDIGO,
            focused_color=ft.Colors.INDIGO,
        )
        
        url_field = ft.TextField(
            label="URL",
            value=link["url"],
            border=ft.InputBorder.OUTLINE,
            width=400,
            prefix_icon=ft.Icons.LINK,
            focused_border_color=ft.Colors.INDIGO,
            focused_color=ft.Colors.INDIGO,
        )
        
        # Dropdown para categorias predefinidas
        category_dropdown = ft.Dropdown(
            label="Categoria",
            width=400,
            options=[
                ft.dropdown.Option("Geral"),
                ft.dropdown.Option("Interno"),
                ft.dropdown.Option("Documentação"),
                ft.dropdown.Option("Ferramentas"),
                ft.dropdown.Option("Suporte"),
            ],
            value=link.get("category", "Geral"),
            prefix_icon=ft.Icons.CATEGORY,
            focused_border_color=ft.Colors.INDIGO,
            focused_color=ft.Colors.INDIGO,
        )
        
        # Função para salvar as alterações
        def handle_save(e):
            title = title_field.value
            description = description_field.value
            url = url_field.value
            category = category_dropdown.value
            
            if not title or not url:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("Título e URL são obrigatórios"),
                        bgcolor=ft.Colors.RED_500,
                        action="OK",
                    )
                )
                return
            
            # Adiciona o protocolo http:// se não estiver presente
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "http://" + url
            
            self._edit_link(link["id"], title, description, url, category)
            
            # Fecha o diálogo
            edit_dialog.open = False
            self.page.update()
            
            # Exibe mensagem de sucesso
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("Link atualizado com sucesso"),
                    bgcolor=ft.Colors.GREEN_500,
                    action="OK",
                )
            )
        
        # Cria o diálogo
        edit_dialog = ft.AlertDialog(
            title=ft.Text("Editar Link"),
            content=ft.Column(
                [
                    title_field,
                    description_field,
                    url_field,
                    category_dropdown,
                ],
                spacing=20,
                width=400,
                height=300,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar", 
                    on_click=lambda e: setattr(edit_dialog, "open", False),
                    style=ft.ButtonStyle(color=ft.Colors.GREY_700),
                ),
                ft.ElevatedButton(
                    "Salvar", 
                    on_click=handle_save,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.INDIGO,
                        color=ft.Colors.WHITE,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        self.page.dialog = edit_dialog
        edit_dialog.open = True
        self.page.update()
    
    def _show_delete_dialog(self, link):
        """Exibe o diálogo para confirmar a exclusão de um link"""
        # Cria o diálogo
        delete_dialog = ft.AlertDialog(
            title=ft.Text("Confirmar Exclusão"),
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.WARNING_AMBER_ROUNDED,
                        color=ft.Colors.RED_500,
                        size=64,
                    ),
                    ft.Text(
                        f"Tem certeza que deseja excluir o link '{link['title']}'?",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Esta ação não pode ser desfeita.",
                        size=12,
                        color=ft.Colors.GREY_700,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar", 
                    on_click=lambda e: setattr(delete_dialog, "open", False),
                    style=ft.ButtonStyle(color=ft.Colors.GREY_700),
                ),
                ft.ElevatedButton(
                    "Excluir",
                    on_click=lambda e: self._confirm_delete(delete_dialog, link["id"]),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.RED_500,
                        color=ft.Colors.WHITE,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        self.page.dialog = delete_dialog
        delete_dialog.open = True
        self.page.update()
    
    def _confirm_delete(self, dialog, link_id):
        """Confirma a exclusão de um link"""
        # Fecha o diálogo
        dialog.open = False
        self.page.update()
        
        # Exclui o link
        self._delete_link(link_id)
        
        # Exibe mensagem de sucesso
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text("Link excluído com sucesso"),
                bgcolor=ft.Colors.GREEN_500,
                action="OK",
            )
        )
    
    def _show_import_dialog(self, e=None):
        """Exibe o diálogo para importar links em massa"""
        # Área de texto para colar os links
        import_text = ft.TextField(
            label="Cole os links no formato CSV",
            hint_text="título,descrição,url,categoria",
            border=ft.InputBorder.OUTLINE,
            width=600,
            multiline=True,
            min_lines=10,
            max_lines=20,
            focused_border_color=ft.Colors.INDIGO,
            focused_color=ft.Colors.INDIGO,
        )
        
        # Exemplo de formato em um card
        example_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Formato esperado:",
                            weight=ft.FontWeight.BOLD,
                            size=14,
                        ),
                        ft.Container(
                            content=ft.Text(
                                "título,descrição,url,categoria",
                                font_family="monospace",
                                size=12,
                            ),
                            bgcolor=ft.Colors.GREY_100,
                            border_radius=4,
                            padding=8,
                            margin=ft.margin.only(top=4, bottom=8),
                        ),
                        ft.Text(
                            "Exemplo:",
                            weight=ft.FontWeight.BOLD,
                            size=14,
                        ),
                        ft.Container(
                            content=ft.Text(
                                "Portal OGS,Portal interno da equipe,https://portal.ogs.com.br,Interno\nDocumentação,Base de conhecimento,https://docs.ogs.com.br,Documentação",
                                font_family="monospace",
                                size=12,
                                no_wrap=False,
                            ),
                            bgcolor=ft.Colors.GREY_100,
                            border_radius=4,
                            padding=8,
                            margin=ft.margin.only(top=4),
                        ),
                    ],
                ),
                padding=16,
            ),
            elevation=0,
            color=ft.Colors.SURFACE_VARIANT,
        )
        
        # Função para processar a importação
        def handle_import(e):
            csv_text = import_text.value
            
            if not csv_text:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("Nenhum dado para importar"),
                        bgcolor=ft.Colors.RED_500,
                        action="OK",
                    )
                )
                return
            
            try:
                # Processa o CSV
                reader = csv.reader(io.StringIO(csv_text))
                imported_count = 0
                
                for row in reader:
                    if len(row) >= 3:  # Pelo menos título, descrição e URL
                        title = row[0].strip()
                        description = row[1].strip()
                        url = row[2].strip()
                        category = row[3].strip() if len(row) > 3 else "Geral"
                        
                        if title and url:  # Título e URL são obrigatórios
                            # Adiciona o protocolo http:// se não estiver presente
                            if not url.startswith("http://") and not url.startswith("https://"):
                                url = "http://" + url
                            
                            self._add_link(title, description, url, category)
                            
                            imported_count += 1
                
                # Fecha o diálogo
                import_dialog.open = False
                self.page.update()
                
                # Exibe mensagem de sucesso
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"{imported_count} links importados com sucesso"),
                        bgcolor=ft.Colors.GREEN_500,
                        action="OK",
                    )
                )
            except Exception as e:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"Erro ao importar links: {e}"),
                        bgcolor=ft.Colors.RED_500,
                        action="OK",
                    )
                )
        
        # Cria o diálogo
        import_dialog = ft.AlertDialog(
            title=ft.Text("Importar Links em Massa"),
            content=ft.Column(
                [
                    example_card,
                    ft.Container(height=16),
                    import_text,
                ],
                spacing=0,
                width=600,
                height=500,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar", 
                    on_click=lambda e: setattr(import_dialog, "open", False),
                    style=ft.ButtonStyle(color=ft.Colors.GREY_700),
                ),
                ft.ElevatedButton(
                    "Importar", 
                    on_click=handle_import,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.INDIGO,
                        color=ft.Colors.WHITE,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        self.page.dialog = import_dialog
        import_dialog.open = True
        self.page.update()
    
    def get_view(self):
        """Retorna a visualização do módulo"""
        # Carrega os links
        self._load_links()
        
        # Título com ícone
        title_row = ft.Row(
            [
                ft.Icon(
                    ft.Icons.LINK,
                    size=32,
                    color=ft.Colors.INDIGO,
                ),
                ft.Text(
                    "Links Úteis", 
                    size=28, 
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.INDIGO,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        
        # Barra de pesquisa com design melhorado
        search_field = ft.TextField(
            label="Pesquisar links",
            prefix_icon=ft.Icons.SEARCH,
            border=ft.InputBorder.OUTLINE,
            expand=True,
            on_change=self._handle_search,
            border_radius=8,
            focused_border_color=ft.Colors.INDIGO,
            focused_color=ft.Colors.INDIGO,
            hint_text="Digite para pesquisar por título, descrição, URL ou categoria",
        )
        
        # Botões de ação com design melhorado
        add_button = ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ADD, size=16),
                    ft.Text("Adicionar Link", size=14),
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            on_click=self._show_add_dialog,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=ft.Colors.INDIGO,
                color=ft.Colors.WHITE,
            ),
            height=40,
        )
        
        import_button = ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.UPLOAD_FILE, size=16),
                    ft.Text("Importar", size=14),
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            on_click=self._show_import_dialog,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=ft.Colors.INDIGO_200,
                color=ft.Colors.INDIGO_900,
            ),
            height=40,
        )
        
        # Lista de links com design melhorado
        self.links_list = ft.Column(
            controls=[],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        # Atualiza a visualização dos links
        self._update_links_view()
        
        # Layout principal com design melhorado
        return ft.Container(
            content=ft.Column(
                [
                    # Cabeçalho com fundo e sombra
                    ft.Container(
                        content=ft.Column(
                            [
                                # Título e descrição
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            title_row,
                                            ft.Text(
                                                "Gerencie seus links úteis para acesso rápido",
                                                size=14,
                                                color=ft.Colors.GREY_700,
                                            ),
                                        ],
                                        spacing=4,
                                    ),
                                    margin=ft.margin.only(bottom=16),
                                ),
                                
                                # Barra de pesquisa e botões
                                ft.ResponsiveRow(
                                    [
                                        ft.Container(
                                            content=search_field,
                                            col={"xs": 12, "sm": 12, "md": 6, "lg": 7, "xl": 8},
                                            padding=ft.padding.only(right=8),
                                        ),
                                        ft.Container(
                                            content=ft.Row(
                                                [
                                                    add_button,
                                                    ft.Container(width=8),
                                                    import_button,
                                                ],
                                                spacing=0,
                                            ),
                                            col={"xs": 12, "sm": 12, "md": 6, "lg": 5, "xl": 4},
                                            padding=ft.padding.only(left=8),
                                            alignment=ft.alignment.center_right,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        padding=ft.padding.all(24),
                        bgcolor=ft.Colors.WHITE,
                        border_radius=ft.border_radius.only(bottom_left=16, bottom_right=16),
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=15,
                            color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
                            offset=ft.Offset(0, 2),
                        ),
                    ),
                    
                    # Lista de links
                    ft.Container(
                        content=self.links_list,
                        padding=ft.padding.only(top=8, bottom=24),
                        expand=True,
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
            bgcolor=ft.Colors.GREY_50,
        )
    
    def did_mount(self, page):
        """Chamado quando o módulo é montado na página"""
        self.page = page
    
    def will_unmount(self):
        """Chamado quando o módulo é desmontado da página"""
        pass


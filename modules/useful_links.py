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
            "icon": ft.icons.LINK,
            "color": ft.colors.INDIGO,
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
                        bgcolor=ft.colors.RED_500,
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
                        bgcolor=ft.colors.RED_500,
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
                    content=ft.Text(
                        "Nenhum link encontrado",
                        size=16,
                        italic=True,
                        color=ft.colors.GREY_500,
                    ),
                    alignment=ft.alignment.center,
                    padding=20,
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
                        content=ft.Text(
                            category,
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=ft.colors.INDIGO,
                        ),
                        padding=ft.padding.only(left=10, top=20, bottom=10),
                    )
                )
                
                # Adiciona os links da categoria
                for link in links:
                    self.links_list.controls.append(self._create_link_card(link))
        
        if self.page:
            self.page.update()
    
    def _create_link_card(self, link):
        """Cria um card para exibir um link"""
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.icons.LINK, color=ft.colors.INDIGO),
                                ft.Text(
                                    link["title"],
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.colors.INDIGO,
                                    no_wrap=False,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    expand=True,
                                ),
                            ],
                            spacing=10,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        ft.Container(
                            content=ft.Text(
                                link["description"],
                                size=14,
                                no_wrap=False,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            margin=ft.margin.only(top=5, bottom=10),
                        ),
                        ft.Row(
                            [
                                ft.Text(
                                    link["url"],
                                    size=12,
                                    color=ft.colors.BLUE_400,
                                    no_wrap=False,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    expand=True,
                                    selectable=True,
                                ),
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    icon_color=ft.colors.ORANGE,
                                    tooltip="Editar link",
                                    on_click=lambda e, l=link: self._show_edit_dialog(l),
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE,
                                    icon_color=ft.colors.RED,
                                    tooltip="Excluir link",
                                    on_click=lambda e, l=link: self._show_delete_dialog(l),
                                ),
                                ft.ElevatedButton(
                                    text="Abrir",
                                    icon=ft.icons.OPEN_IN_NEW,
                                    on_click=lambda e, url=link["url"]: self._open_link(e, url),
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                    ),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END,
                            spacing=5,
                        ),
                    ],
                    spacing=5,
                ),
                padding=15,
                width=None,  # Permite que o card se ajuste à largura disponível
            ),
            elevation=2,
            margin=ft.margin.only(bottom=10, left=10, right=10),
        )
    
    def _show_add_dialog(self, e=None):
        """Exibe o diálogo para adicionar um novo link"""
        # Campos do formulário
        title_field = ft.TextField(
            label="Título",
            border=ft.InputBorder.OUTLINE,
            width=400,
        )
        
        description_field = ft.TextField(
            label="Descrição",
            border=ft.InputBorder.OUTLINE,
            width=400,
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        
        url_field = ft.TextField(
            label="URL",
            border=ft.InputBorder.OUTLINE,
            width=400,
            prefix_icon=ft.icons.LINK,
        )
        
        category_field = ft.TextField(
            label="Categoria",
            border=ft.InputBorder.OUTLINE,
            width=400,
            value="Geral",
        )
        
        # Função para adicionar o link
        def handle_add(e):
            title = title_field.value
            description = description_field.value
            url = url_field.value
            category = category_field.value
            
            if not title or not url:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("Título e URL são obrigatórios"),
                        bgcolor=ft.colors.RED_500,
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
                    bgcolor=ft.colors.GREEN_500,
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
                    category_field,
                ],
                spacing=20,
                width=400,
                height=300,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(add_dialog, "open", False)),
                ft.ElevatedButton("Adicionar", on_click=handle_add),
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
        )
        
        description_field = ft.TextField(
            label="Descrição",
            value=link["description"],
            border=ft.InputBorder.OUTLINE,
            width=400,
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        
        url_field = ft.TextField(
            label="URL",
            value=link["url"],
            border=ft.InputBorder.OUTLINE,
            width=400,
            prefix_icon=ft.icons.LINK,
        )
        
        category_field = ft.TextField(
            label="Categoria",
            value=link.get("category", "Geral"),
            border=ft.InputBorder.OUTLINE,
            width=400,
        )
        
        # Função para salvar as alterações
        def handle_save(e):
            title = title_field.value
            description = description_field.value
            url = url_field.value
            category = category_field.value
            
            if not title or not url:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("Título e URL são obrigatórios"),
                        bgcolor=ft.colors.RED_500,
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
                    bgcolor=ft.colors.GREEN_500,
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
                    category_field,
                ],
                spacing=20,
                width=400,
                height=300,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(edit_dialog, "open", False)),
                ft.ElevatedButton("Salvar", on_click=handle_save),
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
            content=ft.Text(f"Tem certeza que deseja excluir o link '{link['title']}'?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(delete_dialog, "open", False)),
                ft.ElevatedButton(
                    "Excluir",
                    on_click=lambda e: self._confirm_delete(delete_dialog, link["id"]),
                    style=ft.ButtonStyle(
                        bgcolor=ft.colors.RED_500,
                        color=ft.colors.WHITE,
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
                bgcolor=ft.colors.GREEN_500,
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
        )
        
        # Exemplo de formato
        example_text = ft.Text(
            "Formato esperado: título,descrição,url,categoria\nExemplo:\nPortal OGS,Portal interno da equipe,https://portal.ogs.com.br,Interno\nDocumentação,Base de conhecimento,https://docs.ogs.com.br,Documentação",
            size=12,
            color=ft.colors.GREY_700,
        )
        
        # Função para processar a importação
        def handle_import(e):
            csv_text = import_text.value
            
            if not csv_text:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("Nenhum dado para importar"),
                        bgcolor=ft.colors.RED_500,
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
                        bgcolor=ft.colors.GREEN_500,
                        action="OK",
                    )
                )
            except Exception as e:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"Erro ao importar links: {e}"),
                        bgcolor=ft.colors.RED_500,
                        action="OK",
                    )
                )
        
        # Cria o diálogo
        import_dialog = ft.AlertDialog(
            title=ft.Text("Importar Links em Massa"),
            content=ft.Column(
                [
                    example_text,
                    ft.Container(height=10),
                    import_text,
                ],
                spacing=10,
                width=600,
                height=400,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(import_dialog, "open", False)),
                ft.ElevatedButton("Importar", on_click=handle_import),
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
        
        # Título
        title = ft.Text("Links Úteis", size=24, weight=ft.FontWeight.BOLD)
        
        # Barra de pesquisa
        search_field = ft.TextField(
            label="Pesquisar links",
            prefix_icon=ft.icons.SEARCH,
            border=ft.InputBorder.OUTLINE,
            expand=True,
            on_change=self._handle_search,
        )
        
        # Botões de ação
        add_button = ft.ElevatedButton(
            text="Adicionar Link",
            icon=ft.icons.ADD,
            on_click=self._show_add_dialog,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )
        
        import_button = ft.ElevatedButton(
            text="Importar Links",
            icon=ft.icons.UPLOAD_FILE,
            on_click=self._show_import_dialog,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )
        
        # Lista de links
        self.links_list = ft.Column(
            controls=[],
            spacing=5,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        # Atualiza a visualização dos links
        self._update_links_view()
        
        # Layout principal
        return ft.Column(
            [
                # Cabeçalho
                ft.Container(
                    content=ft.Row(
                        [
                            title,
                            ft.Container(width=20),
                            search_field,
                            ft.Container(width=10),
                            add_button,
                            ft.Container(width=10),
                            import_button,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.padding.only(left=20, right=20, top=20, bottom=10),
                ),
                
                # Divisor
                ft.Divider(height=1),
                
                # Lista de links
                ft.Container(
                    content=self.links_list,
                    padding=ft.padding.only(left=10, right=10, top=10, bottom=20),
                    expand=True,
                ),
            ],
            expand=True,
        )
    
    def did_mount(self, page):
        """Chamado quando o módulo é montado na página"""
        self.page = page
    
    def will_unmount(self):
        """Chamado quando o módulo é desmontado da página"""
        pass


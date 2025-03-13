import flet as ft
import webbrowser
import subprocess
import platform
import threading
import math
import json
import os
import socket
import time
from servidores import SERVIDORES  # Importa a lista de servidores

# URL base do Zabbix
ZABBIX_URL_BASE = "http://10.200.4.21/zabbix.php?action=search&search="

def main(page: ft.Page):
    page.title = "Monitoramento de Servidores - Zabbix"
    page.theme_mode = ft.ThemeMode.LIGHT  # Modo claro
    page.bgcolor = ft.colors.BLACK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO  # Habilita rolagem na página

    # Definir tema personalizado
    page.theme = ft.Theme(
        color_scheme_seed=ft.colors.BLUE_700,
        # Usando VisualDensity em vez de ThemeVisualDensity (depreciado)
        visual_density=ft.VisualDensity.COMFORTABLE,
    )

    # Configuração para responsividade usando a nova sintaxe
    if hasattr(page, 'window'):
        page.window.width = 1200
        page.window.min_width = 400
        page.window.height = 800
        page.window.min_height = 600
        largura_tela = page.window.width
    else:
        # Fallback para versões antigas do Flet
        largura_tela = 1200

    # Função para atualizar a largura da tela quando a janela for redimensionada
    def page_resize(e):
        nonlocal largura_tela
        if hasattr(page, 'window'):
            largura_tela = page.window.width
        # Atualiza a visualização se estiver no modo grade
        if modo_visualizacao == "grade":
            atualizar_lista_servidores(None)
        page.update()

    # Registra o evento de redimensionamento com o novo nome
    if hasattr(page, 'on_resized'):
        page.on_resized = page_resize
    elif hasattr(page, 'on_resize'):
        # Fallback para versões antigas
        page.on_resize = page_resize

    # Armazenamento local para favoritos
    # Usando client_storage se disponível, caso contrário uma variável normal
    try:
        favoritos = page.client_storage.get("favoritos") or []
    except AttributeError:
        # Fallback para versões do Flet sem client_storage
        favoritos = []

    # Lista de servidores que pode ser modificada
    lista_de_servidores = SERVIDORES.copy()

    # Variável para controlar o modo de visualização (lista ou favoritos)
    # Usando uma variável global em vez de ft.State
    mostrar_apenas_favoritos = False

    # Dicionário para armazenar o status online/offline de cada servidor
    status_servidores = {}

    # Dicionário para armazenar o status das portas de cada servidor
    status_portas = {}

    # Variáveis para paginação
    itens_por_pagina = 10
    pagina_atual = 1
    total_paginas = 1

    # Variável para controlar o modo de visualização (lista ou grade)
    modo_visualizacao = "lista"  # Pode ser "lista" ou "grade"

    # Caminho para o arquivo de servidores personalizados
    arquivo_servidores_personalizados = "servidores_personalizados.json"

    # Carregar servidores personalizados se o arquivo existir
    def carregar_servidores_personalizados():
        nonlocal lista_de_servidores
        try:
            if os.path.exists(arquivo_servidores_personalizados):
                with open(arquivo_servidores_personalizados, 'r', encoding='utf-8') as arquivo:
                    servidores_personalizados = json.load(arquivo)
                    # Mesclar com a lista original, substituindo servidores com mesmo IP
                    servidores_dict = {servidor["ip"]: servidor for servidor in lista_de_servidores}
                    for servidor in servidores_personalizados:
                        servidores_dict[servidor["ip"]] = servidor
                    lista_de_servidores = list(servidores_dict.values())
        except Exception as e:
            print(f"Erro ao carregar servidores personalizados: {e}")

    # Salvar servidores personalizados
    def salvar_servidores_personalizados():
        try:
            with open(arquivo_servidores_personalizados, 'w', encoding='utf-8') as arquivo:
                json.dump(lista_de_servidores, arquivo, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Erro ao salvar servidores personalizados: {e}")

    # Carregar servidores personalizados ao iniciar
    carregar_servidores_personalizados()

    # Função para carregar imagens (pode ser expandida conforme necessário)
    def carregar_imagens():
        # Dicionário de imagens para botões, com caminho/url das imagens
        return {
            "zabbix": "./assets/zabbix.png",  # Substitua pelo caminho real da imagem
            "unidade": "./assets/pixeon.jpeg",  # Substitua pelo caminho real da imagem
        }

    # Carregar imagens
    imagens = carregar_imagens()

    def ping(host):
        """
        Realiza um ping no host e retorna True se estiver online, False caso contrário.
        """
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', host]
        try:
            return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
        except:
            return False

    def verificar_porta(host, porta):
        """Verifica se uma porta específica está aberta no host."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # Timeout de 2 segundos
            resultado = sock.connect_ex((host, int(porta)))
            sock.close()
            return resultado == 0  # 0 significa que a porta está aberta
        except:
            return False

    def verificar_portas_servidor(servidor):
        """Verifica todas as portas configuradas para um servidor."""
        ip = servidor["ip"]
        portas = servidor.get("portas", [])
        resultado = {}
        
        for porta_info in portas:
            porta = porta_info["porta"]
            resultado[porta] = verificar_porta(ip, porta)
        
        return resultado

    def verificar_status_servidores():
        """
        Verifica o status de todos os servidores em segundo plano.
        """
        for servidor in lista_de_servidores:
            ip = servidor["ip"]
            # Verifica ping
            status_servidores[ip] = ping(ip)
            
            # Verifica portas se o servidor tiver portas configuradas
            if "portas" in servidor and servidor["portas"]:
                if ip not in status_portas:
                    status_portas[ip] = {}
                
                status_portas[ip] = verificar_portas_servidor(servidor)
        
        # Atualiza a interface após verificar todos os servidores
        atualizar_lista_servidores(None)

    def iniciar_verificacao_status():
        """
        Inicia a verificação de status em uma thread separada para não bloquear a UI.
        """
        thread = threading.Thread(target=verificar_status_servidores)
        thread.daemon = True
        thread.start()

    def iniciar_verificacao_portas():
        """
        Inicia a verificação de portas em uma thread separada para não bloquear a UI.
        """
        def task():
            for servidor in lista_de_servidores:
                ip = servidor["ip"]
                if "portas" in servidor and servidor["portas"]:
                    if ip not in status_portas:
                        status_portas[ip] = {}
                    
                    status_portas[ip] = verificar_portas_servidor(servidor)
            
            # Atualiza a interface após verificar todas as portas
            atualizar_lista_servidores(None)
        
        # Exibe mensagem informando que a verificação começou
        page.snack_bar = ft.SnackBar(
            content=ft.Text("Verificando portas de todos os servidores..."),
            bgcolor=ft.colors.BLUE_500,
        )
        page.snack_bar.open = True
        page.update()
        
        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()

    # Botão para verificar status de todos os servidores
    botao_verificar_status = ft.IconButton(
        icon=ft.icons.REFRESH,
        icon_color=ft.colors.BLUE_500,
        bgcolor=ft.colors.WHITE,
        tooltip="Verificar status de todos os servidores",
        on_click=lambda e: iniciar_verificacao_status(),
    )

    # Botão para verificar portas de todos os servidores
    botao_verificar_portas = ft.IconButton(
        icon=ft.icons.SETTINGS_ETHERNET,
        icon_color=ft.colors.BLUE_500,
        bgcolor=ft.colors.WHITE,
        tooltip="Verificar portas de todos os servidores",
        on_click=lambda e: iniciar_verificacao_portas(),
    )

    # Botão para alternar entre visualização em lista e grade
    def alternar_modo_visualizacao(e):
        """Alterna entre visualização em lista e grade."""
        nonlocal modo_visualizacao
        modo_visualizacao = "grade" if modo_visualizacao == "lista" else "lista"
        
        if modo_visualizacao == "lista":
            botao_visualizacao.icon = ft.icons.GRID_VIEW
            botao_visualizacao.tooltip = "Alternar para visualização em grade"
        else:
            botao_visualizacao.icon = ft.icons.VIEW_LIST
            botao_visualizacao.tooltip = "Alternar para visualização em lista"
        
        atualizar_lista_servidores(None)

    botao_visualizacao = ft.IconButton(
        icon=ft.icons.GRID_VIEW,
        icon_color=ft.colors.BLUE_500,
        bgcolor=ft.colors.WHITE,
        tooltip="Alternar para visualização em grade",
        on_click=alternar_modo_visualizacao,
    )

    # Botão para gerenciar servidores (adicionar, editar, remover)
    botao_gerenciar_servidores = ft.IconButton(
        icon=ft.icons.SETTINGS,
        icon_color=ft.colors.BLUE_500,
        bgcolor=ft.colors.WHITE,
        tooltip="Gerenciar servidores",
        on_click=lambda e: abrir_dialogo_gerenciar_servidores(),
    )

    def abrir_zabbix(host_ip):
        """Abre a URL do Zabbix no navegador para o servidor específico."""
        url = f"{ZABBIX_URL_BASE}{host_ip}"
        webbrowser.open(url)
       
    def abrir_ip_unidade(ip_unidade):
        """Abre a URL com o IP da unidade no navegador."""
        url = f"http://{ip_unidade}/"
        webbrowser.open(url)

    def alternar_favorito(e, servidor_ip):
        """Adiciona ou remove um servidor dos favoritos."""
        if servidor_ip in favoritos:
            favoritos.remove(servidor_ip)
        else:
            favoritos.append(servidor_ip)
       
        # Tentativa de salvar os favoritos no armazenamento local se disponível
        try:
            page.client_storage.set("favoritos", favoritos)
        except AttributeError:
            pass  # Ignora se client_storage não estiver disponível
       
        # Atualiza a lista para refletir os favoritos
        atualizar_lista_servidores(None)

    def alternar_visualizacao_favoritos(e):
        """Alterna entre mostrar todos os servidores ou apenas favoritos."""
        nonlocal mostrar_apenas_favoritos
        mostrar_apenas_favoritos = not mostrar_apenas_favoritos
       
        if mostrar_apenas_favoritos:
            botao_favoritos.icon = ft.icons.STAR
            botao_favoritos.tooltip = "Mostrar todos os servidores"
        else:
            botao_favoritos.icon = ft.icons.STAR_BORDER
            botao_favoritos.tooltip = "Mostrar apenas favoritos"
       
        atualizar_lista_servidores(None)
        page.update()

    def ir_para_pagina(nova_pagina):
        """Navega para a página especificada."""
        nonlocal pagina_atual
        if 1 <= nova_pagina <= total_paginas:
            pagina_atual = nova_pagina
            atualizar_lista_servidores(None)

    # Função para calcular o número de cards por linha com base na largura da tela
    def calcular_cards_por_linha():
        # Ajusta o número de cards por linha com base na largura da tela
        if largura_tela < 600:
            return 1  # Telas muito pequenas: 1 card por linha
        elif largura_tela < 900:
            return 2  # Telas pequenas: 2 cards por linha
        elif largura_tela < 1200:
            return 3  # Telas médias: 3 cards por linha
        else:
            return 4  # Telas grandes: 4 cards por linha

    def atualizar_lista_servidores(e):
        """Filtra a lista de servidores conforme a pesquisa por nome, IP ou tags."""
        nonlocal total_paginas, pagina_atual
        termo = pesquisa_input.value.lower().strip() if pesquisa_input.value else ""
        
        # Filtra os servidores conforme os critérios
        servidores_filtrados = []
        for servidor in lista_de_servidores:
            nome = servidor["nome"].lower()
            ip = servidor["ip"]
            tags = ", ".join(servidor.get("tags", [])).lower()  # Obtém as tags em string
            descricao = servidor.get("descricao", "").lower()  # Obtém a descrição

            # Verifica se deve mostrar apenas favoritos
            if mostrar_apenas_favoritos and ip not in favoritos:
                continue

            # Verifica se o termo está no nome, IP, tags ou descrição
            if termo == "" or termo in nome or termo in ip or termo in tags or termo in descricao:
                servidores_filtrados.append(servidor)
        
        # Calcula o total de páginas
        total_servidores = len(servidores_filtrados)
        total_paginas = max(1, math.ceil(total_servidores / itens_por_pagina))
        
        # Ajusta a página atual se necessário
        if pagina_atual > total_paginas:
            pagina_atual = total_paginas
        
        # Calcula os índices de início e fim para a página atual
        inicio = (pagina_atual - 1) * itens_por_pagina
        fim = min(inicio + itens_por_pagina, total_servidores)
        
        # Obtém os servidores para a página atual
        servidores_pagina_atual = servidores_filtrados[inicio:fim]
        
        # Limpa a lista atual
        lista_servidores.controls.clear()
        
        # Adiciona os servidores à lista conforme o modo de visualização
        if modo_visualizacao == "lista":
            # Visualização em lista (vertical)
            for servidor in servidores_pagina_atual:
                lista_servidores.controls.append(criar_linha_servidor(servidor))
        else:
            # Visualização em grade (grid)
            # Determina quantos cards por linha com base na largura da tela
            cards_por_linha = calcular_cards_por_linha()
            
            # Calcula a largura do card com base no número de cards por linha
            # Subtrai o espaçamento entre os cards (10px * (cards_por_linha - 1))
            largura_disponivel = largura_tela - 60  # Subtrai o padding da página (20px de cada lado) e margem extra
            largura_card = max(250, (largura_disponivel - (10 * (cards_por_linha - 1))) / cards_por_linha)
            
            # Cria linhas de grade com o número adequado de cards por linha
            for i in range(0, len(servidores_pagina_atual), cards_por_linha):
                # Cria uma linha com os cards
                linha = ft.Row(
                    controls=[
                        criar_card_servidor_grade(servidor, largura_card)
                        for servidor in servidores_pagina_atual[i:i+cards_por_linha]
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=10,
                    wrap=True,  # Permite que os cards quebrem para a próxima linha se necessário
                )
                lista_servidores.controls.append(linha)
        
        # Atualiza os controles de paginação
        atualizar_controles_paginacao()
        
        # Atualiza o contador de servidores
        contador.value = f"{total_servidores} servidores (Página {pagina_atual} de {total_paginas})"
        page.update()

    def atualizar_controles_paginacao():
        """Atualiza os controles de paginação."""
        controles_paginacao.controls.clear()
        
        # Botão para primeira página
        controles_paginacao.controls.append(
            ft.IconButton(
                icon=ft.icons.FIRST_PAGE,
                icon_color=ft.colors.BLUE_500,
                disabled=pagina_atual == 1,
                on_click=lambda e: ir_para_pagina(1),
                tooltip="Primeira página",
            )
        )
        
        # Botão para página anterior
        controles_paginacao.controls.append(
            ft.IconButton(
                icon=ft.icons.NAVIGATE_BEFORE,
                icon_color=ft.colors.BLUE_500,
                disabled=pagina_atual == 1,
                on_click=lambda e: ir_para_pagina(pagina_atual - 1),
                tooltip="Página anterior",
            )
        )
        
        # Indicador de página atual
        controles_paginacao.controls.append(
            ft.Text(f"{pagina_atual} de {total_paginas}", size=14)
        )
        
        # Botão para próxima página
        controles_paginacao.controls.append(
            ft.IconButton(
                icon=ft.icons.NAVIGATE_NEXT,
                icon_color=ft.colors.BLUE_500,
                disabled=pagina_atual == total_paginas,
                on_click=lambda e: ir_para_pagina(pagina_atual + 1),
                tooltip="Próxima página",
            )
        )
        
        # Botão para última página
        controles_paginacao.controls.append(
            ft.IconButton(
                icon=ft.icons.LAST_PAGE,
                icon_color=ft.colors.BLUE_500,
                disabled=pagina_atual == total_paginas,
                on_click=lambda e: ir_para_pagina(total_paginas),
                tooltip="Última página",
            )
        )

    def criar_botao_com_imagem(imagem_path, tooltip, on_click_handler, fallback_icon, fallback_color):
        """Cria um botão que pode usar imagem ou ícone como fallback."""
        try:
            # Cria um container para arredondar a imagem
            imagem_arredondada = ft.Container(
                content=ft.Image(
                    src=imagem_path,
                    width=27,
                    height=27,
                    fit=ft.ImageFit.CONTAIN,
                ),
                border_radius=12,  # Arredonda a imagem (metade da largura/altura para círculo perfeito)
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,  # Suaviza as bordas
                padding=0,  # Adiciona um pequeno padding para não ficar colado na borda
            )
           
            return ft.IconButton(
                icon=None,
                content=imagem_arredondada,
                bgcolor=ft.colors.BLACK,
                tooltip=tooltip,
                on_click=on_click_handler,
            )
        except Exception:
            # Se falhar, usa o ícone como fallback
            return ft.IconButton(
                icon=fallback_icon,
                icon_color=fallback_color,
                bgcolor=ft.colors.BLACK,
                tooltip=tooltip,
                on_click=on_click_handler,
            )

    def criar_card_servidor_grade(servidor, largura=280):
        """Cria um cartão para visualização em grade."""
        tags = servidor.get("tags", [])  # Obtém a lista de tags
        ip_unidade = servidor.get("ip_unidade", servidor["ip"])
        descricao = servidor.get("descricao", "")  # Obtém a descrição
        portas = servidor.get("portas", [])  # Obtém as portas configuradas
        
        # Verifica se o servidor está nos favoritos
        is_favorito = servidor["ip"] in favoritos
        
        # Verifica o status online/offline do servidor
        ip = servidor["ip"]
        is_online = status_servidores.get(ip, None)  # None se ainda não foi verificado
        
        # Define a cor do indicador de status
        status_color = ft.colors.GREEN_500 if is_online == True else ft.colors.RED_500 if is_online == False else ft.colors.GREY_500
        status_text = "Online" if is_online == True else "Offline" if is_online == False else "Status desconhecido"
        
        # Cria os indicadores de status das portas
        portas_status = []
        if portas and ip in status_portas:
            for porta_info in portas:
                porta = porta_info["porta"]
                descricao_porta = porta_info.get("descricao", f"Porta {porta}")
                
                # Verifica o status da porta
                porta_online = status_portas[ip].get(porta, None)
                
                # Define a cor do indicador de status
                porta_color = ft.colors.GREEN_500 if porta_online == True else ft.colors.RED_500 if porta_online == False else ft.colors.GREY_500
                porta_status_text = f"{descricao_porta}: " + ("Aberta" if porta_online == True else "Fechada" if porta_online == False else "Desconhecido")
                
                # Cria o indicador de status da porta
                portas_status.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(name=ft.icons.CIRCLE, color=porta_color, size=8),
                                ft.Text(porta_status_text, size=10, color=porta_color),
                            ],
                            spacing=2,
                        ),
                        padding=3,
                        border_radius=8,
                        bgcolor=ft.colors.WHITE,
                        margin=ft.margin.only(right=3, bottom=3),
                    )
                )
        
        return ft.Container(
            content=ft.Column(
                [
                    # Cabeçalho com nome e status
                    ft.Row(
                        [
                            ft.Icon(name=ft.icons.DNS, color=ft.colors.BLUE_500, size=24),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(name=ft.icons.CIRCLE, color=status_color, size=10),
                                        ft.Text(status_text, size=10, color=status_color),
                                    ],
                                    spacing=2,
                                ),
                                padding=3,
                                border_radius=8,
                                bgcolor=ft.colors.WHITE,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    # Nome do servidor
                    ft.Text(
                        servidor["nome"],
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.colors.BLACK,
                        no_wrap=False,
                        selectable=True,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    # IP do servidor
                    ft.Text(
                        f"IP: {servidor['ip']}", 
                        size=12, 
                        color=ft.colors.GREY_600,
                        selectable=True,
                    ),
                    # Descrição (se existir)
                    ft.Container(
                        content=ft.Text(
                            descricao if descricao else "Sem descrição",
                            size=12,
                            color=ft.colors.GREY_700,
                            italic=not descricao,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            selectable=True,
                        ),
                        height=40,  # Altura fixa para a descrição
                    ) if True else ft.Container(height=0),  # Sempre mostra o container, mesmo sem descrição
                    # Status das portas (se existirem)
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Status das portas:", size=10, weight=ft.FontWeight.BOLD) if portas_status else ft.Container(height=0),
                                ft.Row(
                                    portas_status,
                                    wrap=True,  # Permite quebra de linha
                                    spacing=2,
                                ) if portas_status else ft.Container(height=0),
                            ],
                            spacing=2,
                        ),
                        height=50 if portas_status else 0,  # Altura fixa para as portas
                    ),
                    # Tags
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Chip(
                                    label=ft.Text(tag, size=10),
                                    bgcolor=ft.colors.BLUE_100,
                                    padding=3,
                                )
                                for tag in tags[:3]  # Limita a 3 tags na visualização em grade
                            ],
                            wrap=True,
                            spacing=5,
                        ),
                        height=30,  # Altura fixa para as tags
                    ),
                    # Botões de ação
                    ft.Row(
                        [
                            # Botão para verificar status individual
                            ft.IconButton(
                                icon=ft.icons.NETWORK_PING,
                                icon_color=ft.colors.BLUE_500,
                                icon_size=18,
                                tooltip="Verificar status",
                                on_click=lambda e, ip=servidor["ip"]: verificar_status_individual(ip),
                            ),
                            # Botão de Favorito
                            ft.IconButton(
                                icon=ft.icons.STAR if is_favorito else ft.icons.STAR_BORDER,
                                icon_color=ft.colors.AMBER_500,
                                icon_size=18,
                                tooltip="Favorito" if is_favorito else "Adicionar aos favoritos",
                                on_click=lambda e, ip=servidor["ip"]: alternar_favorito(e, ip),
                            ),
                            # Botão para editar servidor
                            ft.IconButton(
                                icon=ft.icons.EDIT,
                                icon_color=ft.colors.ORANGE_500,
                                icon_size=18,
                                tooltip="Editar servidor",
                                on_click=lambda e, srv=servidor: abrir_dialogo_editar_servidor(srv),
                            ),
                            # Botão Zabbix
                            ft.IconButton(
                                icon=ft.icons.OPEN_IN_BROWSER,
                                icon_color=ft.colors.BLUE_500,
                                icon_size=18,
                                tooltip="Abrir no Zabbix",
                                on_click=lambda e, ip=servidor["ip"]: abrir_zabbix(ip),
                            ),
                            # Botão Unidade
                            ft.IconButton(
                                icon=ft.icons.MAPS_HOME_WORK,
                                icon_color=ft.colors.GREEN_500,
                                icon_size=18,
                                tooltip="Acessar interface da unidade",
                                on_click=lambda e, ip=ip_unidade: abrir_ip_unidade(ip),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=2,
                    ),
                ],
                spacing=5,
                alignment=ft.MainAxisAlignment.START,
            ),
            width=largura,  # Largura dinâmica baseada no cálculo
            height=250,  # Altura aumentada para acomodar as portas
            padding=15,
            bgcolor=ft.colors.WHITE,
            border_radius=12,
            shadow=ft.BoxShadow(blur_radius=5, spread_radius=1, color=ft.colors.GREY_300),
            on_hover=lambda e: aplicar_efeito_hover(e) if hasattr(ft.Container, "on_hover") else None,
            margin=5,  # Adiciona uma pequena margem para evitar que os cards fiquem muito próximos
        )

    def criar_linha_servidor(servidor):
        """Cria um cartão estilizado para cada servidor, incluindo as tags."""
        tags = servidor.get("tags", [])  # Obtém a lista de tags
        ip_unidade = servidor.get("ip_unidade", servidor["ip"])  # Usa o ip_unidade se existir, senão usa o IP do servidor
        descricao = servidor.get("descricao", "")  # Obtém a descrição
        portas = servidor.get("portas", [])  # Obtém as portas configuradas
       
        # Caminho da imagem específica para este servidor (se existir)
        zabbix_img = servidor.get("zabbix_img", imagens["zabbix"])
        unidade_img = servidor.get("unidade_img", imagens["unidade"])
       
        # Verifica se o servidor está nos favoritos
        is_favorito = servidor["ip"] in favoritos
        
        # Verifica o status online/offline do servidor
        ip = servidor["ip"]
        is_online = status_servidores.get(ip, None)  # None se ainda não foi verificado
        
        # Define a cor do indicador de status
        status_color = ft.colors.GREEN_500 if is_online == True else ft.colors.RED_500 if is_online == False else ft.colors.GREY_500
        status_text = "Online" if is_online == True else "Offline" if is_online == False else "Status desconhecido"
        
        # Cria os indicadores de status das portas
        portas_status = []
        if portas and ip in status_portas:
            for porta_info in portas:
                porta = porta_info["porta"]
                descricao_porta = porta_info.get("descricao", f"Porta {porta}")
                
                # Verifica o status da porta
                porta_online = status_portas[ip].get(porta, None)
                
                # Define a cor do indicador de status
                porta_color = ft.colors.GREEN_500 if porta_online == True else ft.colors.RED_500 if porta_online == False else ft.colors.GREY_500
                porta_status_text = f"{descricao_porta}: " + ("Aberta" if porta_online == True else "Fechada" if porta_online == False else "Desconhecido")
                
                # Cria o indicador de status da porta
                portas_status.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(name=ft.icons.CIRCLE, color=porta_color, size=10),
                                ft.Text(porta_status_text, size=12, color=porta_color),
                            ],
                            spacing=5,
                        ),
                        padding=5,
                        border_radius=10,
                        bgcolor=ft.colors.WHITE,
                        margin=ft.margin.only(right=5, bottom=5),
                    )
                )
       
        # Container principal
        return ft.Container(
            content=ft.Column(
                [
                    ft.ResponsiveRow(
                        [
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Icon(name=ft.icons.DNS, color=ft.colors.BLUE_500, size=30),
                                            ft.Column(
                                                [
                                                    ft.Row(
                                                        [
                                                            ft.Text(
                                                                servidor["nome"],
                                                                size=16,
                                                                weight=ft.FontWeight.BOLD,
                                                                color=ft.colors.BLACK,
                                                                no_wrap=False,
                                                                selectable=True,
                                                                max_lines=2,
                                                                overflow=ft.TextOverflow.ELLIPSIS,
                                                            ),
                                                            # Indicador de status
                                                            ft.Container(
                                                                content=ft.Row(
                                                                    [
                                                                        ft.Icon(
                                                                            name=ft.icons.CIRCLE, 
                                                                            color=status_color, 
                                                                            size=12
                                                                        ),
                                                                        ft.Text(
                                                                            status_text,
                                                                            size=12,
                                                                            color=status_color,
                                                                        ),
                                                                    ],
                                                                    spacing=5,
                                                                ),
                                                                padding=5,
                                                                border_radius=10,
                                                                bgcolor=ft.colors.WHITE,
                                                            ),
                                                        ],
                                                        alignment=ft.MainAxisAlignment.START,
                                                        spacing=10,
                                                        wrap=True,  # Permite quebra de linha
                                                    ),
                                                    # Substituindo Wrap por Row com wrap=True
                                                    ft.Row(
                                                        [
                                                            ft.Text(
                                                                f"IP: {servidor['ip']}", 
                                                                size=14, 
                                                                color=ft.colors.GREY_600,
                                                                selectable=True,
                                                            ),
                                                            *[
                                                                ft.Chip(
                                                                    label=ft.Text(tag),
                                                                    bgcolor=ft.colors.BLUE_100,
                                                                    padding=5
                                                                )
                                                                for tag in tags
                                                            ]
                                                        ],
                                                        spacing=10,
                                                        wrap=True,  # Permite quebra de linha
                                                    ),
                                                    # Descrição (se existir)
                                                    ft.Text(
                                                        descricao,
                                                        size=14,
                                                        color=ft.colors.GREY_700,
                                                        max_lines=2,
                                                        overflow=ft.TextOverflow.ELLIPSIS,
                                                        selectable=True,
                                                    ) if descricao else ft.Container(height=0),
                                                    # Status das portas (se existirem)
                                                    ft.Row(
                                                        portas_status,
                                                        wrap=True,  # Permite quebra de linha
                                                    ) if portas_status else ft.Container(height=0),
                                                ],
                                                expand=True,
                                                spacing=5,
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.START,
                                        expand=True,
                                    ),
                                ],
                                col={"sm": 12, "md": 8, "lg": 9, "xl": 10},
                            ),
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            # Botão para verificar status individual
                                            ft.IconButton(
                                                icon=ft.icons.NETWORK_PING,
                                                icon_color=ft.colors.BLUE_500,
                                                bgcolor=ft.colors.BLACK,
                                                tooltip="Verificar status",
                                                on_click=lambda e, ip=servidor["ip"]: verificar_status_individual(ip),
                                            ),
                                            # Botão de Favorito
                                            ft.IconButton(
                                                icon=ft.icons.STAR if is_favorito else ft.icons.STAR_BORDER,
                                                icon_color=ft.colors.AMBER_500,
                                                bgcolor=ft.colors.BLACK,
                                                tooltip="Remover dos favoritos" if is_favorito else "Adicionar aos favoritos",
                                                on_click=lambda e, ip=servidor["ip"]: alternar_favorito(e, ip),
                                            ),
                                            # Botão para editar servidor
                                            ft.IconButton(
                                                icon=ft.icons.EDIT,
                                                icon_color=ft.colors.ORANGE_500,
                                                bgcolor=ft.colors.BLACK,
                                                tooltip="Editar servidor",
                                                on_click=lambda e, srv=servidor: abrir_dialogo_editar_servidor(srv),
                                            ),
                                            criar_botao_com_imagem(
                                                zabbix_img,
                                                "Abrir no Zabbix",
                                                lambda e, ip=servidor["ip"]: abrir_zabbix(ip),
                                                ft.icons.OPEN_IN_BROWSER,
                                                ft.colors.BLUE_500
                                            ),
                                            criar_botao_com_imagem(
                                                unidade_img,
                                                "Acessar interface da unidade",
                                                lambda e, ip=ip_unidade: abrir_ip_unidade(ip),
                                                ft.icons.MAPS_HOME_WORK,
                                                ft.colors.GREEN_500
                                            ),
                                        ],
                                        spacing=5,
                                        wrap=True,  # Permite quebra de linha em telas pequenas
                                        alignment=ft.MainAxisAlignment.END,
                                    ),
                                ],
                                col={"sm": 12, "md": 4, "lg": 3, "xl": 2},
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                            ),
                        ],
                        spacing=10,
                    ),
                ],
                spacing=10
            ),
            padding=15,
            bgcolor=ft.colors.WHITE,
            border_radius=12,
            shadow=ft.BoxShadow(blur_radius=5, spread_radius=1, color=ft.colors.GREY_300),
            # Adiciona efeito de hover se a versão do Flet suportar
            on_hover=lambda e: aplicar_efeito_hover(e) if hasattr(ft.Container, "on_hover") else None,
        )

    def verificar_status_individual(ip):
        """
        Verifica o status de um servidor individual e atualiza a interface.
        """
        def task():
            # Encontra o servidor pelo IP
            servidor = None
            for srv in lista_de_servidores:
                if srv["ip"] == ip:
                    servidor = srv
                    break
            
            # Verifica o ping
            status_servidores[ip] = ping(ip)
            
            # Verifica as portas se o servidor tiver portas configuradas
            if servidor and "portas" in servidor and servidor["portas"]:
                if ip not in status_portas:
                    status_portas[ip] = {}
                
                status_portas[ip] = verificar_portas_servidor(servidor)
            
            # Atualiza a interface
            atualizar_lista_servidores(None)
        
        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()

    def aplicar_efeito_hover(e):
        """Aplica efeito visual quando o mouse passa sobre o cartão."""
        try:
            if e.data == "true":  # Mouse entrou
                e.control.shadow = ft.BoxShadow(blur_radius=10, spread_radius=3, color=ft.colors.BLUE_200)
                e.control.update()
            else:  # Mouse saiu
                e.control.shadow = ft.BoxShadow(blur_radius=5, spread_radius=1, color=ft.colors.GREY_300)
                e.control.update()
        except Exception:
            # Ignora erros em versões do Flet que não suportam este recurso
            pass

    # Funções para importar e exportar servidores
    def exportar_servidores(caminho=None):
        """Exporta a lista de servidores para um arquivo JSON."""
        try:
            if caminho is None:
                # Usa um nome de arquivo padrão com timestamp
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                caminho = f"servidores_exportados_{timestamp}.json"
            
            with open(caminho, "w", encoding="utf-8") as arquivo:
                json.dump(lista_de_servidores, arquivo, ensure_ascii=False, indent=4)
            
            return True, caminho
        except Exception as e:
            print(f"Erro ao exportar servidores: {e}")
            return False, str(e)

    def importar_servidores(caminho):
        """Importa servidores de um arquivo JSON."""
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo:
                servidores_importados = json.load(arquivo)
            
            # Verifica se é uma lista válida
            if not isinstance(servidores_importados, list):
                return False, "Formato de arquivo inválido. Esperava uma lista de servidores."
            
            # Verifica se cada item tem pelo menos nome e IP
            servidores_validos = []
            for servidor in servidores_importados:
                if isinstance(servidor, dict) and "nome" in servidor and "ip" in servidor:
                    servidores_validos.append(servidor)
            
            if not servidores_validos:
                return False, "Nenhum servidor válido encontrado no arquivo."
            
            # Mescla com a lista existente
            servidores_dict = {servidor["ip"]: servidor for servidor in lista_de_servidores}
            for servidor in servidores_validos:
                servidores_dict[servidor["ip"]] = servidor
            
            # Atualiza a lista de servidores
            lista_de_servidores.clear()
            lista_de_servidores.extend(servidores_dict.values())
            
            # Salva os servidores personalizados
            salvar_servidores_personalizados()
            
            return True, f"{len(servidores_validos)} servidores importados com sucesso."
        except json.JSONDecodeError:
            return False, "Arquivo JSON inválido."
        except Exception as e:
            print(f"Erro ao importar servidores: {e}")
            return False, str(e)

    # Funções para gerenciar servidores
    def abrir_dialogo_gerenciar_servidores():
        """Abre o diálogo para gerenciar servidores."""
        # Cria uma lista de servidores para o diálogo
        lista_servidores_dialogo = ft.ListView(
            expand=True,
            spacing=10,
            auto_scroll=True,
            height=400,
        )
        
        # Função para exportar servidores
        def exportar_servidores_dialog():
            # Cria um diálogo para escolher o nome do arquivo
            nome_arquivo_input = ft.TextField(
                label="Nome do arquivo",
                value=f"servidores_exportados_{time.strftime('%Y%m%d_%H%M%S')}.json",
                border=ft.InputBorder.OUTLINE,
                expand=True,
            )
            
            def confirmar_exportacao(e):
                caminho = nome_arquivo_input.value
                sucesso, resultado = exportar_servidores(caminho)
                
                # Fecha o diálogo de exportação
                dialogo_exportar.open = False
                page.update()
                
                # Exibe mensagem de sucesso ou erro
                if sucesso:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Servidores exportados com sucesso para {resultado}"),
                        bgcolor=ft.colors.GREEN_500,
                    )
                else:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Erro ao exportar servidores: {resultado}"),
                        bgcolor=ft.colors.RED_500,
                    )
                
                page.snack_bar.open = True
                page.update()
            
            dialogo_exportar = ft.AlertDialog(
                title=ft.Text("Exportar Servidores", size=20, weight=ft.FontWeight.BOLD),
                content=ft.Column(
                    [
                        ft.Text("Escolha um nome para o arquivo de exportação:"),
                        ft.Container(height=10),
                        nome_arquivo_input,
                    ],
                    width=400,
                    height=150,
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: setattr(dialogo_exportar, "open", False)),
                    ft.TextButton(
                        "Exportar", 
                        on_click=confirmar_exportacao,
                        style=ft.ButtonStyle(color=ft.colors.BLUE_500),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            # Exibe o diálogo
            page.dialog = dialogo_exportar
            dialogo_exportar.open = True
            page.update()
        
        # Função para importar servidores
        def importar_servidores_dialog():
            # Cria um diálogo para escolher o arquivo
            caminho_arquivo_input = ft.TextField(
                label="Caminho do arquivo",
                border=ft.InputBorder.OUTLINE,
                expand=True,
                hint_text="Ex: servidores.json",
            )
            
            def confirmar_importacao(e):
                caminho = caminho_arquivo_input.value
                
                if not caminho:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text("Por favor, informe o caminho do arquivo."),
                        bgcolor=ft.colors.RED_500,
                    )
                    page.snack_bar.open = True
                    page.update()
                    return
                
                sucesso, mensagem = importar_servidores(caminho)
                
                # Fecha o diálogo de importação
                dialogo_importar.open = False
                
                # Fecha o diálogo de gerenciar servidores
                dialogo_gerenciar.open = False
                page.update()
                
                # Exibe mensagem de sucesso ou erro
                if sucesso:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(mensagem),
                        bgcolor=ft.colors.GREEN_500,
                    )
                    # Reabre o diálogo de gerenciar servidores atualizado
                    page.update()
                    abrir_dialogo_gerenciar_servidores()
                else:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Erro ao importar servidores: {mensagem}"),
                        bgcolor=ft.colors.RED_500,
                    )
                
                page.snack_bar.open = True
                page.update()
            
            dialogo_importar = ft.AlertDialog(
                title=ft.Text("Importar Servidores", size=20, weight=ft.FontWeight.BOLD),
                content=ft.Column(
                    [
                        ft.Text("Informe o caminho do arquivo JSON com a lista de servidores:"),
                        ft.Container(height=10),
                        caminho_arquivo_input,
                        ft.Container(height=10),
                        ft.Text(
                            "O arquivo deve conter uma lista de objetos com pelo menos os campos 'nome' e 'ip'.",
                            size=12,
                            color=ft.colors.GREY_700,
                        ),
                    ],
                    width=400,
                    height=150,
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: setattr(dialogo_importar, "open", False)),
                    ft.TextButton(
                        "Importar", 
                        on_click=confirmar_importacao,
                        style=ft.ButtonStyle(color=ft.colors.BLUE_500),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            # Exibe o diálogo
            page.dialog = dialogo_importar
            dialogo_importar.open = True
            page.update()
        
        # Cria o diálogo
        dialogo_gerenciar = ft.AlertDialog(
            title=ft.Text("Gerenciar Servidores", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Text("Adicione, edite ou remova servidores da lista."),
                    ft.Container(height=10),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                text="Importar Servidores",
                                icon=ft.icons.UPLOAD_FILE,
                                on_click=lambda e: importar_servidores_dialog(),
                                style=ft.ButtonStyle(
                                    bgcolor=ft.colors.GREEN_700,
                                    color=ft.colors.WHITE,
                                ),
                            ),
                            ft.ElevatedButton(
                                text="Exportar Servidores",
                                icon=ft.icons.DOWNLOAD,
                                on_click=lambda e: exportar_servidores_dialog(),
                                style=ft.ButtonStyle(
                                    bgcolor=ft.colors.BLUE_700,
                                    color=ft.colors.WHITE,
                                ),
                            ),
                            ft.ElevatedButton(
                                text="Adicionar Servidor",
                                icon=ft.icons.ADD,
                                on_click=lambda e: abrir_dialogo_adicionar_servidor(dialogo_gerenciar),
                                style=ft.ButtonStyle(
                                    bgcolor=ft.colors.BLUE_500,
                                    color=ft.colors.WHITE,
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=10,
                        wrap=True,  # Permite quebra de linha em telas pequenas
                    ),
                    ft.Container(height=10),
                    lista_servidores_dialogo,
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                width=700,  # Aumentado para acomodar os novos botões
                height=500,
            ),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: setattr(dialogo_gerenciar, "open", False)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Preenche a lista com os servidores
        for servidor in lista_de_servidores:
            lista_servidores_dialogo.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        servidor["nome"],
                                        weight=ft.FontWeight.BOLD,
                                        size=16,
                                    ),
                                    ft.Text(
                                        servidor["ip"],
                                        size=14,
                                        color=ft.colors.GREY_700,
                                    ),
                                    ft.Text(
                                        servidor.get("descricao", "Sem descrição"),
                                        size=12,
                                        color=ft.colors.GREY_600,
                                        italic=not servidor.get("descricao"),
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    # Mostra as portas configuradas
                                    ft.Row(
                                        [
                                            ft.Text(
                                                f"Portas: {', '.join([str(p['porta']) for p in servidor.get('portas', [])])}",
                                                size=12,
                                                color=ft.colors.BLUE_500,
                                            ) if servidor.get("portas") else ft.Text(
                                                "Sem portas configuradas",
                                                size=12,
                                                color=ft.colors.GREY_500,
                                                italic=True,
                                            )
                                        ]
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.EDIT,
                                        icon_color=ft.colors.BLUE_500,
                                        tooltip="Editar servidor",
                                        on_click=lambda e, srv=servidor: abrir_dialogo_editar_servidor(srv, dialogo_gerenciar),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.DELETE,
                                        icon_color=ft.colors.RED_500,
                                        tooltip="Remover servidor",
                                        on_click=lambda e, srv=servidor: confirmar_remocao_servidor(srv, dialogo_gerenciar),
                                    ),
                                ],
                                spacing=5,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=15,
                    bgcolor=ft.colors.WHITE,
                    border_radius=8,
                    border=ft.border.all(1, ft.colors.GREY_300),
                    shadow=ft.BoxShadow(blur_radius=2, spread_radius=1, color=ft.colors.GREY_200),
                )
            )
        
        # Exibe o diálogo
        page.dialog = dialogo_gerenciar
        dialogo_gerenciar.open = True
        page.update()

    def abrir_dialogo_adicionar_servidor(dialogo_pai=None):
        """Abre o diálogo para adicionar um novo servidor."""
        # Campos do formulário
        nome_input = ft.TextField(
            label="Nome do Servidor",
            border=ft.InputBorder.OUTLINE,
            expand=True,
        )
        
        ip_input = ft.TextField(
            label="Endereço IP",
            border=ft.InputBorder.OUTLINE,
            expand=True,
        )
        
        ip_unidade_input = ft.TextField(
            label="IP da Unidade (opcional)",
            border=ft.InputBorder.OUTLINE,
            expand=True,
            hint_text="Se diferente do IP do servidor",
        )
        
        descricao_input = ft.TextField(
            label="Descrição",
            border=ft.InputBorder.OUTLINE,
            expand=True,
            multiline=True,
            min_lines=3,
            max_lines=5,
            hint_text="Adicione uma descrição para este servidor",
        )
        
        tags_input = ft.TextField(
            label="Tags (separadas por vírgula)",
            border=ft.InputBorder.OUTLINE,
            expand=True,
            hint_text="Ex: Produção, Crítico, Backup",
        )
        
        # Nova seção para portas
        portas_container = ft.Column(
            controls=[],
            spacing=5,
        )
        
        # Container para mostrar o status das portas
        status_portas_container = ft.Column(
            controls=[],
            spacing=5,
            visible=False,  # Inicialmente oculto
        )
        
        # Lista para armazenar as portas adicionadas
        portas_adicionadas = []
        
        # Função para adicionar um novo campo de porta
        def adicionar_campo_porta():
            # Campos para porta e descrição
            porta_input = ft.TextField(
                label="Porta",
                border=ft.InputBorder.OUTLINE,
                width=100,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            
            descricao_porta_input = ft.TextField(
                label="Descrição",
                border=ft.InputBorder.OUTLINE,
                expand=True,
                hint_text="Ex: HTTP, SSH, Banco de Dados",
            )
            
            # Botão para remover este campo
            def remover_campo():
                # Encontra o índice do campo na lista
                for i, controle in enumerate(portas_container.controls):
                    if controle == campo_container:
                        portas_container.controls.pop(i)
                        portas_adicionadas.pop(i)
                        break
                
                portas_container.update()
            
            botao_remover = ft.IconButton(
                icon=ft.icons.DELETE,
                icon_color=ft.colors.RED_500,
                tooltip="Remover porta",
                on_click=lambda e: remover_campo(),
            )
            
            # Container para agrupar os campos
            campo_container = ft.Row(
                [
                    porta_input,
                    descricao_porta_input,
                    botao_remover,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            
            # Adiciona o container à lista de portas
            portas_container.controls.append(campo_container)
            portas_adicionadas.append({"input": porta_input, "descricao": descricao_porta_input})
            portas_container.update()
        
        # Botão para adicionar porta
        botao_adicionar_porta = ft.ElevatedButton(
            text="Adicionar Porta",
            icon=ft.icons.ADD,
            on_click=lambda e: adicionar_campo_porta(),
            style=ft.ButtonStyle(
                bgcolor=ft.colors.BLUE_500,
                color=ft.colors.WHITE,
            ),
        )
        
        # Função para verificar as portas adicionadas
        def verificar_portas_adicionadas(e):
            # Limpa o container de status
            status_portas_container.controls.clear()
            
            # Verifica se há portas para verificar
            if not portas_adicionadas:
                status_portas_container.controls.append(
                    ft.Text("Nenhuma porta adicionada para verificar.", color=ft.colors.GREY_700)
                )
                status_portas_container.visible = True
                status_portas_container.update()
                return
            
            # Verifica se o IP foi informado
            if not ip_input.value:
                status_portas_container.controls.append(
                    ft.Text("Informe o IP do servidor para verificar as portas.", color=ft.colors.RED_500)
                )
                status_portas_container.visible = True
                status_portas_container.update()
                return
            
            # Adiciona um indicador de carregamento
            status_portas_container.controls.append(
                ft.Text("Verificando portas...", color=ft.colors.BLUE_500)
            )
            status_portas_container.visible = True
            status_portas_container.update()
            
            # Função para verificar as portas em segundo plano
            def verificar_portas_thread():
                # Obtém o IP do servidor
                ip = ip_input.value
                
                # Limpa o container de status
                status_portas_container.controls.clear()
                
                # Verifica cada porta
                for porta_info in portas_adicionadas:
                    porta_valor = porta_info["input"].value
                    descricao_valor = porta_info["descricao"].value
                    
                    if porta_valor:
                        try:
                            porta = int(porta_valor)
                            # Verifica se a porta está aberta
                            porta_aberta = verificar_porta(ip, porta)
                            
                            # Define a cor do indicador de status
                            porta_color = ft.colors.GREEN_500 if porta_aberta else ft.colors.RED_500
                            porta_status_text = f"{descricao_valor if descricao_valor else f'Porta {porta}'}: " + ("Aberta" if porta_aberta else "Fechada")
                            
                            # Adiciona o indicador de status da porta
                            status_portas_container.controls.append(
                                ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.Icon(name=ft.icons.CIRCLE, color=porta_color, size=12),
                                            ft.Text(porta_status_text, size=14, color=porta_color),
                                        ],
                                        spacing=5,
                                    ),
                                    padding=5,
                                    border_radius=10,
                                    bgcolor=ft.colors.WHITE,
                                    border=ft.border.all(1, ft.colors.GREY_300),
                                    margin=ft.margin.only(bottom=5),
                                )
                            )
                        except ValueError:
                            # Ignora portas inválidas
                            status_portas_container.controls.append(
                                ft.Text(f"Porta inválida: {porta_valor}", color=ft.colors.RED_500)
                            )
                
                # Se não houver portas válidas
                if not status_portas_container.controls:
                    status_portas_container.controls.append(
                        ft.Text("Nenhuma porta válida para verificar.", color=ft.colors.GREY_700)
                    )
                
                status_portas_container.update()
            
            # Inicia a verificação em uma thread separada
            thread = threading.Thread(target=verificar_portas_thread)
            thread.daemon = True
            thread.start()
        
        # Botão para verificar portas
        botao_verificar_portas = ft.ElevatedButton(
            text="Verificar Portas",
            icon=ft.icons.SETTINGS_ETHERNET,
            on_click=verificar_portas_adicionadas,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN_700,
                color=ft.colors.WHITE,
            ),
        )
        
        # Função para adicionar o servidor
        def adicionar_servidor(e):
            # Validação básica
            if not nome_input.value or not ip_input.value:
                # Exibe mensagem de erro
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Nome e IP são obrigatórios!"),
                    bgcolor=ft.colors.RED_500,
                )
                page.snack_bar.open = True
                page.update()
                return
            
            # Cria o novo servidor
            novo_servidor = {
                "nome": nome_input.value,
                "ip": ip_input.value,
            }
            
            # Adiciona IP da unidade se fornecido
            if ip_unidade_input.value:
                novo_servidor["ip_unidade"] = ip_unidade_input.value
            
            # Adiciona descrição se fornecida
            if descricao_input.value:
                novo_servidor["descricao"] = descricao_input.value
            
            # Adiciona tags se fornecidas
            if tags_input.value:
                novo_servidor["tags"] = [tag.strip() for tag in tags_input.value.split(",") if tag.strip()]
            else:
                novo_servidor["tags"] = []
            
            # Adiciona portas se fornecidas
            portas = []
            for porta_info in portas_adicionadas:
                porta_valor = porta_info["input"].value
                descricao_valor = porta_info["descricao"].value
                
                if porta_valor:
                    try:
                        porta = int(porta_valor)
                        porta_item = {
                            "porta": porta,
                            "descricao": descricao_valor if descricao_valor else f"Porta {porta}"
                        }
                        portas.append(porta_item)
                    except ValueError:
                        # Ignora portas inválidas
                        pass
            
            if portas:
                novo_servidor["portas"] = portas
            
            # Adiciona o servidor à lista
            lista_de_servidores.append(novo_servidor)
            
            # Salva os servidores personalizados
            salvar_servidores_personalizados()
            
            # Fecha o diálogo
            dialogo_adicionar.open = False
            
            # Se houver um diálogo pai, fecha-o também e reabre atualizado
            if dialogo_pai:
                dialogo_pai.open = False
                page.update()
                abrir_dialogo_gerenciar_servidores()
            else:
                # Atualiza a lista de servidores
                atualizar_lista_servidores(None)
                
                # Exibe mensagem de sucesso
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Servidor adicionado com sucesso!"),
                    bgcolor=ft.colors.GREEN_500,
                )
                page.snack_bar.open = True
                page.update()
        
        # Cria o diálogo
        dialogo_adicionar = ft.AlertDialog(
            title=ft.Text("Adicionar Servidor", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    nome_input,
                    ft.Container(height=10),
                    ip_input,
                    ft.Container(height=10),
                    ip_unidade_input,
                    ft.Container(height=10),
                    descricao_input,
                    ft.Container(height=10),
                    tags_input,
                    ft.Container(height=20),
                    ft.Divider(),
                    ft.Text("Portas para monitorar:", weight=ft.FontWeight.BOLD),
                    ft.Container(height=5),
                    portas_container,
                    ft.Container(height=5),
                    ft.Row(
                        [
                            botao_adicionar_porta,
                            botao_verificar_portas,  # Novo botão para verificar portas
                        ],
                        spacing=10,
                    ),
                    ft.Container(height=10),
                    # Container para mostrar o status das portas
                    status_portas_container,
                ],
                width=500,
                height=500,
                scroll=ft.ScrollMode.AUTO,
                spacing=5,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dialogo_adicionar, "open", False)),
                ft.TextButton(
                    "Adicionar", 
                    on_click=adicionar_servidor,
                    style=ft.ButtonStyle(color=ft.colors.BLUE_500),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        page.dialog = dialogo_adicionar
        dialogo_adicionar.open = True
        page.update()

    def abrir_dialogo_editar_servidor(servidor, dialogo_pai=None):
        """Abre o diálogo para editar um servidor existente."""
        # Campos do formulário preenchidos com os dados do servidor
        nome_input = ft.TextField(
            label="Nome do Servidor",
            value=servidor["nome"],
            border=ft.InputBorder.OUTLINE,
            expand=True,
        )
        
        ip_input = ft.TextField(
            label="Endereço IP",
            value=servidor["ip"],
            border=ft.InputBorder.OUTLINE,
            expand=True,
        )
        
        ip_unidade_input = ft.TextField(
            label="IP da Unidade (opcional)",
            value=servidor.get("ip_unidade", ""),
            border=ft.InputBorder.OUTLINE,
            expand=True,
            hint_text="Se diferente do IP do servidor",
        )
        
        descricao_input = ft.TextField(
            label="Descrição",
            value=servidor.get("descricao", ""),
            border=ft.InputBorder.OUTLINE,
            expand=True,
            multiline=True,
            min_lines=3,
            max_lines=5,
            hint_text="Adicione uma descrição para este servidor",
        )
        
        tags_input = ft.TextField(
            label="Tags (separadas por vírgula)",
            value=", ".join(servidor.get("tags", [])),
            border=ft.InputBorder.OUTLINE,
            expand=True,
            hint_text="Ex: Produção, Crítico, Backup",
        )
        
        # Nova seção para portas
        portas_container = ft.Column(
            controls=[],
            spacing=5,
        )
        
        # Container para mostrar o status das portas
        status_portas_container = ft.Column(
            controls=[],
            spacing=5,
            visible=False,  # Inicialmente oculto
        )
        
        # Lista para armazenar as portas adicionadas
        portas_adicionadas = []
        
        # Função para adicionar um novo campo de porta
        def adicionar_campo_porta(porta_valor=None, descricao_valor=None):
            # Campos para porta e descrição
            porta_input = ft.TextField(
                label="Porta",
                value=str(porta_valor) if porta_valor is not None else "",
                border=ft.InputBorder.OUTLINE,
                width=100,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            
            descricao_porta_input = ft.TextField(
                label="Descrição",
                value=descricao_valor if descricao_valor is not None else "",
                border=ft.InputBorder.OUTLINE,
                expand=True,
                hint_text="Ex: HTTP, SSH, Banco de Dados",
            )
            
            # Botão para remover este campo
            def remover_campo():
                # Encontra o índice do campo na lista
                for i, controle in enumerate(portas_container.controls):
                    if controle == campo_container:
                        portas_container.controls.pop(i)
                        portas_adicionadas.pop(i)
                        break
                
                portas_container.update()
            
            botao_remover = ft.IconButton(
                icon=ft.icons.DELETE,
                icon_color=ft.colors.RED_500,
                tooltip="Remover porta",
                on_click=lambda e: remover_campo(),
            )
            
            # Container para agrupar os campos
            campo_container = ft.Row(
                [
                    porta_input,
                    descricao_porta_input,
                    botao_remover,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            
            # Adiciona o container à lista de portas
            portas_container.controls.append(campo_container)
            portas_adicionadas.append({"input": porta_input, "descricao": descricao_porta_input})
            portas_container.update()
        
        # Adiciona as portas existentes
        for porta_info in servidor.get("portas", []):
            adicionar_campo_porta(porta_info["porta"], porta_info.get("descricao", ""))
        
        # Botão para adicionar porta
        botao_adicionar_porta = ft.ElevatedButton(
            text="Adicionar Porta",
            icon=ft.icons.ADD,
            on_click=lambda e: adicionar_campo_porta(),
            style=ft.ButtonStyle(
                bgcolor=ft.colors.BLUE_500,
                color=ft.colors.WHITE,
            ),
        )
        
        # Função para verificar as portas adicionadas
        def verificar_portas_adicionadas(e):
            # Limpa o container de status
            status_portas_container.controls.clear()
            
            # Verifica se há portas para verificar
            if not portas_adicionadas:
                status_portas_container.controls.append(
                    ft.Text("Nenhuma porta adicionada para verificar.", color=ft.colors.GREY_700)
                )
                status_portas_container.visible = True
                status_portas_container.update()
                return
            
            # Adiciona um indicador de carregamento
            status_portas_container.controls.append(
                ft.Text("Verificando portas...", color=ft.colors.BLUE_500)
            )
            status_portas_container.visible = True
            status_portas_container.update()
            
            # Função para verificar as portas em segundo plano
            def verificar_portas_thread():
                # Obtém o IP do servidor
                ip = ip_input.value
                
                # Limpa o container de status
                status_portas_container.controls.clear()
                
                # Verifica cada porta
                for porta_info in portas_adicionadas:
                    porta_valor = porta_info["input"].value
                    descricao_valor = porta_info["descricao"].value
                    
                    if porta_valor:
                        try:
                            porta = int(porta_valor)
                            # Verifica se a porta está aberta
                            porta_aberta = verificar_porta(ip, porta)
                            
                            # Define a cor do indicador de status
                            porta_color = ft.colors.GREEN_500 if porta_aberta else ft.colors.RED_500
                            porta_status_text = f"{descricao_valor if descricao_valor else f'Porta {porta}'}: " + ("Aberta" if porta_aberta else "Fechada")
                            
                            # Adiciona o indicador de status da porta
                            status_portas_container.controls.append(
                                ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.Icon(name=ft.icons.CIRCLE, color=porta_color, size=12),
                                            ft.Text(porta_status_text, size=14, color=porta_color),
                                        ],
                                        spacing=5,
                                    ),
                                    padding=5,
                                    border_radius=10,
                                    bgcolor=ft.colors.WHITE,
                                    border=ft.border.all(1, ft.colors.GREY_300),
                                    margin=ft.margin.only(bottom=5),
                                )
                            )
                        except ValueError:
                            # Ignora portas inválidas
                            status_portas_container.controls.append(
                                ft.Text(f"Porta inválida: {porta_valor}", color=ft.colors.RED_500)
                            )
                
                # Se não houver portas válidas
                if not status_portas_container.controls:
                    status_portas_container.controls.append(
                        ft.Text("Nenhuma porta válida para verificar.", color=ft.colors.GREY_700)
                    )
                
                status_portas_container.update()
            
            # Inicia a verificação em uma thread separada
            thread = threading.Thread(target=verificar_portas_thread)
            thread.daemon = True
            thread.start()
        
        # Botão para verificar portas
        botao_verificar_portas = ft.ElevatedButton(
            text="Verificar Portas",
            icon=ft.icons.SETTINGS_ETHERNET,
            on_click=verificar_portas_adicionadas,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN_700,
                color=ft.colors.WHITE,
            ),
        )
        
        # Função para salvar as alterações
        def salvar_alteracoes(e):
            # Validação básica
            if not nome_input.value or not ip_input.value:
                # Exibe mensagem de erro
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Nome e IP são obrigatórios!"),
                    bgcolor=ft.colors.RED_500,
                )
                page.snack_bar.open = True
                page.update()
                return
            
            # Atualiza os dados do servidor
            ip_antigo = servidor["ip"]  # Guarda o IP antigo para identificar o servidor
            
            # Atualiza os campos
            servidor["nome"] = nome_input.value
            servidor["ip"] = ip_input.value
            
            # Atualiza IP da unidade
            if ip_unidade_input.value:
                servidor["ip_unidade"] = ip_unidade_input.value
            elif "ip_unidade" in servidor:
                del servidor["ip_unidade"]
            
            # Atualiza descrição
            if descricao_input.value:
                servidor["descricao"] = descricao_input.value
            elif "descricao" in servidor:
                del servidor["descricao"]
            
            # Atualiza tags
            if tags_input.value:
                servidor["tags"] = [tag.strip() for tag in tags_input.value.split(",") if tag.strip()]
            else:
                servidor["tags"] = []
            
            # Atualiza portas
            portas = []
            for porta_info in portas_adicionadas:
                porta_valor = porta_info["input"].value
                descricao_valor = porta_info["descricao"].value
                
                if porta_valor:
                    try:
                        porta = int(porta_valor)
                        porta_item = {
                            "porta": porta,
                            "descricao": descricao_valor if descricao_valor else f"Porta {porta}"
                        }
                        portas.append(porta_item)
                    except ValueError:
                        # Ignora portas inválidas
                        pass
            
            if portas:
                servidor["portas"] = portas
            elif "portas" in servidor:
                del servidor["portas"]
            
            # Atualiza favoritos se o IP mudou
            if ip_antigo != servidor["ip"] and ip_antigo in favoritos:
                favoritos.remove(ip_antigo)
                favoritos.append(servidor["ip"])
                try:
                    page.client_storage.set("favoritos", favoritos)
                except AttributeError:
                    pass
            
            # Salva os servidores personalizados
            salvar_servidores_personalizados()
            
            # Fecha o diálogo
            dialogo_editar.open = False
            
            # Se houver um diálogo pai, fecha-o também e reabre atualizado
            if dialogo_pai:
                dialogo_pai.open = False
                page.update()
                abrir_dialogo_gerenciar_servidores()
            else:
                # Atualiza a lista de servidores
                atualizar_lista_servidores(None)
                
                # Exibe mensagem de sucesso
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Servidor atualizado com sucesso!"),
                    bgcolor=ft.colors.GREEN_500,
                )
                page.snack_bar.open = True
                page.update()
        
        # Cria o diálogo
        dialogo_editar = ft.AlertDialog(
            title=ft.Text("Editar Servidor", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    nome_input,
                    ft.Container(height=10),
                    ip_input,
                    ft.Container(height=10),
                    ip_unidade_input,
                    ft.Container(height=10),
                    descricao_input,
                    ft.Container(height=10),
                    tags_input,
                    ft.Container(height=20),
                    ft.Divider(),
                    ft.Text("Portas para monitorar:", weight=ft.FontWeight.BOLD),
                    ft.Container(height=5),
                    portas_container,
                    ft.Container(height=5),
                    ft.Row(
                        [
                            botao_adicionar_porta,
                            botao_verificar_portas,  # Novo botão para verificar portas
                        ],
                        spacing=10,
                    ),
                    ft.Container(height=10),
                    # Container para mostrar o status das portas
                    status_portas_container,
                ],
                width=500,
                height=500,
                scroll=ft.ScrollMode.AUTO,
                spacing=5,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dialogo_editar, "open", False)),
                ft.TextButton(
                    "Salvar", 
                    on_click=salvar_alteracoes,
                    style=ft.ButtonStyle(color=ft.colors.BLUE_500),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        page.dialog = dialogo_editar
        dialogo_editar.open = True
        page.update()

    def confirmar_remocao_servidor(servidor, dialogo_pai=None):
        """Exibe um diálogo de confirmação para remover um servidor."""
        # Função para remover o servidor
        def remover_servidor(e):
            # Remove o servidor da lista
            lista_de_servidores.remove(servidor)
            
            # Remove dos favoritos se estiver lá
            if servidor["ip"] in favoritos:
                favoritos.remove(servidor["ip"])
                try:
                    page.client_storage.set("favoritos", favoritos)
                except AttributeError:
                    pass
            
            # Salva os servidores personalizados
            salvar_servidores_personalizados()
            
            # Fecha o diálogo
            dialogo_confirmar.open = False
            
            # Se houver um diálogo pai, fecha-o também e reabre atualizado
            if dialogo_pai:
                dialogo_pai.open = False
                page.update()
                abrir_dialogo_gerenciar_servidores()
            else:
                # Atualiza a lista de servidores
                atualizar_lista_servidores(None)
                
                # Exibe mensagem de sucesso
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Servidor removido com sucesso!"),
                    bgcolor=ft.colors.GREEN_500,
                )
                page.snack_bar.open = True
                page.update()
        
        # Cria o diálogo
        dialogo_confirmar = ft.AlertDialog(
            title=ft.Text("Confirmar Remoção", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.RED),
            content=ft.Column(
                [
                    ft.Text(f"Tem certeza que deseja remover o servidor:"),
                    ft.Container(height=10),
                    ft.Text(f"Nome: {servidor['nome']}", weight=ft.FontWeight.BOLD),
                    ft.Text(f"IP: {servidor['ip']}"),
                    ft.Container(height=10),
                    ft.Text("Esta ação não pode ser desfeita!", color=ft.colors.RED),
                ],
                width=400,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dialogo_confirmar, "open", False)),
                ft.TextButton(
                    "Remover", 
                    on_click=remover_servidor, 
                    style=ft.ButtonStyle(color=ft.colors.RED_500)
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        page.dialog = dialogo_confirmar
        dialogo_confirmar.open = True
        page.update()

    # Campo de pesquisa estilizado
    pesquisa_input = ft.TextField(
        hint_text="🔍 Pesquisar por nome, IP, tag ou descrição...",
        on_change=atualizar_lista_servidores,
        expand=True,
        autofocus=True,
        bgcolor=ft.colors.WHITE,
        border_radius=12,
        border=ft.InputBorder.OUTLINE,
        border_color=ft.colors.BLUE_400,
        height=50,
        prefix_icon=ft.icons.SEARCH,
    )

    # Botão para alternar entre todos os servidores e favoritos
    botao_favoritos = ft.IconButton(
        icon=ft.icons.STAR_BORDER,
        icon_color=ft.colors.AMBER_500,
        bgcolor=ft.colors.WHITE,
        tooltip="Mostrar apenas favoritos",
        on_click=alternar_visualizacao_favoritos,
    )

    # Botão para alternar modo claro/escuro
    botao_tema = ft.IconButton(
        icon=ft.icons.DARK_MODE,
        icon_color=ft.colors.GREY_700,
        bgcolor=ft.colors.WHITE,
        tooltip="Alternar modo escuro",
        on_click=lambda e: alternar_tema(e),
    )

    # Controles de paginação
    controles_paginacao = ft.Row(
        controls=[],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=5,
    )

    def alternar_tema(e):
        """Alterna entre modo claro e escuro."""
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
            botao_tema.icon = ft.icons.LIGHT_MODE
            botao_tema.icon_color = ft.colors.YELLOW_500
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            botao_tema.icon = ft.icons.DARK_MODE
            botao_tema.icon_color = ft.colors.GREY_700
       
        page.update()

    # Contador de servidores
    contador = ft.Text(
        f"{len(lista_de_servidores)} servidores",
        color=ft.colors.GREY_700,
        size=12,
    )

    # Container para o contador
    container_contador = ft.Container(
        content=contador,
        padding=ft.padding.only(left=10, right=10),
        bgcolor=ft.colors.GREY_200,
        border_radius=10,
        height=30,
        alignment=ft.alignment.center,
    )

    # Controle para ajustar itens por página
    def alterar_itens_por_pagina(e):
        nonlocal itens_por_pagina
        itens_por_pagina = int(e.control.value)
        ir_para_pagina(1)  # Volta para a primeira página ao alterar itens por página

    dropdown_itens_por_pagina = ft.Dropdown(
        width=100,
        options=[
            ft.dropdown.Option("5"),
            ft.dropdown.Option("10"),
            ft.dropdown.Option("20"),
            ft.dropdown.Option("50"),
        ],
        value="10",
        on_change=alterar_itens_por_pagina,
        label="Itens",
    )

    # Lista de servidores com rolagem ativada
    lista_servidores = ft.ListView(
        expand=True,
        spacing=10,
        auto_scroll=False,  # Impede rolagem automática ao atualizar
        height=800,  # Define uma altura fixa para ativar a rolagem
    )

    # Preenche a lista com servidores
    for servidor in lista_de_servidores:
        lista_servidores.controls.append(criar_linha_servidor(servidor))

    # Layout principal
    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.ResponsiveRow(
                        [
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Icon(ft.icons.DNS, color=ft.colors.BLUE_500, size=32),
                                            ft.Text(
                                                "Monitoramento de Servidores do PACS", 
                                                size=24, 
                                                weight=ft.FontWeight.BOLD,
                                                no_wrap=False,
                                                max_lines=2,
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.START,
                                        wrap=True,
                                    ),
                                ],
                                col={"sm": 12, "md": 6, "lg": 6, "xl": 6},
                            ),
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            botao_gerenciar_servidores,  # Botão para gerenciar servidores
                                            botao_visualizacao,  # Botão para alternar entre lista e grade
                                            botao_verificar_status,  # Botão para verificar status de todos os servidores
                                            botao_verificar_portas,  # Botão para verificar portas de todos os servidores
                                            botao_favoritos,  # Botão para mostrar favoritos
                                            botao_tema,  # Botão para alternar tema
                                        ],
                                        alignment=ft.MainAxisAlignment.END,
                                        spacing=10,
                                        wrap=True,  # Permite quebra de linha em telas pequenas
                                    ),
                                ],
                                col={"sm": 12, "md": 6, "lg": 6, "xl": 6},
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.ResponsiveRow(
                        [
                            ft.Column(
                                [
                                    pesquisa_input,
                                ],
                                col={"sm": 12, "md": 8, "lg": 9, "xl": 10},
                            ),
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            dropdown_itens_por_pagina,  # Dropdown para itens por página
                                            container_contador,  # Contador de servidores
                                        ],
                                        spacing=10,
                                        alignment=ft.MainAxisAlignment.END,
                                    ),
                                ],
                                col={"sm": 12, "md": 4, "lg": 3, "xl": 2},
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Divider(height=1, color=ft.colors.GREY_400),
                    lista_servidores,  # Apenas o ListView tem a rolagem ativada
                    controles_paginacao,  # Controles de navegação entre páginas
                ],
                expand=True,
                spacing=15,
            ),
            padding=20,
            border_radius=12,
            bgcolor=ft.colors.WHITE,
            shadow=ft.BoxShadow(blur_radius=10, spread_radius=2, color=ft.colors.GREY_400),
            expand=True,  # Permite que o container se expanda para preencher o espaço disponível
        )
    )

    # Inicializa os controles de paginação
    atualizar_controles_paginacao()

    # Inicia a verificação de status ao carregar a aplicação
    iniciar_verificacao_status()

ft.app(target=main)
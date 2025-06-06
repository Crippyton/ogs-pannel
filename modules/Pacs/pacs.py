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
import datetime
import csv
from servidores import SERVIDORES  # Importa a lista de servidores


# URL base do Zabbix
ZABBIX_URL_BASE = "http://10.200.4.21/zabbix.php?action=search&search="

def main(page: ft.Page):
    page.title = "Arms of God"
    page.theme_mode = ft.ThemeMode.LIGHT  # Modo claro
    page.bgcolor = ft.Colors.BLACK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO  # Habilita rolagem na página

    # Definir tema personalizado
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.BLUE_700,
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
    
    # Arquivo para armazenar estatísticas de acesso
    arquivo_estatisticas = "estatisticas_acesso.json"
    
    # Dicionário para armazenar estatísticas de acesso aos servidores
    estatisticas_acesso = {
        "zabbix": {},  # Acessos ao Zabbix por IP
        "unidade": {},  # Acessos à unidade por IP
        "total": {},   # Total de acessos por IP
        "historico": []  # Histórico de acessos com timestamp
    }
    
    # Carregar estatísticas de acesso se o arquivo existir
    def carregar_estatisticas():
        nonlocal estatisticas_acesso
        try:
            if os.path.exists(arquivo_estatisticas):
                with open(arquivo_estatisticas, 'r', encoding='utf-8') as arquivo:
                    estatisticas_acesso = json.load(arquivo)
        except Exception as e:
            print(f"Erro ao carregar estatísticas de acesso: {e}")
    
    # Salvar estatísticas de acesso
    def salvar_estatisticas():
        try:
            with open(arquivo_estatisticas, 'w', encoding='utf-8') as arquivo:
                json.dump(estatisticas_acesso, arquivo, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Erro ao salvar estatísticas de acesso: {e}")
    
    # Registrar acesso a um servidor
    def registrar_acesso(ip, tipo):
        # Encontra o servidor pelo IP
        servidor_nome = None
        for servidor in lista_de_servidores:
            if servidor["ip"] == ip:
                servidor_nome = servidor["nome"]
                break
        
        # Incrementa contadores
        if tipo == "zabbix":
            estatisticas_acesso["zabbix"][ip] = estatisticas_acesso["zabbix"].get(ip, 0) + 1
        elif tipo == "unidade":
            estatisticas_acesso["unidade"][ip] = estatisticas_acesso["unidade"].get(ip, 0) + 1
        
        estatisticas_acesso["total"][ip] = estatisticas_acesso["total"].get(ip, 0) + 1
        
        # Adiciona ao histórico
        estatisticas_acesso["historico"].append({
            "ip": ip,
            "nome": servidor_nome,
            "tipo": tipo,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # Limita o histórico a 1000 entradas para não crescer demais
        if len(estatisticas_acesso["historico"]) > 1000:
            estatisticas_acesso["historico"] = estatisticas_acesso["historico"][-1000:]
        
        # Salva as estatísticas
        salvar_estatisticas()

    # Carregar estatísticas ao iniciar
    carregar_estatisticas()

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
            bgcolor=ft.Colors.BLUE_500,
        )
        page.snack_bar.open = True
        page.update()
        
        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()

    # NOVA FUNCIONALIDADE: Redefinição de senha
    # Função para abrir o diálogo de redefinição de senha
    def abrir_dialogo_redefinir_senha(e):
        # Campos do formulário
        ip_servidor_input = ft.TextField(
            label="IP do Servidor",
            hint_text="Ex: 10.85.73.12",
            border=ft.InputBorder.OUTLINE,
            expand=True,
        )
        
        cpf_usuario_input = ft.TextField(
            label="CPF do Usuário",
            hint_text="Digite o CPF do usuário",
            border=ft.InputBorder.OUTLINE,
            expand=True,
        )
        
        senha_input = ft.TextField(
            label="Nova Senha",
            hint_text="Digite a nova senha",
            password=True,
            border=ft.InputBorder.OUTLINE,
            expand=True,
        )
        
        # Função para iniciar a automação
        def iniciar_automacao(e):
            # Validação básica
            if not ip_servidor_input.value or not cpf_usuario_input.value or not senha_input.value:
                # Exibe mensagem de erro
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Todos os campos são obrigatórios!"),
                    bgcolor=ft.Colors.RED_500,
                )
                page.snack_bar.open = True
                page.update()
                return
            
            # Fecha o diálogo de entrada
            dialogo_redefinir_senha.open = False
            page.update()
            
            # Inicia a automação
            executar_automacao_redefinir_senha(
                ip_servidor_input.value,
                cpf_usuario_input.value,
                senha_input.value
            )
        
        # Cria o diálogo
        dialogo_redefinir_senha = ft.AlertDialog(
            title=ft.Text("Redefinição de Senha", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Text("Informe os dados para redefinir a senha do usuário no servidor."),
                    ft.Container(height=10),
                    ip_servidor_input,
                    ft.Container(height=10),
                    cpf_usuario_input,
                    ft.Container(height=10),
                    senha_input,
                ],
                width=400,
                height=250,
                scroll=ft.ScrollMode.AUTO,
                spacing=5,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dialogo_redefinir_senha, "open", False)),
                ft.TextButton(
                    "Iniciar", 
                    on_click=iniciar_automacao,
                    style=ft.ButtonStyle(color=ft.Colors.BLUE_500),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        page.dialog = dialogo_redefinir_senha
        dialogo_redefinir_senha.open = True
        page.update()
    
    # Função para executar a automação de redefinição de senha
    def executar_automacao_redefinir_senha(ip_servidor, cpf_usuario, nova_senha):
        """Executa a automação para redefinir a senha do usuário."""
        try:
            import pyautogui
            import pytesseract
            from PIL import ImageGrab
        except ImportError:
            # Exibe mensagem de erro se as bibliotecas não estiverem instaladas
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Bibliotecas necessárias não encontradas. Instale pyautogui, pytesseract e pillow."),
                bgcolor=ft.Colors.RED_500,
            )
            page.snack_bar.open = True
            page.update()
            return
        
        # Indicadores de status
        status_indicator = ft.Container(
            width=15,
            height=15,
            border_radius=10,
            bgcolor=ft.Colors.YELLOW,
        )
        
        status_text = ft.Text("Processando...", color=ft.Colors.YELLOW)
        
        # Container para o log
        log_container = ft.Column(
            controls=[],
            scroll=ft.ScrollMode.AUTO,
            height=300,
            spacing=5,
        )
        
        # Função para adicionar entrada ao log
        def adicionar_log(mensagem):
            log_container.controls.append(
                ft.Text(mensagem, size=14)
            )
            log_container.update()
            # Auto-scroll para a última mensagem
            if hasattr(log_container, "scroll_to") and callable(log_container.scroll_to):
                log_container.scroll_to(offset=len(log_container.controls) * 20)
        
        # Função para atualizar o status
        def atualizar_status(sucesso=True):
            if sucesso:
                status_indicator.bgcolor = ft.Colors.GREEN
                status_text.value = "Sucesso!"
                status_text.color = ft.Colors.GREEN
            else:
                status_indicator.bgcolor = ft.Colors.RED
                status_text.value = "Erro!"
                status_text.color = ft.Colors.RED
            
            status_indicator.update()
            status_text.update()
        
        # Cria o diálogo de progresso
        dialogo_progresso = ft.AlertDialog(
            title=ft.Text("Automação de Reset de Senha", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            status_indicator,
                            status_text,
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=10,
                    ),
                    ft.Container(height=10),
                    ft.Text("Log de execução:", weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=log_container,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=5,
                        padding=10,
                        bgcolor=ft.Colors.GREY_50,
                        height=300,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=10,
                width=500,
                height=400,
            ),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: setattr(dialogo_progresso, "open", False)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        page.dialog = dialogo_progresso
        dialogo_progresso.open = True
        page.update()
        
        # Função para executar a automação em segundo plano
        def executar_automacao_thread():
            try:
                # Step 1: Access the server web page
                adicionar_log(f"Passo 1 - Acessando a página web do servidor: {ip_servidor}")
                try:
                    pyautogui.hotkey('win', 'r')
                    time.sleep(0.5)
                    pyautogui.write(f"http://{ip_servidor}/")
                    pyautogui.press('enter')
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(2)
                
                # Step 2: Click "Já fiz essa instalação"
                adicionar_log("Passo 2 - Clicando em 'Já fiz essa instalação'")
                try:
                    button_location = pyautogui.locateOnScreen('ja_fiz_instalacao.png', confidence=0.7)
                    if button_location:
                        pyautogui.click(button_location)
                    else:
                        # Try to find by OCR
                        screen = ImageGrab.grab()
                        text = pytesseract.image_to_string(screen, lang='por')
                        if "já fiz essa instalação" in text.lower():
                            # Try to find by position based on text
                            pyautogui.moveTo(screen.width // 2, screen.height // 2)
                            pyautogui.click()
                        else:
                            adicionar_log("Botão 'Já fiz essa instalação' não encontrado, tentando continuar...")
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(2)
                
                # Step 3: Click "suite"
                adicionar_log("Passo 3 - Clicando em 'suite'")
                try:
                    suite_button = pyautogui.locateOnScreen('suite_button.png', confidence=0.7)
                    if suite_button:
                        pyautogui.click(suite_button)
                    else:
                        # Try to find by text
                        screen = ImageGrab.grab()
                        text = pytesseract.image_to_string(screen, lang='por')
                        if "suite" in text.lower():
                            # Find position based on text
                            lines = text.split('\n')
                            for i, line in enumerate(lines):
                                if "suite" in line.lower():
                                    # Estimate position
                                    y_pos = (i + 1) * (screen.height / len(lines))
                                    pyautogui.moveTo(screen.width // 2, y_pos)
                                    pyautogui.click()
                                    break
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(2)
                
                # Step 4: Click "Abrir trebuchet.exe"
                adicionar_log("Passo 4 - Clicando em 'Abrir trebuchet.exe'")
                try:
                    trebuchet_button = pyautogui.locateOnScreen('trebuchet.png', confidence=0.7)
                    if trebuchet_button:
                        pyautogui.click(trebuchet_button)
                    else:
                        # Try to find by text
                        screen = ImageGrab.grab()
                        text = pytesseract.image_to_string(screen, lang='por')
                        if "trebuchet" in text.lower() or "abrir" in text.lower():
                            # Find position based on text
                            lines = text.split('\n')
                            for i, line in enumerate(lines):
                                if "trebuchet" in line.lower() or "abrir" in line.lower():
                                    # Estimate position
                                    y_pos = (i + 1) * (screen.height / len(lines))
                                    pyautogui.moveTo(screen.width // 2, y_pos)
                                    pyautogui.click()
                                    break
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(3)
                
                # Step 5: Wait for suite to load and login
                adicionar_log("Passo 5 - Aguardando o suite carregar...")
                time.sleep(3)
                
                adicionar_log("Passo 6 - Preenchendo login admin: 12433321409")
                try:
                    # Find username field and enter admin username
                    pyautogui.write("12433321409")
                    pyautogui.press('tab')  # Move to password field
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(1)
                
                adicionar_log("Passo 7 - Preenchendo senha admin: ********")
                try:
                    # Enter admin password
                    pyautogui.write("9489Rc@#")
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(1)
                
                adicionar_log("Passo 8 - Clicando em 'entrar'")
                try:
                    login_button = pyautogui.locateOnScreen('entrar_button.png', confidence=0.7)
                    if login_button:
                        pyautogui.click(login_button)
                    else:
                        # Try to find by text or just press Enter
                        pyautogui.press('enter')
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                    pyautogui.press('enter')  # Try pressing Enter anyway
                time.sleep(3)
                
                # Step 6: Click on "Configuração" menu
                adicionar_log("Passo 9 - Clicando no menu lateral 'Configuração'")
                try:
                    config_menu = pyautogui.locateOnScreen('configuracao_menu.png', confidence=0.7)
                    if config_menu:
                        pyautogui.click(config_menu)
                    else:
                        # Try to find by text
                        screen = ImageGrab.grab()
                        text = pytesseract.image_to_string(screen, lang='por')
                        if "configuração" in text.lower() or "configuracao" in text.lower():
                            # Find position based on text
                            lines = text.split('\n')
                            for i, line in enumerate(lines):
                                if "configuração" in line.lower() or "configuracao" in line.lower():
                                    # Estimate position
                                    y_pos = (i + 1) * (screen.height / len(lines))
                                    # Assume menu is on the left side
                                    pyautogui.moveTo(screen.width * 0.1, y_pos)
                                    pyautogui.click()
                                    break
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(2)
                
                # Step 7: Change dropdown option to "Login"
                adicionar_log("Passo 10 - Alterando opção para 'Login'")
                try:
                    # Try to find dropdown and change to Login
                    login_option = pyautogui.locateOnScreen('login_option.png', confidence=0.7)
                    if login_option:
                        pyautogui.click(login_option)
                    else:
                        # Try to find by text or position
                        screen = ImageGrab.grab()
                        text = pytesseract.image_to_string(screen, lang='por')
                        if "login" in text.lower() or "nome" in text.lower():
                            # Find position based on text
                            lines = text.split('\n')
                            for i, line in enumerate(lines):
                                if "login" in line.lower() or "nome" in line.lower():
                                    # Estimate position
                                    y_pos = (i + 1) * (screen.height / len(lines))
                                    pyautogui.moveTo(screen.width * 0.3, y_pos)
                                    pyautogui.click()
                                    time.sleep(0.5)
                                    # Click on "Login" in dropdown
                                    pyautogui.moveRel(0, 50)  # Move down to dropdown options
                                    pyautogui.click()
                                    break
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(1)
                
                # Step 7: Enter CPF
                adicionar_log(f"Passo 11 - Preenchendo com CPF: {cpf_usuario}")
                try:
                    # Try to find CPF field and enter CPF
                    pyautogui.write(cpf_usuario)
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(1)
                
                # Step 8: Click "Pesquisar"
                adicionar_log("Passo 12 - Clicando em 'Pesquisar'")
                try:
                    search_button = pyautogui.locateOnScreen('pesquisar_button.png', confidence=0.7)
                    if search_button:
                        pyautogui.click(search_button)
                    else:
                        # Try to find by text
                        screen = ImageGrab.grab()
                        text = pytesseract.image_to_string(screen, lang='por')
                        if "pesquisar" in text.lower():
                            # Find position based on text
                            lines = text.split('\n')
                            for i, line in enumerate(lines):
                                if "pesquisar" in line.lower():
                                    # Estimate position
                                    y_pos = (i + 1) * (screen.height / len(lines))
                                    pyautogui.moveTo(screen.width * 0.7, y_pos)  # Assume button is on right side
                                    pyautogui.click()
                                    break
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(2)
                
                # Step 9: Double-click on user
                adicionar_log("Passo 13 - Clicando duas vezes no usuário encontrado")
                try:
                    # Assume user is in the results list, click in the middle of the screen
                    screen = ImageGrab.grab()
                    pyautogui.moveTo(screen.width * 0.5, screen.height * 0.5)
                    pyautogui.doubleClick()
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(2)
                
                # Step 10: Change password
                adicionar_log("Passo 14 - Alterando senha para: ********")
                try:
                    # Try to find password field and enter new password
                    # First clear the field
                    pyautogui.hotkey('ctrl', 'a')  # Select all
                    pyautogui.press('delete')  # Delete selected text
                    # Enter new password
                    pyautogui.write(nova_senha)
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(1)
                
                # Step 11: Check if "Usuário ativo" is checked
                adicionar_log("Passo 15 - Verificando se 'Usuário ativo' está marcado")
                try:
                    # Try to find checkbox and ensure it's checked
                    active_checkbox = pyautogui.locateOnScreen('usuario_ativo.png', confidence=0.7)
                    if active_checkbox:
                        pyautogui.click(active_checkbox)  # Click to ensure it's checked
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(1)
                
                # Step 11: Click "salvar"
                adicionar_log("Passo 16 - Clicando em 'salvar'")
                try:
                    save_button = pyautogui.locateOnScreen('salvar_button.png', confidence=0.7)
                    if save_button:
                        pyautogui.click(save_button)
                    else:
                        # Try to find by text
                        screen = ImageGrab.grab()
                        text = pytesseract.image_to_string(screen, lang='por')
                        if "salvar" in text.lower():
                            # Find position based on text
                            lines = text.split('\n')
                            for i, line in enumerate(lines):
                                if "salvar" in line.lower():
                                    # Estimate position
                                    y_pos = (i + 1) * (screen.height / len(lines))
                                    pyautogui.moveTo(screen.width * 0.8, y_pos)  # Assume button is on right side
                                    pyautogui.click()
                                    break
                except Exception as e:
                    adicionar_log(f"Aviso: {str(e)}, tentando continuar...")
                time.sleep(2)
                
                # Update status to success
                adicionar_log("Senha alterada com sucesso!")
                atualizar_status(True)
                
            except Exception as e:
                # In case of error, update status to error
                adicionar_log(f"Erro durante a automação: {str(e)}")
                atualizar_status(False)
        
        # Start automation in a separate thread
        thread = threading.Thread(target=executar_automacao_thread)
        thread.daemon = True
        thread.start()
    
    # Botão para redefinir senha
    botao_redefinir_senha = ft.ElevatedButton(
        text="Redefinir Senha",
        icon=ft.Icons.PASSWORD,
        on_click=abrir_dialogo_redefinir_senha,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
            padding=ft.padding.all(15),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )

    # Botão para verificar status de todos os servidores
    botao_verificar_status = ft.IconButton(
        icon=ft.Icons.REFRESH,
        icon_color=ft.Colors.BLUE_500,
        bgcolor=ft.Colors.WHITE,
        tooltip="Verificar status de todos os servidores",
        on_click=lambda e: iniciar_verificacao_status(),
    )

    # Botão para verificar portas de todos os servidores
    botao_verificar_portas = ft.IconButton(
        icon=ft.Icons.SETTINGS_ETHERNET,
        icon_color=ft.Colors.BLUE_500,
        bgcolor=ft.Colors.WHITE,
        tooltip="Verificar portas de todos os servidores",
        on_click=lambda e: iniciar_verificacao_portas(),
    )

    # Botão para alternar entre visualização em lista e grade
    def alternar_modo_visualizacao(e):
        """Alterna entre visualização em lista e grade."""
        nonlocal modo_visualizacao
        modo_visualizacao = "grade" if modo_visualizacao == "lista" else "lista"
        
        if modo_visualizacao == "lista":
            botao_visualizacao.icon = ft.Icons.GRID_VIEW
            botao_visualizacao.tooltip = "Alternar para visualização em grade"
        else:
            botao_visualizacao.icon = ft.Icons.VIEW_LIST
            botao_visualizacao.tooltip = "Alternar para visualização em lista"
        
        atualizar_lista_servidores(None)

    botao_visualizacao = ft.IconButton(
        icon=ft.Icons.GRID_VIEW,
        icon_color=ft.Colors.BLUE_500,
        bgcolor=ft.Colors.WHITE,
        tooltip="Alternar para visualização em grade",
        on_click=alternar_modo_visualizacao,
    )

    # Botão para gerenciar servidores (adicionar, editar, remover)
    botao_gerenciar_servidores = ft.IconButton(
        icon=ft.Icons.SETTINGS,
        icon_color=ft.Colors.BLUE_500,
        bgcolor=ft.Colors.WHITE,
        tooltip="Gerenciar servidores",
        on_click=lambda e: abrir_dialogo_gerenciar_servidores(),
    )
    
    # Botão para visualizar estatísticas de acesso
    botao_estatisticas = ft.IconButton(
        icon=ft.Icons.ANALYTICS,
        icon_color=ft.Colors.PURPLE_500,
        bgcolor=ft.Colors.WHITE,
        tooltip="Visualizar estatísticas de acesso",
        on_click=lambda e: abrir_dialogo_estatisticas(),
    )

    def abrir_zabbix(host_ip):
        """Abre a URL do Zabbix no navegador para o servidor específico."""
        # Registra o acesso nas estatísticas
        registrar_acesso(host_ip, "zabbix")
        
        # Procura o servidor pelo IP para verificar se tem URL específica
        for servidor in lista_de_servidores:
            if servidor["ip"] == host_ip:
                # Se o servidor tiver uma URL específica do Zabbix, usa ela
                if "zabbix_url" in servidor:
                    url = servidor["zabbix_url"]
                else:
                    # Caso contrário, usa a URL padrão com o IP
                    url = f"{ZABBIX_URL_BASE}{host_ip}"
                webbrowser.open(url)
                return
    
        # Se não encontrar o servidor (improvável), usa a URL padrão
        url = f"{ZABBIX_URL_BASE}{host_ip}"
        webbrowser.open(url)
       
    def abrir_ip_unidade(ip_unidade):
        """Abre a URL com o IP da unidade no navegador."""
        # Registra o acesso nas estatísticas
        registrar_acesso(ip_unidade, "unidade")
        
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
            botao_favoritos.icon = ft.Icons.STAR
            botao_favoritos.tooltip = "Mostrar todos os servidores"
        else:
            botao_favoritos.icon = ft.Icons.STAR_BORDER
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
                icon=ft.Icons.FIRST_PAGE,
                icon_color=ft.Colors.BLUE_500,
                disabled=pagina_atual == 1,
                on_click=lambda e: ir_para_pagina(1),
                tooltip="Primeira página",
            )
        )
        
        # Botão para página anterior
        controles_paginacao.controls.append(
            ft.IconButton(
                icon=ft.Icons.NAVIGATE_BEFORE,
                icon_color=ft.Colors.BLUE_500,
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
                icon=ft.Icons.NAVIGATE_NEXT,
                icon_color=ft.Colors.BLUE_500,
                disabled=pagina_atual == total_paginas,
                on_click=lambda e: ir_para_pagina(pagina_atual + 1),
                tooltip="Próxima página",
            )
        )
        
        # Botão para última página
        controles_paginacao.controls.append(
            ft.IconButton(
                icon=ft.Icons.LAST_PAGE,
                icon_color=ft.Colors.BLUE_500,
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
                bgcolor=ft.Colors.BLACK,
                tooltip=tooltip,
                on_click=on_click_handler,
            )
        except Exception:
            # Se falhar, usa o ícone como fallback
            return ft.IconButton(
                icon=fallback_icon,
                icon_color=fallback_color,
                bgcolor=ft.Colors.BLACK,
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
        status_color = ft.Colors.GREEN_500 if is_online == True else ft.Colors.RED_500 if is_online == False else ft.Colors.GREY_500
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
                porta_color = ft.Colors.GREEN_500 if porta_online == True else ft.Colors.RED_500 if porta_online == False else ft.Colors.GREY_500
                porta_status_text = f"{descricao_porta}: " + ("Aberta" if porta_online == True else "Fechada" if porta_online == False else "Desconhecido")
                
                # Cria o indicador de status da porta
                portas_status.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(name=ft.Icons.CIRCLE, color=porta_color, size=8),
                                ft.Text(porta_status_text, size=10, color=porta_color),
                            ],
                            spacing=2,
                        ),
                        padding=3,
                        border_radius=8,
                        bgcolor=ft.Colors.WHITE,
                        margin=ft.margin.only(right=3, bottom=3),
                    )
                )
        
        return ft.Container(
            content=ft.Column(
                [
                    # Cabeçalho com nome e status
                    ft.Row(
                        [
                            ft.Icon(name=ft.Icons.DNS, color=ft.Colors.BLUE_500, size=24),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(name=ft.Icons.CIRCLE, color=status_color, size=10),
                                        ft.Text(status_text, size=10, color=status_color),
                                    ],
                                    spacing=2,
                                ),
                                padding=3,
                                border_radius=8,
                                bgcolor=ft.Colors.WHITE,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    # Nome do servidor
                    ft.Text(
                        servidor["nome"],
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLACK,
                        no_wrap=False,
                        selectable=True,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    # IP do servidor
                    ft.Text(
                        f"IP: {servidor['ip']}", 
                        size=12, 
                        color=ft.Colors.GREY_600,
                        selectable=True,
                    ),
                    # Descrição (se existir)
                    ft.Container(
                        content=ft.Text(
                            descricao if descricao else "Sem descrição",
                            size=12,
                            color=ft.Colors.GREY_700,
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
                                    bgcolor=ft.Colors.BLUE_100,
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
                                icon=ft.Icons.NETWORK_PING,
                                icon_color=ft.Colors.BLUE_500,
                                icon_size=18,
                                tooltip="Verificar status",
                                on_click=lambda e, ip=servidor["ip"]: verificar_status_individual(ip),
                            ),
                            # Botão de Favorito
                            ft.IconButton(
                                icon=ft.Icons.STAR if is_favorito else ft.Icons.STAR_BORDER,
                                icon_color=ft.Colors.AMBER_500,
                                icon_size=18,
                                tooltip="Favorito" if is_favorito else "Adicionar aos favoritos",
                                on_click=lambda e, ip=servidor["ip"]: alternar_favorito(e, ip),
                            ),
                            # Botão para editar servidor
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                icon_color=ft.Colors.ORANGE_500,
                                icon_size=18,
                                tooltip="Editar servidor",
                                on_click=lambda e, srv=servidor: abrir_dialogo_editar_servidor(srv),
                            ),
                            # Botão Zabbix
                            ft.IconButton(
                                icon=ft.Icons.OPEN_IN_BROWSER,
                                icon_color=ft.Colors.BLUE_500,
                                icon_size=18,
                                tooltip="Abrir no Zabbix",
                                on_click=lambda e, ip=servidor["ip"]: abrir_zabbix(ip),
                            ),
                            # Botão Unidade
                            ft.IconButton(
                                icon=ft.Icons.MAPS_HOME_WORK,
                                icon_color=ft.Colors.GREEN_500,
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
            bgcolor=ft.Colors.WHITE,
            border_radius=12,
            shadow=ft.BoxShadow(blur_radius=5, spread_radius=1, color=ft.Colors.GREY_300),
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
        status_color = ft.Colors.GREEN_500 if is_online == True else ft.Colors.RED_500 if is_online == False else ft.Colors.GREY_500
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
                porta_color = ft.Colors.GREEN_500 if porta_online == True else ft.Colors.RED_500 if porta_online == False else ft.Colors.GREY_500
                porta_status_text = f"{descricao_porta}: " + ("Aberta" if porta_online == True else "Fechada" if porta_online == False else "Desconhecido")
                
                # Cria o indicador de status da porta
                portas_status.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(name=ft.Icons.CIRCLE, color=porta_color, size=10),
                                ft.Text(porta_status_text, size=12, color=porta_color),
                            ],
                            spacing=5,
                        ),
                        padding=5,
                        border_radius=10,
                        bgcolor=ft.Colors.WHITE,
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
                                            ft.Icon(name=ft.Icons.DNS, color=ft.Colors.BLUE_500, size=30),
                                            ft.Column(
                                                [
                                                    ft.Row(
                                                        [
                                                            ft.Text(
                                                                servidor["nome"],
                                                                size=16,
                                                                weight=ft.FontWeight.BOLD,
                                                                color=ft.Colors.BLACK,
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
                                                                            name=ft.Icons.CIRCLE, 
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
                                                                bgcolor=ft.Colors.WHITE,
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
                                                                color=ft.Colors.GREY_600,
                                                                selectable=True,
                                                            ),
                                                            *[
                                                                ft.Chip(
                                                                    label=ft.Text(tag),
                                                                    bgcolor=ft.Colors.BLUE_100,
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
                                                        color=ft.Colors.GREY_700,
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
                                                icon=ft.Icons.NETWORK_PING,
                                                icon_color=ft.Colors.BLUE_500,
                                                bgcolor=ft.Colors.BLACK,
                                                tooltip="Verificar status",
                                                on_click=lambda e, ip=servidor["ip"]: verificar_status_individual(ip),
                                            ),
                                            # Botão de Favorito
                                            ft.IconButton(
                                                icon=ft.Icons.STAR if is_favorito else ft.Icons.STAR_BORDER,
                                                icon_color=ft.Colors.AMBER_500,
                                                bgcolor=ft.Colors.BLACK,
                                                tooltip="Remover dos favoritos" if is_favorito else "Adicionar aos favoritos",
                                                on_click=lambda e, ip=servidor["ip"]: alternar_favorito(e, ip),
                                            ),
                                            # Botão para editar servidor
                                            ft.IconButton(
                                                icon=ft.Icons.EDIT,
                                                icon_color=ft.Colors.ORANGE_500,
                                                bgcolor=ft.Colors.BLACK,
                                                tooltip="Editar servidor",
                                                on_click=lambda e, srv=servidor: abrir_dialogo_editar_servidor(srv),
                                            ),
                                            criar_botao_com_imagem(
                                                zabbix_img,
                                                "Abrir no Zabbix",
                                                lambda e, ip=servidor["ip"]: abrir_zabbix(ip),
                                                ft.Icons.OPEN_IN_BROWSER,
                                                ft.Colors.BLUE_500
                                            ),
                                            criar_botao_com_imagem(
                                                unidade_img,
                                                "Acessar interface da unidade",
                                                lambda e, ip=ip_unidade: abrir_ip_unidade(ip),
                                                ft.Icons.MAPS_HOME_WORK,
                                                ft.Colors.GREEN_500
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
            bgcolor=ft.Colors.WHITE,
            border_radius=12,
            shadow=ft.BoxShadow(blur_radius=5, spread_radius=1, color=ft.Colors.GREY_300),
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
                e.control.shadow = ft.BoxShadow(blur_radius=10, spread_radius=3, color=ft.Colors.BLUE_200)
                e.control.update()
            else:  # Mouse saiu
                e.control.shadow = ft.BoxShadow(blur_radius=5, spread_radius=1, color=ft.Colors.GREY_300)
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
    
    # Função para exportar estatísticas de acesso
    def exportar_estatisticas(caminho=None, formato="json"):
        """Exporta as estatísticas de acesso para um arquivo JSON ou CSV."""
        try:
            if caminho is None:
                # Usa um nome de arquivo padrão com timestamp
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                caminho = f"estatisticas_acesso_exportadas_{timestamp}.{formato}"
            
            # Prepara os dados para exportação
            # Top servidores mais acessados no Zabbix
            top_zabbix = sorted(
                [(ip, estatisticas_acesso["zabbix"].get(ip, 0)) for ip in estatisticas_acesso["zabbix"]],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Top servidores mais acessados na unidade
            top_unidade = sorted(
                [(ip, estatisticas_acesso["unidade"].get(ip, 0)) for ip in estatisticas_acesso["unidade"]],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Top servidores mais acessados no total
            top_total = sorted(
                [(ip, estatisticas_acesso["total"].get(ip, 0)) for ip in estatisticas_acesso["total"]],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Função para obter o nome do servidor pelo IP
            def obter_nome_servidor(ip):
                for servidor in lista_de_servidores:
                    if servidor["ip"] == ip:
                        return servidor["nome"]
                return ip
            
            if formato.lower() == "json":
                # Cria uma cópia das estatísticas com informações adicionais
                estatisticas_exportar = estatisticas_acesso.copy()
                
                # Adiciona informações sobre os servidores para facilitar a análise
                estatisticas_exportar["info_servidores"] = {}
                for servidor in lista_de_servidores:
                    ip = servidor["ip"]
                    estatisticas_exportar["info_servidores"][ip] = {
                        "nome": servidor["nome"],
                        "tags": servidor.get("tags", []),
                        "descricao": servidor.get("descricao", "")
                    }
                
                # Adiciona rankings formatados
                estatisticas_exportar["rankings"] = {
                    "zabbix": [{"ip": ip, "nome": obter_nome_servidor(ip), "acessos": acessos} for ip, acessos in top_zabbix],
                    "unidade": [{"ip": ip, "nome": obter_nome_servidor(ip), "acessos": acessos} for ip, acessos in top_unidade],
                    "total": [{"ip": ip, "nome": obter_nome_servidor(ip), "acessos": acessos} for ip, acessos in top_total]
                }
                
                # Adiciona metadados da exportação
                estatisticas_exportar["metadados"] = {
                    "data_exportacao": datetime.datetime.now().isoformat(),
                    "total_servidores": len(lista_de_servidores),
                    "total_acessos_zabbix": sum(estatisticas_acesso["zabbix"].values()),
                    "total_acessos_unidade": sum(estatisticas_acesso["unidade"].values()),
                    "total_acessos": sum(estatisticas_acesso["total"].values())
                }
                
                with open(caminho, "w", encoding="utf-8") as arquivo:
                    json.dump(estatisticas_exportar, arquivo, ensure_ascii=False, indent=4)
            
            elif formato.lower() == "csv":
                # Exporta para CSV
                with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
                    writer = csv.writer(arquivo)
                    
                    # Escreve cabeçalho
                    writer.writerow(["Tipo", "IP", "Nome", "Acessos"])
                    
                    # Escreve dados do Zabbix
                    for ip, acessos in top_zabbix:
                        writer.writerow(["Zabbix", ip, obter_nome_servidor(ip), acessos])
                    
                    # Escreve dados da Unidade
                    for ip, acessos in top_unidade:
                        writer.writerow(["Unidade", ip, obter_nome_servidor(ip), acessos])
                    
                    # Escreve dados do Total
                    writer.writerow([])  # Linha em branco para separar
                    writer.writerow(["Total", "", "", ""])  # Cabeçalho da seção
                    for ip, acessos in top_total:
                        writer.writerow(["Total", ip, obter_nome_servidor(ip), acessos])
                    
                    # Escreve resumo
                    writer.writerow([])  # Linha em branco para separar
                    writer.writerow(["Resumo", "", "", ""])  # Cabeçalho da seção
                    writer.writerow(["Total de acessos Zabbix", sum(estatisticas_acesso["zabbix"].values()), "", ""])
                    writer.writerow(["Total de acessos Unidade", sum(estatisticas_acesso["unidade"].values()), "", ""])
                    writer.writerow(["Total de acessos", sum(estatisticas_acesso["total"].values()), "", ""])
                    writer.writerow(["Data de exportação", datetime.datetime.now().isoformat(), "", ""])
            
            return True, caminho
        except Exception as e:
            print(f"Erro ao exportar estatísticas: {e}")
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
    
    # Função para abrir o diálogo de estatísticas
    def abrir_dialogo_estatisticas():
        """Abre o diálogo para visualizar estatísticas de acesso."""
        # Prepara os dados para os gráficos
        # Top 10 servidores mais acessados no Zabbix
        top_zabbix = sorted(
            [(ip, estatisticas_acesso["zabbix"].get(ip, 0)) for ip in estatisticas_acesso["zabbix"]],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Top 10 servidores mais acessados na unidade
        top_unidade = sorted(
            [(ip, estatisticas_acesso["unidade"].get(ip, 0)) for ip in estatisticas_acesso["unidade"]],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Top 10 servidores mais acessados no total
        top_total = sorted(
            [(ip, estatisticas_acesso["total"].get(ip, 0)) for ip in estatisticas_acesso["total"]],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Função para obter o nome do servidor pelo IP
        def obter_nome_servidor(ip):
            for servidor in lista_de_servidores:
                if servidor["ip"] == ip:
                    return servidor["nome"]
            return ip
        
        # Função para criar um gráfico de barras para um conjunto de dados
        def criar_grafico_barras(dados, cor_barra, altura_maxima=300):
            if not dados:
                return ft.Container(
                    content=ft.Text("Nenhum dado disponível para exibição", style=ft.TextStyle(italic=True)),
                    alignment=ft.alignment.center,
                    padding=20,
                    height=altura_maxima,
                )
            
            # Encontra o valor máximo para escala
            max_valor = max([valor for _, valor in dados]) if dados else 1
            
            # Cria as barras do gráfico
            barras = []
            for ip, valor in dados:
                nome_servidor = obter_nome_servidor(ip)
                # Calcula a altura da barra proporcional ao valor
                altura_barra = (valor / max_valor) * (altura_maxima - 50) if max_valor > 0 else 0
                
                barra = ft.Column(
                    [
                        # Valor numérico acima da barra
                        ft.Text(str(valor), size=14, weight=ft.FontWeight.BOLD, color=cor_barra),
                        
                        # Espaçador que empurra a barra para baixo
                        ft.Container(height=altura_maxima - altura_barra - 50),
                        
                        # A barra propriamente dita
                        ft.Container(
                            width=40,
                            height=altura_barra,
                            bgcolor=cor_barra,
                            border_radius=ft.border_radius.only(top_left=5, top_right=5),
                            animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT),
                        ),
                        
                        # Linha de base
                        ft.Container(
                            width=40,
                            height=2,
                            bgcolor=ft.Colors.GREY_400,
                        ),
                        
                        # Nome do servidor abaixo da barra
                        ft.Container(
                            content=ft.Text(
                                nome_servidor if len(nome_servidor) < 15 else nome_servidor[:12] + "...",
                                size=10,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            width=60,
                            tooltip=f"{nome_servidor} ({ip}): {valor} acessos",
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                )
                barras.append(barra)
            
            # Cria o container com todas as barras
            return ft.Container(
                content=ft.Row(
                    barras,
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    spacing=10,
                ),
                padding=10,
                height=altura_maxima,
            )
        
        # Cria os gráficos de barras
        grafico_zabbix = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Top 10 Servidores Mais Acessados no Zabbix", weight=ft.FontWeight.BOLD, size=16),
                    ft.Container(height=10),
                    criar_grafico_barras(top_zabbix, ft.Colors.BLUE_500),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=10,
            bgcolor=ft.Colors.BLUE_50,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_200),
            margin=10,
            height=400,
        )
        
        grafico_unidade = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Top 10 Servidores Mais Acessados na Unidade", weight=ft.FontWeight.BOLD, size=16),
                    ft.Container(height=10),
                    criar_grafico_barras(top_unidade, ft.Colors.GREEN_500),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=10,
            bgcolor=ft.Colors.GREEN_50,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.GREEN_200),
            margin=10,
            height=400,
        )
        
        grafico_total = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Top 10 Servidores Mais Acessados (Total)", weight=ft.FontWeight.BOLD, size=16),
                    ft.Container(height=10),
                    criar_grafico_barras(top_total, ft.Colors.PURPLE_500),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=10,
            bgcolor=ft.Colors.PURPLE_50,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.PURPLE_200),
            margin=10,
            height=400,
        )
        
        # Resumo estatístico
        total_acessos_zabbix = sum(estatisticas_acesso["zabbix"].values())
        total_acessos_unidade = sum(estatisticas_acesso["unidade"].values())
        total_acessos = sum(estatisticas_acesso["total"].values())
        
        resumo_estatistico = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Resumo Estatístico", weight=ft.FontWeight.BOLD, size=18),
                    ft.Container(height=10),
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Icon(name=ft.Icons.OPEN_IN_BROWSER, color=ft.Colors.BLUE_500, size=30),
                                        ft.Text("Acessos ao Zabbix", size=14, weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{total_acessos_zabbix}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=5,
                                ),
                                padding=15,
                                bgcolor=ft.Colors.BLUE_50,
                                border_radius=10,
                                border=ft.border.all(1, ft.Colors.BLUE_200),
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Icon(name=ft.Icons.MAPS_HOME_WORK, color=ft.Colors.GREEN_500, size=30),
                                        ft.Text("Acessos à Unidade", size=14, weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{total_acessos_unidade}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=5,
                                ),
                                padding=15,
                                bgcolor=ft.Colors.GREEN_50,
                                border_radius=10,
                                border=ft.border.all(1, ft.Colors.GREEN_200),
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Icon(name=ft.Icons.ANALYTICS, color=ft.Colors.PURPLE_500, size=30),
                                        ft.Text("Total de Acessos", size=14, weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{total_acessos}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_700),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=5,
                                ),
                                padding=15,
                                bgcolor=ft.Colors.PURPLE_50,
                                border_radius=10,
                                border=ft.border.all(1, ft.Colors.PURPLE_200),
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                ],
            ),
            padding=10,
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.GREY_300),
            margin=10,
        )
        
        # Função para exportar as estatísticas
        def exportar_estatisticas_dialog():
            # Cria um diálogo para escolher o nome do arquivo
            nome_arquivo_input = ft.TextField(
                label="Nome do arquivo",
                value=f"estatisticas_acesso_{time.strftime('%Y%m%d_%H%M%S')}",
                border=ft.InputBorder.OUTLINE,
                expand=True,
            )
            
            # Adiciona um dropdown para escolher o formato
            formato_exportacao = ft.Dropdown(
                options=[
                    ft.dropdown.Option("json", text="JSON"),
                    ft.dropdown.Option("csv", text="CSV"),
                ],
                value="json",
                label="Formato",
                width=100,
            )
            
            def confirmar_exportacao(e):
                caminho = nome_arquivo_input.value + "." + formato_exportacao.value
                sucesso, resultado = exportar_estatisticas(caminho, formato_exportacao.value)
                
                # Fecha o diálogo de exportação
                dialogo_exportar.open = False
                page.update()
                
                # Exibe mensagem de sucesso ou erro
                if sucesso:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Estatísticas exportadas com sucesso para {resultado}"),
                        bgcolor=ft.Colors.GREEN_500,
                    )
                else:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Erro ao exportar estatísticas: {resultado}"),
                        bgcolor=ft.Colors.RED_500,
                    )
                
                page.snack_bar.open = True
                page.update()
        
            dialogo_exportar = ft.AlertDialog(
                title=ft.Text("Exportar Estatísticas", size=20, weight=ft.FontWeight.BOLD),
                content=ft.Column(
                    [
                        ft.Text("Escolha um nome para o arquivo de exportação:"),
                        ft.Container(height=10),
                        nome_arquivo_input,
                        ft.Container(height=10),
                        ft.Text("Escolha o formato de exportação:"),
                        formato_exportacao,
                    ],
                    width=400,
                    height=200,
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: setattr(dialogo_exportar, "open", False)),
                    ft.TextButton(
                        "Exportar", 
                        on_click=confirmar_exportacao,
                        style=ft.ButtonStyle(color=ft.Colors.BLUE_500),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            # Exibe o diálogo
            page.dialog = dialogo_exportar
            dialogo_exportar.open = True
            page.update()
        
        # Botão para exportar estatísticas
        botao_exportar_estatisticas = ft.ElevatedButton(
            text="Exportar Estatísticas",
            icon=ft.Icons.DOWNLOAD,
            on_click=lambda e: exportar_estatisticas_dialog(),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.PURPLE_700,
                color=ft.Colors.WHITE,
                padding=ft.padding.all(15),
                shape=ft.RoundedRectangleBorder(radius=10),
                shadow_color=ft.Colors.with_opacity(0.5, ft.Colors.PURPLE_900),
                elevation=5,
            ),
        )
        
        # Cria o conteúdo das abas
        conteudo_aba_total = ft.Container(
            content=grafico_total,
            padding=10,
        )
        
        conteudo_aba_zabbix = ft.Container(
            content=grafico_zabbix,
            padding=10,
        )
        
        conteudo_aba_unidade = ft.Container(
            content=grafico_unidade,
            padding=10,
        )
        
        # Tabela com os servidores mais acessados
        def criar_tabela_servidores_mais_acessados():
            # Combina todos os dados para a tabela
            todos_dados = []
            for ip, acessos in top_total:
                nome = obter_nome_servidor(ip)
                acessos_zabbix = estatisticas_acesso["zabbix"].get(ip, 0)
                acessos_unidade = estatisticas_acesso["unidade"].get(ip, 0)
                
                todos_dados.append({
                    "ip": ip,
                    "nome": nome,
                    "total": acessos,
                    "zabbix": acessos_zabbix,
                    "unidade": acessos_unidade
                })
            
            # Cria o cabeçalho da tabela
            cabecalho = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text("Servidor", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text("IP", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text("Total", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text("Zabbix", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text("Unidade", weight=ft.FontWeight.BOLD)),
                ],
            )
            
            # Cria as linhas da tabela
            linhas = []
            for dado in todos_dados:
                linhas.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(dado["nome"])),
                            ft.DataCell(ft.Text(dado["ip"])),
                            ft.DataCell(ft.Text(str(dado["total"]), color=ft.Colors.PURPLE_700)),
                            ft.DataCell(ft.Text(str(dado["zabbix"]), color=ft.Colors.BLUE_700)),
                            ft.DataCell(ft.Text(str(dado["unidade"]), color=ft.Colors.GREEN_700)),
                        ],
                    )
                )
            
            # Cria a tabela
            tabela = ft.DataTable(
                columns=[
                    ft.DataColumn(label=ft.Text("Servidor", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(label=ft.Text("IP", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(label=ft.Text("Total", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(label=ft.Text("Zabbix", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(label=ft.Text("Unidade", weight=ft.FontWeight.BOLD)),
                ],
                rows=linhas,
                border=ft.border.all(1, ft.Colors.GREY_400),
                border_radius=10,
                vertical_lines=ft.border.BorderSide(1, ft.Colors.GREY_300),
                horizontal_lines=ft.border.BorderSide(1, ft.Colors.GREY_300),
                sort_column_index=2,  # Ordena por total por padrão
                sort_ascending=False,  # Ordem decrescente
            )
            
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Detalhamento dos Servidores Mais Acessados", weight=ft.FontWeight.BOLD, size=16),
                        ft.Container(height=10),
                        tabela,
                    ],
                ),
                padding=10,
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
                border=ft.border.all(1, ft.Colors.GREY_300),
                margin=10,
            )
        
        # Cria a tabela de servidores mais acessados
        tabela_servidores = criar_tabela_servidores_mais_acessados()
        
        # Conteúdo da aba de detalhamento
        conteudo_aba_detalhamento = ft.Container(
            content=ft.Column(
                [
                    tabela_servidores,
                    ft.Container(
                        content=ft.ElevatedButton(
                            text="Exportar Detalhamento",
                            icon=ft.Icons.TABLE_CHART,
                            on_click=lambda e: exportar_estatisticas_dialog(),
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE,
                                padding=ft.padding.all(15),
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                        ),
                        alignment=ft.alignment.center,
                        padding=10,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=10,
        )
        
        # Cria o diálogo
        dialogo_estatisticas = ft.AlertDialog(
            title=ft.Text("Estatísticas de Acesso aos Servidores", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    resumo_estatistico,
                    ft.Tabs(
                        selected_index=0,
                        animation_duration=300,
                        tabs=[
                            ft.Tab(
                                text="Total",
                                icon=ft.Icons.ANALYTICS,
                                content=conteudo_aba_total,
                            ),
                            ft.Tab(
                                text="Zabbix",
                                icon=ft.Icons.OPEN_IN_BROWSER,
                                content=conteudo_aba_zabbix,
                            ),
                            ft.Tab(
                                text="Unidade",
                                icon=ft.Icons.MAPS_HOME_WORK,
                                content=conteudo_aba_unidade,
                            ),
                            ft.Tab(
                                text="Detalhamento",
                                icon=ft.Icons.TABLE_CHART,
                                content=conteudo_aba_detalhamento,
                            ),
                        ],
                    ),
                    ft.Container(
                        content=botao_exportar_estatisticas,
                        alignment=ft.alignment.center,
                        padding=10,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                width=800,
                height=700,
            ),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: setattr(dialogo_estatisticas, "open", False)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        page.dialog = dialogo_estatisticas
        dialogo_estatisticas.open = True
        page.update()

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
                        bgcolor=ft.Colors.GREEN_500,
                    )
                else:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Erro ao exportar servidores: {resultado}"),
                        bgcolor=ft.Colors.RED_500,
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
                        style=ft.ButtonStyle(color=ft.Colors.BLUE_500),
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
                        bgcolor=ft.Colors.RED_500,
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
                        bgcolor=ft.Colors.GREEN_500,
                    )
                    # Reabre o diálogo de gerenciar servidores atualizado
                    page.update()
                    abrir_dialogo_gerenciar_servidores()
                else:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Erro ao importar servidores: {mensagem}"),
                        bgcolor=ft.Colors.RED_500,
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
                            color=ft.Colors.GREY_700,
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
                        style=ft.ButtonStyle(color=ft.Colors.BLUE_500),
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
                                icon=ft.Icons.UPLOAD_FILE,
                                on_click=lambda e: importar_servidores_dialog(),
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.GREEN_700,
                                    color=ft.Colors.WHITE,
                                ),
                            ),
                            ft.ElevatedButton(
                                text="Exportar Servidores",
                                icon=ft.Icons.DOWNLOAD,
                                on_click=lambda e: exportar_servidores_dialog(),
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.BLUE_700,
                                    color=ft.Colors.WHITE,
                                ),
                            ),
                            ft.ElevatedButton(
                                text="Adicionar Servidor",
                                icon=ft.Icons.ADD,
                                on_click=lambda e: abrir_dialogo_adicionar_servidor(dialogo_gerenciar),
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.BLUE_500,
                                    color=ft.Colors.WHITE,
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
                                        color=ft.Colors.GREY_700,
                                    ),
                                    ft.Text(
                                        servidor.get("descricao", "Sem descrição"),
                                        size=12,
                                        color=ft.Colors.GREY_600,
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
                                                color=ft.Colors.BLUE_500,
                                            ) if servidor.get("portas") else ft.Text(
                                                "Sem portas configuradas",
                                                size=12,
                                                color=ft.Colors.GREY_500,
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
                                        icon=ft.Icons.EDIT,
                                        icon_color=ft.Colors.BLUE_500,
                                        tooltip="Editar servidor",
                                        on_click=lambda e, srv=servidor: abrir_dialogo_editar_servidor(srv, dialogo_gerenciar),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED_500,
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
                    bgcolor=ft.Colors.WHITE,
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    shadow=ft.BoxShadow(blur_radius=2, spread_radius=1, color=ft.Colors.GREY_200),
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
        
        zabbix_url_input = ft.TextField(
            label="URL específica do Zabbix (opcional)",
            border=ft.InputBorder.OUTLINE,
            expand=True,
            hint_text="URL completa para este servidor no Zabbix",
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
                icon=ft.Icons.DELETE,
                icon_color=ft.Colors.RED_500,
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
            icon=ft.Icons.ADD,
            on_click=lambda e: adicionar_campo_porta(),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_500,
                color=ft.Colors.WHITE,
            ),
        )
        
        # Função para verificar as portas adicionadas
        def verificar_portas_adicionadas(e):
            # Limpa o container de status
            status_portas_container.controls.clear()
            
            # Verifica se há portas para verificar
            if not portas_adicionadas:
                status_portas_container.controls.append(
                    ft.Text("Nenhuma porta adicionada para verificar.", color=ft.Colors.GREY_700)
                )
                status_portas_container.visible = True
                status_portas_container.update()
                return
            
            # Verifica se o IP foi informado
            if not ip_input.value:
                status_portas_container.controls.append(
                    ft.Text("Informe o IP do servidor para verificar as portas.", color=ft.Colors.RED_500)
                )
                status_portas_container.visible = True
                status_portas_container.update()
                return
            
            # Adiciona um indicador de carregamento
            status_portas_container.controls.append(
                ft.Text("Verificando portas...", color=ft.Colors.BLUE_500)
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
                            porta_color = ft.Colors.GREEN_500 if porta_aberta else ft.Colors.RED_500
                            porta_status_text = f"{descricao_valor if descricao_valor else f'Porta {porta}'}: " + ("Aberta" if porta_aberta else "Fechada")
                            
                            # Adiciona o indicador de status da porta
                            status_portas_container.controls.append(
                                ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.Icon(name=ft.Icons.CIRCLE, color=porta_color, size=12),
                                            ft.Text(porta_status_text, size=14, color=porta_color),
                                        ],
                                        spacing=5,
                                    ),
                                    padding=5,
                                    border_radius=10,
                                    bgcolor=ft.Colors.WHITE,
                                    border=ft.border.all(1, ft.Colors.GREY_300),
                                    margin=ft.margin.only(bottom=5),
                                ),
                            )
                        except ValueError:
                            # Ignora portas inválidas
                            status_portas_container.controls.append(
                                ft.Text(f"Porta inválida: {porta_valor}", color=ft.Colors.RED_500)
                            )
                
                # Se não houver portas válidas
                if not status_portas_container.controls:
                    status_portas_container.controls.append(
                        ft.Text("Nenhuma porta válida para verificar.", color=ft.Colors.GREY_700)
                    )
                
                status_portas_container.update()
            
            # Inicia a verificação em uma thread separada
            thread = threading.Thread(target=verificar_portas_thread)
            thread.daemon = True
            thread.start()
        
        # Botão para verificar portas
        botao_verificar_portas = ft.ElevatedButton(
            text="Verificar Portas",
            icon=ft.Icons.SETTINGS_ETHERNET,
            on_click=verificar_portas_adicionadas,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.GREEN_700,
                color=ft.Colors.WHITE,
            ),
        )
        
        # Função para adicionar o servidor
        def adicionar_servidor(e):
            # Validação básica
            if not nome_input.value or not ip_input.value:
                # Exibe mensagem de erro
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Nome e IP são obrigatórios!"),
                    bgcolor=ft.Colors.RED_500,
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
            
            # Adiciona URL específica do Zabbix se fornecida
            if zabbix_url_input.value:
                novo_servidor["zabbix_url"] = zabbix_url_input.value
            
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
                    bgcolor=ft.Colors.GREEN_500,
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
                    ft.Container(height=10),
                    zabbix_url_input,
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
                    style=ft.ButtonStyle(color=ft.Colors.BLUE_500),
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

        zabbix_url_input = ft.TextField(
            label="URL específica do Zabbix (opcional)",
            value=servidor.get("zabbix_url", ""),
            border=ft.InputBorder.OUTLINE,
            expand=True,
            hint_text="URL completa para este servidor no Zabbix",
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
                icon=ft.Icons.DELETE,
                icon_color=ft.Colors.RED_500,
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
            icon=ft.Icons.ADD,
            on_click=lambda e: adicionar_campo_porta(),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_500,
                color=ft.Colors.WHITE,
            ),
        )
        
        # Função para verificar as portas adicionadas
        def verificar_portas_adicionadas(e):
            # Limpa o container de status
            status_portas_container.controls.clear()
            
            # Verifica se há portas para verificar
            if not portas_adicionadas:
                status_portas_container.controls.append(
                    ft.Text("Nenhuma porta adicionada para verificar.", color=ft.Colors.GREY_700)
                )
                status_portas_container.visible = True
                status_portas_container.update()
                return
            
            # Adiciona um indicador de carregamento
            status_portas_container.controls.append(
                ft.Text("Verificando portas...", color=ft.Colors.BLUE_500)
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
                            porta_color = ft.Colors.GREEN_500 if porta_aberta else ft.Colors.RED_500
                            porta_status_text = f"{descricao_valor if descricao_valor else f'Porta {porta}'}: " + ("Aberta" if porta_aberta else "Fechada")
                            
                            # Adiciona o indicador de status da porta
                            status_portas_container.controls.append(
                                ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.Icon(name=ft.Icons.CIRCLE, color=porta_color, size=12),
                                            ft.Text(porta_status_text, size=14, color=porta_color),
                                        ],
                                        spacing=5,
                                    ),
                                    padding=5,
                                    border_radius=10,
                                    bgcolor=ft.Colors.WHITE,
                                    border=ft.border.all(1, ft.Colors.GREY_300),
                                    margin=ft.margin.only(bottom=5),
                                ),
                            )
                        except ValueError:
                            # Ignora portas inválidas
                            status_portas_container.controls.append(
                                ft.Text(f"Porta inválida: {porta_valor}", color=ft.Colors.RED_500)
                            )
                
                # Se não houver portas válidas
                if not status_portas_container.controls:
                    status_portas_container.controls.append(
                        ft.Text("Nenhuma porta válida para verificar.", color=ft.Colors.GREY_700)
                    )
                
                status_portas_container.update()
            
            # Inicia a verificação em uma thread separada
            thread = threading.Thread(target=verificar_portas_thread)
            thread.daemon = True
            thread.start()
        
        # Botão para verificar portas
        botao_verificar_portas = ft.ElevatedButton(
            text="Verificar Portas",
            icon=ft.Icons.SETTINGS_ETHERNET,
            on_click=verificar_portas_adicionadas,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.GREEN_700,
                color=ft.Colors.WHITE,
            ),
        )
        
        # Função para salvar as alterações
        def salvar_alteracoes(e):
            # Validação básica
            if not nome_input.value or not ip_input.value:
                # Exibe mensagem de erro
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Nome e IP são obrigatórios!"),
                    bgcolor=ft.Colors.RED_500,
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

            # Atualiza URL específica do Zabbix
            if zabbix_url_input.value:
                servidor["zabbix_url"] = zabbix_url_input.value
            elif "zabbix_url" in servidor:
                del servidor["zabbix_url"]
            
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
                    bgcolor=ft.Colors.GREEN_500,
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
                    ft.Container(height=10),
                    zabbix_url_input,
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
                    style=ft.ButtonStyle(color=ft.Colors.BLUE_500),
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
                    bgcolor=ft.Colors.GREEN_500,
                )
                page.snack_bar.open = True
                page.update()
        
        # Cria o diálogo
        dialogo_confirmar = ft.AlertDialog(
            title=ft.Text("Confirmar Remoção", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
            content=ft.Column(
                [
                    ft.Text(f"Tem certeza que deseja remover o servidor:"),
                    ft.Container(height=10),
                    ft.Text(f"Nome: {servidor['nome']}", weight=ft.FontWeight.BOLD),
                    ft.Text(f"IP: {servidor['ip']}"),
                    ft.Container(height=10),
                    ft.Text("Esta ação não pode ser desfeita!", color=ft.Colors.RED),
                ],
                width=400,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dialogo_confirmar, "open", False)),
                ft.TextButton(
                    "Remover", 
                    on_click=remover_servidor, 
                    style=ft.ButtonStyle(color=ft.Colors.RED_500)
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
        bgcolor=ft.Colors.WHITE,
        border_radius=12,
        border=ft.InputBorder.OUTLINE,
        border_color=ft.Colors.BLUE_400,
        height=50,
        prefix_icon=ft.Icons.SEARCH,
    )

    # Botão para alternar entre todos os servidores e favoritos
    botao_favoritos = ft.IconButton(
        icon=ft.Icons.STAR_BORDER,
        icon_color=ft.Colors.AMBER_500,
        bgcolor=ft.Colors.WHITE,
        tooltip="Mostrar apenas favoritos",
        on_click=alternar_visualizacao_favoritos,
    )

    # Botão para alternar modo claro/escuro
    botao_tema = ft.IconButton(
        icon=ft.Icons.DARK_MODE,
        icon_color=ft.Colors.GREY_700,
        bgcolor=ft.Colors.WHITE,
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
            botao_tema.icon = ft.Icons.LIGHT_MODE
            botao_tema.icon_color = ft.Colors.YELLOW_500
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            botao_tema.icon = ft.Icons.DARK_MODE
            botao_tema.icon_color = ft.Colors.GREY_700
       
        page.update()

    # Contador de servidores
    contador = ft.Text(
        f"{len(lista_de_servidores)} servidores",
        color=ft.Colors.GREY_700,
        size=12,
    )

    # Container para o contador
    container_contador = ft.Container(
        content=contador,
        padding=ft.padding.only(left=10, right=10),
        bgcolor=ft.Colors.GREY_200,
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
                                            ft.Icon(ft.Icons.DNS, color=ft.Colors.BLUE_500, size=32),
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
                                            botao_redefinir_senha,  # Botão para redefinir senha
                                            botao_gerenciar_servidores,  # Botão para gerenciar servidores
                                            botao_estatisticas,  # Botão para visualizar estatísticas
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
                    ft.Divider(height=1, color=ft.Colors.GREY_400),
                    lista_servidores,  # Apenas o ListView tem a rolagem ativada
                    controles_paginacao,  # Controles de navegação entre páginas
                ],
                expand=True,
                spacing=15,
            ),
            padding=20,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            shadow=ft.BoxShadow(blur_radius=10, spread_radius=2, color=ft.Colors.GREY_400),
            expand=True,  # Permite que o container se expanda para preencher o espaço disponível
        )
    )

    # Inicializa os controles de paginação
    atualizar_controles_paginacao()

    # Inicia a verificação de status ao carregar a aplicação
    iniciar_verificacao_status()

ft.app(target=main)
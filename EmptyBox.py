from PyQt5.QtWidgets import *
import sys
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon
from urllib.parse import urlparse
import os
import random
import uuid
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from subprocess import Popen
import requests
import socket
from PyQt5.QtNetwork import QNetworkProxy

class TorManager:
    def __init__(self):
        self.tor_process = None
        self.tor_port = 9050
        self.connection_progress = 0
        self.status = "Desconectado"
        self.fully_bootstrapped = False
        
    def start_tor(self):
        try:
            self.status = "Conectando"
            self.connection_progress = 0
            self.fully_bootstrapped = False
            
            # Define o diretório para logs
            log_dir = os.path.join(os.path.expanduser('~'), '.emptybox', 'logs')
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception as e:
                print(f"Erro ao criar diretório de logs: {e}")
                self.status = "Erro ao criar diretório de logs"
                return False

            # Define o caminho do arquivo de log
            log_path = os.path.join(log_dir, 'tor_log.txt')
            print(f"Tentando criar arquivo de log em: {log_path}")  # Debug

            # Tenta encontrar o tor.exe em diferentes locais
            possible_paths = [
                os.path.join(os.path.dirname(sys.executable), "tor", "tor.exe"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "tor", "tor.exe"),
                os.path.join(sys._MEIPASS, "tor", "tor.exe") if hasattr(sys, '_MEIPASS') else None
            ]
            
            # Debug: mostra todos os caminhos verificados
            print("Procurando tor.exe em:")
            for path in possible_paths:
                if path:
                    print(f"- {path} {'(encontrado)' if os.path.exists(path) else '(não encontrado)'}")
            
            tor_path = None
            for path in possible_paths:
                if path and os.path.exists(path):
                    tor_path = path
                    break
            
            if not tor_path:
                error_msg = "Erro: tor.exe não encontrado"
                print(error_msg)
                self.status = error_msg
                return False
            
            print(f"Usando Tor em: {tor_path}")
            
            try:
                # Tenta criar o arquivo de log
                self.log_file = open(log_path, "w+", encoding='utf-8')
            except Exception as e:
                print(f"Erro ao criar arquivo de log: {e}")
                self.status = f"Erro ao criar arquivo de log: {e}"
                return False
            
            try:
                # Tenta iniciar o Tor com stderr redirecionado para o arquivo de log
                self.tor_process = Popen(
                    [tor_path],
                    stdout=self.log_file,
                    stderr=self.log_file,
                    creationflags=0x08000000  # CREATE_NO_WINDOW flag
                )
            except Exception as e:
                print(f"Erro ao iniciar processo do Tor: {e}")
                self.status = f"Erro ao iniciar Tor: {e}"
                if hasattr(self, 'log_file'):
                    self.log_file.close()
                return False
            
            # Aguarda inicialização
            for _ in range(120):  # 60 segundos de timeout
                if self.check_bootstrap():
                    self.connection_progress = 100
                    self.status = "Conectado"
                    print("Tor iniciado com sucesso")
                    self.fully_bootstrapped = True
                    return True
                    
                # Atualiza progresso baseado no log
                self.log_file.seek(0)
                log_content = self.log_file.read()
                for line in log_content.splitlines():
                    if "Bootstrapped" in line and "%" in line:
                        try:
                            self.connection_progress = int(line.split("%")[0].split()[-1])
                            print(line)  # Mostra progresso no terminal
                        except:
                            pass
                
                QThread.msleep(500)
            
            self.status = "Timeout na conexão"
            return False
            
        except Exception as e:
            self.status = f"Erro: {e}"
            return False
    
    def check_bootstrap(self):
        try:
            self.log_file.seek(0)
            log_content = self.log_file.read()
            if "Bootstrapped 100% (done): Done" in log_content:
                return True
            return False
        except:
            return False
            
    def stop_tor(self):
        if self.tor_process:
            self.tor_process.terminate()
        if hasattr(self, 'log_file'):
            self.log_file.close()
            try:
                os.remove("tor_log.txt")
            except:
                pass

    def get_status_text(self):
        if self.status == "Conectando":
            return f"🔄 Conectando ao Tor ({self.connection_progress}%)"
        elif self.status == "Conectado" and self.fully_bootstrapped:
            return "✅ Conectado ao Tor"
        else:
            return f"❌ {self.status}"

# Gerenciador de páginas personalizado
class WebEnginePage(QWebEnginePage):
    def createWindow(self, _type):
        # Solicita ao componente principal que crie uma nova aba
        main_window = self.view().window()
        if isinstance(main_window, MainWindow):
            return main_window.create_new_tab()
        return super().createWindow(_type)
    
class AdBlocker(QWebEngineUrlRequestInterceptor):
    def __init__(self):
        super().__init__()
        # Lista de domínios de anúncios a serem bloqueados
        self.blocked_domains = [
            "adsense.google.com",
            "doubleclick.net",
            "blaze.com"
        ]

    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        for domain in self.blocked_domains:
            if domain in url:
                info.block(True)
                print(f"Bloqueado: {url}")
                return

# Janela principal
class MainWindow(QMainWindow):

    def navigate_home(self):
        browser = self.current_browser()
        if browser:
            browser.setUrl(QUrl("https://duckduckgo.com"))

    def check_home_loaded(self, ok):
        browser = self.current_browser()
        if not ok:
            QMessageBox.warning(self, "Erro", "Não foi possível carregar a página inicial.")
        try:
            # Tenta desconectar apenas se o browser existir
            if browser:
                browser.loadFinished.disconnect(self.check_home_loaded)
        except TypeError:
            # Ignora erro se o sinal não estiver conectado
            pass

    @staticmethod
    def is_valid_url(url):
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc) and bool(parsed.scheme)
        except:
            return False

    def navigate_to_url(self):
        if not self.tor_manager.fully_bootstrapped:
            QMessageBox.warning(self, "Aguarde", "Aguarde o Tor iniciar completamente")
            return
            
        browser = self.current_browser()
        if browser:
            url = self.url_bar.text().strip()
            
            # Se não for uma URL válida e não tiver domínio, faz busca no DuckDuckGo
            if not self.is_valid_url(url) and '.' not in url:
                search_query = url.replace(' ', '+')
                search_url = f'https://duckduckgo.com/?q={search_query}'
                browser.setUrl(QUrl(search_url))
                return
            
            # Continua com a lógica existente para URLs
            if not self.is_valid_url(url):
                if not url.startswith(('http://', 'https://')):
                    test_url = 'https://' + url
                    if self.is_valid_url(test_url):
                        self.try_https_url(url)
                        return
                QMessageBox.warning(self, "URL Inválida", "Por favor, insira uma URL válida.")
                return

            if not url.startswith(('http://', 'https://')):
                self.try_https_url(url)
            else:
                browser.setUrl(QUrl(url))

    def try_https_url(self, url):
        browser = self.current_browser()
        if browser:
            # Primeiro tenta com https
            https_url = 'https://' + url
            browser.loadFinished.connect(lambda ok: self.handle_load_result(ok, url))
            browser.setUrl(QUrl(https_url))

    def handle_load_result(self, ok, original_url):
        browser = self.current_browser()
        if browser:
            # Desconecta o sinal para não interferir em futuras navegações
            browser.loadFinished.disconnect()
            
            if not ok:
                # Se https falhou, tenta com http
                http_url = 'http://' + original_url
                browser.setUrl(QUrl(http_url))

    def create_new_tab(self, url=QUrl()):
        new_browser = QWebEngineView()
        page = WebEnginePage(self.default_profile, new_browser)
        new_browser.setPage(page)
        
        new_browser.setUrl(url)
        new_browser.urlChanged.connect(self.update_url)
        new_browser.urlChanged.connect(lambda q: self.update_tab_title(new_browser, q))
        
        if not url.isEmpty():
            new_browser.loadFinished.connect(self.check_home_loaded)
        
        i = self.tabs.addTab(new_browser, "Nova Aba")
        self.tabs.setCurrentIndex(i)
        return page

    def close_tab(self, index):
        if self.tabs.count() > 1:
            browser = self.tabs.widget(index)
            
            # Primeiro carrega about:blank para parar mídias e scripts
            browser.setUrl(QUrl('about:blank'))
            
            # Espera um momento para garantir que tudo foi interrompido
            def finish_closing():
                # Limpa o perfil se for uma aba isolada
                if browser in self.tab_profiles:
                    profile = self.tab_profiles[browser]
                    profile_path = profile.persistentStoragePath()
                    
                    # Remove o perfil do dicionário
                    del self.tab_profiles[browser]
                    
                    # Limpa os dados do perfil
                    browser.deleteLater()
                    profile.deleteLater()
                    
                    # Remove os arquivos do perfil
                    try:
                        if os.path.exists(profile_path):
                            import shutil
                            shutil.rmtree(os.path.dirname(profile_path))
                    except:
                        pass
                
                self.tabs.removeTab(index)
            
            # Agenda a finalização após um breve delay
            QTimer.singleShot(100, finish_closing)

    def update_tab_title(self, browser, q):
        i = self.tabs.indexOf(browser)
        if i != -1:
            self.tabs.setTabText(i, q.toString())


    def update_url(self, q):
        self.url_bar.setText(q.toString())

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowIcon(QIcon('icon.ico'))
        
        # Adicione estes logs
        print(f"Diretório atual: {os.getcwd()}")
        print(f"Diretório do executável: {os.path.dirname(sys.executable)}")
        if hasattr(sys, '_MEIPASS'):
            print(f"Diretório PyInstaller: {sys._MEIPASS}")
        
        # Inicializa o perfil padrão
        self.default_profile = QWebEngineProfile.defaultProfile()
        self.default_profile.setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # Aplica o script de override ao perfil padrão também
        self.default_profile.scripts().insert(self.create_override_script())
        
        # Configura o cache e cookies de forma mais eficiente
        self.default_profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        self.default_profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
        
        # Adiciona o bloqueador de anúncios
        self.ad_blocker = AdBlocker()
        self.default_profile.setUrlRequestInterceptor(self.ad_blocker)

        # Configura o gerenciador de downloads
        self.default_profile.downloadRequested.connect(self.handle_download)
        
        # Configura o diretório de cache e dados persistentes
        cache_path = os.path.join(os.path.expanduser('~'), '.emptybox')
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
        self.default_profile.setCachePath(os.path.join(cache_path, 'cache'))
        self.default_profile.setPersistentStoragePath(os.path.join(cache_path, 'storage'))
        
        # Configurações do perfil
        settings = self.default_profile.settings()
        self.setup_profile_settings(settings)
        
        # Inicializa as abas
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)
        
        # Configura a barra de navegação
        self.navbar = QToolBar()
        self.addToolBar(self.navbar)
        self.setup_navbar()
        
        # Lista de User Agents para rotação
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.2365.66"
        ]
        
        # Adiciona botão de nova aba
        new_tab_btn = QAction('📄 Nova Aba', self)
        new_tab_btn.triggered.connect(self.create_new_isolated_tab)
        self.navbar.addAction(new_tab_btn)
        
        # Dicionário para manter referência aos perfis
        self.tab_profiles = {}
        
        # Configura proxy global para Tor
        proxy = QNetworkProxy(QNetworkProxy.Socks5Proxy, "127.0.0.1", 9050)
        capabilities = (QNetworkProxy.ListeningCapability | 
                       QNetworkProxy.TunnelingCapability | 
                       QNetworkProxy.UdpTunnelingCapability | 
                       QNetworkProxy.HostNameLookupCapability)
        proxy.setCapabilities(QNetworkProxy.Capabilities(capabilities))
        QNetworkProxy.setApplicationProxy(proxy)
        
        # Força WebRTC a usar o proxy
        settings = self.default_profile.settings()
        settings.setAttribute(QWebEngineSettings.WebRTCPublicInterfacesOnly, False)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        
        # Inicia o Tor antes de criar as abas
        self.tor_manager = TorManager()
        if not self.tor_manager.start_tor():
            QMessageBox.critical(self, "Erro", "Não foi possível iniciar o Tor")
            sys.exit(1)
        
        # Cria a primeira aba depois de iniciar o Tor
        self.create_new_tab(QUrl("about:blank"))  # Começa com página em branco
        
        # Adiciona barra de status
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_tor_status()
        
        # Timer para atualizar status do Tor
        self.tor_timer = QTimer()
        self.tor_timer.timeout.connect(self.update_tor_status)
        self.tor_timer.start(5000)  # Atualiza a cada 5 segundos
        
        self.showMaximized()

    def handle_download(self, download):
        """Gerencia o download de arquivos"""
        # Exibe a caixa de diálogo para salvar o arquivo
        save_path, _ = QFileDialog.getSaveFileName(self, "Salvar arquivo como", download.path())
        if save_path:
            download.setPath(save_path)
            download.accept()
            QMessageBox.information(self, "Download Iniciado", f"Baixando: {save_path}")
        else:
            download.cancel()
            QMessageBox.warning(self, "Download Cancelado", "O download foi cancelado.")

    def setup_navbar(self):
        #botao de voltar
        back_btn = QAction('↩', self)
        back_btn.triggered.connect(lambda: self.current_browser().back())
        self.navbar.addAction(back_btn)

        #botao de avançar
        forward_btn = QAction('↪', self)
        forward_btn.triggered.connect(lambda: self.current_browser().forward())
        self.navbar.addAction(forward_btn)

        #botao de atualizar
        reload_btn = QAction('🔃', self)
        reload_btn.triggered.connect(lambda: self.current_browser().reload())
        self.navbar.addAction(reload_btn)

        #botao home
        home_btn = QAction('🏠', self)
        home_btn.triggered.connect(self.navigate_home)
        self.navbar.addAction(home_btn)

        #barra de endereço
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.navbar.addWidget(self.url_bar)

        # Botão de debug
        debug_btn = QAction('🔍 Debug', self)
        debug_btn.triggered.connect(self.show_profile_info)
        self.navbar.addAction(debug_btn)

    def current_browser(self):
        return self.tabs.currentWidget()

    def setup_profile_settings(self, settings):
        """Configura as settings padrão para um perfil"""
        settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)  # Desabilita plugins desnecessários
        settings.setAttribute(QWebEngineSettings.DnsPrefetchEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, False)
        settings.setAttribute(QWebEngineSettings.HyperlinkAuditingEnabled, False)  # Remove pings
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, False)
        settings.setAttribute(QWebEngineSettings.SpatialNavigationEnabled, False)  # Navegação espacial
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, False)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, True)
        settings.setAttribute(QWebEngineSettings.AutoLoadImages, True)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebRTCPublicInterfacesOnly, False)  # Desabilita interfaces públicas
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)  # Restringe acesso remoto
        settings.setAttribute(QWebEngineSettings.ScreenCaptureEnabled, False)  # Desabilita captura de tela
        settings.setAttribute(QWebEngineSettings.AllowGeolocationOnInsecureOrigins, False)  # Desabilita geolocalização
        settings.setAttribute(QWebEngineSettings.AllowWindowActivationFromJavaScript, True)
        settings.setAttribute(QWebEngineSettings.ShowScrollBars, True)
        
        # Configurações mais restritivas para WebRTC
        settings.setAttribute(QWebEngineSettings.WebRTCPublicInterfacesOnly, False)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.DnsPrefetchEnabled, False)  # Desabilita prefetch de DNS
        settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, False)
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, False)
        settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, False)  # Bloqueia conteúdo inseguro

    def create_new_isolated_tab(self):
        # Gera um ID único para o perfil
        profile_id = str(uuid.uuid4())
        
        # Cria um novo perfil isolado com parent
        profile = QWebEngineProfile(f"UniqueProfile_{profile_id}", self)
        profile.setPersistentStoragePath("")
        
        # Define um User Agent aleatório e headers em inglês
        profile.setHttpUserAgent(random.choice(self.user_agents))
        profile.setHttpAcceptLanguage("en-US,en;q=0.9")
        profile.cookieStore().deleteAllCookies()
        
        # Configura o diretório isolado para este perfil
        profile_path = os.path.join(os.path.expanduser('~'), '.emptybox', 'profiles', profile_id)
        if not os.path.exists(profile_path):
            os.makedirs(profile_path)
            
        profile.setPersistentStoragePath(os.path.join(profile_path, 'storage'))
        profile.setCachePath(os.path.join(profile_path, 'cache'))
        
        # Configura cache e cookies
        profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)  # Cache apenas em memória
        profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        
        # Adiciona o gerenciador de downloads para o perfil isolado
        profile.downloadRequested.connect(self.handle_download)
        
        # Configura as settings do perfil
        settings = profile.settings()
        self.setup_profile_settings(settings)
        
        # Antes de criar a página, vamos definir os scripts de injeção
        profile.scripts().insert(self.create_override_script())
        
        # Cria nova aba com o perfil isolado
        new_browser = QWebEngineView()
        page = WebEnginePage(profile, new_browser)
        new_browser.setPage(page)
        
        # Configura a nova aba
        new_browser.setUrl(QUrl("https://duckduckgo.com"))
        new_browser.urlChanged.connect(self.update_url)
        new_browser.urlChanged.connect(lambda q: self.update_tab_title(new_browser, q))
        
        # Adiciona a nova aba
        i = self.tabs.addTab(new_browser, "Nova Aba Privativa")
        self.tabs.setCurrentIndex(i)
        
        # Guarda referência ao perfil
        self.tab_profiles[new_browser] = profile
        
        # Configura proxy para Tor de forma mais segura
        proxy = QNetworkProxy(QNetworkProxy.Socks5Proxy, "127.0.0.1", 9050)
        capabilities = (QNetworkProxy.ListeningCapability | 
                       QNetworkProxy.TunnelingCapability | 
                       QNetworkProxy.UdpTunnelingCapability | 
                       QNetworkProxy.HostNameLookupCapability)
        proxy.setCapabilities(QNetworkProxy.Capabilities(capabilities))
        QNetworkProxy.setApplicationProxy(proxy)
        
        # Força WebRTC a usar o proxy nas configurações do perfil
        settings = profile.settings()
        settings.setAttribute(QWebEngineSettings.WebRTCPublicInterfacesOnly, False)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        
        # Configurações adicionais para o perfil
        profile.setPersistentStoragePath("")
        profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)  # Cache apenas em memória
        profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        profile.setUrlRequestInterceptor(self.ad_blocker)  # Adiciona bloqueador também nas abas isoladas
        
        return page

    def create_override_script(self):
        # Cria um novo script para injeção
        script = QWebEngineScript()
        
        # Define resoluções aleatórias comuns
        resolutions = [
            (1366, 768),   # HD
            (1920, 1080),  # Full HD
            (1440, 900),   # WXGA+
            (1680, 1050),  # WSXGA+
            (1280, 800),   # WXGA
        ]
        
        # Escolhe uma resolução aleatória
        width, height = random.choice(resolutions)
        
        # Script JavaScript para sobrescrever propriedades do navegador
        js_code = f"""
        (function() {{
            // Bloqueio mais agressivo do WebRTC
            const rtcBlock = {{
                createDataChannel: function() {{ return null; }},
                createOffer: function() {{ return null; }},
                createAnswer: function() {{ return null; }},
                setLocalDescription: function() {{ return null; }},
                setRemoteDescription: function() {{ return null; }}
            }};
            
            // Bloqueia todas as implementações do WebRTC
            window.RTCPeerConnection = undefined;
            window.webkitRTCPeerConnection = undefined;
            window.mozRTCPeerConnection = undefined;
            window.RTCDataChannel = undefined;
            window.DataChannel = undefined;
            window.webkitRTCPeerConnection = undefined;
            window.MediaStreamTrack = undefined;
            window.RTCSessionDescription = undefined;
            window.RTCIceCandidate = undefined;
            
            // Bloqueia mediaDevices
            Object.defineProperty(navigator, 'mediaDevices', {{
                value: undefined,
                writable: false,
                configurable: false
            }});
            
            // Bloqueia getUserMedia
            navigator.getUserMedia = undefined;
            navigator.webkitGetUserMedia = undefined;
            navigator.mozGetUserMedia = undefined;
            navigator.msGetUserMedia = undefined;
            
            // Bloqueia qualquer tentativa de criar novas conexões WebRTC
            Object.defineProperty(window, 'RTCPeerConnection', {{
                value: function() {{ return rtcBlock; }},
                writable: false,
                configurable: false
            }});
            
            // Sobrescreve propriedades de tela
            Object.defineProperty(window.screen, 'width', {{
                get: function() {{ return {width}; }}
            }});
            Object.defineProperty(window.screen, 'height', {{
                get: function() {{ return {height}; }}
            }});
            Object.defineProperty(window.screen, 'availWidth', {{
                get: function() {{ return {width}; }}
            }});
            Object.defineProperty(window.screen, 'availHeight', {{
                get: function() {{ return {height}; }}
            }});
            
            // Sobrescreve window.innerWidth/Height
            Object.defineProperty(window, 'innerWidth', {{
                get: function() {{ return {width}; }}
            }});
            Object.defineProperty(window, 'innerHeight', {{
                get: function() {{ return {height}; }}
            }});
            
            // Sobrescreve propriedades do objeto navigator
            const overrides = {{
                hardwareConcurrency: {random.randint(2, 8)},
                deviceMemory: {random.choice([2, 4, 8, 16])},
                platform: "{random.choice(['Win32', 'MacIntel', 'Linux x86_64'])}",
            }};
            
            for (let prop in overrides) {{
                Object.defineProperty(navigator, prop, {{
                    get: function() {{ return overrides[prop]; }}
                }});
            }}
        }})();
        """
        
        script.setSourceCode(js_code)
        script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setRunsOnSubFrames(True)
        
        return script

    def show_profile_info(self):
        current_browser = self.current_browser()
        if current_browser in self.tab_profiles:
            profile = self.tab_profiles[current_browser]
            # Executa JavaScript para obter a resolução atual
            current_browser.page().runJavaScript(
                "({width: window.screen.width, height: window.screen.height})",
                lambda result: self.show_profile_details(profile, result)
            )
        else:
            QMessageBox.information(self, "Informações do Perfil", 
                "Esta é uma aba com perfil padrão\n"
                f"User Agent: {self.default_profile.httpUserAgent()}\n"
                f"Caminho: {self.default_profile.persistentStoragePath()}")

    def show_profile_details(self, profile, screen_info):
        info = f"""
        Informações do Perfil:
        ---------------------
        ID do Perfil: {profile.storageName()}
        User Agent: {profile.httpUserAgent()}
        Resolução Simulada: {screen_info['width']}x{screen_info['height']}
        Caminho de Armazenamento: {profile.persistentStoragePath()}
        Tipo de Cache: {profile.httpCacheType()}
        Política de Cookies: {profile.persistentCookiesPolicy()}
        """
        QMessageBox.information(self, "Informações do Perfil", info)

    def update_tor_status(self):
        if not self.tor_manager.fully_bootstrapped:
            if self.tor_manager.check_bootstrap():
                self.tor_manager.fully_bootstrapped = True
                self.tor_manager.status = "Conectado"
                self.tor_manager.connection_progress = 100
                # Carrega a página inicial quando o Tor estiver pronto
                for i in range(self.tabs.count()):
                    browser = self.tabs.widget(i)
                    if browser.url().toString() == "about:blank":
                        browser.setUrl(QUrl("https://duckduckgo.com"))
            else:
                # Bloqueia navegação enquanto Tor não estiver pronto
                for i in range(self.tabs.count()):
                    browser = self.tabs.widget(i)
                    if browser.url().toString() != "about:blank":
                        browser.setUrl(QUrl("about:blank"))
        
        self.status_bar.showMessage(self.tor_manager.get_status_text())

    def closeEvent(self, event):
        self.tor_manager.stop_tor()
        event.accept()

# Inicialização da aplicação
app = QApplication(sys.argv)
QApplication.setApplicationName("EmptyBox")
app.setWindowIcon(QIcon('icon.ico'))
window = MainWindow()

app.exec_()

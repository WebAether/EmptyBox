# EmptyBox

EmptyBox é um navegador focado em anonimato, desenvolvido em Python utilizando PyQt5. Ele oferece diversas funcionalidades para garantir a privacidade do usuário.

## Funcionalidades Principais

- **Rede Tor Integrada**: Todo o tráfego é roteado pela rede Tor para anonimato de ponta a ponta.
- **Isolamento de Perfis por Aba**: Cada aba funciona de forma isolada, sem compartilhar cookies ou sessões.
- **Bloqueador de Anúncios**: Bloqueio básico de anúncios para uma experiência de navegação mais limpa.
- **User Agent Randomizado**: Cada aba recebe um User Agent diferente, dificultando o fingerprinting.
- **Simulação de Resoluções e Navegadores**: O navegador pode simular diferentes resoluções de tela, sistemas operacionais e versões de navegadores.
- **WebRTC Desativado**: Nenhum vazamento de IP público ou local, garantindo mais privacidade.
- **Bloqueio de Scripts**: Bloqueia scripts potencialmente perigosos para proteger o usuário.
- **Configurações de Privacidade Aprimoradas**: Recursos como WebGL, geolocalização e captura de tela estão desativados.

## Requisitos

- Python 3.8 ou superior
- PyQt5
- PyQtWebEngine

## Instalação

1. Clone este repositório:
   ```bash
   git clone https://github.com/WebAether/EmptyBox.git
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Execute o navegador:
   ```bash
   python EmptyBox.py
   ```

## Contribuindo

Contribuições são bem-vindas! Siga os passos abaixo:

1. Faça um fork do repositório.
2. Crie uma branch para sua feature ou correção de bug:
   ```bash
   git checkout -b minha-feature
   ```
3. Faça os commits das suas alterações:
   ```bash
   git commit -m "Descrição da alteração"
   ```
4. Envie suas alterações:
   ```bash
   git push origin minha-feature
   ```
5. Abra um Pull Request.

## Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## Contato

- **Autor**: WebAether  
- **Email**: [ian.mont2010@gmail.com](mailto:ian.mont2010@gmail.com)

---

_Desenvolvido com foco em anonimato e privacidade._

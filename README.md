# Integração MeLi e Chatwoot

![Versão](https://img.shields.io/badge/versão-2.2-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-yellow.svg)
![Docker](https://img.shields.io/badge/Docker-blue.svg?logo=docker)

Esta aplicação atua como uma ponte robusta entre plataformas de e-commerce (inicialmente, o **Mercado Livre**) e uma instância auto-hospedada do **Chatwoot**. O objetivo é centralizar o atendimento ao cliente, permitindo que a equipe de suporte gerencie todas as interações — desde perguntas em anúncios até o chat pós-venda — em uma única caixa de entrada unificada.

## ✨ Funcionalidades Principais

* **Comunicação Bidirecional:** Receba perguntas e mensagens do Mercado Livre no Chatwoot e responda diretamente pela interface do Chatwoot, com as respostas sendo enviadas de volta ao Mercado Livre.
* **Suporte a Anexos:** Envie e receba arquivos (imagens, PDFs) tanto do cliente para o Chatwoot quanto do Chatwoot para o cliente.
* **Chat Contínuo:** Todas as mensagens de uma mesma venda são agrupadas em uma única conversa no Chatwoot, mantendo o histórico completo e organizado.
* **Gerenciamento de Estado Inteligente:** Utiliza um banco de dados SQLite para "lembrar" de todas as interações processadas, evitando a duplicação de conversas, mesmo após reinicializações.
* **Arquitetura Escalável:** Projetado de forma modular para permitir a fácil adição de outros canais de venda (ex: Shopee, Amazon) no futuro.
* **Pronto para Produção:** Empacotado com Docker e Gunicorn, utilizando Supervisor para gerenciar os processos, garantindo estabilidade e reinicialização automática em caso de falhas.

---

## 🏛️ Arquitetura

A aplicação consiste em dois processos principais que rodam simultaneamente dentro de um contêiner Docker, gerenciados pelo Supervisor:

1.  **Poller (`main.py`):** Um script que verifica periodicamente a API do Mercado Livre em busca de novas perguntas e mensagens.
2.  **Webhook Listener (`webhook_server.py`):** Um servidor web Flask que recebe notificações (webhooks) do Chatwoot sempre que um agente envia uma resposta.

O estado da aplicação (tokens de autenticação e IDs de interações processadas) é armazenado de forma persistente em um banco de dados **SQLite**, utilizando um volume Docker para garantir que os dados não sejam perdidos entre deploys.

---

## 🚀 Guia de Implantação

Siga estes passos para configurar e implantar a integração.

### 1. Pré-requisitos

* Acesso de **Administrador** a uma instância do **Chatwoot** (self-hosted).
* Uma conta de vendedor no **Mercado Livre**.
* Uma **VPS** com Docker e um painel de gerenciamento como o [EasyPanel](https://easypanel.io/).
* Um **domínio ou subdomínio** apontado para o IP da sua VPS.
* Uma conta no **GitHub** (ou similar) para hospedar o código.
* Ferramenta de API como o [Postman](https://www.postman.com/downloads/) para a autorização inicial.

### 2. Configuração no Mercado Livre

1.  **Crie uma Aplicação:** Acesse o [Portal de Desenvolvedores do Mercado Livre](https://developers.mercadolivre.com.br/) e crie uma nova aplicação.
2.  **URI de Redirect:** No campo `URI de redirect`, insira a URL principal da sua aplicação (ex: `https://sua-integracao.com.br`).
3.  **Permissões (Scopes):** Conceda as seguintes permissões:
    * `offline_access` (obrigatório para renovação automática de token)
    * `read`
    * `write`
4.  **Anote as Credenciais:** Copie o **`App ID`** e a **`Chave secreta (Secret Key)`**.

### 3. Configuração no Chatwoot

1.  **Crie as Caixas de Entrada:**
    * Vá em **Configurações > Caixas de Entrada > Adicionar caixa de entrada** e selecione o canal **"API"**.
    * Crie duas caixas separadas:
        * **Caixa 1:** Nome `Mercado Livre - Perguntas`, Webhook URL `https://sua-integracao.com.br/webhook`.
        * **Caixa 2:** Nome `Mercado Livre - Vendas`, Webhook URL `https://sua-integracao.com.br/webhook`.
    * Anote o **ID de cada caixa de entrada** (visível na URL do navegador ao editá-las).
2.  **Crie o Webhook:**
    * Vá em **Configurações > Webhooks > Adicionar novo Webhook**.
    * **URL:** `https://sua-integracao.com.br/webhook`.
    * **Assinaturas:** Marque **apenas** a caixa `message_created`.
3.  **Obtenha o Token de Acesso:**
    * No seu perfil de usuário, copie o seu **`Token de Acesso`**.

### 4. Autorização Inicial (Apenas uma vez)

1.  **Construa a URL de Autorização:**
    ```
    [https://auth.mercadolibre.com/authorization?response_type=code&client_id=SEU_APP_ID&redirect_uri=SUA_URL_DE_REDIRECT](https://auth.mercadolibre.com/authorization?response_type=code&client_id=SEU_APP_ID&redirect_uri=SUA_URL_DE_REDIRECT)
    ```
2.  **Obtenha o Código:** Acesse a URL no navegador, autorize a aplicação e copie o código `TG-...` da barra de endereço após o redirecionamento.
3.  **Troque o Código pelos Tokens:** Use o Postman para fazer uma requisição `POST` para `https://api.mercadolibre.com/oauth/token` com os seguintes dados no corpo (`x-www-form-urlencoded`):
    * `grant_type`: `authorization_code`
    * `client_id`: Seu App ID.
    * `client_secret`: Sua Chave Secreta.
    * `code`: O código `TG-...` que você copiou.
    * `redirect_uri`: Sua URI de redirect.
4.  **Salve os Tokens:** Na resposta, copie os valores de **`access_token`** e **`refresh_token`**.

### 5. Implantação (EasyPanel)

1.  **Envie o Código:** Faça o push de todos os arquivos do projeto para o seu repositório no GitHub.
2.  **Crie o Serviço:** No EasyPanel, crie um novo serviço a partir do seu repositório Git.
3.  **Configure o Build:** Selecione a opção para usar o `Dockerfile` e exponha a porta `5000`.
4.  **Configure as Variáveis de Ambiente:** Na seção "Environment Variables", adicione todas as chaves do arquivo `.env.example` e preencha com as credenciais que você coletou nos passos anteriores.
5.  **Configure o Volume Persistente (Obrigatório):**
    * Vá para a aba **"Storage"**.
    * Adicione um **"Volume Mount"**.
    * **Name:** `meli-chatwoot-data` (ou um nome de sua preferência).
    * **Mount Path:** `/app`

6.  **Faça o Deploy:** Inicie o deploy. A aplicação será construída e iniciada. Monitore os logs para garantir que ambos os processos (`poller` e `webhook`) estão rodando.





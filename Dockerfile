# Dockerfile

# 1. Use uma imagem Python oficial como base
FROM python:3.10-slim

# 2. Defina o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3. Instale o supervisor, um gerenciador de processos
RUN apt-get update && apt-get install -y supervisor

# 4. Copie o arquivo de dependências e instale-as
#    Isso é feito antes para aproveitar o cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copie todo o resto do código da sua aplicação
COPY . .

# 6. Copie o arquivo de configuração do supervisor para o local correto
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 7. Exponha a porta que o nosso servidor web (Gunicorn) vai usar
EXPOSE 5000

# 8. O comando para iniciar a aplicação quando o contêiner rodar
#    Ele inicia o serviço do supervisor, que por sua vez inicia nossos scripts.
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

# Imagem base leve de Python
FROM python:3.12-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Copiar e instalar dependências primeiro (aproveita cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código fonte do bot
COPY bot.py config.py data_manager.py ./

# Criar a pasta de dados persistentes
RUN mkdir -p data

# Arrancar o bot
CMD ["python", "bot.py"]

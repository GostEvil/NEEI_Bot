# Imagem base leve de Python
FROM python:3.12-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Instalar dependências de sistema necessárias para a Verificação 1:
# - tesseract-ocr: motor OCR para extrair texto de imagens/PDFs digitalizados
# - tesseract-ocr-por: pacote de língua portuguesa para Tesseract
# - poppler-utils: necessário para o pdf2image converter páginas PDF em imagem
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências primeiro (aproveita cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código fonte do bot
COPY bot.py config.py data_manager.py verificacao1.py ./
COPY verification/ ./verification/

# Criar a pasta de dados persistentes
RUN mkdir -p data

# Arrancar o bot
CMD ["python", "bot.py"]

import os
import requests
from bs4 import BeautifulSoup
import re
import base64
from PIL import Image
from io import BytesIO

# 1. URL da página
URL = "https://en.namu.wiki/w/Italian%20Brainrot/%EB%93%B1%EC%9E%A5%20%EC%BA%90%EB%A6%AD%ED%84%B0"

# 2. Pastas de destino
IMAGES_DIR = "./images"
IMAGES_PNG_DIR = "./images/imagensPNG"
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(IMAGES_PNG_DIR, exist_ok=True)

# 3. Buscar página com cabeçalhos para evitar bloqueios
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
response = requests.get(URL, headers=headers)
if response.status_code != 200:
    print(f"Failed to fetch the page. Status code: {response.status_code}")
    exit()

soup = BeautifulSoup(response.text, "html.parser")

# 4. Para cada personagem:
# Os personagens têm <span id="NOME"> dentro de <h3>
for h3 in soup.find_all('h3', class_="m-nrnZ0o"):
    print(f"Found h3: {h3}")  # Log para depuração
    span = h3.find('span')
    if span and span.has_attr('id'):
        name = span['id'].strip()
        print(f"Found character name: {name}")  # Log para depuração

        # Procurar a imagem (a seguir ao título na maioria dos casos)
        next_img = h3.find_next('img')
        if next_img and next_img.has_attr('src'):
            img_url = next_img['src']
            print(f"Found image URL: {img_url}")  # Log para depuração

            # Nome do ficheiro seguro
            img_name_html = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name) + ".html"
            img_path_html = os.path.join(IMAGES_DIR, img_name_html)

            # Verificar se é uma imagem Base64
            if img_url.startswith("data:image"):
                try:
                    print(f"Saving Base64 image for {name} as HTML...")
                    # Salvar o conteúdo Base64 como .html
                    with open(img_path_html, 'w') as f:
                        f.write(img_url)
                    print(f"Image saved as {img_path_html}")

                    # Converter de HTML para PNG
                    base64_data = img_url.split(",")[1]
                    img_data = base64.b64decode(base64_data)
                    img = Image.open(BytesIO(img_data))
                    img_name_png = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name) + ".png"
                    img_path_png = os.path.join(IMAGES_PNG_DIR, img_name_png)
                    img.save(img_path_png)
                    print(f"Image converted and saved as {img_path_png}")
                except Exception as e:
                    print(f"Failed to save or convert Base64 image for {name}: {e}")
            else:
                # Download da imagem via URL
                try:
                    print(f"Downloading image for {name}...")
                    img_data = requests.get(img_url).content
                    # Salvar como HTML
                    with open(img_path_html, 'wb') as f:
                        f.write(img_data)
                    print(f"Image saved as {img_path_html}")

                    # Converter de HTML para PNG
                    img = Image.open(BytesIO(img_data))
                    img_name_png = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name) + ".png"
                    img_path_png = os.path.join(IMAGES_PNG_DIR, img_name_png)
                    img.save(img_path_png)
                    print(f"Image converted and saved as {img_path_png}")
                except Exception as e:
                    print(f"Failed to download or convert image for {name}: {e}")
        else:
            print(f"No image found for {name}")

print("Process finished.")
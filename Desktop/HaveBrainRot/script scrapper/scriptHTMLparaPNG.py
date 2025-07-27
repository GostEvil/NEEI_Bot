import os
from PIL import Image
from io import BytesIO
import base64

# Diretórios
IMAGES_DIR = r"C:\Users\nunos\Desktop\HaveBrainRot\script scrapper\images"
IMAGES_PNG_DIR = r"C:\Users\nunos\Desktop\HaveBrainRot\script scrapper\images\imagensPNG"

# Criar pasta de destino para PNGs, se não existir
os.makedirs(IMAGES_PNG_DIR, exist_ok=True)

# Converter arquivos HTML para PNG
for file_name in os.listdir(IMAGES_DIR):
    if file_name.endswith(".html"):
        file_path_html = os.path.join(IMAGES_DIR, file_name)
        try:
            # Ler conteúdo do arquivo HTML
            with open(file_path_html, 'r') as f:
                content = f.read()
            
            # Verificar se o conteúdo contém dados Base64 válidos
            if "data:image" in content and "," in content:
                base64_data = content.split(",")[1]
                try:
                    # Decodificar Base64 e abrir como imagem
                    img_data = base64.b64decode(base64_data)
                    img = Image.open(BytesIO(img_data))

                    # Salvar como PNG na pasta de destino
                    png_file_name = os.path.splitext(file_name)[0] + ".png"
                    png_file_path = os.path.join(IMAGES_PNG_DIR, png_file_name)
                    img.save(png_file_path)
                    print(f"Converted {file_name} to {png_file_name}")
                except Exception as e:
                    print(f"Failed to decode or save image for {file_name}: {e}")
            else:
                print(f"File {file_name} does not contain valid Base64 image data.")
        except Exception as e:
            print(f"Failed to process {file_name}: {e}")

print("Conversion process completed.")
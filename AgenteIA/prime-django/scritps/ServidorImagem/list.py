import logging
import os

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurações
GED_FOLDER = "E:/imagens/Ged"  # Pasta base para uploads
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}

# Garante que a pasta de uploads existe
os.makedirs(GED_FOLDER, exist_ok=True)

app.config["GED_FOLDER"] = GED_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/files", methods=["GET"])
def list_files():
    print("Iniciando list_files")

    # Lista todos os arquivos e pastas
    path = request.args.get("path", "")  # Permite especificar um subcaminho
    logger.info(f"Caminho recebido: {path}")

    path_parts = path.split("/")
    nome_arquivo = path_parts.pop(-1) if path_parts[-1] != "" else path_parts.pop(-2)
    logger.info(f"Nome do arquivo procurado: {nome_arquivo}")

    if not nome_arquivo:
        print("Nome do arquivo não fornecido")
        return jsonify({"error": "No file name"}), 400

    abs_path = f"{GED_FOLDER}/{'/'.join(path_parts)}"
    logger.info(f"Caminho absoluto usado para a busca: {abs_path}")

    try:
        # Se o caminho não existir, use o nome do caminho como filtro
        files_and_dirs = [f for f in os.listdir(abs_path) if nome_arquivo in f]
        logger.info(f"Arquivos e diretórios encontrados: {files_and_dirs}")
    except Exception as e:
        logger.exception(f"Erro ao listar arquivos e diretórios: {e}")
        return jsonify({"error": "Erro ao acessar o diretório"}), 500

    return jsonify(files_and_dirs)


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = request.form.get("path", "")  # Caminho de destino enviado no POST
        save_path = os.path.join(GED_FOLDER, path)
        os.makedirs(save_path, exist_ok=True)
        file.save(os.path.join(save_path, filename))
        return jsonify({"message": "File uploaded successfully"}), 201
    return jsonify({"error": "File type not allowed"}), 400


@app.route("/download/<path:filename>", methods=["GET"])
def download_file(filename):
    return send_from_directory(GED_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")

import os
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configurações
GED_FOLDER = "C:/IMAGENS/GED"  # Pasta base para uploads
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}

# Garante que a pasta de uploads existe
os.makedirs(GED_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = GED_FOLDER


def allowed_file(filename: str) -> bool:
    """Verifica se o arquivo é permitido."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/files", methods=["GET"])
def list_files():
    """Lista todos os arquivos e pastas."""
    path = request.args.get("path", "")  # Permite especificar um subcaminho
    path_parts = path.split("/")
    nome_arquivo = path_parts.pop(-1) if path_parts[-1] != "" else path_parts.pop(-2)

    if not nome_arquivo:
        return jsonify({"error": "No file name"}), 400

    abs_path = os.path.join(GED_FOLDER, *path_parts)

    # Se o caminho não existir, use o nome do caminho como filtro
    if not os.path.exists(abs_path):
        return jsonify({"error": "Path does not exist"}), 404

    files_and_dirs = [f for f in os.listdir(abs_path) if nome_arquivo in f]

    return jsonify(files_and_dirs)


@app.route("/upload", methods=["POST"])
def upload_file():
    """Faz upload de um arquivo."""
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
    """Faz download de um arquivo."""
    return send_from_directory(GED_FOLDER, filename, as_attachment=False)


if __name__ == "__main__":
    app.run(debug=True)

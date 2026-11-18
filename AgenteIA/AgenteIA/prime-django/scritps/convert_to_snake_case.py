import re
import os
import subprocess
import logging

logger = logging.getLogger(__name__)


def convert_to_snake_case(name):
    # Verifica se o nome já está em snake_case
    if re.match(r"^[a-z0-9_]+$", name):
        return name  # Retorna o nome original se já estiver em snake_case

    # Converte para snake_case evitando duplo underline
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    snake_case = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    # Remove qualquer duplo underline resultante da conversão
    snake_case = re.sub(r"__+", "_", snake_case)

    return snake_case


def rename_variables_and_methods(file_path, issues):
    logger.info(f"Processing file: {file_path}")
    try:
        with open(file_path, encoding="utf-8") as file:
            content = file.read()
    except UnicodeDecodeError as e:
        logger.info(f"Error reading {file_path}: {e}")
        return

    changes_made = False
    for line_number, name in issues:
        pattern = r"\b" + re.escape(name) + r"\b"
        snake_case_name = convert_to_snake_case(name)
        new_content = re.sub(pattern, snake_case_name, content)
        if content != new_content:
            logger.info(f"Renamed {name} to {snake_case_name} at line {line_number}")
            changes_made = True
            content = new_content

    if changes_made:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        logger.info(f"Finished processing file: {file_path} with changes.")
    else:
        logger.info(f"No changes made to file: {file_path}")


def process_directory(directory, ignore_dirs):
    absolute_directory = os.path.abspath(directory)
    logger.info(f"Checking directory: {absolute_directory}")
    if not os.path.exists(absolute_directory):
        logger.info(f"Directory does not exist: {absolute_directory}")
        return

    for root, dirs, files in os.walk(absolute_directory):
        if any(ignored_dir in root for ignored_dir in ignore_dirs):
            logger.info(f"Ignoring directory: {root}")
            continue

        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                logger.info(f"Found Python file: {file_path}")

                result = subprocess.run(["ruff", file_path], capture_output=True, text=True)
                ruff_output = result.stdout

                issues = []
                for line in ruff_output.splitlines():
                    if "N802" in line or "N803" in line or "N806" in line:
                        match = re.search(
                            r"(\d+):\d+:\sN80[236]\s(?:Function name|Argument name|Variable)\s`(.+?)`\s", line
                        )
                        if match:
                            line_number = int(match.group(1))
                            variable_name = match.group(2).strip()
                            issues.append((line_number, variable_name))

                if issues:
                    rename_variables_and_methods(file_path, issues)


# Defina o caminho correto para o diretório de apps
apps_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps"))

# Lista de diretórios a serem ignorados
ignore_dirs = [".venv", "__pycache__", "migrations", "static", "media"]

# Processar o diretório
logger.info(f"Starting to process directory: {apps_directory}")
process_directory(apps_directory, ignore_dirs)

print("Finished processing all files.")

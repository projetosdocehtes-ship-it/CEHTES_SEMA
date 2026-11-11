@echo off

:: Atualize o pip
python -m pip install --upgrade pip

:: Instale as dependências listadas no requirements.txt
pip install -r requirements_dev.txt

:: Adicione outras configurações ou instalações, se necessário

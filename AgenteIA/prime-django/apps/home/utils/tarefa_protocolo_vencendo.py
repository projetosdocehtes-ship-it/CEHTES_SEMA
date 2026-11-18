import requests

url = "http://192.168.1.73:8000/protocolos/verificar_protocolos_vencendo/"

response = requests.get(url)

if response.status_code == 200:
    print("Tarefa executada!")
else:
    print("ERRO ao executar a tarefa.")

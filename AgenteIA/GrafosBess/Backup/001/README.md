# Simulador Profissional de Usina FV + BESS

Aplicação full stack com:

- Backend em Django + Django REST Framework
- Frontend em React + Vite + React Flow
- Editor visual com drag-and-drop
- Catálogo de componentes
- Inspetor lateral
- Salvamento de layout em JSON
- Simulação básica de validação técnica
- Seed automática com componentes de exemplo

## Estrutura

- `backend/`
- `frontend/`

## 1) Rodando o backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

pip install -r requirements.txt
python manage.py makemigrations energia
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Backend disponível em:

- `http://127.0.0.1:8000/api/`
- `http://127.0.0.1:8000/admin/`

## 2) Rodando o frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend disponível em:

- `http://127.0.0.1:5173`

## Login admin

Crie com:

```bash
python manage.py createsuperuser
```

## Funcionalidades do MVP profissional

- Arrastar componentes da lateral para o diagrama
- Conectar componentes
- Selecionar nó
- Editar rótulo e fabricante/modelo exibidos
- Remover nó
- Salvar layout no Django
- Reabrir layout salvo
- Rodar simulação
- Alertas básicos:
  - bateria ligada diretamente em inversor FV
  - PCS ausente entre bateria e barramento
  - falta de POC
  - falta de transformador
  - equipamento sem dados essenciais

## Próximas evoluções sugeridas

- Nós SVG customizados por símbolo elétrico
- Camadas de ligação por tipo: CC, CA, MT, sinal
- Cálculo de strings FV
- Curvas de carga e despacho da bateria
- Relatórios PDF
- Multiusuário e multiempresa
- Catálogo importável por Excel/CSV
```

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
- Botão para gerar automaticamente um diagrama base

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
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

## 2) Rodando o frontend

```bash
cd frontend
npm install
npm run dev
```

## Geração automática do diagrama

Na barra superior existe o botão:

- **Gerar diagrama base**

Ele cria automaticamente um fluxo visual semelhante a um diagrama unifilar de referência, com esta sequência:

- Campo FV → String Box → Seccionadora CC → DPS CC → Inversor FV → Barramento BT
- Banco de Baterias → PCS → Barramento BT
- Barramento BT → Transformador → Proteção MT → POC

Essa montagem usa os componentes cadastrados no banco.

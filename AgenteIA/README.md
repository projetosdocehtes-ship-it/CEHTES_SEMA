# CEHTES SEMA — Simulador e ferramentas de engenharia

Este diretório reúne o simulador visual de usinas fotovoltaicas e armazenamento de energia, os motores de análise de microrredes e a aplicação Prime Django. O objetivo é montar projetos, configurar equipamentos, executar cenários e consultar resultados técnicos em uma interface web.

**FV** significa geração fotovoltaica; **BESS** é o sistema de armazenamento de energia em baterias; **MPPT** é o controle de rastreamento do ponto de máxima potência dos módulos FV.

## O que o projeto oferece

- **GrafosBess:** editor visual de diagramas, catálogo de componentes, configuração do projeto e simulação de sistemas com FV, bateria, inversor, carga, rede e gerador diesel.
- **Resultados:** gráficos, relatórios e análise automática dos resultados das simulações, conforme o motor escolhido.
- **Cenários e transitório:** estudos de falha da rede, resposta do BESS e do diesel e recuperação após o retorno da rede, conforme a configuração do projeto.
- **Equipamentos - Projeto:** integração com os modelos de `prime-django/apps/Equipamentos`, usando o projeto selecionado para gerar gráficos de equipamentos. Inclui modelos de arranjo FV, MPPT, bateria, inversor, elo CC e sequência de partida.
- **Microrredes:** análises de fluxo de potência, falhas, dinâmica e aspectos tarifários/econômicos.
- **POP / Ajuda:** procedimento operacional para consulta na tela e download do documento.
- **Prime Django:** aplicação web com módulos próprios, incluindo os motores de Equipamentos e Análise Econômica.

Os resultados dependem dos parâmetros e das simplificações de cada modelo. O cenário de carga de 120 kW é um caso de estudo; não representa uma garantia de atendimento para qualquer dimensionamento ou condição de operação.

## Estrutura das pastas

```text
CEHTES_SEMA/
└── AgenteIA/                      # Este README
    ├── GrafosBess/
    │   ├── backend/              # Django, API e integração com os motores
    │   ├── frontend/             # React, Vite e editor visual
    │   ├── docs/pop/             # Documento do procedimento operacional
    │   └── iniciar.bat           # Inicialização do simulador
    ├── prime-django/
    │   ├── apps/Equipamentos/    # Modelos e simulação de equipamentos
    │   ├── apps/AnaliseEconomica/
    │   └── start_cehtes.bat      # Inicialização da aplicação Django
    ├── microrredes/              # Motores, entradas, documentação e testes
    ├── AgenteIA/                 # Agentes e aplicações adicionais preservados
    ├── Publicar-CEHTES.bat       # Preparação, revisão e publicação no GitHub
    └── COMO-PUBLICAR-CEHTES.txt
```

Mantenha `GrafosBess`, `prime-django` e `microrredes` lado a lado. A integração localiza os motores por esses caminhos relativos. A pasta interna `AgenteIA/AgenteIA` é parte do conteúdo preservado; os dois BATs descritos aqui pertencem às pastas diretamente abaixo deste README.

## Como instalar

### Instalador para outro computador Windows

Baixe [Instalar-CEHTES.bat](Instalar-CEHTES.bat) e [Instalar-CEHTES.ps1](Instalar-CEHTES.ps1) para a **mesma pasta**. Com Git, Python 3.12 (reconhecido por `py -3.12`) e Node.js com npm instalados, execute o BAT e escolha uma pasta nova de destino. Ele baixa a `main`, mantém as subpastas, prepara os ambientes Python, o banco do GrafosBess e o frontend. O PostgreSQL e o `.env` do Prime Django precisam ser configurados separadamente.

Consulte [COMO-INSTALAR-CEHTES.txt](COMO-INSTALAR-CEHTES.txt) para exemplos, instalação opcional de microrredes e configuração do banco. A instalação completa em uma máquina limpa ainda precisa ser validada; falhas de dependências são exibidas e interrompem o instalador.

### 1. Pré-requisitos e obtenção do código

O roteiro abaixo usa **Windows e Prompt de Comando (CMD)**. Instale Git, Python com o inicializador `py` e Node.js com npm. Para reproduzir o ambiente do Prime Django, use Python **3.12** (o ambiente local consultado usa 3.12.8). O frontend usa Vite 5; sua faixa de Node declarada é 18 ou 20+, devendo ser escolhida uma versão ainda mantida e compatível.

O Prime Django completo também precisa de **PostgreSQL**, com um banco e um usuário preparados. O backend do GrafosBess utiliza **SQLite**, criado pelas migrações.

```bat
git clone https://github.com/projetosdocehtes-ship-it/CEHTES_SEMA.git
cd CEHTES_SEMA\AgenteIA
```

Nos exemplos seguintes, substitua `C:\caminho\CEHTES_SEMA\AgenteIA` pela pasta clonada. Bancos locais, credenciais, ambientes virtuais e `node_modules` não acompanham o clone. As migrações criam a estrutura do banco, mas não restauram os dados privados de uma instalação existente.

### 2. Preparar o Prime Django

```bat
cd /d C:\caminho\CEHTES_SEMA\AgenteIA\prime-django
py -3.12 -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Crie `prime-django\.env` localmente com os valores do seu ambiente, por exemplo:

```dotenv
DEBUG=True
SECRET_KEY=SUBSTITUA_POR_UMA_CHAVE_ALEATORIA_LOCAL
DB_USERNAME=seu_usuario_postgresql
DB_PASS=sua_senha_local
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=cehtes_sema
```

Gere uma chave para substituir o exemplo:

```bat
venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

O banco indicado em `DB_NAME` precisa existir antes das migrações. Configure integrações adicionais apenas se utilizar os módulos correspondentes. Não publique o `.env`. O `.env` de publicação que fica ao lado deste README configura os scripts Git e é diferente do `.env` da aplicação.

O `requirements.txt` do Prime Django contém muitas bibliotecas sem versões fixadas e algumas dependências nativas. Uma instalação nova pode exigir ajustes de compatibilidade; este roteiro foi conferido no código, mas não substitui uma validação em uma máquina limpa. A configuração atual também imprime a URL do PostgreSQL na inicialização: evite compartilhar esse trecho do terminal, pois ele pode conter a senha.

### 3. Preparar o GrafosBess

```bat
cd /d C:\caminho\CEHTES_SEMA\AgenteIA\GrafosBess\backend
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_data

cd ..\frontend
npm install
```

O backend declara Django 5.1.7, Django REST Framework e django-cors-headers. O frontend utiliza React 18, Vite 5 e React Flow. Use ambientes separados: o Prime Django declara Django 5.0.9.

O motor **Equipamentos - Projeto** procura `prime-django\venv\Scripts\python.exe`. Prepare esse ambiente mesmo quando for usar somente a interface do GrafosBess. Essa integração executa um processo Python local; não exige que o servidor web da porta 8001 esteja aberto. Se o ambiente não existir, o código tenta o Python do backend, que pode não conter as dependências necessárias.

### 4. Preparar as análises de microrredes

Para usar os motores dessa pasta:

```bat
cd /d C:\caminho\CEHTES_SEMA\AgenteIA\microrredes
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .
```

Consulte também o [README de microrredes](microrredes/README.md) para entradas e comandos de cada análise.

## Como subir os serviços com os BATs

### Prime Django — start_cehtes.bat

No computador usado no desenvolvimento:

```bat
cd /d C:\Cethes\CEHTES_SEMA\CEHTES_SEMA\AgenteIA\prime-django
call start_cehtes.bat
```

O BAT entra na própria pasta, exige o ambiente `venv`, ativa-o, verifica a presença do Django, executa `migrate` e `collectstatic --noinput` e inicia `runserver 8001`. Também abre o navegador em:

**http://127.0.0.1:8001/calendar/**

Ele só tenta instalar o `requirements.txt` se o Django não estiver instalado. Por isso, faça a instalação completa das dependências na preparação inicial. Se precisar de um usuário administrador, crie-o com `venv\Scripts\python.exe manage.py createsuperuser` após as migrações.

### Simulador GrafosBess — iniciar.bat

```bat
cd /d C:\Cethes\CEHTES_SEMA\CEHTES_SEMA\AgenteIA\GrafosBess
call iniciar.bat
```

**Execute a partir da pasta `GrafosBess`**, pois esse BAT usa caminhos relativos. Ele prepara ou recria `backend\.venv` quando necessário, instala dependências do backend, aplica migrações, executa `seed_data` e abre terminais para a API e o frontend. Instala os pacotes npm quando `node_modules` não existe.

| Serviço | Endereço | Uso |
| --- | --- | --- |
| Prime Django | http://127.0.0.1:8001/calendar/ | Aplicação Django |
| API GrafosBess | http://127.0.0.1:8000 | Backend do simulador |
| Interface GrafosBess | http://127.0.0.1:5173 | Editor, simulações e resultados |

Os serviços podem funcionar simultaneamente, pois usam portas diferentes. Aguarde as mensagens de inicialização nos terminais; a mensagem final do BAT, sozinha, não comprova que todos os serviços iniciaram. Caso a porta 5173 esteja ocupada, confira no terminal o endereço efetivamente informado pelo Vite.

Para encerrar, pressione **Ctrl+C em cada terminal de serviço**. Os BATs executam servidores de desenvolvimento local; uma publicação do site na internet exige uma configuração própria de produção.

## Exemplo de uso do simulador

1. Inicie o GrafosBess e abra a interface na porta 5173.
2. Selecione ou crie um projeto, monte o diagrama e confira conexões, parâmetros e unidades dos equipamentos.
3. Para estudar a perda da rede, configure o cenário de falha, o período de interrupção e os parâmetros do BESS e do diesel no estudo transitório.
4. Execute a análise desejada. Para os modelos de equipamentos, use **Executar Equipamentos - Projeto**.
5. Abra **Resultados** e verifique potência demandada e atendida, déficit, atuação dos equipamentos e recuperação. A disponibilidade de cada grandeza depende do motor utilizado.
6. Consulte **POP / Ajuda** para o procedimento passo a passo e o download do documento.

Para o caso de 120 kW, confira especialmente a unidade da carga, limites do inversor e dos MPPTs, arranjo FV, potência e energia disponíveis na bateria, estado de carga e condições de partida. A pré-carga adia a conexão da carga até a estabilização: diferencie esse intervalo de preparação de uma interrupção após a conexão.

## Problemas comuns

| Sintoma | O que conferir |
| --- | --- |
| “Virtualenv não encontrado” no Prime Django | Crie `prime-django\venv` e instale seu `requirements.txt`. |
| Erro ao conectar no PostgreSQL | Serviço ativo, banco criado e variáveis `DB_*` no `.env` do Prime Django. |
| Falha ao localizar `backend` ou `frontend` | Execute `iniciar.bat` a partir de `GrafosBess`. |
| Interface abre, mas não carrega dados | Verifique o terminal da API na porta 8000 e as migrações. |
| Erro ao executar Equipamentos | Confira as pastas irmãs e as dependências de `prime-django\venv`. A execução grava arquivos em `GrafosBess/backend/media/equipamentos/`. |
| Porta ocupada | Encerre a execução anterior antes de iniciar outra instância. |

## Atualizar e publicar código

O botão ou BAT de inicialização sobe os serviços **localmente**. Publicar código no GitHub é outra operação, feita pelos scripts `Publicar-CEHTES.bat` e auxiliares. Consulte [COMO-PUBLICAR-CEHTES.txt](COMO-PUBLICAR-CEHTES.txt) antes de usá-los e confira a branch configurada no `.env` local de publicação.

O repositório mantém os caminhos das subpastas; arquivos ignorados, credenciais, bancos locais e dependências instaladas ficam fora da publicação. Para atualizar um clone sem alterações pendentes, use `git pull --ff-only` e reinstale dependências quando os respectivos arquivos de requisitos mudarem.

## Documentação complementar

- [GrafosBess](GrafosBess/README.md)
- [Microrredes](microrredes/README.md)
- [POP — documento Word](GrafosBess/docs/pop/POP_SIM_001_FV_BESS.docx)
- [Iniciar Prime Django](prime-django/start_cehtes.bat)
- [Iniciar GrafosBess](GrafosBess/iniciar.bat)

# App Minutas

## Descrição

O app **Minutas** faz parte do projeto **Cartórios** e é responsável pela gestão das minutas dos documentos produzidos pelos cartórios, como certidões, fichas de Projeto CEHTES, entre outros.

Este app foi desenvolvido utilizando Django, Crispy Forms, django-tables2 e é compatível com o Django-Tenants para suportar uma arquitetura multitenant.

## Funcionalidades

- Cadastro de tipos de minutas (certidões, registros, etc.)
- Interface para edição de conteúdo das minutas
- Relacionamento com outros apps para inserção dinâmica de dados nas minutas
- Suporte a múltiplos tenants (cartórios)

## Modelos

### Minuta

- `nome`: Nome descritivo da minuta.
- `tipo`: Tipo da minuta (certidão, registro, etc.)
- `conteudo`: Conteúdo em formato de texto para a minuta.

### TipoMinuta

- `nome`: Nome descritivo do tipo da minuta.

## Views

Este app utiliza Class-Based Views (CBV) para todas as funcionalidades.

- `MinutaListView`: Exibe a lista de minutas.
- `MinutaCreateView`: Para criação de novas minutas.
- `MinutaUpdateView`: Para atualização de minutas existentes.

## Como Utilizar

1. Clone o projeto Cartórios.
2. Navegue até o diretório do app Minutas.
3. Rode as migrações para criar as tabelas necessárias.
4. Inicie o servidor Django.
5. Acesse o painel administrativo para começar a criar minutas.

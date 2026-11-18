import json
from io import BytesIO

from django.db.models import Q
from django.utils import timezone

from apps.cartorios.models import Usuario
from apps.home.models import Contribuintes, Livro02, Lote, Rua, Rural
from apps.integracoes.models import Pgnm


# Inicio para gerar todos os dados do livro 4 que serao enviados para a ONR
def gerar_lote_livro_4_onr(usuario_id):
    tipo_registro = "M"
    numero_livro = "2"

    # FILTRAR DE USUARIO
    usuario = Usuario.objects.get(pk=usuario_id)

    # NUMERO_CARTORIO  1 ou 2
    numero_cartorio = usuario.cartorio.numero_cartorio

    # FILTRAR TODOS OS REGISTROS NAO ENVIADOS NO PGNM
    registros = Livro02.objects.filter(
        Q(data_envio_livro_4__isnull=True, tipo=tipo_registro, cartorio=numero_cartorio)
        | Q(enviar_livro_4=True, tipo=tipo_registro, cartorio=numero_cartorio),
    )

    if registros.exists():
        return None

    dados = {
        "INDICADOR_REAL": {
            "cns": usuario.cartorio.cns,  # cns DO CARTORIO
            "REAL": gerar_vetor_real(
                numero_livro,
                registros,
                usuario.cartorio.cns,
                usuario.cartorio.municipio.uf.sigla,
                usuario.cartorio.municipio_id,
            ),
        },
    }

    # Prepare the JSON data
    json_data = json.dumps(dados)

    # Use BytesIO to create file in memory
    response_file = BytesIO()
    response_file.write(json_data.encode("utf-8"))  # Write the JSON data to the buffer
    response_file.seek(0)  # Go to the start of the buffer

    return response_file


# Tipo de Envio
def get_envio() -> int:
    # 0 = ATUAL
    # 1 = ATUALIZAÇÃO
    # 2 = ENCERRADA/CANCELADA
    return 0


# Obter o CNM do IMOVEL
# INFORMAR: cns CARTORIO, livro DO CARTORIO, numero DO IMOVEL
def get_cnm_onr(cns, livro, numero):
    numero_gerado = str(cns).zfill(6) + str(livro).zfill(1) + str(numero).zfill(7)
    numero_gerado_formatado = (
        str(cns).zfill(6) + "." + str(livro).zfill(1) + "." + str(numero).zfill(7)
    )
    valor_gerado = int(numero_gerado) * 100
    valor_gerado_restante = valor_gerado % 97
    valor_gerado_restante = 98 - valor_gerado_restante
    numero_retornar = (
        numero_gerado_formatado + "-" + str(valor_gerado_restante).zfill(2)
    )

    return str(numero_retornar)


def get_nome_fazenda(chave, coluna):
    # Suponhamos que 'coluna' seja um campo na model 'Rural'.
    # E 'chave' é o ID do imóvel que você deseja consultar.
    value = Rural.objects.filter(imovel_id=chave).values_list(coluna, flat=True)

    return str(value[0]).strip() if value else ""


# Obter o TIPO
def get_registro_tipo(get_tipo_registro) -> int | None:
    # 1 = Matrícula
    if get_tipo_registro == "M":
        return 1
    # 2 = Matrícula MÃE
    # AINDA NAO IMPLEMENTANDO
    # 3 = Livro 3-reg-aux
    elif get_tipo_registro == "A":
        return 3
    # 4 = Transcrição
    elif get_tipo_registro == "T":
        return 4
    return None


# Obter o TIPO
def get_tipo_imovel(classe) -> int:
    #  1 = casa
    #  2 = apartamento
    #  3 = loja
    #  4 = sala/conjunto
    #  5 = terreno/fração
    #  6 = galpão
    #  7 = prédio comercial
    #  8 = prédio residencial
    #  9 = fazenda/sítio/chácara
    # 10 = vaga
    # 11 = depósito

    if classe == "R":
        return 9
    else:
        return 5


# Obter o TIPO
def get_localizacao(classe) -> int:
    # 1 = RURAL
    if classe == "R":
        return 1
    # 0 = URBANO
    else:
        return 0


# Obter o Logradouro
def get_logradouro(classe) -> int:
    # 1 Acampamento
    # 2 Acesso
    # 3 Açude
    # 4 Adro
    # 5 Aeroporto
    # 6 Afluente
    # 7 Aglomerado
    # 8 Agrovila
    # 9 Alagado
    # 10 Alameda
    # 11 Aldeia
    # 12 Aleia
    # 13 Alto
    # 14 Anel
    # 15 Antiga
    # 16 Antigo
    # 17 Área
    # 18 Areal
    # 19 Arraial
    # 20 Arroio
    # 21 Artéria
    # 22 Assentamento
    # 23 Atalho
    # 24 Aterro
    # 25 Autódromo
    # 26 Avenida
    # 27 Baia
    # 28 Bairro
    # 29 Baixa
    # 30 Baixada
    # 31 Baixadão
    # 32 Baixão
    # 33 Baixo
    # 34 Balão
    # 35 Balneário
    # 36 Barra
    # 37 Barragem
    # 38 Barranca
    # 39 Barranco
    # 40 Barreiro
    # 41 Barro
    # 42 Beco
    # 43 Beira
    # 44 Beirada
    # 45 Belvedere
    # 46 Bloco
    # 47 Bocaina
    # 48 Boqueirão
    # 49 Bosque
    # 50 Boulevard
    # 51 Brejo
    # 52 Buraco
    # 53 Cabeceira
    # 54 Cachoeira
    # 55 Cachoeirinha
    # 56 Cais
    # 57 Calcada
    # 58 Calçadão
    # 59 Caminho
    # 60 Campo
    # 61 Canal
    # 62 Canteiro
    # 63 Capão
    # 64 Capoeira
    # 65 Cartódromo
    # 66 Central
    # 67 Centro
    # 68 Cerca
    # 69 Cerrado
    # 70 Cerro
    # 71 Chácara
    # 72 Chapada
    # 73 Chapadão
    # 74 Charco
    # 75 Cidade
    # 76 Circular
    # 77 Cohab
    # 78 Colina
    # 79 Colônia
    # 80 Comunidade
    # 81 Condomínio
    # 82 Conjunto
    # 83 Continuação
    # 84 Contorno
    # 85 Corredor
    # 86 Córrego
    # 87 Costa
    # 88 Coxilha
    # 89 Cruzamento
    # 90 Descida
    # 91 Desvio
    # 92 Dique
    # 93 Distrito
    # 94 Divisa
    # 95 Divisão
    # 96 Divisor
    # 97 Edifício
    # 98 Eixo
    # 99 Elevado
    # 100 Encosta
    # 101 Engenho
    # 102 Enseada
    # 103 Entrada
    # 104 Entreposto
    # 105 Entroncamento
    # 106 Escada
    # 107 Escadão
    # 108 Escadaria
    # 109 Escadinha
    # 110 Espigão
    # 111 Esplanada
    # 112 Esquina
    # 113 Estação
    # 114 Estacionamento
    # 115 Estádio
    # 116 Estância
    # 117 Estrada
    # 118 Extensão
    # 119 Faixa
    # 120 Favela
    # 121 Fazenda
    # 122 Feira
    # 123 Ferrovia
    # 124 Final
    # 125 Floresta
    # 126 Folha
    # 127 Fonte
    # 128 Fortaleza
    # 129 Freguesia
    # 130 Fundos
    # 131 Furo
    # 132 Galeria
    # 133 Gameleira
    # 134 Garimpo
    # 135 Gleba
    # 136 Granja
    # 137 Grota
    # 138 Habitacional
    # 139 Haras
    # 140 Hipódromo
    # 141 Horto
    # 142 Igarapé
    # 143 Ilha
    # 144 Inaplicável
    # 145 Invasão
    # 146 Jardim
    # 147 Jardinete
    # 148 Ladeira
    # 149 Lado
    # 150 Lago
    # 151 Lagoa
    # 152 Lagoinha
    # 153 Largo
    # 154 Lateral
    # 155 Leito
    # 156 Ligação
    # 157 Limeira
    # 158 Limite
    # 159 Limites
    # 160 Linha
    # 161 Lote
    # 162 Loteamento
    # 163 Lugarejo
    # 164 Maloca
    # 165 Manancial
    # 166 Mangue
    # 167 Margem
    # 168 Margens
    # 169 Marginal
    # 170 Marina
    # 171 Mata
    # 172 Mato
    # 173 Módulo
    # 174 Monte
    # 175 Morro
    # 176 Muro
    # 177 Não Especificado
    # 178 Núcleo
    # 179 Oca
    # 180 Oleoduto
    # 181 Olho
    # 182 Olhos
    # 183 Orla
    # 184 Outros
    # 185 Paco
    # 186 Palafita
    # 187 Pântano
    # 188 Parada
    # 189 Paradouro
    # 190 Paralela
    # 191 Parque
    # 192 Particular
    # 193 Passagem
    # 194 Passarela
    # 195 Passeio
    # 196 Passo
    # 197 Pasto
    # 198 Pátio
    # 199 Pavilhão
    # 200 Pedra
    # 201 Pedras
    # 202 Pedreira
    # 203 Penhasco
    # 204 Perimetral
    # 205 Perímetro
    # 206 Perto
    # 207 Planalto
    # 208 Plataforma
    # 209 Ponta
    # 210 Ponte
    # 211 Ponto
    # 212 Porto
    # 213 Posto
    # 214 Povoado
    # 215 Praça
    # 216 Praia
    # 217 Projeção
    # 218 Projetada
    # 219 Projeto
    # 220 Prolongamento
    # 221 Propriedade
    # 222 Próximo
    # 223 Quadra
    # 224 Quarteirão
    # 225 Quilombo
    # 226 Quilometro
    # 227 Quinta
    # 228 Quintas
    # 229 Rachão
    # 230 Ramal
    # 231 Rampa
    # 232 Rancho
    # 233 Recanto
    # 234 Região
    # 235 Represa
    # 236 Residencial
    # 237 Reta
    # 238 Retiro
    # 239 Retorno
    # 240 Riacho
    # 241 Ribanceira
    # 242 Ribeirão
    # 243 Rincão
    # 244 Rio
    # 245 Rocha
    # 246 Rochedo
    # 247 Rodovia
    # 248 Rotatória
    # 249 Rotula
    # 250 Rua
    # 251 Ruela
    # 252 Saco
    # 253 Saída
    # 254 Sanga
    # 255 Sede
    # 256 Sem
    # 257 Seringal
    # 258 Serra
    # 259 Sertão
    # 260 Servidão
    # 261 Seta
    # 262 Setor
    # 263 Sitio
    # 264 Sopé
    # 265 Subida
    # 266 Superquadra
    # 267 Tapera
    # 268 Terminal
    # 269 Terra
    # 270 Terreno
    # 271 Terrenos
    # 272 Transversal
    # 273 Travessa
    # 274 Travessão
    # 275 Travessia
    # 276 Trecho
    # 277 Trevo
    # 278 Trilha
    # 279 Trilho
    # 280 Trilhos
    # 281 Trincheira
    # 282 Túnel
    # 283 Unidade
    # 284 Usina
    # 285 Vala
    # 286 Valão
    # 287 Vale
    # 288 Vargem
    # 289 Variante
    # 290 Várzea
    # 291 Velódromo
    # 292 Vereda
    # 293 Vertente
    # 294 Via
    # 295 Viaduto
    # 296 Vicinal
    # 297 Viela
    # 298 Vila
    # 299 Vilarejo
    # 300 Volta
    # 301 Zona
    # 302 1a Travessa da Avenida
    # 303 1a Travessa da Rua
    # 304 2a Travessa da Avenida
    # 305 2a Travessa da Rua
    # 306 3a Travessa da Avenida
    # 307 3a Travessa da Rua
    # 308 4a Travessa da Avenida
    # 309 4a Travessa da Rua
    # 310 5a Travessa da Avenida
    # 311 5a Travessa da Rua
    if classe == "R":
        return 121
    else:
        return 250


# Obter o Codigo do Estado
def get_uf(sigla_estado) -> int | None:
    # 11 Rondônia RO
    # 12 Acre AC
    # 13 Amazonas AM
    # 14 Roraima RR
    # 15 Pará PA
    # 16 Amapá AP
    # 17 Tocantins TO
    # 21 Maranhão MA
    # 22 Piauí PI
    # 23 Ceará CE
    # 24 Rio Grande do Norte RN
    # 25 Paraíba PB
    # 26 Pernambuco PE
    # 27 Alagoas AL
    # 28 Sergipe SE
    # 29 Bahia BA
    # 31 Minas Gerais MG
    # 32 Espirito Santo ES
    # 33 Rio de Janeiro RJ
    # 35 São Paulo SP
    # 41 Paraná PR
    # 42 Santa Catarina SC
    # 43 Rio Grande do Sul RS
    # 50 Mato Grosso do Sul MS
    # 51 Mato Grosso MT
    # 52 Goiás GO
    # 53 Distrito Federal DF

    if sigla_estado == "MG":
        return 31
    return None


# Obter os dados do Tipo de Imovel
def get_dados_imovel(numero, tipo, cartorio, coluna):
    # Tentativa de encontrar o primeiro imóvel que corresponde aos filtros fornecidos
    try:
        # Acessa diretamente o atributo desejado do imóvel, se existir
        return getattr(
            Livro02.objects.get(numero=numero, tipo=tipo, cartorio=cartorio),
            coluna,
            "",
        )
    except Livro02.DoesNotExist:
        # Retorna uma string vazia se nenhum imóvel correspondente for encontrado
        return ""


def get_lote(chave, coluna):
    # Substitua 'coluna' pelo campo específico que você deseja recuperar.
    # Suponha que 'chave' é o valor da chave de 'Livro02' que você está procurando.
    return (
        Lote.objects.filter(
            unidade__imovel=chave,  # Assim acessa a FK diretamente
            setor__gt="",  # Exclui lotes com o campo 'setor' vazio
        )
        .values_list(coluna, flat=True)
        .first()
    )

    # Isso irá retornar o primeiro valor encontrado ou None se nenhum for encontrado


# PEGANDO O NOME DA RUA
def get_rua(chave, coluna):
    # Realize uma única consulta utilizando o relacionamento entre 'Rua' e 'Unidade'.
    value = Rua.objects.filter(unidade__imovel_id=chave).values_list(coluna, flat=True)

    # Retorna o primeiro valor, se existir, e retira espaços em branco.
    return str(value[0]).strip() if value else "Nao Consta"


def get_contribuintes(chave, coluna):
    # Substitua 'coluna' pelo campo específico que você deseja recuperar do modelo 'Contribuintes'.
    # 'chave' é o ID do imóvel que você está procurando.
    value = Contribuintes.objects.filter(imovel_id=chave).values_list(coluna, flat=True)
    return str(value[0]).strip() if value else "Nao Consta"


# Gerar o INDICADOR REAL
def gerar_vetor_real(
    numero_livro,
    registros,
    cns,
    sigla_estado,
    cidade,
):
    vetor, _lista_ids_registros = [], []
    livro = "4"
    sequencia = 1

    # Gerar a lista de matriculas
    for registro in registros:
        print("Gerando o indicador real: " + str(registro.numero))

        # ENCONTROU IMOVEL
        if registro.imovel:
            # Obter os dados do IMOVEL
            tipoenvio = get_envio()
            numero_registro = get_cnm_onr(
                str(cns),
                str(numero_livro),
                str(registro.numero),
            )
            registro_tipo = sequencia
            tipo_de_imovel = get_tipo_imovel(registro.classe)
            localizacao = get_localizacao(registro.classe)
            tipo_logradouro = get_logradouro(registro.classe)

            # Obter dados do Cadastro do Imovel - lote
            if registro.classe != "R":
                nome_logradouro = get_rua(registro.imovel, "nome")
                numero_logradouro = get_rua(registro.imovel, "numero_edificacao")
                uf = get_uf(sigla_estado)
                cidade = cidade
                bairro = get_lote(registro.imovel, "setor")
                setor = get_lote(registro.imovel, "setor")
                quadra = get_lote(registro.imovel, "quadra")
                lote = get_lote(registro.imovel, "numero_unidade")
                contribuinte = get_contribuintes(registro.imovel, "numero_contribuinte")
            else:
                nome_logradouro = "NAO CONSTA"
                numero_logradouro = "NAO CONSTA"
                uf = get_uf(sigla_estado)
                cidade = cidade
                bairro = "NAO CONSTA"
                quadra = ""
                setor = ""
                lote = ""
                contribuinte = ""

            # Obter dados do Cadastro do Imovel - RURAL
            if registro.classe == "R":
                numero_incra = get_contribuintes(registro.imovel, "numero_contribuinte")
                denominacaorural = get_nome_fazenda(registro.imovel, "caracteristica")
            else:
                numero_incra = ""
                denominacaorural = ""

            # Obter dados do Cadastro do Imovel - CONDOMINIO

            vetor.append(
                {
                    "tipoenvio": tipoenvio,
                    "numero_registro": numero_registro,
                    "registro_tipo": registro_tipo,
                    "tipo_de_imovel": tipo_de_imovel,
                    "localizacao": localizacao,
                    "tipo_logradouro": tipo_logradouro,
                    "NOME_LOGRADOURO": nome_logradouro,
                    "NUMERO_LOGRADOURO": numero_logradouro,
                    "uf": uf,
                    "cidade": cidade,
                    "bairro": bairro,
                    "CEP": registro.cep,
                    "COMPLEMENTO": "",
                    "quadra": quadra,
                    "CONJUNTO": "",
                    "setor": setor,
                    "lote": lote,
                    "LOTEAMENTO": "",
                    "contribuinte": [contribuinte],
                    "RURAL": {
                        "CAR": "",
                        "NIRF": "",
                        "CCIR": "",
                        "numero_incra": numero_incra,
                        "SIGEF": "",
                        "denominacaorural": denominacaorural,
                        "ACIDENTEGEOGRAFICO": "",
                    },
                    "CONDOMINIO": {
                        "NOME_CONDOMINIO": "",
                        "BLOCO": "",
                        "CONJUNTO": "",
                        "TORRE": "",
                        "APTO": "",
                        "VAGA": "",
                    },
                },
            )

    # Criando uma lista cada imóvel
    registros_ids = [registro.imovel for registro in registros]

    # Atualiza todos os imóveis que correspondem aos IDs na Lista_id_imovel
    registros = Livro02.objects.filter(pk__in=registros_ids).update(
        data_envio_livro_4=timezone.now(),
        enviar_livro_4=False,
    )

    # GERAR UM ADITOR DE ENVIO DO PGNM - livro 4
    for numero_atual in registros:
        _, created = Pgnm.objects.update_or_create(
            imovel_id=numero_atual,
            livro=livro,
            created_at=timezone.now(),
            defaults={
                "created_at": timezone.now(),
            },
        )

    return vetor

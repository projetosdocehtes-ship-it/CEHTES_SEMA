import math

#------------------------------------------- Variaveis Globais -------------------------------------------

# T_sim = 5
# Resolucao_Clima = 24*60*10
Resolucao_Clima = 300000
# Iteracao_Sim = 24*60*10

Passo = 5E-5
T_sim = 2
Iteracao_Sim = math.ceil( T_sim / Passo ) # Comentar isso caso queira simular painel fotovoltaico

nome_cidade = "Goiânia"
pais = "BR"
data = "20240116"
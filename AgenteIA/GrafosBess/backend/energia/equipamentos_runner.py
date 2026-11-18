import json
import math
from pathlib import Path
import sys

from django.conf import settings


def main():
    entrada, saida, media, prime = map(Path, sys.argv[1:])
    sys.path.insert(0, str(prime))
    settings.configure(BASE_DIR=prime, MEDIA_ROOT=media, MEDIA_URL='/media/')
    from apps.Equipamentos import Var_globais
    from apps.Equipamentos.sim import executar_simulacao
    config = json.loads(entrada.read_text(encoding='utf-8'))['Config_Simulacao'][0]
    Var_globais.Passo_global = config['Passo_sim']
    Var_globais.T_sim_global = config['Tempo_sim']
    Var_globais.Num_Iteracao_global = math.ceil(config['Tempo_sim'] / config['Passo_sim'])
    resultado = executar_simulacao(json_path=entrada, output_dir=saida.parent, por_equipamento=True)
    saida.write_text(json.dumps(resultado, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()

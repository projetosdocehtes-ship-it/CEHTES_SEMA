from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
d = Document()
s = d.sections[0]
s.page_width, s.page_height = Cm(21), Cm(29.7)
s.top_margin = s.bottom_margin = Cm(1.8)
s.left_margin = s.right_margin = Cm(2)
for name in ['Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2']:
    st = d.styles[name]
    st.font.name = 'Calibri'
    st.font.color.rgb = RGBColor(0, 0, 0)
    for border in list(st.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
d.styles['Normal'].font.size = Pt(11)
d.styles['Normal'].paragraph_format.space_after = Pt(7)
d.styles['Normal'].paragraph_format.line_spacing = 1.08
d.styles['Title'].font.size = Pt(23)
d.styles['Heading 1'].font.size = Pt(17)
d.styles['Heading 2'].font.size = Pt(12)
footer = s.footer.paragraphs[0]
footer.text = 'POP SIM 001  •  Revisão 01  •  '
field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), 'PAGE'); footer._p.append(field)
footer.style = d.styles['Normal']; footer.runs[0].font.size = Pt(9)

def p(t): d.add_paragraph(t)
def h(t): d.add_heading(t, 1)
def sub(t): d.add_heading(t, 2)
def page(t): d.add_page_break(); h(t)
def step(n, title, text):
    q = d.add_paragraph(); q.add_run(f'{n}. {title} ').bold = True; q.add_run(text)
def table(head, rows, widths):
    t = d.add_table(rows=1, cols=len(head)); t.autofit = False
    for c, w in zip(t.columns, widths): c.width = Cm(w)
    for c, txt in zip(t.rows[0].cells, head): c.text = txt
    for vals in rows:
        for c, txt in zip(t.add_row().cells, vals): c.text = txt
    for i, row in enumerate(t.rows):
        for j, c in enumerate(row.cells):
            c.width = Cm(widths[j])
            pr = c._tc.get_or_add_tcPr()
            borders = OxmlElement('w:tcBorders')
            for edge in ['top', 'left', 'bottom', 'right']:
                b = OxmlElement('w:'+edge); b.set(qn('w:val'),'single'); b.set(qn('w:sz'),'4'); b.set(qn('w:color'),'D9D9D9'); borders.append(b)
            pr.append(borders)
            shade = OxmlElement('w:shd'); shade.set(qn('w:fill'), 'E7EDF2' if i == 0 else 'FFFFFF'); pr.append(shade)
            margins = OxmlElement('w:tcMar')
            for edge in ['top', 'left', 'bottom', 'right']:
                e = OxmlElement('w:'+edge); e.set(qn('w:w'), '90'); e.set(qn('w:type'),'dxa'); margins.append(e)
            pr.append(margins)
            for para in c.paragraphs:
                para.paragraph_format.space_after = Pt(3)
                for r in para.runs: r.font.size = Pt(10); r.bold = i == 0
    repeat = OxmlElement('w:tblHeader'); t.rows[0]._tr.get_or_add_trPr().append(repeat)
    d.add_paragraph().paragraph_format.space_after = Pt(0)

d.add_paragraph('Procedimento operacional padrão', 'Title')
d.add_paragraph('Configuração execução e análise das simulações FV e BESS', 'Subtitle')
p('Código POP SIM 001 | Revisão 01 | Emissão 11 de novembro de 2026')
h('1 Objetivo e aplicação')
p('Padronizar a preparação do projeto, a execução dos ensaios e a leitura dos resultados no Simulador Usina FV + BESS. O operador deve conseguir reproduzir a configuração, identificar atendimento ou déficit da carga e guardar evidências suficientes para revisão.')
p('Este procedimento se aplica à aplicação local em http://localhost:5173/ e à integração Equipamentos - Projeto. Seu uso é exclusivamente em simulação. As etapas não constituem instruções para manobras em uma instalação elétrica física.')
h('2 Responsabilidades e condições de uso')
p('Operador: conferir entradas e unidades, executar o ensaio, registrar parâmetros e guardar o relatório original. Revisor técnico: avaliar coerência, limites do modelo e critérios de aceitação. Responsável pelo projeto: controlar as revisões do POP e aprovar alterações no caso de referência.')
p('Antes de começar, os serviços do frontend e do backend devem estar ativos. É necessário ter o projeto carregado, acesso ao catálogo e ao Inspector, além de uma pasta para guardar entradas, resultados e figuras. Se a aplicação não abrir, solicitar ao responsável técnico a inicialização dos serviços; não recriar o banco para resolver indisponibilidade.')
h('3 Escolha do ensaio')
table(['Objetivo', 'Comando na aba Simulador', 'Escopo'], [
('Pré-carga e atendimento de 120 kW', 'Executar Equipamentos - Projeto', 'FV, inversor, bateria e carga; potência média e elo CC finito.'),
('Perda e retorno da distribuidora', 'Cenários de falha — Transitório → Falha da rede distribuidora (BESS + diesel)', 'Continuidade por potência, SOC e transferência ideal; sem tensão, frequência ou sincronismo.')], [4.1,6.1,6.8])
p('Não usar o resultado de Equipamentos para concluir sobre a atuação do diesel. A presença de um componente no unifilar não garante que o motor selecionado o simule.')

page('4 Preparação do projeto')
step(1, 'Abrir e identificar o projeto.', 'Acessar http://localhost:5173/ e conferir o nome exibido na aba Simulador. Para reproduzir este POP, usar Projeto Exemplo e verificar os parâmetros abaixo antes de executar.')
step(2, 'Preservar as entradas.', 'Na aba Resultado, abrir Editar / imprimir JSON — Entradas da simulação e usar Baixar JSON editado sem modificar o conteúdo. Guardar uma cópia com data e identificação do projeto. A cópia deve corresponder às entradas que serão usadas no ensaio.')
step(3, 'Conferir o unifilar.', 'Abrir Unifilar. Verificar FV, inversor, bateria, barramento e carga; no ensaio da distribuidora, conferir também o diesel e a condição de conexão à rede. Selecionar cada componente e conferir os dados no Inspector. Usar o símbolo correspondente ao tipo de carga.')
step(4, 'Conferir a configuração de referência.', 'Os valores desta tabela pertencem ao caso de teste aprovado. Não substituir automaticamente pelos valores de outro equipamento do catálogo. O inversor é uma referência genérica de simulação, não um modelo comercial validado.')
table(['Componente', 'Configuração do caso de referência'], [
('Carga', '120 kW de potência ativa; fator de potência 0,9999. Conferir que não foi digitado 120000 em um campo em kW.'),
('Inversor', '150 kW; 380 V; limite de saída 250 A; eficiência 0,976; quatro MPPTs com limite de 200 A por entrada.'),
('Arranjo FV', '531 módulos de 610 W, total 323,91 kWp. Grupos independentes: 18 × 10; 18 × 10; 18 × 9; 9 × 1 (módulos em série × strings em paralelo).'),
('Bateria', '500 kWh; 480 V; carga e descarga máximas de 120 kW; SOC inicial 50%; SOC mínimo 20%.'),
('Elo CC', '5 mF; nominal 800 V; mínimo 700 V; máximo 850 V; recomposição em 5 ms. A partida sequenciada inicia o elo em 0 V.')], [3.1,13.9])
step(5, 'Corrigir divergências antes do ensaio.', 'A integração converte a potência da carga para VA usando o fator de potência e a capacidade da bateria para Ah usando a tensão nominal. Não repetir manualmente essas conversões no campo original em kW ou kWh. Se um parâmetro avançado não estiver exposto no Inspector, ajustar uma cópia das entradas e usar Importar JSON gerar blocos; depois conferir novamente o unifilar e as entradas geradas.')
p('Evitar Gerar diagrama base sobre o caso já conferido: o comando cria uma nova composição a partir do catálogo e exige nova conferência dos parâmetros.')

page('5 Ensaio de pré carga e atendimento da carga')
step(6, 'Configurar o ensaio.', 'Na aba Simulador, localizar Equipamentos - Projeto. Marcar Testar apoio da bateria com queda de irradiância e confirmar Duração (s) igual a 0,3. O passo é 20 µs, totalizando 15000 passos.')
step(7, 'Executar.', 'Clicar em Executar Equipamentos - Projeto e aguardar a conclusão. O ensaio utiliza 25 °C, irradiância inicial de 1000 W/m², queda para 100 W/m² em 0,12 s e retorno em 0,22 s.')
step(8, 'Conferir a sequência automática.', 'Com o elo CC configurado nos inversores, a integração habilita a partida sequenciada. A pré-carga é limitada a 50 kW até atingir 95% da tensão nominal do elo. A carga permanece desconectada até a tensão do inversor ficar dentro de ±2% da nominal durante 20 ms contínuos. Uma proteção ativa impede o fechamento inicial.')
step(9, 'Ler os resultados.', 'Na aba Resultado, conferir o nome do projeto, duração, número de passos e avisos do motor. Em Balanço de potência e déficit, ler Sequência de partida, Após conectar a carga, Durante a queda e Recuperação. Abrir Balanco_CC_CA em tamanho original para examinar as curvas.')
sub('Critérios para aceitar este ensaio')
p('Registrar como aprovado no modelo somente se o contator fechar após a estabilização, a carga conectada for de 120 kW, não houver déficit acima de 1 W após o fechamento, a energia não atendida for desprezível no arredondamento do relatório e não houver atuação de proteção. Conferir também o balanço de energia e os limites de potência e SOC.')
p('A espera programada antes do fechamento deve aparecer separadamente. Energia adiada nesse intervalo não foi fornecida à carga. A média de potência do ensaio completo será menor que 120 kW porque inclui o período desconectado; usar Após conectar a carga para avaliar atendimento durante a operação.')
sub('Referência observada em 11 de novembro de 2026')
table(['Grandeza', 'Resultado de referência'], [
('Fim da pré-carga', '29,04 ms'), ('Fechamento do contator', '79,36 ms'),
('Espera e energia adiada', '79,36 ms e 2,6453 Wh'),
('Potência após a conexão', '120,000 kW; déficit acima de 1 W durante 0,000 ms'),
('Queda de irradiância e recuperação', '120,000 kW entregues em ambas as janelas'),
('Elo CC', 'Energia inicial 0 J; tensão final 814,716 V')], [7,10])
p('Estes valores são referência de reprodução para a mesma configuração, não garantia para outros projetos. O fechamento e o regulador de corrente são idealizados em potência média; o ensaio não valida transitórios eletromagnéticos de chaveamento.')

page('6 Leitura da tela de resultados')
p('A tela abaixo registra a execução de referência. Localizar a sequência de partida e comparar a linha Após conectar a carga com as linhas Durante a queda e Recuperação. O relatório numérico complementa a inspeção das figuras.')
image = ROOT / 'equipamentos-partida.png'
if image.exists():
    from PIL import Image
    with Image.open(image) as im: w, height = im.size
    picwidth = min(17, 17.2*w/height)
    d.add_picture(str(image), width=Cm(picwidth))
    p('Figura 1  Resultado da execução com pré-carga e conexão programada da carga')
sub('Como interpretar os sinais')
p('Potência positiva da bateria significa fornecimento de energia; negativa significa recarga. A potência positiva do elo CC indica descarga de sua reserva; negativa indica recomposição. Na queda de irradiância, verificar se a redução de FV é compensada pela bateria e pelo elo, mantendo a potência entregue à carga.')
p('O déficit representa demanda conectada menos potência entregue, limitado a zero quando não há insuficiência. Diferenças muito pequenas decorrentes de arredondamento numérico devem ser avaliadas em conjunto com o critério explícito de 1 W, sem alterar os resultados originais.')

page('7 Ensaio de falha da rede distribuidora')
step(10, 'Escolher o motor correto.', 'Na aba Simulador, em Cenários de falha — Transitório, selecionar Falha da rede distribuidora (BESS + diesel). Se a opção estiver indisponível, conferir presença de bateria e gerador e a configuração de conexão à rede.')
step(11, 'Definir um caso reproduzível.', 'Usar Sugerir cenário como ponto de partida e conferir todos os campos. Para um ensaio de 120 kW, aplicar os valores propostos abaixo. A sugestão automática pode calcular outra carga a partir da potência do gerador; ajustar explicitamente Carga do ensaio (kW).')
table(['Campo na tela', 'Valor proposto'], [
('Início do evento (s)', '2'), ('Duração do evento (s)', '6'), ('Duração do ensaio (s)', '12'),
('Passo de simulação (s)', '0,01'), ('Carga do ensaio (kW)', '120'),
('Tempo de partida do diesel (s)', '2'), ('Rampa até potência nominal (s)', '1'),
('Espera após retorno da rede (s)', '1'), ('Disponibilidade FV (%) — 0: noite', '0')], [12,5])
step(12, 'Executar e conferir as janelas.', 'Clicar em Executar transitório. Neste caso proposto, a falha começa em 2 s, a rede retorna em 8 s e a retransferência está prevista em 9 s. Os 3 s restantes permitem observar a recuperação. Este caso é uma instrução de ensaio; seus resultados devem ser obtidos em nova execução.')
step(13, 'Avaliar BESS e diesel.', 'Em Resultado, conferir as potências de rede, FV, BESS, diesel e carga, a curva de déficit e o SOC. Durante a partida e a rampa do diesel, o BESS deve suprir a parcela restante da demanda respeitando seus limites. Depois da retransferência, conferir rede conectada e déficit nulo em todas as amostras.')
step(14, 'Ler a análise automática.', 'Conferir Atendimento da carga, Reserva do BESS, Resposta do diesel e Recuperação da rede. Para este cenário, a análise trata déficit acima de 0,000001 kW como atenção. Registrar qualquer limite atingido e explicar sua consequência, mesmo quando a carga ainda é atendida.')
p('Aceitar somente o balanço de potência dentro da janela simulada: déficit nulo, energia não atendida nula, SOC dentro dos limites e recuperação confirmada. Este motor não calcula tensão, frequência ou sincronismo; portanto, não comprova transferência física sem interrupção.')

page('8 Tratamento de desvios e registro')
sub('Quando o resultado estiver fora do esperado')
p('Se o contator não fechar, verificar pré-carga, tensão, proteções e duração do ensaio. Se houver déficit depois da conexão, verificar unidades da carga, potência e corrente do inversor, reserva do elo CC, limites e SOC da bateria e arranjo FV. Se o diesel não assumir, verificar o motor selecionado, sua presença no projeto e os tempos de partida e rampa. Corrigir a entrada identificada e executar novamente, preservando as duas versões do relatório.')
p('Se houver Network Error, confirmar que o backend está ativo e que não está reiniciando. Após restabelecer o serviço, repetir o ensaio. Uma mensagem de execução iniciada não substitui um relatório concluído.')
sub('Horas equivalentes e energia não atendida')
p('Quando o relatório apresentar horas equivalentes de falta associadas ao curto-circuito, conferir a soma dos intervalos em que a falta está ativa, dividida por 3600. Não usar apenas a contagem de amostras nem extrapolar a última amostra. Exemplo: 0,15 s correspondem a 0,000041667 h. Esse indicador não deve ser interpretado automaticamente como autonomia do BESS ou duração da falha da distribuidora.')
p('A energia não atendida é a integral do déficit de potência no tempo. Para déficit em kW e tempo em segundos, dividir a soma por 3600 para obter kWh. No relatório de Equipamentos, o campo de energia não atendida usa Wh; manter a unidade ao comparar ensaios.')
sub('Guardar as evidências')
step(15, 'Exportar.', 'Usar Editar / imprimir JSON — Relatório Equipamentos e Baixar JSON editado para guardar o resultado original. Imprimir JSON abre a impressão da cópia. A edição nessa área não recalcula o ensaio; para mudar entradas, importar a cópia na aba Simulador e executar novamente. Guardar também as figuras abertas em tamanho original e, para transitórios, o relatório ou uma captura da análise disponível.')
step(16, 'Registrar e revisar.', 'Preencher os campos abaixo e associar os arquivos da execução. Se usar Salvar cenário atual na aba Cenários, conferir o conteúdo salvo; o cenário não substitui a cópia dos relatórios e das figuras do ensaio.')
p('Projeto e identificação da execução: _______________________________________')
p('Data e hora: __________________  Operador: _________________________________')
p('Motor e parâmetros do evento: ___________________________________________')
p('Carga: ______ kW  SOC inicial / mínimo / final: ______ / ______ / ______ %')
p('Fechamento do contator ou retransferência: __________ s  Déficit máximo: ______ kW')
p('Energia não atendida e unidade: __________  Espera programada: __________ s')
p('Conclusão: aprovado no modelo / reprovado / inconclusivo  Evidências: ______________')
p('Desvios e ações: _____________________  Revisor e data: _____________________')
p('Controle de revisão: revisão 01, emissão inicial com pré-carga, apoio da bateria e procedimento de falha da rede. Revisar este POP quando mudarem os campos da interface, os motores, as unidades ou os critérios de aceitação.')

d.core_properties.title = 'POP de configuração execução e análise das simulações FV e BESS'
d.core_properties.subject = 'Procedimento de operação do simulador local'
d.core_properties.author = 'Documentação do projeto'
d.save(OUT / 'POP_SIM_001_FV_BESS.docx')
print(OUT / 'POP_SIM_001_FV_BESS.docx')

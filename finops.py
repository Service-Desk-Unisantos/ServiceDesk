# Importa o modulo csv para salvar os dados coletados em arquivo.
import csv
# Importa o modulo os para pegar informacoes do processo atual.
import os
# Importa o modulo threading para rodar estresse e monitoramento em paralelo.
import threading
# Importa o modulo time para controlar duracao e intervalo das coletas.
import time

# Importa o psutil para ler uso de CPU e RAM do processo atual.
import psutil

# Define o preco por segundo quando a CPU estiver em 100% de uso.
CPU_PRICE_FULL_PER_SECOND = 0.05
# Define o preco por segundo quando a RAM estiver em 1024 MB (1 GB).
RAM_PRICE_PER_1024MB_PER_SECOND = 0.02
# Define por quantos segundos o teste deve rodar (entre 30 e 60 conforme requisito).
DURATION_SECONDS = 45
# Define o nome do arquivo CSV de saida.
CSV_FILE_NAME = "relatorio_custos.csv"
# Define o nome do arquivo PDF de saida.
PDF_FILE_NAME = "analise_finops.pdf"

# Cria um sinal compartilhado para encerrar as rotinas de forma controlada.
stop_event = threading.Event()
# Cria a lista onde cada amostra de 1 segundo sera armazenada.
collected_rows = []
# Cria um lock simples para proteger escrita/leitura da lista compartilhada.
rows_lock = threading.Lock()


# Funcao auxiliar para verificar se um numero e primo (custo de CPU).
def is_prime(number):
    # Se o numero for menor que 2, nao e primo.
    if number < 2:
        # Retorna falso para numeros menores que 2.
        return False
    # Comeca o divisor em 2.
    divisor = 2
    # Testa divisores enquanto divisor * divisor for menor ou igual ao numero.
    while divisor * divisor <= number:
        # Se dividir sem resto, nao e primo.
        if number % divisor == 0:
            # Retorna falso ao encontrar divisor exato.
            return False
        # Avanca para o proximo divisor.
        divisor += 1
    # Se nao encontrou divisor, o numero e primo.
    return True


# Worker de estresse: força CPU + RAM por tempo continuo.
def dummy_worker(duration_seconds, stop_signal):
    # Calcula o instante limite para finalizar o estresse.
    end_time = time.time() + duration_seconds
    # Lista local para manter blocos de memoria temporarios.
    memory_chunks = []
    # Contador para variar a carga a cada iteracao.
    loop_counter = 0

    # Executa continuamente ate chegar no tempo limite ou sinal de parada.
    while time.time() < end_time and not stop_signal.is_set():
        # Define inicio variavel da faixa de numeros para teste de primalidade.
        start_value = 10000 + (loop_counter % 500)
        # Define fim variavel da faixa para gerar pequenas oscilacoes de carga.
        end_value = start_value + 1500 + ((loop_counter % 5) * 300)
        # Acumulador simples para evitar otimizacoes triviais.
        prime_sum = 0

        # Percorre a faixa fazendo calculo matematico intenso.
        for candidate in range(start_value, end_value):
            # Soma somente quando o numero for primo.
            if is_prime(candidate):
                # Acumula o valor primo encontrado.
                prime_sum += candidate

        # Cria um bloco de string para consumir memoria intencionalmente.
        chunk = "x" * (200_000 + (loop_counter % 4) * 50_000)
        # Guarda o bloco na lista local para manter RAM ocupada temporariamente.
        memory_chunks.append(chunk)

        # Limita quantidade de blocos para nao estourar memoria da maquina.
        if len(memory_chunks) > 12:
            # Remove o bloco mais antigo para manter carga de memoria controlada.
            memory_chunks.pop(0)

        # Faz uma pausa curta em alguns ciclos para criar curva menos artificial.
        if loop_counter % 7 == 0:
            # Dorme alguns milissegundos para variar uso de CPU no tempo.
            time.sleep(0.03)

        # Incrementa o contador de ciclo da rotina de estresse.
        loop_counter += 1

        # Usa a variavel para evitar que linter considere valor inutilizado.
        _ = prime_sum

    # Sinaliza parada ao final do worker de estresse.
    stop_signal.set()


# Worker de monitoramento: coleta metricas a cada 1 segundo e calcula custo.
def profiler_worker(duration_seconds, stop_signal, output_rows, output_lock):
    # Captura o processo Python atual para medir CPU e RAM dele.
    process = psutil.Process(os.getpid())
    # Inicializa medicao de CPU para que a proxima chamada com intervalo seja valida.
    process.cpu_percent(interval=None)
    # Inicia acumulador de custo total.
    accumulated_cost = 0.0
    # Inicia contador de segundos da coleta.
    second_counter = 0

    # Roda ate completar o tempo alvo ou receber sinal de parada.
    while second_counter < duration_seconds and not stop_signal.is_set():
        # Mede CPU do processo durante exatamente 1 segundo.
        cpu_percent = process.cpu_percent(interval=1.0)
        # Le uso de memoria residente (RSS) em bytes.
        ram_bytes = process.memory_info().rss
        # Converte RAM de bytes para megabytes (MB).
        ram_mb = ram_bytes / (1024 * 1024)

        # Calcula custo proporcional de CPU no segundo atual.
        cpu_cost = (cpu_percent / 100.0) * CPU_PRICE_FULL_PER_SECOND
        # Calcula custo proporcional de RAM no segundo atual.
        ram_cost = (ram_mb / 1024.0) * RAM_PRICE_PER_1024MB_PER_SECOND
        # Soma os custos para obter custo parcial do segundo.
        partial_cost = cpu_cost + ram_cost
        # Atualiza custo acumulado total.
        accumulated_cost += partial_cost

        # Avanca o tempo amostrado em segundos.
        second_counter += 1

        # Monta o registro padrao exigido para CSV e analise.
        row = {
            # Guarda o segundo atual da coleta.
            "Tempo_Segundos": second_counter,
            # Guarda percentual de uso de CPU no instante.
            "Uso_CPU_Percentual": cpu_percent,
            # Guarda uso de RAM em MB no instante.
            "Uso_RAM_MB": ram_mb,
            # Guarda custo parcial calculado para o instante.
            "Custo_Parcial_R$": partial_cost,
            # Guarda custo acumulado ate o instante.
            "Custo_Acumulado_R$": accumulated_cost,
        }

        # Entra em secao critica para gravar na lista compartilhada com seguranca.
        with output_lock:
            # Adiciona a linha coletada na estrutura final.
            output_rows.append(row)

    # Garante sinal de parada quando o profiler terminar.
    stop_signal.set()


# Exporta as amostras coletadas para o CSV com as colunas exigidas.
def write_csv(rows, csv_path):
    # Define exatamente os nomes das colunas solicitadas no enunciado.
    headers = [
        "Tempo_Segundos",
        "Uso_CPU_Percentual",
        "Uso_RAM_MB",
        "Custo_Parcial_R$",
        "Custo_Acumulado_R$",
    ]

    # Abre (ou cria) o arquivo CSV no caminho informado.
    with open(csv_path, mode="w", newline="", encoding="utf-8") as csv_file:
        # Cria o escritor CSV padrao separado por virgula.
        writer = csv.writer(csv_file)
        # Escreve o cabecalho oficial no arquivo.
        writer.writerow(headers)

        # Percorre cada linha coletada para persistir no arquivo.
        for row in rows:
            # Escreve os valores com arredondamento para facilitar leitura.
            writer.writerow(
                [
                    row["Tempo_Segundos"],
                    round(row["Uso_CPU_Percentual"], 2),
                    round(row["Uso_RAM_MB"], 2),
                    round(row["Custo_Parcial_R$"], 6),
                    round(row["Custo_Acumulado_R$"], 6),
                ]
            )


# Escapa caracteres especiais para texto literal dentro do PDF.
def escape_pdf_text(text):
    # Substitui barra invertida por forma escapada do PDF.
    escaped = text.replace("\\", "\\\\")
    # Escapa parenteses de abertura para nao quebrar string PDF.
    escaped = escaped.replace("(", "\\(")
    # Escapa parenteses de fechamento para nao quebrar string PDF.
    escaped = escaped.replace(")", "\\)")
    # Retorna texto pronto para comandos Tj.
    return escaped


# Gera um paragrafo curto (ate 5 linhas) correlacionando pico e custo.
def build_analysis_lines(rows):
    # Se nao houver dados, retorna linhas padrao de contingencia.
    if not rows:
        # Retorna diagnostico minimo quando nao ha amostras.
        return [
            "Sem amostras suficientes para analise.",
            "Execute novamente para gerar dados de CPU e RAM.",
        ]

    # Calcula o pico de custo parcial por segundo.
    peak_row = max(rows, key=lambda item: item["Custo_Parcial_R$"])
    # Calcula media de CPU para contexto tecnico do teste.
    avg_cpu = sum(item["Uso_CPU_Percentual"] for item in rows) / len(rows)
    # Calcula media de RAM para contexto tecnico do teste.
    avg_ram = sum(item["Uso_RAM_MB"] for item in rows) / len(rows)

    # Monta linha 1 conectando pico de processamento ao custo.
    line_1 = (
        f"No segundo {peak_row['Tempo_Segundos']}, houve o maior custo parcial "
        f"(R$ {peak_row['Custo_Parcial_R$']:.4f})."
    )
    # Monta linha 2 com efeito direto do uso de CPU no faturamento.
    line_2 = (
        f"Esse pico coincidiu com CPU em {peak_row['Uso_CPU_Percentual']:.1f}% e "
        f"RAM em {peak_row['Uso_RAM_MB']:.1f} MB."
    )
    # Monta linha 3 com medias para comparar estabilidade da carga.
    line_3 = (
        f"Durante o teste, a media foi {avg_cpu:.1f}% de CPU e {avg_ram:.1f} MB de RAM."
    )
    # Monta linha 4 reforcando impacto financeiro acumulado da rotina.
    line_4 = (
        "Quanto mais tempo a rotina permanece em alto processamento, "
        "maior o custo acumulado na simulacao FinOps."
    )

    # Retorna no maximo 4 linhas curtas para manter objetividade.
    return [line_1, line_2, line_3, line_4]


# Gera um PDF simples com grafico de linha e paragrafo tecnico, sem libs externas.
def write_pdf(rows, pdf_path):
    # Define tamanho da pagina A4 em pontos PDF.
    page_width = 595
    # Define altura da pagina A4 em pontos PDF.
    page_height = 842
    # Define area do grafico (origem X).
    chart_x = 60
    # Define area do grafico (origem Y).
    chart_y = 360
    # Define largura do grafico.
    chart_width = 470
    # Define altura do grafico.
    chart_height = 250

    # Extrai lista do custo acumulado para construir curva.
    accumulated_values = [row["Custo_Acumulado_R$"] for row in rows]
    # Define custo maximo para escala vertical segura.
    max_accumulated = max(accumulated_values) if accumulated_values else 1.0

    # Evita divisao por zero caso maximo seja zero.
    if max_accumulated <= 0:
        # Ajusta valor minimo da escala.
        max_accumulated = 1.0

    # Cria lista de comandos de desenho e texto do conteudo PDF.
    commands = []

    # Define helper para escrever uma linha de texto em coordenada fixa.
    def add_text(x, y, size, text):
        # Escapa caracteres especiais do texto para sintaxe PDF.
        safe_text = escape_pdf_text(text)
        # Adiciona comando BT/ET de texto.
        commands.append(f"BT /F1 {size} Tf {x} {y} Td ({safe_text}) Tj ET")

    # Escreve titulo do relatorio na parte superior.
    add_text(60, 800, 16, "Analise FinOps - Monitoramento de CPU e RAM")
    # Escreve subtitulo com formato do eixo X.
    add_text(60, 780, 11, "Grafico: Custo acumulado por segundo")

    # Desenha eixo X do grafico.
    commands.append(f"0 0 0 RG 1 w {chart_x} {chart_y} m {chart_x + chart_width} {chart_y} l S")
    # Desenha eixo Y do grafico.
    commands.append(f"0 0 0 RG 1 w {chart_x} {chart_y} m {chart_x} {chart_y + chart_height} l S")

    # Desenha linhas horizontais leves para melhorar leitura visual.
    for step in range(1, 6):
        # Calcula posicao Y da linha de grade.
        y = chart_y + (chart_height / 6) * step
        # Adiciona linha cinza clara de grade.
        commands.append(f"0.85 0.85 0.85 RG 0.5 w {chart_x} {y:.2f} m {chart_x + chart_width} {y:.2f} l S")

    # Se houver pelo menos um ponto, desenha a curva de custo acumulado.
    if accumulated_values:
        # Define quantidade de pontos no grafico.
        total_points = len(accumulated_values)

        # Percorre cada ponto para converter dado em coordenada 2D.
        for index, value in enumerate(accumulated_values):
            # Calcula coordenada X proporcional ao tempo.
            x = chart_x if total_points == 1 else chart_x + (index / (total_points - 1)) * chart_width
            # Calcula coordenada Y proporcional ao custo acumulado.
            y = chart_y + (value / max_accumulated) * chart_height

            # No primeiro ponto usa comando move-to.
            if index == 0:
                # Inicia caminho da curva.
                commands.append(f"0 0.35 0.75 RG 1.4 w {x:.2f} {y:.2f} m")
            else:
                # Liga cada ponto com linha para formar o grafico.
                commands.append(f"{x:.2f} {y:.2f} l")

        # Finaliza o desenho da curva no PDF.
        commands.append("S")

    # Escreve rotulo do eixo X.
    add_text(chart_x + 180, chart_y - 22, 10, "Tempo (segundos)")
    # Escreve rotulo do eixo Y (texto simples horizontal para manter codigo didatico).
    add_text(chart_x - 5, chart_y + chart_height + 12, 10, "Custo acumulado (R$)")
    # Escreve valor maximo de referencia do eixo Y.
    add_text(chart_x + chart_width + 5, chart_y + chart_height - 3, 9, f"Max: R$ {max_accumulated:.4f}")
    # Escreve valor final acumulado de referencia.
    final_total = accumulated_values[-1] if accumulated_values else 0.0
    # Escreve valor final embaixo do grafico.
    add_text(60, 330, 11, f"Custo acumulado final: R$ {final_total:.4f}")

    # Monta linhas do paragrafo analitico com no maximo 5 linhas curtas.
    analysis_lines = build_analysis_lines(rows)
    # Define titulo da secao de diagnostico.
    add_text(60, 295, 12, "Diagnostico tecnico (FinOps):")

    # Define altura inicial para primeira linha do diagnostico.
    text_y = 275
    # Percorre linhas do diagnostico para desenhar no PDF.
    for line in analysis_lines[:5]:
        # Adiciona linha de texto no PDF.
        add_text(60, text_y, 10, line)
        # Move para a proxima linha com espacamento constante.
        text_y -= 15

    # Junta todos os comandos em um unico stream de conteudo.
    content_stream = "\n".join(commands).encode("latin-1", errors="replace")

    # Monta objeto 1: catalogo principal do PDF.
    obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
    # Monta objeto 2: lista de paginas do documento.
    obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    # Monta objeto 3: definicao da pagina com fonte e conteudo.
    obj3 = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 "
        + str(page_width).encode("ascii")
        + b" "
        + str(page_height).encode("ascii")
        + b"] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
    )
    # Monta objeto 4: stream com comandos de desenho e texto.
    obj4 = b"<< /Length " + str(len(content_stream)).encode("ascii") + b" >>\nstream\n" + content_stream + b"\nendstream"
    # Monta objeto 5: fonte padrao Helvetica.
    obj5 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    # Agrupa objetos no indice numerico para gerar o arquivo.
    objects = [obj1, obj2, obj3, obj4, obj5]
    # Inicia buffer binario final do PDF.
    pdf_bytes = bytearray()
    # Escreve cabecalho de versao do PDF.
    pdf_bytes.extend(b"%PDF-1.4\n")
    # Cria lista de offsets para tabela xref.
    offsets = [0]

    # Escreve cada objeto e registra seu offset no arquivo.
    for index, obj in enumerate(objects, start=1):
        # Guarda posicao inicial do objeto atual.
        offsets.append(len(pdf_bytes))
        # Escreve cabecalho do objeto com numero e geracao.
        pdf_bytes.extend(f"{index} 0 obj\n".encode("ascii"))
        # Escreve conteudo interno do objeto.
        pdf_bytes.extend(obj)
        # Fecha o objeto no formato PDF.
        pdf_bytes.extend(b"\nendobj\n")

    # Guarda offset onde comeca a tabela xref.
    xref_offset = len(pdf_bytes)
    # Escreve cabecalho da tabela xref.
    pdf_bytes.extend(b"xref\n")
    # Escreve tamanho total (objeto 0 + objetos reais).
    pdf_bytes.extend(f"0 {len(offsets)}\n".encode("ascii"))
    # Escreve entrada padrao do objeto 0 (livre).
    pdf_bytes.extend(b"0000000000 65535 f \n")

    # Escreve cada entrada da tabela de offsets dos objetos reais.
    for offset in offsets[1:]:
        # Formata offset em 10 digitos conforme padrao PDF.
        pdf_bytes.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    # Escreve trailer com referencia ao catalogo.
    pdf_bytes.extend(b"trailer\n")
    # Informa tamanho e raiz do documento.
    pdf_bytes.extend(f"<< /Size {len(offsets)} /Root 1 0 R >>\n".encode("ascii"))
    # Informa onde a tabela xref comeca.
    pdf_bytes.extend(b"startxref\n")
    # Escreve valor do offset da xref.
    pdf_bytes.extend(f"{xref_offset}\n".encode("ascii"))
    # Finaliza arquivo PDF corretamente.
    pdf_bytes.extend(b"%%EOF\n")

    # Abre o arquivo de saida PDF em modo binario.
    with open(pdf_path, "wb") as pdf_file:
        # Grava todos os bytes gerados no disco.
        pdf_file.write(pdf_bytes)


# Ponto de entrada principal do script.
def main():
    # Exibe inicio da execucao para facilitar acompanhamento.
    print("Iniciando teste FinOps (estresse + monitoramento)...")
    # Exibe duracao configurada do teste.
    print(f"Duracao configurada: {DURATION_SECONDS} segundos")

    # Cria thread do worker de estresse (CPU + RAM).
    stress_thread = threading.Thread(target=dummy_worker, args=(DURATION_SECONDS, stop_event), daemon=True)
    # Cria thread do profiler que coleta metricas por segundo.
    profiler_thread = threading.Thread(
        target=profiler_worker,
        args=(DURATION_SECONDS, stop_event, collected_rows, rows_lock),
        daemon=True,
    )

    # Inicia thread de estresse.
    stress_thread.start()
    # Inicia thread de monitoramento.
    profiler_thread.start()

    # Aguarda o profiler concluir as coletas previstas.
    profiler_thread.join()
    # Garante sinal de parada caso o estresse ainda esteja rodando.
    stop_event.set()
    # Aguarda finalizacao do estresse por completo.
    stress_thread.join()

    # Entra em secao critica para copiar resultado final coletado.
    with rows_lock:
        # Cria snapshot para exportacao fora do lock.
        rows_snapshot = list(collected_rows)

    # Salva CSV exigido pelo trabalho.
    write_csv(rows_snapshot, CSV_FILE_NAME)
    # Salva PDF com grafico e diagnostico tecnico.
    write_pdf(rows_snapshot, PDF_FILE_NAME)

    # Calcula total final para exibicao no console.
    total_cost = rows_snapshot[-1]["Custo_Acumulado_R$"] if rows_snapshot else 0.0
    # Exibe resumo de amostras coletadas.
    print(f"Amostras coletadas: {len(rows_snapshot)}")
    # Exibe caminho do CSV gerado.
    print(f"CSV gerado: {CSV_FILE_NAME}")
    # Exibe caminho do PDF gerado.
    print(f"PDF gerado: {PDF_FILE_NAME}")
    # Exibe custo total acumulado no periodo.
    print(f"Custo acumulado final: R$ {total_cost:.4f}")


# Executa somente quando o arquivo for chamado diretamente.
if __name__ == "__main__":
    # Chama a funcao principal do programa.
    main()

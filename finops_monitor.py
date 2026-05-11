#!/usr/bin/env python3
"""Modulo autonomo de monitoramento de hardware e precificacao FinOps.

Executa uma carga sintetica de CPU e memoria em paralelo com um profiler que:
- coleta CPU e RAM do processo atual a cada 1 segundo;
- calcula custo parcial e acumulado;
- exporta um CSV;
- gera um PDF simples com grafico e analise tecnica.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import textwrap
import threading
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

try:
    import psutil
except ModuleNotFoundError as exc:
    raise SystemExit(
        "A biblioteca 'psutil' nao foi encontrada no interpretador Python atual.\n"
        "Instale no mesmo ambiente usado para rodar este script, por exemplo:\n"
        "  python3 -m pip install psutil\n"
        "Ou, se estiver usando a venv do projeto:\n"
        "  source .venv/bin/activate && pip install psutil\n"
    ) from exc


CPU_COST_PER_SECOND = 0.05
RAM_COST_PER_SECOND_PER_GB = 0.02
BYTES_PER_MB = 1024 * 1024
MB_PER_GB = 1024


@dataclass
class Sample:
    tempo_segundos: int
    uso_cpu_percentual: float
    uso_ram_mb: float
    custo_parcial: float
    custo_acumulado: float


class DummyWorker(threading.Thread):
    """Carga sintetica que pressiona CPU e memoria por um periodo fixo."""

    def __init__(
        self,
        duration_seconds: int,
        stop_event: threading.Event,
        target_memory_mb: int = 96,
    ) -> None:
        super().__init__(daemon=True)
        self.duration_seconds = duration_seconds
        self.stop_event = stop_event
        self.target_memory_mb = target_memory_mb
        self._memory_chunks: list[bytearray] = []

    def run(self) -> None:
        deadline = time.monotonic() + self.duration_seconds
        cycle = 0

        while time.monotonic() < deadline and not self.stop_event.is_set():
            self._burn_cpu()

            # Mantem uma alocacao progressiva de memoria para refletir custo RAM.
            if (
                cycle % 4 == 0
                and len(self._memory_chunks) < self.target_memory_mb
            ):
                self._memory_chunks.append(bytearray(BYTES_PER_MB))

            cycle += 1

        # Mantem a referencia ate o fim da thread para sustentar o uso de RAM.
        _ = self._memory_chunks

    @staticmethod
    def _burn_cpu() -> int:
        prime_count = 0
        for candidate in range(2, 12000):
            is_prime = True
            limit = math.isqrt(candidate)
            for divisor in range(2, limit + 1):
                if candidate % divisor == 0:
                    is_prime = False
                    break
            if is_prime:
                prime_count += 1
        return prime_count


class Profiler(threading.Thread):
    """Coleta metricas do processo atual a cada 1 segundo."""

    def __init__(self, duration_seconds: int, stop_event: threading.Event) -> None:
        super().__init__(daemon=True)
        self.duration_seconds = duration_seconds
        self.stop_event = stop_event
        self.samples: list[Sample] = []

    def run(self) -> None:
        process = psutil.Process(os.getpid())
        process.cpu_percent(interval=None)
        accumulated = 0.0

        for second in range(1, self.duration_seconds + 1):
            if self.stop_event.is_set():
                break

            cpu_percent = min(max(process.cpu_percent(interval=1.0), 0.0), 100.0)
            ram_mb = process.memory_info().rss / BYTES_PER_MB
            partial_cost = calculate_instant_cost(cpu_percent, ram_mb)
            accumulated += partial_cost

            sample = Sample(
                tempo_segundos=second,
                uso_cpu_percentual=cpu_percent,
                uso_ram_mb=ram_mb,
                custo_parcial=partial_cost,
                custo_acumulado=accumulated,
            )
            self.samples.append(sample)

            print(
                f"[{second:02d}s] CPU={cpu_percent:6.2f}% | "
                f"RAM={ram_mb:8.2f} MB | "
                f"Custo parcial=R$ {partial_cost:0.6f} | "
                f"Acumulado=R$ {accumulated:0.6f}"
            )

        self.stop_event.set()


def calculate_instant_cost(cpu_percent: float, ram_mb: float) -> float:
    cpu_cost = (cpu_percent / 100.0) * CPU_COST_PER_SECOND
    ram_cost = (ram_mb / MB_PER_GB) * RAM_COST_PER_SECOND_PER_GB
    return cpu_cost + ram_cost


def write_csv(samples: list[Sample], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "Tempo_Segundos",
                "Uso_CPU_Percentual",
                "Uso_RAM_MB",
                "Custo_Parcial_R$",
                "Custo_Acumulado_R$",
            ]
        )
        for sample in samples:
            writer.writerow(
                [
                    sample.tempo_segundos,
                    f"{sample.uso_cpu_percentual:.2f}",
                    f"{sample.uso_ram_mb:.2f}",
                    f"{sample.custo_parcial:.6f}",
                    f"{sample.custo_acumulado:.6f}",
                ]
            )


def build_analysis_paragraph(samples: list[Sample]) -> str:
    if not samples:
        return (
            "Nao houve amostras suficientes para a analise. "
            "Execute o modulo por pelo menos 30 segundos para observar o efeito "
            "do estresse no custo acumulado."
        )

    peak_cpu = max(samples, key=lambda item: item.uso_cpu_percentual)
    peak_ram = max(samples, key=lambda item: item.uso_ram_mb)
    peak_cost = max(samples, key=lambda item: item.custo_parcial)
    total_cost = samples[-1].custo_acumulado

    return (
        f"O grafico mostra maior inclinacao proxima do segundo "
        f"{peak_cost.tempo_segundos}, quando o custo parcial atingiu "
        f"R$ {peak_cost.custo_parcial:.6f}. Nesse intervalo, o processo chegou a "
        f"{peak_cpu.uso_cpu_percentual:.2f}% de CPU e {peak_ram.uso_ram_mb:.2f} MB "
        f"de RAM, provando que os picos de processamento e alocacao elevam "
        f"diretamente a simulacao de faturamento. Ao final da execucao, o custo "
        f"acumulado foi de R$ {total_cost:.6f}, evidenciando financeiramente o "
        f"impacto da operacao de estresse."
    )


def _pdf_escape(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _draw_text(commands: list[str], x: float, y: float, text: str, size: int = 12) -> None:
    commands.append(f"BT /F1 {size} Tf {x:.2f} {y:.2f} Td ({_pdf_escape(text)}) Tj ET")


def generate_pdf(samples: list[Sample], paragraph: str, output_path: Path) -> None:
    page_width = 595.0
    page_height = 842.0
    chart_x = 60.0
    chart_y = 360.0
    chart_width = 470.0
    chart_height = 280.0

    max_cost = max((sample.custo_acumulado for sample in samples), default=1.0)
    max_cost = max(max_cost, 0.001)
    max_time = max((sample.tempo_segundos for sample in samples), default=1)

    commands: list[str] = []
    commands.append("0.2 w")
    commands.append("0 0 0 RG")
    commands.append(f"{chart_x} {chart_y} {chart_width} {chart_height} re S")

    _draw_text(commands, 60, 800, "Analise FinOps - ServiceDesk", 18)
    _draw_text(commands, 60, 780, "Grafico de custo acumulado por segundo", 11)
    _draw_text(commands, 240, 342, "Tempo (segundos)", 10)
    _draw_text(commands, 64, 655, "Custo", 10)
    _draw_text(commands, 64, 642, "Acumulado (R$)", 10)

    # Linhas horizontais de referencia.
    for tick in range(6):
        y = chart_y + (chart_height / 5) * tick
        value = (max_cost / 5) * tick
        commands.append("0.85 G")
        commands.append(f"{chart_x} {y:.2f} m {chart_x + chart_width} {y:.2f} l S")
        commands.append("0 G")
        _draw_text(commands, 10, y - 3, f"{value:.4f}", 8)

    # Marcadores do eixo X.
    tick_total = min(max_time, 5)
    for tick in range(tick_total + 1):
        x = chart_x + (chart_width / max(tick_total, 1)) * tick
        label_value = round((max_time / max(tick_total, 1)) * tick)
        commands.append(f"{x:.2f} {chart_y} m {x:.2f} {chart_y - 5} l S")
        _draw_text(commands, x - 7, chart_y - 18, str(label_value), 8)

    # Plota linha do custo acumulado.
    if samples:
        commands.append("1 0 0 RG")
        first = samples[0]
        first_x = chart_x + ((first.tempo_segundos - 1) / max(max_time - 1, 1)) * chart_width
        first_y = chart_y + (first.custo_acumulado / max_cost) * chart_height
        commands.append(f"{first_x:.2f} {first_y:.2f} m")
        for sample in samples[1:]:
            x = chart_x + ((sample.tempo_segundos - 1) / max(max_time - 1, 1)) * chart_width
            y = chart_y + (sample.custo_acumulado / max_cost) * chart_height
            commands.append(f"{x:.2f} {y:.2f} l")
        commands.append("S")
        commands.append("0 G")

    _draw_text(commands, 60, 300, "Diagnostico tecnico", 14)
    wrapped_lines = textwrap.wrap(paragraph, width=92)
    for index, line in enumerate(wrapped_lines[:5]):
        _draw_text(commands, 60, 276 - (index * 18), line, 11)

    content_stream = "\n".join(commands) + "\n"
    content_bytes = content_stream.encode("latin-1", errors="ignore")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width:.0f} {page_height:.0f}] "
            "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ).encode("latin-1"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            f"<< /Length {len(content_bytes)} >>\nstream\n".encode("latin-1")
            + content_bytes
            + b"endstream"
        ),
    ]

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("latin-1")
    )

    output_path.write_bytes(pdf)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa estresse de hardware, monitora o processo e calcula custo FinOps."
    )
    parser.add_argument(
        "--duracao",
        type=int,
        default=40,
        help="Duracao do teste em segundos. O padrao de 40s atende ao enunciado.",
    )
    parser.add_argument(
        "--memoria-mb",
        type=int,
        default=96,
        help="Meta aproximada de memoria alocada pelo worker dummy.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.duracao < 1:
        raise SystemExit("A duracao deve ser maior que zero.")

    base_dir = Path(__file__).resolve().parent
    csv_path = base_dir / "relatorio_custos.csv"
    pdf_path = base_dir / "analise_finops.pdf"

    stop_event = threading.Event()
    worker = DummyWorker(
        duration_seconds=args.duracao,
        stop_event=stop_event,
        target_memory_mb=args.memoria_mb,
    )
    profiler = Profiler(duration_seconds=args.duracao, stop_event=stop_event)

    print("Iniciando modulo de estresse e monitoramento FinOps...")
    worker.start()
    profiler.start()

    profiler.join()
    stop_event.set()
    worker.join(timeout=2.0)

    write_csv(profiler.samples, csv_path)
    analysis_paragraph = build_analysis_paragraph(profiler.samples)
    generate_pdf(profiler.samples, analysis_paragraph, pdf_path)

    print(f"\nCSV gerado em: {csv_path}")
    print(f"PDF gerado em: {pdf_path}")
    print("Analise tecnica:")
    print(analysis_paragraph)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

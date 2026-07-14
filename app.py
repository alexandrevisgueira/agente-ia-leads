"""
Qualificador de Leads de Saúde via LLM (Gemini API)
-----------------------------------------------------
O que este script faz, de verdade:
1. Lê um CSV de leads (id, mensagem).
2. Para cada lead, envia a mensagem para o Gemini com um prompt fixo,
   pedindo uma classificação estruturada (ALTO/MÉDIO/BAIXO impacto).
3. Salva um relatório .txt individual para leads classificados como ALTO impacto.

Nota de precisão técnica: isso é uma integração com LLM orientada por prompt,
não um "agente autônomo" no sentido técnico (sem memória, sem decisão
multi-etapa, sem uso de ferramentas). Vale nomear assim em entrevista.
"""

import os
import csv
import time
import logging

import requests
from dotenv import load_dotenv
from tqdm import tqdm

# -----------------------------------------------------------------
# CONFIGURAÇÃO
# -----------------------------------------------------------------
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_ID = "models/gemini-flash-latest"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/{MODEL_ID}:generateContent?key={API_KEY}"

MAX_RETRIES = 5          # antes: while True sem limite -> podia travar pra sempre
RETRY_WAIT_SECONDS = 15
REQUEST_TIMEOUT = 20     # antes: requests.post sem timeout -> podia travar indefinidamente

ARQUIVO_ENTRADA = "leads.csv"
PASTA_SAIDA = "relatorios_premium"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------
# CHAMADA À API
# -----------------------------------------------------------------
def qualificar_lead_saude(mensagem: str) -> str | None:
    """
    Envia a mensagem do lead ao Gemini e retorna o texto da análise.
    Retorna None se a chamada falhar de forma não recuperável.
    """
    if not API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY não encontrada. Verifique seu arquivo .env."
        )

    instrucoes = (
        "Você é um Consultor Sênior em Saúde. Analise este lead: "
        f"'{mensagem}'.\n\n"
        "Estruture sua resposta assim:\n"
        "CLASSIFICAÇÃO: [ALTO/MÉDIO/BAIXO]\n"
        "PERFIL: [Resumo do decisor]\n"
        "DOR: [Problema principal]\n"
        "ESTRATÉGIA: [Como abordar esse lead]\n"
    )
    payload = {"contents": [{"parts": [{"text": instrucoes}]}]}

    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(url=API_URL, json=payload, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.Timeout:
            logger.warning("Timeout na tentativa %s/%s", tentativa, MAX_RETRIES)
            continue
        except requests.exceptions.RequestException as exc:
            logger.error("Erro de conexão: %s", exc)
            return None

        if response.status_code == 200:
            data = response.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                logger.error("Resposta da API em formato inesperado: %s", data)
                return None

        if response.status_code == 429:
            logger.info("Cota excedida. Aguardando %ss (tentativa %s/%s)...",
                        RETRY_WAIT_SECONDS, tentativa, MAX_RETRIES)
            time.sleep(RETRY_WAIT_SECONDS)
            continue

        logger.error("Erro HTTP %s: %s", response.status_code, response.text[:200])
        return None

    logger.error("Número máximo de tentativas excedido para este lead.")
    return None


# -----------------------------------------------------------------
# PROCESSAMENTO EM LOTE
# -----------------------------------------------------------------
def processar_com_relatorios():
    if not os.path.exists(ARQUIVO_ENTRADA):
        logger.error("Arquivo %s não encontrado!", ARQUIVO_ENTRADA)
        return

    os.makedirs(PASTA_SAIDA, exist_ok=True)

    with open(ARQUIVO_ENTRADA, "r", encoding="utf-8") as f:
        total_leads = sum(1 for _ in f) - 1

    logger.info("Iniciando processamento de %s leads...", total_leads)

    sucesso, falhas = 0, 0

    with open(ARQUIVO_ENTRADA, mode="r", encoding="utf-8") as entrada:
        leitor = csv.DictReader(entrada)
        for linha in tqdm(leitor, total=total_leads, desc="Processando", unit="lead"):
            analise = qualificar_lead_saude(linha["mensagem"])

            if analise is None:
                falhas += 1
                continue

            if "ALTO" in analise.upper():
                nome_arquivo = f"lead_{linha['id']}_prioridade_maxima.txt"
                caminho_completo = os.path.join(PASTA_SAIDA, nome_arquivo)
                with open(caminho_completo, "w", encoding="utf-8") as f:
                    f.write(f"--- RELATÓRIO ESTRATÉGICO (LEAD ID {linha['id']}) ---\n\n")
                    f.write(f"MENSAGEM ORIGINAL: {linha['mensagem']}\n")
                    f.write("-" * 40 + "\n")
                    f.write(analise)

            sucesso += 1
            time.sleep(1)  # respeita rate limit da API

    logger.info("Concluído. %s leads processados, %s falhas.", sucesso, falhas)
    logger.info("Relatórios de Alto Impacto salvos em: %s", PASTA_SAIDA)


if __name__ == "__main__":
    processar_com_relatorios()
import os
import requests
import time
import csv
from dotenv import load_dotenv
from tqdm import tqdm

# 1. CONFIGURAÇÃO
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

def qualificar_lead_saude(mensagem):
    model_id = "models/gemini-flash-latest"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_id}:generateContent?key={api_key}"
    
    # Prompt de Alta Performance
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

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        elif response.status_code == 429:
            return "ERRO_COTA"
        return f"Erro {response.status_code}"
    except:
        return "Erro de Conexão"

# 2. PROCESSAMENTO E GERAÇÃO DE ARQUIVOS INDIVIDUAIS
def processar_com_relatorios():
    arquivo_entrada = 'leads.csv'
    pasta_saida = 'relatorios_premium'

    # Criar a pasta de relatórios se não existir
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)

    if not os.path.exists(arquivo_entrada):
        print(f"❌ Arquivo {arquivo_entrada} não encontrado!")
        return

    # Contar total de leads
    with open(arquivo_entrada, 'r', encoding='utf-8') as f:
        total_leads = sum(1 for linha in f) - 1

    print(f"\n🚀 Iniciando Fábrica de Relatórios Estratégicos...")

    with open(arquivo_entrada, mode='r', encoding='utf-8') as entrada:
        leitor = csv.DictReader(entrada)

        for linha in tqdm(leitor, total=total_leads, desc="Processando", unit="lead"):
            while True:
                analise = qualificar_lead_saude(linha['mensagem'])
                
                if analise == "ERRO_COTA":
                    time.sleep(15)
                else:
                    # Salvar apenas se for ALTO IMPACTO nos arquivos individuais
                    if "ALTO" in analise.upper():
                        nome_arquivo = f"lead_{linha['id']}_prioridade_maxima.txt"
                        caminho_completo = os.path.join(pasta_saida, nome_arquivo)
                        
                        with open(caminho_completo, 'w', encoding='utf-8') as f:
                            f.write(f"--- RELATÓRIO ESTRATÉGICO (LEAD ID {linha['id']}) ---\n\n")
                            f.write(f"MENSAGEM ORIGINAL: {linha['mensagem']}\n")
                            f.write("-" * 40 + "\n")
                            f.write(analise)
                    break
            
            time.sleep(1)

    print(f"\n✅ SUCESSO! Relatórios de Alto Impacto salvos na pasta: {pasta_saida}")

if __name__ == "__main__":
    processar_com_relatorios()
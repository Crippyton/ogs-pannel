import os
import re

def atualizar_flet_enums_em_arquivo(caminho_arquivo):
    with open(caminho_arquivo, "r", encoding="utf-8") as file:
        content = file.read()

    original = content

    content = re.sub(r"\bft\.colors\.with_opacity\(", "ft.Colors.with_opacity(", content)
    content = re.sub(r"\bft\.colors\.", "ft.Colors.", content)
    content = re.sub(r"\bft\.icons\.", "ft.Icons.", content)

    if content != original:
        with open(caminho_arquivo, "w", encoding="utf-8") as file:
            file.write(content)
        print(f"✅ Corrigido: {caminho_arquivo}")

def corrigir_projeto_completo(caminho_raiz):
    for root, _, files in os.walk(caminho_raiz):
        for filename in files:
            if filename.endswith(".py"):
                atualizar_flet_enums_em_arquivo(os.path.join(root, filename))

if __name__ == "__main__":
    projeto_dir = os.path.dirname(os.path.abspath(__file__))
    print("🔧 Corrigindo enums deprecados do Flet...\n")
    corrigir_projeto_completo(projeto_dir)
    print("\n✅ Correção concluída com sucesso.")

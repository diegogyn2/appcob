import os
import requests
import json
import streamlit as st
from dotenv import load_dotenv
from typing import Union, List, Dict
from datetime import datetime, timedelta

class ClientControl:
    """
    Uma classe para gerenciar uma base de dados JSON simples armazenada 
    em um único arquivo dentro de um Gist do GitHub.
    """
    def __init__(self, token: str, gist_id: str):
        """
        Inicializa o objeto e autentica a conexão com o Gist.

        Args:
            token (str): O Personal Access Token (PAT) do GitHub.
            gist_id (str): O ID do Gist que será usado como banco de dados.
        
        Raises:
            ValueError: Se o token não for fornecido.
            ConnectionError: Se a autenticação com a API do GitHub falhar.
        """
        if not token:
            raise ValueError("❌ ERRO: O token do GitHub não foi fornecido.")
        
        self.token = token
        self.gist_id = gist_id
        # O nome do arquivo no Gist é um detalhe de implementação interno e fixo.
        self.filename = "dados.json" 
        self.api_headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json"
        }
        
        # A autenticação é chamada no momento da criação do objeto.
        self._autenticar()

    def _autenticar(self):
        """Método privado para verificar o token na inicialização."""
        print("--- Verificando autenticação com o GitHub... ---")
        url = "https://api.github.com/user"
        try:
            response = requests.get(url, headers=self.api_headers)
            response.raise_for_status() # Lança erro para status 4xx ou 5xx
            usuario = response.json()
            print(f"✅ Autenticação bem-sucedida como '{usuario['login']}'.")
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 401:
                raise ConnectionError("ERRO DE AUTENTICAÇÃO: O token fornecido é inválido ou expirou.")
            else:
                raise ConnectionError(f"Falha na autenticação com status: {err.response.status_code}.")
        except requests.exceptions.RequestException as err:
            raise ConnectionError(f"Erro de conexão com a API do GitHub: {err}")

    def consultar_dados(self) -> Union[List[Dict], None]:
        """Consulta o Gist e retorna todo o conteúdo do arquivo JSON."""
        print(f"\n--- Consultando dados do Gist '{self.gist_id}'... ---")
        url = f"https://api.github.com/gists/{self.gist_id}"
        try:
            response = requests.get(url, headers=self.api_headers)
            response.raise_for_status()
            gist_data = response.json()
            conteudo_string = gist_data["files"][self.filename]["content"]
            print("✅ Dados lidos com sucesso!")
            return json.loads(conteudo_string)
        except Exception as err:
            print(f"❌ Erro ao consultar o Gist: {err}")
            return None

    def atualizar_gist(self, novo_conteudo: List[Dict]) -> bool:
        """Sobrescreve o arquivo no Gist com o novo conteúdo."""
        print(f"--- Atualizando dados no Gist... ---")
        url = f"https://api.github.com/gists/{self.gist_id}"
        payload = {"files": {self.filename: {"content": json.dumps(novo_conteudo, indent=2)}}}
        try:
            response = requests.patch(url, headers=self.api_headers, json=payload)
            response.raise_for_status()
            print("✅ Gist atualizado com sucesso no GitHub!")
            return True
        except Exception as err:
            print(f"❌ Erro ao atualizar o Gist: {err}")
            return False

    def _encontrar_devedor(self, lista_devedores: List[Dict], nome: str) -> Union[Dict, None]:
        """Método auxiliar para encontrar um devedor na lista pelo nome."""
        for devedor in lista_devedores:
            if devedor.get("nome", "").lower() == nome.lower():
                return devedor
        return None

    def cadastrar_novo_devedor(self, nome: str, n_parcelas: int, vl_par: float, p_vencimento: str):
        """Cadastra um novo devedor com suas parcelas iniciais."""
        print(f"\n--- Cadastrando '{nome}'... ---")
        dados = self.consultar_dados()
        if dados is None: dados = []
        if self._encontrar_devedor(dados, nome):
            print(f"⚠️  Devedor '{nome}' já está cadastrado. Operação cancelada.")
            return
        try:
            vencimento_base = datetime.strptime(p_vencimento, "%Y-%m-%d")
            parcelas = []
            for i in range(n_parcelas):
                vencimento = vencimento_base + timedelta(days=30 * i)
                parcelas.append({"valor": vl_par, "vencimento": vencimento.strftime("%Y-%m-%d"), "paga": False})
            novo_devedor = {"nome": nome, "parcelas": parcelas}
            dados.append(novo_devedor)
            if self.atualizar_gist(dados):
                print(f"✅ Devedor '{nome}' salvo com sucesso.")
        except ValueError:
            print("❌ Data de vencimento inválida. Use o formato YYYY-MM-DD.")

    def adicionar_parcela(self, nome_devedor: str, valor: float, vencimento: str):
        """Adiciona uma única parcela a um devedor existente."""
        print(f"\n--- Adicionando parcela para '{nome_devedor}'... ---")
        dados = self.consultar_dados()
        if dados is None: return
        devedor_encontrado = self._encontrar_devedor(dados, nome_devedor)
        if not devedor_encontrado:
            print(f"❌ Devedor '{nome_devedor}' não encontrado.")
            return
        try:
            datetime.strptime(vencimento, "%Y-%m-%d")
            nova_parcela = {"valor": valor, "vencimento": vencimento, "paga": False}
            devedor_encontrado["parcelas"].append(nova_parcela)
            if self.atualizar_gist(dados):
                print(f"✅ Parcela salva com sucesso para '{nome_devedor}'.")
        except ValueError:
            print("❌ Data de vencimento inválida. Use o formato YYYY-MM-DD.")

    def deletar_devedor(self, nome_devedor: str):
        """Remove um devedor e todas as suas parcelas da lista."""
        print(f"\n--- Deletando '{nome_devedor}'... ---")
        dados = self.consultar_dados()
        if dados is None: return
        nova_lista = [d for d in dados if d.get("nome", "").lower() != nome_devedor.lower()]
        if len(nova_lista) == len(dados):
            print(f"❌ Devedor '{nome_devedor}' não encontrado.")
            return
        if self.atualizar_gist(nova_lista):
            print(f"✅ Devedor '{nome_devedor}' deletado com sucesso.")

    def deletar_parcela(self, nome_devedor: str, vencimento_parcela: str):
        """Encontra um devedor e deleta uma de suas parcelas pela data de vencimento."""
        print(f"\n--- Deletando parcela de '{vencimento_parcela}' para '{nome_devedor}'... ---")
        dados = self.consultar_dados()
        if dados is None: return
        devedor_encontrado = self._encontrar_devedor(dados, nome_devedor)
        if not devedor_encontrado:
            print(f"❌ Devedor '{nome_devedor}' não encontrado.")
            return
        n_parcelas_original = len(devedor_encontrado["parcelas"])
        parcelas_atualizadas = [p for p in devedor_encontrado["parcelas"] if p.get("vencimento") != vencimento_parcela]
        if len(parcelas_atualizadas) == n_parcelas_original:
            print(f"❌ Nenhuma parcela com vencimento em '{vencimento_parcela}' foi encontrada.")
            return
        devedor_encontrado["parcelas"] = parcelas_atualizadas
        if self.atualizar_gist(dados):
            print(f"✅ Parcela de '{vencimento_parcela}' deletada com sucesso.")

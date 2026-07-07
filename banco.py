import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================
# BANCO DE DADOS (PostgreSQL / Supabase)
# A string de conexão vem da variável de ambiente DATABASE_URL,
# configurada no Render (Environment -> Environment Variables),
# apontando para o seu projeto Supabase.
# Nenhuma informação/credencial fica escrita no código.
# ============================================================
DATABASE_URL = os.environ["DATABASE_URL"]

FUSO_BR = ZoneInfo("America/Sao_Paulo")


@contextmanager
def get_cursor():
    """
    Context manager que abre a conexão, entrega um cursor (RealDictCursor,
    pra acessar colunas pelo nome tipo linha['id']), comita no final se
    tudo deu certo, ou desfaz (rollback) se algo der erro.
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def criar_banco():
    """
    Cria as tabelas caso ainda não existam. Chamar uma vez ao iniciar o app.
    - cotacoes: 1 linha por cotação, com um token único usado no link público.
    - itens_cotacao: os itens de cada cotação, com o preço preenchido depois
      pelo fornecedor (começa NULL).
    """
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cotacoes (
                id SERIAL PRIMARY KEY,
                token TEXT UNIQUE NOT NULL,
                fornecedor TEXT,
                data_criacao TIMESTAMPTZ NOT NULL,
                status TEXT NOT NULL DEFAULT 'aguardando'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS itens_cotacao (
                id SERIAL PRIMARY KEY,
                cotacao_id INTEGER NOT NULL REFERENCES cotacoes (id),
                grupo TEXT,
                item TEXT NOT NULL,
                volume TEXT,
                qtd REAL,
                preco_unitario REAL
            )
        """)


def criar_cotacao(fornecedor, itens):
    """
    Salva uma nova cotação e seus itens.
    'itens' é a lista que já vem do dcc.Store (lista-store) da tela principal.
    Retorna (id_cotacao, token) -- o token é o que entra no link enviado ao fornecedor.
    Usamos um token aleatório (uuid4) em vez do id sequencial para que o link
    não seja adivinhável por quem não recebeu (ele é público e sem login).
    """
    token = uuid.uuid4().hex
    agora = datetime.now(FUSO_BR)

    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO cotacoes (token, fornecedor, data_criacao, status) VALUES (%s, %s, %s, %s) RETURNING id",
            (token, fornecedor, agora, 'aguardando')
        )
        cotacao_id = cur.fetchone()['id']

        for item in itens:
            cur.execute(
                """INSERT INTO itens_cotacao (cotacao_id, grupo, item, volume, qtd, preco_unitario)
                   VALUES (%s, %s, %s, %s, %s, NULL)""",
                (cotacao_id, item.get('grupo'), item.get('item'), item.get('volume'), item.get('qtd'))
            )

    return cotacao_id, token


def _formatar_cotacao(cotacao, itens):
    """Monta o dicionário de retorno padrão, convertendo a data para texto ISO."""
    return {
        "id": cotacao['id'],
        "token": cotacao['token'],
        "fornecedor": cotacao['fornecedor'],
        "status": cotacao['status'],
        "data_criacao": cotacao['data_criacao'].isoformat(),
        "itens": [dict(i) for i in itens],
    }


def buscar_cotacao_por_token(token):
    """Busca a cotação e seus itens pelo token do link. Retorna None se não existir."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM cotacoes WHERE token = %s", (token,))
        cotacao = cur.fetchone()
        if cotacao is None:
            return None

        cur.execute("SELECT * FROM itens_cotacao WHERE cotacao_id = %s", (cotacao['id'],))
        itens = cur.fetchall()
        return _formatar_cotacao(cotacao, itens)


def buscar_cotacao_por_id(cotacao_id):
    """Igual a buscar_cotacao_por_token, mas buscando pelo ID (usado na tela de resultado interna)."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM cotacoes WHERE id = %s", (cotacao_id,))
        cotacao = cur.fetchone()
        if cotacao is None:
            return None

        cur.execute("SELECT * FROM itens_cotacao WHERE cotacao_id = %s", (cotacao['id'],))
        itens = cur.fetchall()
        return _formatar_cotacao(cotacao, itens)


def salvar_precos(token, precos):
    """
    Grava os preços preenchidos pelo fornecedor.
    'precos' é uma lista de dicts: [{'id': <id do item>, 'preco_unitario': <valor>}, ...]
    Ao salvar, marca a cotação como 'respondida'.
    """
    with get_cursor() as cur:
        for p in precos:
            cur.execute(
                "UPDATE itens_cotacao SET preco_unitario = %s WHERE id = %s",
                (p.get('preco_unitario'), p['id'])
            )
        cur.execute("UPDATE cotacoes SET status = 'respondida' WHERE token = %s", (token,))


def listar_cotacoes():
    """Lista todas as cotações já criadas (mais recente primeiro)."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM cotacoes ORDER BY id DESC")
        linhas = cur.fetchall()
        return [
            {**dict(r), "data_criacao": r['data_criacao'].isoformat()}
            for r in linhas
        ]

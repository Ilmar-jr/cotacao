import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor

# O Render injeta o DATABASE_URL automaticamente. Localmente, pegará o fallback do localhost.
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/nome_banco")
FUSO_BR = ZoneInfo("America/Sao_Paulo")

@contextmanager
def get_cursor():
    """Gerencia conexões abertas com commit automático e rollback em caso de falha."""
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
    """Cria as tabelas estruturadas com suporte a rodadas no PostgreSQL."""
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cotacoes (
                id SERIAL PRIMARY KEY,
                token TEXT UNIQUE NOT NULL,
                fornecedor TEXT,
                data_criacao TIMESTAMPTZ NOT NULL,
                status TEXT NOT NULL DEFAULT 'aguardando',
                rodada_atual INTEGER NOT NULL DEFAULT 1
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS itens_cotacao (
                id SERIAL PRIMARY KEY,
                cotacao_id INTEGER NOT NULL REFERENCES cotacoes (id) ON DELETE CASCADE,
                grupo TEXT,
                item TEXT NOT NULL,
                volume TEXT,
                qtd REAL,
                preco_unitario REAL,
                rodada INTEGER NOT NULL DEFAULT 1
            )
        """)

def criar_cotacao(fornecedor, itens):
    """Salva uma nova cotação vinculando os itens à rodada inicial 1."""
    token = uuid.uuid4().hex
    agora = datetime.now(FUSO_BR)

    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO cotacoes (token, fornecedor, data_criacao, status, rodada_atual) VALUES (%s, %s, %s, %s, 1) RETURNING id",
            (token, fornecedor, agora, 'aguardando')
        )
        cotacao_id = cur.fetchone()['id']

        for item in itens:
            cur.execute(
                """INSERT INTO itens_cotacao (cotacao_id, grupo, item, volume, qtd, preco_unitario, rodada)
                   VALUES (%s, %s, %s, %s, %s, NULL, 1)""",
                (cotacao_id, item.get('grupo'), item.get('item'), item.get('volume'), item.get('qtd'))
            )

    return cotacao_id, token

def buscar_cotacao_para_responder(token):
    """Retorna a cotação e APENAS os itens que pertencem à rodada ativa no momento."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM cotacoes WHERE token = %s", (token,))
        cotacao = cur.fetchone()
        if cotacao is None:
            return None

        cur.execute(
            "SELECT * FROM itens_cotacao WHERE cotacao_id = %s AND rodada = %s ORDER BY id ASC", 
            (cotacao['id'], cotacao['rodada_atual'])
        )
        itens = cur.fetchall()
        
        return {
            "id": cotacao['id'],
            "token": cotacao['token'],
            "fornecedor": cotacao['fornecedor'],
            "status": cotacao['status'],
            "rodada_atual": cotacao['rodada_atual'],
            "data_criacao": cotacao['data_criacao'].isoformat(),
            "itens": [dict(i) for i in itens]
        }

def buscar_todas_rodadas_id(cotacao_id):
    """Retorna a cotação e o histórico completo de todas as rodadas já realizadas."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM cotacoes WHERE id = %s", (cotacao_id,))
        cotacao = cur.fetchone()
        if cotacao is None:
            return None

        cur.execute("SELECT * FROM itens_cotacao WHERE cotacao_id = %s ORDER BY rodada DESC, id ASC", (cotacao['id'],))
        itens = cur.fetchall()
        
        return {
            "id": cotacao['id'],
            "token": cotacao['token'],
            "fornecedor": cotacao['fornecedor'],
            "status": cotacao['status'],
            "rodada_atual": cotacao['rodada_atual'],
            "data_criacao": cotacao['data_criacao'].isoformat(),
            "itens": [dict(i) for i in itens]
        }

def salvar_precos(token, precos, rodada_atual):
    """Salva os preços informados aplicando-os na respectiva rodada."""
    with get_cursor() as cur:
        for p in precos:
            cur.execute("""
                UPDATE itens_cotacao 
                SET preco_unitario = %s 
                WHERE id = %s AND rodada = %s
            """, (p.get('preco_unitario'), p['id'], rodada_atual))
            
        cur.execute("UPDATE cotacoes SET status = 'respondida' WHERE token = %s", (token,))

def abrir_nova_rodada_negociacao(cotacao_id):
    """Duplica a lista de itens incrementando a rodada evolutiva para negociação."""
    with get_cursor() as cur:
        cur.execute("""
            UPDATE cotacoes 
            SET rodada_atual = rodada_atual + 1, status = 'aguardando' 
            WHERE id = %s 
            RETURNING rodada_atual
        """, (cotacao_id,))
        nova_rodada = cur.fetchone()['rodada_atual']
        
        cur.execute("""
            INSERT INTO itens_cotacao (cotacao_id, grupo, item, volume, qtd, preco_unitario, rodada)
            SELECT cotacao_id, grupo, item, volume, qtd, NULL, %s
            FROM itens_cotacao
            WHERE cotacao_id = %s AND rodada = %s
        """, (nova_rodada, cotacao_id, nova_rodada - 1))

def listar_cotacoes():
    """Lista todas as cotações geradas ordenando pelo ID decrescente."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM cotacoes ORDER BY id DESC")
        linhas = cur.fetchall()
        return [
            {**dict(r), "data_criacao": r['data_criacao'].isoformat()}
            for r in linhas
        ]

import os
from dash import html, dcc, dash_table, Output, Input, State, callback, Dash, callback_context, no_update, ALL
import dash_bootstrap_components as dbc
import pandas as pd
from flask import request
from werkzeug.middleware.proxy_fix import ProxyFix

import banco as bd

# ============================================================
# BANCO DE DADOS
# Cria as tabelas no Postgres/Supabase na primeira execução, caso ainda
# não existam. Não insere nenhuma informação -- só garante a estrutura.
# Precisa da variável de ambiente DATABASE_URL configurada no Render,
# apontando pra string de conexão do seu projeto Supabase.
# ============================================================
bd.criar_banco()

# ============================================================
# TEMA VISUAL
# ============================================================
FONTS_URL = "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap"

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP, FONTS_URL],
    suppress_callback_exceptions=True,  # necessário: a página /responder/<token> só existe em runtime
)
server = app.server  # referência ao Flask por baixo do Dash -- é isso que o Render/gunicorn usa pra servir o app

# O Render fica atrás de um proxy reverso: sem isso, request.host_url viria
# como "http://..." (interno) em vez de "https://seu-app.onrender.com/",
# e o link gerado pro fornecedor sairia errado.
server.wsgi_app = ProxyFix(server.wsgi_app, x_proto=1, x_host=1)

COR_BG = "#0e1218"
COR_CARD = "#161c26"
COR_CARD_2 = "#1c2431"
COR_BORDA = "#2a3242"
COR_TEXTO = "#e8ecf3"
COR_MUTED = "#8b95a5"
COR_ACCENT = "#d9a441"
COR_ACCENT_2 = "#3b82c4"
COR_PERIGO = "#e5484d"
COR_SUCESSO = "#3ba55d"

INDEX_STRING = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background-color: ''' + COR_BG + ''' !important;
                font-family: 'Inter', sans-serif;
            }
            .titulo-cotacao {
                font-family: 'Space Grotesk', sans-serif;
                letter-spacing: 0.5px;
            }
            .card-cotacao {
                background-color: ''' + COR_CARD + ''';
                border: 1px solid ''' + COR_BORDA + ''';
                border-radius: 10px;
            }
            .rotulo-campo {
                font-family: 'Inter', sans-serif;
                font-size: 13px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.6px;
                color: ''' + COR_MUTED + ''';
                margin-bottom: 6px;
            }
            .faixa-ticket {
                border-top: 2px dashed ''' + COR_BORDA + ''';
                border-bottom: 2px dashed ''' + COR_BORDA + ''';
                padding: 10px 0;
                font-family: 'Space Grotesk', sans-serif;
                color: ''' + COR_ACCENT + ''';
                letter-spacing: 1px;
            }
            .badge-resumo {
                background-color: ''' + COR_CARD_2 + ''' !important;
                color: ''' + COR_TEXTO + ''' !important;
                border: 1px solid ''' + COR_BORDA + ''';
                font-family: 'Space Grotesk', sans-serif;
                font-size: 14px;
                padding: 8px 14px;
            }
            .Select-control, .dropdown, div[class*="-control"] {
                background-color: ''' + COR_CARD_2 + ''' !important;
                border-color: ''' + COR_BORDA + ''' !important;
                color: ''' + COR_TEXTO + ''' !important;
            }
            input {
                background-color: ''' + COR_CARD_2 + ''' !important;
                color: ''' + COR_TEXTO + ''' !important;
                border-color: ''' + COR_BORDA + ''' !important;
            }
            .caixa-link {
                background-color: ''' + COR_CARD_2 + ''';
                border: 1px solid ''' + COR_ACCENT_2 + ''';
                border-radius: 8px;
                padding: 14px 16px;
                color: ''' + COR_TEXTO + ''';
                font-family: monospace;
                font-size: 14px;
                word-break: break-all;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''
app.index_string = INDEX_STRING

# ============================================================
# DADOS (planilhas de apoio, usadas só na tela interna)
# ============================================================
produtos = pd.read_excel('produtos.xlsx')
fornecedor = pd.read_excel('fornecedor.xlsx')

fn = fornecedor['Nome do PN'].dropna().unique()
grupo = produtos['Nome do grupo'].dropna().unique()
todos_produtos = produtos['Descrição do item'].dropna().unique()


def campo(label, componente, largura):
    return dbc.Col([
        html.Div(label, className="rotulo-campo"),
        componente
    ], width=largura)


def parse_preco(valor):
    """
    Converte o preço digitado pelo fornecedor em float, aceitando tanto
    vírgula quanto ponto como separador decimal (ex: '12,50' ou '12.50'),
    e também formatos com milhar como '1.234,56'.
    Retorna None se o valor estiver vazio ou não for possível converter.
    """
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip().replace("R$", "").strip()

    if "," in texto and "." in texto:
        # formato "1.234,56" -> ponto é milhar, vírgula é decimal
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        # formato "12,50" -> vírgula é decimal
        texto = texto.replace(",", ".")

    try:
        return float(texto)
    except ValueError:
        return None


# ============================================================
# LAYOUT 1: TELA INTERNA -- montar a cotação
# ============================================================
def layout_cotacao_interna():
    return dbc.Container([

        html.Div([
            html.Div([
                html.I(className="bi bi-clipboard2-data me-2", style={'color': COR_ACCENT_2}),
                html.Span("COTAÇÃO ONLINE", className="titulo-cotacao",
                          style={'fontSize': '28px', 'fontWeight': '700', 'color': COR_TEXTO}),
            ]),
            html.Div("Cadastro e comparação de itens para cotação de fornecedores",
                     style={'color': COR_MUTED, 'fontSize': '14px', 'marginTop': '4px'}),
        ], style={'padding': '18px 4px 8px 4px'}),

        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    campo("Fornecedor", dcc.Dropdown(
                        [{'label': i, 'value': i} for i in fn], id='tab-pn',
                        placeholder="Escolha um fornecedor..", style={'color': '#000'}
                    ), 3),
                    campo("Grupo", dcc.Dropdown(
                        [{'label': i, 'value': i} for i in grupo], id='grupo',
                        placeholder="Escolha um grupo..", style={'color': '#000'}
                    ), 2),
                    campo("Produto", dcc.Dropdown(
                        [{'label': i, 'value': i} for i in todos_produtos], id='produtos',
                        placeholder="Escolha um produto..", style={'color': '#000'}
                    ), 3),
                    campo("Volume", dcc.Input(
                        id='input-volume', type="text", placeholder="Volume",
                        style={'width': '100%', 'height': '38px', 'borderRadius': '6px'}
                    ), 2),
                    campo("Quantidade", dcc.Input(
                        id='input-qtd', type="number", placeholder="Quantidade",
                        style={'width': '100%', 'height': '38px', 'borderRadius': '6px'}
                    ), 2),
                ], className="g-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Button([html.I(className="bi bi-check2-circle me-2"), "Salvar item"],
                                   id='Btn-salvar', n_clicks=0,
                                   style={'backgroundColor': COR_ACCENT_2, 'border': 'none',
                                          'fontWeight': '600', 'width': '100%'})
                    ], width=3),
                    dbc.Col([
                        dbc.Button([html.I(className="bi bi-trash3 me-2"), "Remover selecionado"],
                                   id='Btn-remover', n_clicks=0,
                                   style={'backgroundColor': 'transparent', 'border': f'1px solid {COR_PERIGO}',
                                          'color': COR_PERIGO, 'fontWeight': '600', 'width': '100%'})
                    ], width=3),
                ], className="mt-4 g-3"),
            ])
        ], className="card-cotacao", style={'padding': '10px'}),

        dcc.Store(id='lista-store', data=[]),

        html.Div([
            dbc.Row([
                dbc.Col(html.Span("ITENS DA COTAÇÃO"), width='auto'),
                dbc.Col([
                    dbc.Badge(id='badge-total-itens', children="0 itens", className="badge-resumo me-2"),
                    dbc.Badge(id='badge-total-qtd', children="0 un.", className="badge-resumo"),
                ], width='auto', className="ms-auto"),
            ], justify='between', align='center')
        ], className="faixa-ticket", style={'marginTop': '28px', 'marginBottom': '14px'}),

        dbc.Card([
            dbc.CardBody([
                dash_table.DataTable(
                    id='tabela-lista',
                    columns=[
                        {"name": "Fornecedor", "id": "fornecedor"},
                        {"name": "Grupo", "id": "grupo"},
                        {"name": "Item", "id": "item"},
                        {"name": "Volume", "id": "volume"},
                        {"name": "Qtd", "id": "qtd"}
                    ],
                    data=[],
                    row_selectable='single',
                    page_size=20,
                    style_header={
                        'backgroundColor': COR_CARD_2, 'color': COR_MUTED, 'fontWeight': '600',
                        'textTransform': 'uppercase', 'fontSize': '12px', 'border': 'none',
                        'borderBottom': f'1px solid {COR_BORDA}',
                    },
                    style_cell={
                        'backgroundColor': COR_CARD, 'color': COR_TEXTO, 'textAlign': 'left',
                        'padding': '10px', 'border': 'none', 'borderBottom': f'1px solid {COR_BORDA}',
                        'fontFamily': 'Inter, sans-serif',
                    },
                    style_data_conditional=[
                        {'if': {'state': 'selected'}, 'backgroundColor': COR_CARD_2,
                         'border': f'1px solid {COR_ACCENT_2}'},
                    ],
                    style_as_list_view=True,
                )
            ])
        ], className="card-cotacao"),

        # --- Etapa 2: finalizar e gerar o link para o fornecedor ---
        html.Div([
            dbc.Row([
                dbc.Col(html.Span("ENVIAR PARA O FORNECEDOR"), width='auto'),
            ], align='center')
        ], className="faixa-ticket", style={'marginTop': '28px', 'marginBottom': '14px'}),

        dbc.Card([
            dbc.CardBody([
                html.Div(
                    "Ao finalizar, a cotação é salva com um ID e um link exclusivo é gerado. "
                    "Envie esse link ao fornecedor selecionado para que ele preencha o preço de cada item.",
                    style={'color': COR_MUTED, 'fontSize': '13px', 'marginBottom': '14px'}
                ),
                dbc.Button([html.I(className="bi bi-send-check me-2"), "Finalizar cotação e gerar link"],
                           id='Btn-finalizar', n_clicks=0,
                           style={'backgroundColor': COR_ACCENT, 'border': 'none', 'color': '#12161c',
                                  'fontWeight': '700'}),
                html.Div(id='resultado-link', style={'marginTop': '16px'}),
            ])
        ], className="card-cotacao"),

        # --- Histórico: cotações já criadas, com acesso ao resultado ---
        html.Div([
            dbc.Row([
                dbc.Col(html.Span("COTAÇÕES CRIADAS"), width='auto'),
            ], align='center')
        ], className="faixa-ticket", style={'marginTop': '28px', 'marginBottom': '14px'}),

        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    campo("Buscar", dcc.Input(
                        id='filtro-busca', type="text", placeholder="Nº da cotação ou fornecedor..",
                        style={'width': '100%', 'height': '38px', 'borderRadius': '6px'}
                    ), 4),
                    campo("Status", dcc.Dropdown(
                        id='filtro-status',
                        options=[
                            {'label': 'Todas', 'value': 'todas'},
                            {'label': 'Aguardando fornecedor', 'value': 'aguardando'},
                            {'label': 'Respondida', 'value': 'respondida'},
                        ],
                        value='todas', clearable=False, style={'color': '#000'}
                    ), 3),
                    campo("Criada de", dcc.DatePickerSingle(
                        id='filtro-data-inicio', display_format='DD/MM/YYYY', placeholder="Data inicial"
                    ), 2),
                    campo("até", dcc.DatePickerSingle(
                        id='filtro-data-fim', display_format='DD/MM/YYYY', placeholder="Data final"
                    ), 2),
                ], className="g-3 mb-3"),
                html.Div(id='lista-cotacoes-criadas'),
            ])
        ], className="card-cotacao"),

    ], style={
        'paddingLeft': '80px', 'paddingRight': '80px', 'paddingBottom': '60px', 'minHeight': '100vh',
    }, fluid=True)


def montar_tabela_cotacoes(busca=None, status=None, data_inicio=None, data_fim=None):
    """
    Monta a tabela de cotações criadas (mais recente primeiro), já filtrada
    conforme os campos de busca/status/período, e com o link de cada uma
    (não precisa mais finalizar de novo pra reencontrar o link).
    Cada linha continua clicável (active_cell) e leva para /resultado/<id>.
    """
    cotacoes = bd.listar_cotacoes()

    # --- aplica os filtros em Python (lista já é pequena, não precisa de SQL pra isso) ---
    if busca:
        busca_lower = busca.strip().lower()
        cotacoes = [
            c for c in cotacoes
            if busca_lower in str(c['id'])
            or busca_lower in (c['fornecedor'] or "").lower()
        ]

    if status and status != 'todas':
        cotacoes = [c for c in cotacoes if c['status'] == status]

    if data_inicio:
        cotacoes = [c for c in cotacoes if c['data_criacao'][:10] >= data_inicio[:10]]

    if data_fim:
        cotacoes = [c for c in cotacoes if c['data_criacao'][:10] <= data_fim[:10]]

    if not cotacoes:
        return html.Div("Nenhuma cotação encontrada com esse filtro.",
                         style={'color': COR_MUTED, 'fontSize': '13px'})

    base_url = request.host_url.rstrip('/')

    linhas = [
        {
            "id": c['id'],  # não é uma coluna visível -- só usado no callback pra saber pra onde navegar
            "cotacao": f"#{c['id']}",
            "fornecedor": c['fornecedor'] or "-",
            "data_criacao": c['data_criacao'],
            "status": "Respondida" if c['status'] == 'respondida' else "Aguardando fornecedor",
            "link": f"{base_url}/responder/{c['token']}",
        }
        for c in cotacoes
    ]

    return html.Div([
        html.Div("Clique em uma linha para ver o resultado.",
                  style={'color': COR_MUTED, 'fontSize': '13px', 'marginBottom': '10px'}),
        dash_table.DataTable(
            id='tabela-cotacoes',
            columns=[
                {"name": "Cotação", "id": "cotacao"},
                {"name": "Fornecedor", "id": "fornecedor"},
                {"name": "Criada em", "id": "data_criacao"},
                {"name": "Status", "id": "status"},
                {"name": "Link para o fornecedor", "id": "link"},
            ],
            data=linhas,
            style_header={
                'backgroundColor': COR_CARD_2, 'color': COR_MUTED, 'fontWeight': '600',
                'textTransform': 'uppercase', 'fontSize': '12px', 'border': 'none',
                'borderBottom': f'1px solid {COR_BORDA}',
            },
            style_cell={
                'backgroundColor': COR_CARD, 'color': COR_TEXTO, 'textAlign': 'left',
                'padding': '10px', 'border': 'none', 'borderBottom': f'1px solid {COR_BORDA}',
                'fontFamily': 'Inter, sans-serif', 'cursor': 'pointer',
            },
            style_cell_conditional=[
                {'if': {'column_id': 'link'}, 'fontFamily': 'monospace', 'fontSize': '12px',
                 'color': COR_ACCENT_2, 'cursor': 'text'},
            ],
            style_as_list_view=True,
        )
    ])


# ============================================================
# LAYOUT 2: TELA PÚBLICA -- fornecedor preenche o preço
# ============================================================
def layout_responder_fornecedor(token):
    cotacao = bd.buscar_cotacao_por_token(token)

    if cotacao is None:
        return dbc.Container([
            html.Div([
                html.I(className="bi bi-exclamation-triangle me-2", style={'color': COR_PERIGO}),
                html.Span("Link inválido ou cotação não encontrada.", style={'color': COR_TEXTO, 'fontSize': '18px'})
            ], style={'marginTop': '60px'})
        ], style={'paddingLeft': '80px', 'paddingRight': '80px'}, fluid=True)

    ja_respondida = cotacao['status'] == 'respondida'

    # --- cabeçalho da "tabela" (grid manual, não é dash_table) ---
    cabecalho = dbc.Row([
        dbc.Col("Grupo", width=3), dbc.Col("Item", width=3), dbc.Col("Volume", width=2),
        dbc.Col("Qtd", width=1), dbc.Col("Preço unitário (R$)", width=3),
    ], className="py-2", style={
        'color': COR_MUTED, 'fontWeight': '600', 'textTransform': 'uppercase', 'fontSize': '12px',
        'borderBottom': f'1px solid {COR_BORDA}',
    })

    # --- uma linha por item -- o preço é um dcc.Input próprio, com id
    # {'type': 'preco-input', 'index': <id do item>}. Diferente da dash_table
    # editável, o valor de um dcc.Input fica sempre disponível de imediato
    # (sem depender de perder o foco), então não tem risco de o clique em
    # "Enviar" chegar antes do valor digitado ser registrado.
    linhas = []
    for item in cotacao['itens']:
        if ja_respondida:
            campo_preco = html.Div(
                f"R$ {parse_preco(item['preco_unitario']):,.2f}" if item['preco_unitario'] is not None else "-",
                style={'color': COR_TEXTO}
            )
        else:
            campo_preco = dcc.Input(
                id={'type': 'preco-input', 'index': item['id']},
                type="text",
                placeholder="Ex: 12,50",
                value=(str(item['preco_unitario']) if item['preco_unitario'] is not None else None),
                style={'width': '100%', 'height': '36px', 'borderRadius': '6px'}
            )

        linhas.append(
            dbc.Row([
                dbc.Col(item['grupo'] or "-", width=3, style={'color': COR_TEXTO}),
                dbc.Col(item['item'], width=3, style={'color': COR_TEXTO}),
                dbc.Col(item['volume'] or "-", width=2, style={'color': COR_TEXTO}),
                dbc.Col(item['qtd'], width=1, style={'color': COR_TEXTO}),
                dbc.Col(campo_preco, width=3),
            ], className="py-2 align-items-center", style={'borderBottom': f'1px solid {COR_BORDA}'})
        )

    return dbc.Container([

        html.Div([
            html.Div([
                html.I(className="bi bi-send-check-fill me-2", style={'color': COR_ACCENT_2}),
                html.Span("PREENCHIMENTO DE COTAÇÃO", className="titulo-cotacao",
                          style={'fontSize': '26px', 'fontWeight': '700', 'color': COR_TEXTO}),
            ]),
            html.Div(f"Fornecedor: {cotacao['fornecedor'] or '-'}   •   Cotação nº {cotacao['id']}",
                     style={'color': COR_MUTED, 'fontSize': '14px', 'marginTop': '4px'}),
        ], style={'padding': '18px 4px 8px 4px'}),

        dcc.Store(id='token-cotacao', data=token),

        dbc.Card([
            dbc.CardBody([
                html.Div(
                    "Preencha o preço unitário de cada item abaixo e clique em Enviar."
                    if not ja_respondida else
                    "Esta cotação já foi respondida. Os preços enviados estão abaixo.",
                    style={'color': COR_MUTED, 'fontSize': '13px', 'marginBottom': '14px'}
                ),

                cabecalho,
                html.Div(linhas),

                html.Div([
                    dbc.Button([html.I(className="bi bi-check2-circle me-2"), "Enviar preços"],
                               id='Btn-enviar-precos', n_clicks=0,
                               style={'backgroundColor': COR_ACCENT, 'border': 'none', 'color': '#12161c',
                                      'fontWeight': '700', 'marginTop': '18px'},
                               disabled=ja_respondida),
                    html.Div(id='mensagem-envio', style={'marginTop': '14px'}),
                ]),
            ])
        ], className="card-cotacao"),

    ], style={
        'paddingLeft': '80px', 'paddingRight': '80px', 'paddingBottom': '60px', 'minHeight': '100vh',
    }, fluid=True)


# ============================================================
# LAYOUT 3: TELA INTERNA -- resultado da cotação (após o fornecedor responder)
# ============================================================
def layout_resultado_cotacao(cotacao_id):
    try:
        cotacao = bd.buscar_cotacao_por_id(int(cotacao_id))
    except (TypeError, ValueError):
        cotacao = None

    if cotacao is None:
        return dbc.Container([
            html.Div([
                html.I(className="bi bi-exclamation-triangle me-2", style={'color': COR_PERIGO}),
                html.Span("Cotação não encontrada.", style={'color': COR_TEXTO, 'fontSize': '18px'})
            ], style={'marginTop': '60px', 'marginBottom': '20px'}),
            dcc.Link("← Voltar", href="/", style={'color': COR_ACCENT_2}),
        ], style={'paddingLeft': '80px', 'paddingRight': '80px'}, fluid=True)

    respondida = cotacao['status'] == 'respondida'

    linhas_tabela = []
    total_geral = 0
    for item in cotacao['itens']:
        preco = parse_preco(item['preco_unitario'])
        qtd = item['qtd'] or 0
        subtotal = (preco * qtd) if preco is not None else None
        if subtotal is not None:
            total_geral += subtotal
        linhas_tabela.append({
            "grupo": item['grupo'] or "-",
            "item": item['item'],
            "volume": item['volume'] or "-",
            "qtd": qtd,
            "preco_unitario": f"R$ {preco:,.2f}" if preco is not None else "Aguardando",
            "subtotal": f"R$ {subtotal:,.2f}" if subtotal is not None else "-",
        })

    return dbc.Container([

        html.Div([
            dcc.Link("← Voltar para a tela principal", href="/",
                     style={'color': COR_MUTED, 'fontSize': '13px'}),
            html.Div([
                html.I(className="bi bi-bar-chart-line-fill me-2", style={'color': COR_ACCENT_2}),
                html.Span(f"RESULTADO DA COTAÇÃO Nº {cotacao['id']}", className="titulo-cotacao",
                          style={'fontSize': '26px', 'fontWeight': '700', 'color': COR_TEXTO}),
            ], style={'marginTop': '10px'}),
            html.Div([
                html.Span(f"Fornecedor: {cotacao['fornecedor'] or '-'}   •   Criada em {cotacao['data_criacao']}   •   ",
                          style={'color': COR_MUTED, 'fontSize': '14px'}),
                dbc.Badge("Respondida" if respondida else "Aguardando fornecedor",
                          color="success" if respondida else "warning"),
            ], style={'marginTop': '4px'}),
        ], style={'padding': '18px 4px 8px 4px'}),

        dbc.Card([
            dbc.CardBody([
                dash_table.DataTable(
                    columns=[
                        {"name": "Grupo", "id": "grupo"},
                        {"name": "Item", "id": "item"},
                        {"name": "Volume", "id": "volume"},
                        {"name": "Qtd", "id": "qtd"},
                        {"name": "Preço unitário", "id": "preco_unitario"},
                        {"name": "Subtotal", "id": "subtotal"},
                    ],
                    data=linhas_tabela,
                    style_header={
                        'backgroundColor': COR_CARD_2, 'color': COR_MUTED, 'fontWeight': '600',
                        'textTransform': 'uppercase', 'fontSize': '12px', 'border': 'none',
                        'borderBottom': f'1px solid {COR_BORDA}',
                    },
                    style_cell={
                        'backgroundColor': COR_CARD, 'color': COR_TEXTO, 'textAlign': 'left',
                        'padding': '10px', 'border': 'none', 'borderBottom': f'1px solid {COR_BORDA}',
                        'fontFamily': 'Inter, sans-serif',
                    },
                    style_as_list_view=True,
                ),

                html.Div([
                    html.Span("TOTAL GERAL: ", style={'color': COR_MUTED, 'fontSize': '14px', 'fontWeight': '600'}),
                    html.Span(f"R$ {total_geral:,.2f}" if respondida else "aguardando o fornecedor preencher todos os itens",
                              style={'color': COR_ACCENT, 'fontSize': '20px', 'fontWeight': '700'}),
                ], style={'marginTop': '18px', 'textAlign': 'right'}),
            ])
        ], className="card-cotacao"),

    ], style={
        'paddingLeft': '80px', 'paddingRight': '80px', 'paddingBottom': '60px', 'minHeight': '100vh',
    }, fluid=True)


# ============================================================
# LAYOUT RAIZ + ROTEAMENTO
# ============================================================
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='conteudo-pagina')
])


@callback(
    Output('conteudo-pagina', 'children'),
    Input('url', 'pathname'),
)
def rotear_pagina(pathname):
    """
    Se a URL for /responder/<token>, mostra a tela pública do fornecedor.
    Se for /resultado/<id>, mostra o resultado (visão interna).
    Qualquer outra URL mostra a tela interna de montagem da cotação.
    """
    if pathname and pathname.startswith('/responder/'):
        token = pathname.replace('/responder/', '').strip('/')
        return layout_responder_fornecedor(token)
    if pathname and pathname.startswith('/resultado/'):
        cotacao_id = pathname.replace('/resultado/', '').strip('/')
        return layout_resultado_cotacao(cotacao_id)
    return layout_cotacao_interna()


# ============================================================
# CALLBACK: TELA INTERNA -- montar itens da cotação
# (mesma lógica original + resumo em badges)
# ============================================================
@callback(
    Output('produtos', 'options'),
    Output('produtos', 'value'),
    Output('input-volume', 'value'),
    Output('input-qtd', 'value'),
    Output('lista-store', 'data'),
    Output('tabela-lista', 'data'),
    Output('badge-total-itens', 'children'),
    Output('badge-total-qtd', 'children'),
    Input('grupo', 'value'),
    Input('Btn-salvar', 'n_clicks'),
    Input('Btn-remover', 'n_clicks'),
    State('tab-pn', 'value'),
    State('grupo', 'value'),
    State('produtos', 'value'),
    State('input-volume', 'value'),
    State('input-qtd', 'value'),
    State('lista-store', 'data'),
    State('tabela-lista', 'selected_rows'),
    prevent_initial_call=True
)
def gerenciar(grupo_selecionado, salvar, remover, fornecedor_sel, grupo_sel, produto_sel,
              volume, qtd, lista_atual, linhas_selecionadas):

    def resumo(lista):
        total_itens = len(lista)
        total_qtd = sum(item['qtd'] for item in lista if isinstance(item['qtd'], (int, float)))
        return f"{total_itens} item(ns)", f"{total_qtd} un."

    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

    botao_acionado = ctx.triggered[0]['prop_id'].split('.')[0]

    if botao_acionado == 'grupo':
        if grupo_selecionado is None:
            options_produto = [{'label': i, 'value': i} for i in todos_produtos]
        else:
            produtos_filtrados = produtos[produtos['Nome do grupo'] == grupo_selecionado]['Descrição do item'].dropna().unique()
            options_produto = [{'label': i, 'value': i} for i in produtos_filtrados]
        itens_txt, qtd_txt = resumo(lista_atual)
        return options_produto, None, no_update, no_update, lista_atual, lista_atual, itens_txt, qtd_txt

    if botao_acionado == 'Btn-salvar':
        if produto_sel is None:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

        novo_item = {
            "fornecedor": fornecedor_sel if fornecedor_sel else "-",
            "grupo": grupo_sel if grupo_sel else "-",
            "item": produto_sel,
            "volume": volume if volume else "-",
            "qtd": qtd if qtd else 0
        }
        lista_atual.append(novo_item)
        itens_txt, qtd_txt = resumo(lista_atual)
        return no_update, None, None, None, lista_atual, lista_atual, itens_txt, qtd_txt

    if botao_acionado == 'Btn-remover':
        if not linhas_selecionadas:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        lista_atual.pop(linhas_selecionadas[0])
        itens_txt, qtd_txt = resumo(lista_atual)
        return no_update, no_update, no_update, no_update, lista_atual, lista_atual, itens_txt, qtd_txt

    return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update


# ============================================================
# CALLBACK: FINALIZAR COTAÇÃO -> salva no SQLite e gera o link
# ============================================================
@callback(
    Output('resultado-link', 'children'),
    Output('lista-store', 'data', allow_duplicate=True),
    Output('tabela-lista', 'data', allow_duplicate=True),
    Input('Btn-finalizar', 'n_clicks'),
    State('tab-pn', 'value'),
    State('lista-store', 'data'),
    prevent_initial_call=True
)
def finalizar_cotacao(n_clicks, fornecedor_sel, lista_atual):
    if not lista_atual:
        return dbc.Alert("Adicione ao menos um item antes de finalizar.", color="warning",
                          style={'marginTop': '10px'}), no_update, no_update

    cotacao_id, token = bd.criar_cotacao(fornecedor_sel, lista_atual)

    # Monta o link a partir do host que está servindo a página agora
    # (funciona tanto em localhost quanto no host configurado em produção)
    base_url = request.host_url.rstrip('/')
    link = f"{base_url}/responder/{token}"

    resultado = html.Div([
        html.Div([
            html.I(className="bi bi-check-circle-fill me-2", style={'color': COR_SUCESSO}),
            html.Span(f"Cotação nº {cotacao_id} salva com sucesso.", style={'color': COR_TEXTO, 'fontWeight': '600'})
        ], style={'marginBottom': '10px'}),
        html.Div("Link para enviar ao fornecedor:", style={'color': COR_MUTED, 'fontSize': '13px', 'marginBottom': '6px'}),
        dbc.Row([
            dbc.Col(html.Div(link, className="caixa-link"), width=9),
            dbc.Col(dcc.Clipboard(target_id=None, content=link,
                                   style={'fontSize': '22px', 'color': COR_ACCENT_2, 'cursor': 'pointer'}), width=1,
                    className="d-flex align-items-center justify-content-center"),
        ], align='center', className="g-2"),
    ])

    # Limpa a lista/tabela para começar uma próxima cotação do zero
    return resultado, [], []


# ============================================================
# CALLBACK: CLICOU EM UMA LINHA DA TABELA DE COTAÇÕES -> NAVEGA PARA /resultado/<id>
# ============================================================
@callback(
    Output('url', 'pathname'),
    Input('tabela-cotacoes', 'active_cell'),
    State('tabela-cotacoes', 'data'),
    prevent_initial_call=True
)
def ir_para_resultado(celula_ativa, linhas):
    if not celula_ativa or not linhas:
        return no_update
    if celula_ativa.get('column_id') == 'link':
        return no_update  # deixa selecionar/copiar o texto do link em vez de navegar
    linha = linhas[celula_ativa['row']]
    return f"/resultado/{linha['id']}"


# ============================================================
# CALLBACK: ATUALIZAR A LISTA DE COTAÇÕES CRIADAS
# Roda ao carregar a tela principal e de novo logo após finalizar uma cotação.
# ============================================================
@callback(
    Output('lista-cotacoes-criadas', 'children'),
    Input('url', 'pathname'),
    Input('Btn-finalizar', 'n_clicks'),
    Input('filtro-busca', 'value'),
    Input('filtro-status', 'value'),
    Input('filtro-data-inicio', 'date'),
    Input('filtro-data-fim', 'date'),
    prevent_initial_call=False
)
def atualizar_lista_cotacoes(pathname, n_clicks, busca, status, data_inicio, data_fim):
    # Só monta a lista quando estamos na tela principal (onde o container existe)
    if pathname not in (None, '', '/'):
        return no_update
    return montar_tabela_cotacoes(busca, status, data_inicio, data_fim)


# ============================================================
# CALLBACK: FORNECEDOR ENVIA OS PREÇOS
# ============================================================
@callback(
    Output('mensagem-envio', 'children'),
    Output('Btn-enviar-precos', 'disabled'),
    Input('Btn-enviar-precos', 'n_clicks'),
    State({'type': 'preco-input', 'index': ALL}, 'value'),
    State({'type': 'preco-input', 'index': ALL}, 'id'),
    State('token-cotacao', 'data'),
    prevent_initial_call=True
)
def enviar_precos(n_clicks, valores, ids, token):
    # Cada dcc.Input tem seu próprio id ({'type': 'preco-input', 'index': <id do item>}),
    # então dá pra casar valor <-> item diretamente pela ordem que vieram (ids e
    # valores sempre chegam na mesma ordem um do outro).
    precos = []
    invalidos = 0
    for id_componente, valor in zip(ids, valores):
        preco = parse_preco(valor)
        if preco is None:
            invalidos += 1
        precos.append({'id': id_componente['index'], 'preco_unitario': preco})

    if invalidos:
        return dbc.Alert(
            "Preencha o preço de todos os itens com um número válido (ex: 12,50) antes de enviar.",
            color="warning"
        ), False

    bd.salvar_precos(token, precos)

    return dbc.Alert("Preços enviados com sucesso. Obrigado!", color="success"), True


if __name__ == '__main__':
    # Localmente roda na porta 8050; no Render, a plataforma injeta a
    # variável de ambiente PORT automaticamente -- por isso lemos com getenv.
    # host='0.0.0.0' é necessário pro Render conseguir enxergar o servidor
    # (diferente do 'alterdatasrv' usado antes, que só existia na rede interna).
    porta = int(os.environ.get("PORT", 8050))
    app.run(host='0.0.0.0', port=porta, debug=False)

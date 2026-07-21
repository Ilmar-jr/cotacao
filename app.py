import os
from dash import html, dcc, dash_table, Output, Input, State, callback, Dash, callback_context, no_update, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from flask import request
from werkzeug.middleware.proxy_fix import ProxyFix

import banco as bd

# Executa a criação das tabelas se elas não existirem no Postgres/Supabase
bd.criar_banco()

# ============================================================
# TEMA VISUAL
# ============================================================
FONTS_URL = "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght=500;600;700&family=Inter:wght@400;500;600&display=swap"

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP, FONTS_URL],
    suppress_callback_exceptions=True,
)
server = app.server

# Necessário para o Render gerenciar HTTPS e Proxy
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

SENHA_INTERNA = os.environ.get("SENHA_INTERNA", "admin123")

INDEX_STRING = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body { background-color: ''' + COR_BG + ''' !important; font-family: 'Inter', sans-serif; }
            .titulo-cotacao { font-family: 'Space Grotesk', sans-serif; letter-spacing: 0.5px; }
            .card-cotacao { background-color: ''' + COR_CARD + '''; border: 1px solid ''' + COR_BORDA + '''; border-radius: 10px; }
            .rotulo-campo { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.6px; color: ''' + COR_MUTED + '''; margin-bottom: 6px; }
            .faixa-ticket { border-top: 2px dashed ''' + COR_BORDA + '''; border-bottom: 2px dashed ''' + COR_BORDA + '''; padding: 10px 0; font-family: 'Space Grotesk', sans-serif; color: ''' + COR_ACCENT + '''; letter-spacing: 1px; }
            .badge-resumo { background-color: ''' + COR_CARD_2 + ''' !important; color: ''' + COR_TEXTO + ''' !important; border: 1px solid ''' + COR_BORDA + '''; font-family: 'Space Grotesk', sans-serif; font-size: 14px; padding: 8px 14px; }
            .Select-control, .dropdown, div[class*="-control"] { background-color: ''' + COR_CARD_2 + ''' !important; border-color: ''' + COR_BORDA + ''' !important; color: ''' + COR_TEXTO + ''' !important; }
            input { background-color: ''' + COR_CARD_2 + ''' !important; color: ''' + COR_TEXTO + ''' !important; border-color: ''' + COR_BORDA + ''' !important; }
            .caixa-link { background-color: ''' + COR_CARD_2 + '''; border: 1px solid ''' + COR_ACCENT_2 + '''; border-radius: 8px; padding: 14px 16px; color: ''' + COR_TEXTO + '''; font-family: monospace; font-size: 14px; word-break: break-all; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>
'''
app.index_string = INDEX_STRING

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
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("R$", "").strip()
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None

# ============================================================
# LAYOUT: TELA DE LOGIN INTERNO
# ============================================================
def layout_login():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="bi bi-lock-fill me-2", style={'color': COR_ACCENT, 'fontSize': '32px'}),
                    html.Span("ACESSO RESTRITO", className="titulo-cotacao", style={'fontSize': '24px', 'fontWeight': '700', 'color': COR_TEXTO})
                ], className="text-center mb-4"),
                dbc.Card([
                    dbc.CardBody([
                        html.Div("Senha de Acesso Interno", className="rotulo-campo"),
                        dcc.Input(id='input-senha', type='password', placeholder='Digite a senha...', style={'width': '100%', 'height': '40px', 'borderRadius': '6px', 'marginBottom': '15px'}),
                        dbc.Button("Entrar no Sistema", id='btn-login', n_clicks=0, style={'backgroundColor': COR_ACCENT_2, 'border': 'none', 'width': '100%', 'fontWeight': '600'}),
                        html.Div(id='login-feedback', style={'marginTop': '15px'})
                    ])
                ], className="card-cotacao")
            ], width=4)
        ], justify="center", align="center", style={'minHeight': '80vh'})
    ], fluid=True)

# ============================================================
# LAYOUT 1: TELA INTERNA -- PAINEL COMPLETO
# ============================================================
def layout_cotacao_interna():
    fornecedores_opts = [{'label': 'Todos os Fornecedores', 'value': 'todos'}] + [{'label': f, 'value': f} for f in fn]
    produtos_opts = [{'label': 'Todos os Produtos', 'value': 'todos'}] + [{'label': p, 'value': p} for p in todos_produtos]

    return dbc.Container([
        html.Div([
            html.Div([
                html.I(className="bi bi-diagram-3-fill me-2", style={'color': COR_ACCENT_2}),
                html.Span("SISTEMA DE COTAÇÃO ONLINE B2B", className="titulo-cotacao", style={'fontSize': '28px', 'fontWeight': '700', 'color': COR_TEXTO}),
            ]),
            html.Div("Painel Operacional e Gestão Estratégica de Negociações", style={'color': COR_MUTED, 'fontSize': '14px', 'marginTop': '4px'}),
        ], style={'padding': '18px 4px 18px 4px'}),

        dbc.Tabs([
            # ABA 1: OPERACIONAL
            dbc.Tab(label="📋 Gerenciar & Criar Cotações", tab_id="tab-operacional", children=[
                html.Div([
                    dcc.Store(id='lista-store', data=[]),
                    
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                campo("Fornecedor", dcc.Dropdown(id='tab-pn', options=[{'label': f, 'value': f} for f in fn], placeholder="Selecione o fornecedor...", style={'color': '#000'}), 12)
                            ])
                        ])
                    ], className="card-cotacao mb-3"),

                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                campo("Grupo", dcc.Dropdown(id='grupo', options=[{'label': g, 'value': g} for g in grupo], placeholder="Selecione...", style={'color': '#000'}), 2),
                                campo("Produto", dcc.Dropdown(id='produtos', placeholder="Selecione o produto...", style={'color': '#000'}), 3),
                                campo("Marca Aceita", dcc.Input(id='input-marca', type='text', placeholder="Ex: Piracanjuba, Nestlé...", style={'width': '100%', 'height': '38px', 'borderRadius': '6px'}), 3),
                                campo("Unidade", dcc.Input(id='input-volume', type='text', placeholder="Ex: CX, KG", style={'width': '100%', 'height': '38px', 'borderRadius': '6px'}), 2),
                                campo("Qtd", dcc.Input(id='input-qtd', type='number', placeholder="0", style={'width': '100%', 'height': '38px', 'borderRadius': '6px'}), 1),
                                dbc.Col(dbc.Button([html.I(className="bi bi-plus-circle me-2"), "Add"], id='Btn-salvar', n_clicks=0, style={'backgroundColor': COR_ACCENT_2, 'border': 'none', 'marginTop': '24px', 'width': '100%'}), width=1)
                            ], className="g-2")
                        ])
                    ], className="card-cotacao mb-3"),

                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col(html.Span(id='badge-total-itens', className="badge badge-resumo me-2"), width='auto'),
                                dbc.Col(html.Span(id='badge-total-qtd', className="badge badge-resumo"), width='auto'),
                                dbc.Col(dbc.Button([html.I(className="bi bi-trash me-2"), "Remover Selecionado"], id='Btn-remover', n_clicks=0, size="sm", color="danger", outline=True, className="ms-auto"), width='auto')
                            ], className="mb-3 d-flex align-items-center"),
                            
                            dash_table.DataTable(
                                id='tabela-lista', 
                                row_selectable='single',
                                style_header={'backgroundColor': COR_CARD_2, 'color': COR_MUTED, 'fontWeight': '600'},
                                style_cell={'backgroundColor': COR_CARD, 'color': COR_TEXTO, 'textAlign': 'left'}
                            )
                        ])
                    ], className="card-cotacao mb-4"),

                    dbc.Card([
                        dbc.CardBody([
                            html.Div("Envio da Cotação", style={'color': COR_TEXTO, 'fontWeight': '600', 'marginBottom': '12px'}),
                            dbc.Button([html.I(className="bi bi-send-check me-2"), "Finalizar Cotação e Gerar Link"], id='Btn-finalizar', n_clicks=0, style={'backgroundColor': COR_ACCENT, 'border': 'none', 'color': '#12161c', 'fontWeight': '700'}),
                        ])
                    ], className="card-cotacao mb-4"),

                    html.Div(id='resultado-link'),
                    
                    html.Div([dbc.Row([dbc.Col(html.Span("COTAÇÕES CRIADAS"), width='auto')])], className="faixa-ticket", style={'marginTop': '28px', 'marginBottom': '14px'}),
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                campo("Buscar", dcc.Input(id='filtro-busca', type="text", placeholder="Nº da cotação ou fornecedor..", style={'width': '100%', 'height': '38px', 'borderRadius': '6px'}), 4),
                                campo("Status", dcc.Dropdown(id='filtro-status', options=[{'label': 'Todas', 'value': 'todas'}, {'label': 'Aguardando fornecedor', 'value': 'aguardando'}, {'label': 'Respondida', 'value': 'respondida'}], value='todas', clearable=False, style={'color': '#000'}), 3),
                                campo("Criada de", dcc.DatePickerSingle(id='filtro-data-inicio', display_format='DD/MM/YYYY', placeholder="Data inicial"), 2),
                                campo("até", dcc.DatePickerSingle(id='filtro-data-fim', display_format='DD/MM/YYYY', placeholder="Data final"), 2),
                            ], className="g-3 mb-3"),
                            html.Div(id='lista-cotacoes-criadas'),
                        ])
                    ], className="card-cotacao"),
                ], style={'paddingTop': '20px'})
            ]),

            # ABA 2: RELATÓRIOS E BI
            dbc.Tab(label="📊 Relatório & Análise de Negociação", tab_id="tab-relatorio", children=[
                html.Div([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                campo("Data Inicial", dcc.DatePickerSingle(id='rel-data-inicio', display_format='DD/MM/YYYY', placeholder="Inicio"), 3),
                                campo("Data Final", dcc.DatePickerSingle(id='rel-data-fim', display_format='DD/MM/YYYY', placeholder="Fim"), 3),
                                campo("Fornecedor / Cliente", dcc.Dropdown(id='rel-fornecedor', options=fornecedores_opts, value='todos', clearable=False, style={'color': '#000'}), 3),
                                campo("Produto", dcc.Dropdown(id='rel-produto', options=produtos_opts, value='todos', clearable=False, style={'color': '#000'}), 3),
                            ], className="g-3")
                        ])
                    ], className="card-cotacao mb-4"),

                    dbc.Row([
                        dbc.Col(dbc.Card([dbc.CardBody([
                            html.Div("Total de Cotações Analisadas", style={'color': COR_MUTED, 'fontSize': '12px'}),
                            html.H3(id="kpi-total-cotacoes", style={'color': COR_TEXTO, 'fontWeight': '700'})
                        ])], className="card-cotacao"), width=3),
                        
                        dbc.Col(dbc.Card([dbc.CardBody([
                            html.Div("Investimento Inicial (1ª Rodada)", style={'color': COR_MUTED, 'fontSize': '12px'}),
                            html.H3(id="kpi-valor-inicial", style={'color': COR_TEXTO, 'fontWeight': '700'})
                        ])], className="card-cotacao"), width=3),

                        dbc.Col(dbc.Card([dbc.CardBody([
                            html.Div("Investimento Final (Última Rodada)", style={'color': COR_MUTED, 'fontSize': '12px'}),
                            html.H3(id="kpi-valor-final", style={'color': COR_TEXTO, 'fontWeight': '700'})
                        ])], className="card-cotacao"), width=3),

                        dbc.Col(dbc.Card([dbc.CardBody([
                            html.Div("Resultado da Negociação", style={'color': COR_MUTED, 'fontSize': '12px'}),
                            html.H3(id="kpi-resultado-financeiro", style={'fontWeight': '700'})
                        ])], className="card-cotacao"), width=3),
                    ], className="mb-4"),

                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardBody([
                                html.Div("Evolução do Valor Total por Rodada de Negociação", style={'color': COR_TEXTO, 'fontWeight': '600', 'marginBottom': '12px'}),
                                dcc.Graph(id='grafico-evolucao-rodadas', config={'displayModeBar': False})
                            ])
                        ], className="card-cotacao"), width=7),

                        dbc.Col(dbc.Card([
                            dbc.CardBody([
                                html.Div("Economia Gerada por Fornecedor (R$)", style={'color': COR_TEXTO, 'fontWeight': '600', 'marginBottom': '12px'}),
                                dcc.Graph(id='grafico-economia-fornecedor', config={'displayModeBar': False})
                            ])
                        ], className="card-cotacao"), width=5),
                    ], className="mb-4"),

                    dbc.Card([
                        dbc.CardBody([
                            html.Div("Histórico Detalhado dos Itens Negociados", style={'color': COR_TEXTO, 'fontWeight': '600', 'marginBottom': '12px'}),
                            html.Div(id='tabela-relatorio-detalhada')
                        ])
                    ], className="card-cotacao")
                ], style={'paddingTop': '20px'})
            ])
        ], id="tabs-painel", active_tab="tab-operacional")
    ], style={'paddingLeft': '80px', 'paddingRight': '80px', 'paddingBottom': '60px', 'minHeight': '100vh'}, fluid=True)

# ============================================================
# FUNÇÃO RESTAURADA: MONTAR TABELA DE COTAÇÕES
# ============================================================
def montar_tabela_cotacoes(busca=None, status=None, data_inicio=None, data_fim=None):
    cotacoes = bd.listar_cotacoes()
    if busca:
        busca_lower = busca.strip().lower()
        cotacoes = [c for c in cotacoes if busca_lower in str(c['id']) or busca_lower in (c['fornecedor'] or "").lower()]
    if status and status != 'todas':
        cotacoes = [c for c in cotacoes if c['status'] == status]
    if data_inicio:
        cotacoes = [c for c in cotacoes if str(c['data_criacao'])[:10] >= data_inicio[:10]]
    if data_fim:
        cotacoes = [c for c in cotacoes if str(c['data_criacao'])[:10] <= data_fim[:10]]

    if not cotacoes:
        return html.Div("Nenhuma cotação encontrada com esse filtro.", style={'color': COR_MUTED, 'fontSize': '13px'})

    base_url = request.host_url.rstrip('/')
    linhas = [
        {
            "id": c['id'],
            "cotacao": f"#{c['id']}",
            "fornecedor": c['fornecedor'] or "-",
            "data_criacao": str(c['data_criacao'])[:16],
            "status": "Respondida" if c['status'] == 'respondida' else "Aguardando fornecedor",
            "link": f"{base_url}/responder/{c['token']}",
        } for c in cotacoes
    ]

    return html.Div([
        html.Div("Clique em uma linha para ver o resultado.", style={'color': COR_MUTED, 'fontSize': '13px', 'marginBottom': '10px'}),
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
            style_header={'backgroundColor': COR_CARD_2, 'color': COR_MUTED, 'fontWeight': '600', 'textTransform': 'uppercase', 'fontSize': '12px', 'border': 'none', 'borderBottom': f'1px solid {COR_BORDA}'},
            style_cell={'backgroundColor': COR_CARD, 'color': COR_TEXTO, 'textAlign': 'left', 'padding': '10px', 'border': 'none', 'borderBottom': f'1px solid {COR_BORDA}', 'fontFamily': 'Inter, sans-serif', 'cursor': 'pointer'},
            style_cell_conditional=[{'if': {'column_id': 'link'}, 'fontFamily': 'monospace', 'fontSize': '12px', 'color': COR_ACCENT_2, 'cursor': 'text'}],
            style_as_list_view=True,
        )
    ])

# ============================================================
# LAYOUT 2: TELA PÚBLICA FORNECEDOR
# ============================================================
def layout_responder_fornecedor(token):
    cotacao = bd.buscar_cotacao_para_responder(token)
    if cotacao is None:
        return dbc.Container([html.Div([html.I(className="bi bi-exclamation-triangle me-2", style={'color': COR_PERIGO}), html.Span("Link inválido ou cotação não encontrada.", style={'color': COR_TEXTO, 'fontSize': '18px'})], style={'marginTop': '60px'})], style={'paddingLeft': '80px', 'paddingRight': '80px'}, fluid=True)

    rodada = cotacao['rodada_atual']
    ja_respondida = cotacao['status'] == 'respondida'
    
    # Ajuste nas larguras das colunas para caber a marca
    cabecalho = dbc.Row([
        dbc.Col("Grupo", width=2), 
        dbc.Col("Item", width=3), 
        dbc.Col("Marcas Aceitas", width=2), 
        dbc.Col("Unid", width=1), 
        dbc.Col("Qtd", width=1), 
        dbc.Col(f"Preço Unitário ({rodada}ª Rodada)", width=3)
    ], className="py-2", style={'color': COR_MUTED, 'fontWeight': '600', 'textTransform': 'uppercase', 'fontSize': '12px', 'borderBottom': f'1px solid {COR_BORDA}'})

    linhas = []
    for item in cotacao['itens']:
        if ja_respondida:
            campo_preco = html.Div(f"R$ {parse_preco(item['preco_unitario']):,.2f}" if item['preco_unitario'] is not None else "-", style={'color': COR_TEXTO})
        else:
            campo_preco = dcc.Input(id={'type': 'preco-input', 'index': item['id']}, type="text", placeholder="Ex: 12,50", value=(str(item['preco_unitario']) if item['preco_unitario'] is not None else None), style={'width': '100%', 'height': '36px', 'borderRadius': '6px'})
        
        linhas.append(dbc.Row([
            dbc.Col(item['grupo'] or "-", width=2, style={'color': COR_TEXTO}), 
            dbc.Col(item['item'], width=3, style={'color': COR_TEXTO}), 
            dbc.Col(item.get('marca', '-'), width=2, style={'color': COR_ACCENT_2, 'fontSize': '13px'}), 
            dbc.Col(item['volume'] or "-", width=1, style={'color': COR_TEXTO}), 
            dbc.Col(item['qtd'], width=1, style={'color': COR_TEXTO}), 
            dbc.Col(campo_preco, width=3)
        ], className="py-2 align-items-center", style={'borderBottom': f'1px solid {COR_BORDA}'}))

    return dbc.Container([
        html.Div([
            html.Div([html.I(className="bi bi-send-check-fill me-2", style={'color': COR_ACCENT_2}), html.Span(f"NEGOCIAÇÃO ONLINE - {rodada}ª RODADA", className="titulo-cotacao", style={'fontSize': '26px', 'fontWeight': '700', 'color': COR_TEXTO})]),
            html.Div(f"Fornecedor: {cotacao['fornecedor'] or '-'}   •   Cotação nº {cotacao['id']}", style={'color': COR_MUTED, 'fontSize': '14px', 'marginTop': '4px'}),
        ], style={'padding': '18px 4px 8px 4px'}),
        dcc.Store(id='token-cotacao', data=token),
        dcc.Store(id='rodada-atual-fornecedor', data=rodada),
        dbc.Card([
            dbc.CardBody([
                html.Div("Observe as marcas aceitas antes de inserir os preços para esta fase da negociação e clicar em Enviar." if not ja_respondida else f"Os preços da {rodada}ª rodada já foram enviados e estão em análise.", style={'color': COR_MUTED, 'fontSize': '13px', 'marginBottom': '14px'}),
                cabecalho, html.Div(linhas),
                html.Div([
                    dbc.Button([html.I(className="bi bi-check2-circle me-2"), "Enviar preços da Rodada"], id='Btn-enviar-precos', n_clicks=0, style={'backgroundColor': COR_ACCENT, 'border': 'none', 'color': '#12161c', 'fontWeight': '700', 'marginTop': '18px'}, disabled=ja_respondida),
                    html.Div(id='mensagem-envio', style={'marginTop': '14px'}),
                ]),
            ])
        ], className="card-cotacao"),
    ], style={'paddingLeft': '80px', 'paddingRight': '80px', 'paddingBottom': '60px', 'minHeight': '100vh'}, fluid=True)

# ============================================================
# LAYOUT 3: HISTÓRICO DE RODADAS
# ============================================================
def layout_resultado_cotacao(cotacao_id):
    try:
        cotacao_completa = bd.buscar_todas_rodadas_id(int(cotacao_id))
    except (TypeError, ValueError):
        cotacao_completa = None

    if cotacao_completa is None:
        return dbc.Container([html.Div([html.I(className="bi bi-exclamation-triangle me-2", style={'color': COR_PERIGO}), html.Span("Cotação não encontrada.", style={'color': COR_TEXTO, 'fontSize': '18px'})], style={'marginTop': '60px', 'marginBottom': '20px'}), dcc.Link("← Voltar", href="/", style={'color': COR_ACCENT_2})], style={'paddingLeft': '80px', 'paddingRight': '80px'}, fluid=True)

    respondida = cotacao_completa['status'] == 'respondida'
    linhas_tabela = []
    rodadas_disponiveis = set()
    
    for item in cotacao_completa['itens']:
        preco = parse_preco(item['preco_unitario'])
        qtd = item['qtd'] or 0
        subtotal = (preco * qtd) if preco is not None else 0
        rodadas_disponiveis.add(item['rodada'])
        
        linhas_tabela.append({
            "rodada": f"{item['rodada']}ª Rodada",
            "grupo": item['grupo'] or "-",
            "item": item['item'],
            "marca": item.get('marca', '-'),
            "volume": item['volume'] or "-",
            "qtd": qtd,
            "preco_unitario": f"R$ {preco:,.2f}" if preco is not None else "Aguardando",
            "subtotal": f"R$ {subtotal:,.2f}" if preco is not None else "-"
        })

    opcoes_rodadas = [{'label': f'{r}ª Rodada', 'value': r} for r in sorted(rodadas_disponiveis)]

    return dbc.Container([
        dcc.Download(id="download-excel"),

        html.Div([
            dcc.Link("← Voltar para a tela principal", href="/", style={'color': COR_MUTED, 'fontSize': '13px'}),
            html.Div([html.I(className="bi bi-bar-chart-line-fill me-2", style={'color': COR_ACCENT_2}), html.Span(f"HISTÓRICO DE NEGOCIAÇÃO - COTAÇÃO Nº {cotacao_completa['id']}", className="titulo-cotacao", style={'fontSize': '26px', 'fontWeight': '700', 'color': COR_TEXTO})], style={'marginTop': '10px'}),
            html.Div([html.Span(f"Fornecedor: {cotacao_completa['fornecedor'] or '-'}   •   Criada em {str(cotacao_completa['data_criacao'])[:16]}   •   ", style={'color': COR_MUTED, 'fontSize': '14px'}), dbc.Badge(cotacao_completa['status'].upper(), color="success" if respondida else "warning")], style={'marginTop': '4px'}),
        ], style={'padding': '18px 4px 8px 4px'}),
        
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Div("Negociar valores:", style={'color': COR_TEXTO, 'fontSize': '14px', 'marginBottom': '10px', 'fontWeight': '600'}),
                        dbc.Button([html.I(className="bi bi-arrow-repeat me-2"), "Reabrir Cotação (Solicitar Nova Rodada de Preços)"], id='btn-nova-rodada', n_clicks=0, style={'backgroundColor': COR_ACCENT, 'border': 'none', 'color': '#12161c', 'fontWeight': '700', 'width': '100%'}, size="sm"),
                        html.Div(id='feedback-nova-rodada', style={'marginTop': '10px'})
                    ], width=6, style={'borderRight': f'1px solid {COR_BORDA}'}),
                    
                    dbc.Col([
                        html.Div("Exportar para Excel:", style={'color': COR_TEXTO, 'fontSize': '14px', 'marginBottom': '10px', 'fontWeight': '600'}),
                        dbc.Row([
                            dbc.Col(dcc.Dropdown(id='dropdown-rodada-excel', options=opcoes_rodadas, placeholder="Escolha a rodada...", style={'color': '#000'}), width=7),
                            dbc.Col(dbc.Button([html.I(className="bi bi-file-earmark-excel me-2"), "Baixar"], id='btn-baixar-excel', n_clicks=0, style={'backgroundColor': COR_SUCESSO, 'border': 'none', 'fontWeight': '700', 'width': '100%'}, size="sm"), width=5)
                        ]),
                        html.Div(id='feedback-excel', style={'marginTop': '10px'})
                    ], width=6, className="ps-4")
                ])
            ])
        ], className="card-cotacao mb-4", style={'border': f'1px solid {COR_BORDA}'}),

        dbc.Card([
            dbc.CardBody([
                html.Div("Histórico evolutivo de preços (As rodadas mais recentes aparecem no topo):", style={'color': COR_MUTED, 'fontSize': '13px', 'marginBottom': '14px'}),
                dash_table.DataTable(
                    columns=[
                        {"name": "Fase / Rodada", "id": "rodada"},
                        {"name": "Grupo", "id": "grupo"},
                        {"name": "Item / Produto", "id": "item"},
                        {"name": "Marca", "id": "marca"},
                        {"name": "Unid", "id": "volume"},
                        {"name": "Qtd", "id": "qtd"},
                        {"name": "Preço Ofertado", "id": "preco_unitario"},
                        {"name": "Subtotal da Rodada", "id": "subtotal"},
                    ],
                    data=linhas_tabela,
                    style_header={'backgroundColor': COR_CARD_2, 'color': COR_MUTED, 'fontWeight': '600', 'textTransform': 'uppercase', 'fontSize': '12px', 'border': 'none', 'borderBottom': f'1px solid {COR_BORDA}'},
                    style_cell={'backgroundColor': COR_CARD, 'color': COR_TEXTO, 'textAlign': 'left', 'padding': '10px', 'border': 'none', 'borderBottom': f'1px solid {COR_BORDA}', 'fontFamily': 'Inter, sans-serif'},
                    style_data_conditional=[{'if': {'column_id': 'rodada'}, 'fontWeight': 'bold', 'color': COR_ACCENT_2}],
                    page_size=30,
                    style_as_list_view=True,
                ),
            ])
        ], className="card-cotacao"),
    ], style={'paddingLeft': '80px', 'paddingRight': '80px', 'paddingBottom': '60px', 'minHeight': '100vh'}, fluid=True)

# ============================================================
# CALLBACKS RELATÓRIO BI
# ============================================================
@callback(
    Output('kpi-total-cotacoes', 'children'),
    Output('kpi-valor-inicial', 'children'),
    Output('kpi-valor-final', 'children'),
    Output('kpi-resultado-financeiro', 'children'),
    Output('kpi-resultado-financeiro', 'style'),
    Output('grafico-evolucao-rodadas', 'figure'),
    Output('grafico-economia-fornecedor', 'figure'),
    Output('tabela-relatorio-detalhada', 'children'),
    Input('rel-data-inicio', 'date'),
    Input('rel-data-fim', 'date'),
    Input('rel-fornecedor', 'value'),
    Input('rel-produto', 'value'),
    prevent_initial_call=False
)
def atualizar_painel_relatorio(dt_inicio, dt_fim, fornecedor, produto):
    dados = bd.gerar_relatorio_negociacoes(dt_inicio, dt_fim, fornecedor, produto)

    if not dados:
        fig_vazia = go.Figure().update_layout(template="plotly_dark", paper_bgcolor=COR_CARD, plot_bgcolor=COR_CARD)
        msg_vazia = html.Div("Nenhum registro encontrado para os filtros selecionados.", style={'color': COR_MUTED, 'fontSize': '13px'})
        return "0", "R$ 0,00", "R$ 0,00", "R$ 0,00", {'color': COR_MUTED}, fig_vazia, fig_vazia, msg_vazia

    df = pd.DataFrame(dados)

    cotacoes_unicas = df['cotacao_id'].nunique()
    agrupado = df.groupby(['cotacao_id', 'rodada'])['total_item'].sum().reset_index()
    
    rodada_minima = agrupado.groupby('cotacao_id')['rodada'].min().reset_index()
    rodada_maxima = agrupado.groupby('cotacao_id')['rodada'].max().reset_index()

    val_inicial = sum([agrupado[(agrupado['cotacao_id'] == row['cotacao_id']) & (agrupado['rodada'] == row['rodada'])]['total_item'].values[0] for _, row in rodada_minima.iterrows()])
    val_final = sum([agrupado[(agrupado['cotacao_id'] == row['cotacao_id']) & (agrupado['rodada'] == row['rodada'])]['total_item'].values[0] for _, row in rodada_maxima.iterrows()])

    diferenca = val_inicial - val_final

    if diferenca > 0:
        texto_resultado = f"Economia: R$ {diferenca:,.2f}"
        estilo_resultado = {'color': COR_SUCESSO}
    elif diferenca < 0:
        texto_resultado = f"Prejuízo: R$ {abs(diferenca):,.2f}"
        estilo_resultado = {'color': COR_PERIGO}
    else:
        texto_resultado = "Sem alteração"
        estilo_resultado = {'color': COR_MUTED}

    df_evolucao = df.groupby(['rodada', 'cotacao_id'])['total_item'].sum().reset_index()
    df_evolucao['rodada_label'] = df_evolucao['rodada'].astype(str) + "ª Rodada"
    
    fig_evolucao = px.line(
        df_evolucao, 
        x='rodada_label', 
        y='total_item', 
        color='cotacao_id',
        markers=True,
        labels={'total_item': 'Valor Total (R$)', 'rodada_label': 'Fase de Negociação', 'cotacao_id': 'Cotação Nº'}
    )
    fig_evolucao.update_layout(template="plotly_dark", paper_bgcolor=COR_CARD, plot_bgcolor=COR_CARD, margin=dict(l=20, r=20, t=20, b=20))

    df_fornecedor = df.groupby(['fornecedor', 'rodada'])['total_item'].sum().reset_index()
    f_min = df_fornecedor.groupby('fornecedor')['rodada'].min().reset_index()
    f_max = df_fornecedor.groupby('fornecedor')['rodada'].max().reset_index()

    economia_forn = []
    for f in df_fornecedor['fornecedor'].unique():
        r_ini = f_min[f_min['fornecedor'] == f]['rodada'].values[0]
        r_fim = f_max[f_max['fornecedor'] == f]['rodada'].values[0]
        
        v_ini = df_fornecedor[(df_fornecedor['fornecedor'] == f) & (df_fornecedor['rodada'] == r_ini)]['total_item'].values[0]
        v_fim = df_fornecedor[(df_fornecedor['fornecedor'] == f) & (df_fornecedor['rodada'] == r_fim)]['total_item'].values[0]
        
        economia_forn.append({'fornecedor': f, 'economia': v_ini - v_fim})

    df_econ = pd.DataFrame(economia_forn)
    fig_economia = px.bar(
        df_econ, 
        x='fornecedor', 
        y='economia',
        color='economia',
        color_continuous_scale=['red', 'yellow', 'green'],
        labels={'economia': 'Economia (R$)', 'fornecedor': 'Fornecedor'}
    )
    fig_economia.update_layout(template="plotly_dark", paper_bgcolor=COR_CARD, plot_bgcolor=COR_CARD, margin=dict(l=20, r=20, t=20, b=20))

    df['data_criacao'] = df['data_criacao'].astype(str).str[:10]
    df['preco_unitario'] = df['preco_unitario'].apply(lambda x: f"R$ {x:,.2f}")
    df['total_item'] = df['total_item'].apply(lambda x: f"R$ {x:,.2f}")
    
    tabela = dash_table.DataTable(
        columns=[
            {"name": "Cotação Nº", "id": "cotacao_id"},
            {"name": "Data", "id": "data_criacao"},
            {"name": "Fornecedor", "id": "fornecedor"},
            {"name": "Rodada", "id": "rodada"},
            {"name": "Produto", "id": "produto"},
            {"name": "Qtd", "id": "qtd"},
            {"name": "Preço Unit.", "id": "preco_unitario"},
            {"name": "Subtotal", "id": "total_item"},
        ],
        data=df.to_dict('records'),
        style_header={'backgroundColor': COR_CARD_2, 'color': COR_MUTED, 'fontWeight': '600', 'borderBottom': f'1px solid {COR_BORDA}'},
        style_cell={'backgroundColor': COR_CARD, 'color': COR_TEXTO, 'textAlign': 'left', 'padding': '10px', 'border': 'none', 'borderBottom': f'1px solid {COR_BORDA}'},
        page_size=10,
        style_as_list_view=True
    )

    return (
        str(cotacoes_unicas),
        f"R$ {val_inicial:,.2f}",
        f"R$ {val_final:,.2f}",
        texto_resultado,
        estilo_resultado,
        fig_evolucao,
        fig_economia,
        tabela
    )

# ============================================================
# ROUTING E SEGURANÇA
# ============================================================
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='sessao-interna', storage_type='session', data=False),
    html.Div(id='conteudo-pagina')
])

@callback(
    Output('conteudo-pagina', 'children'),
    Input('url', 'pathname'),
    Input('sessao-interna', 'data')
)
def rotear_pagina(pathname, logado):
    if pathname and pathname.startswith('/responder/'):
        token = pathname.replace('/responder/', '').strip('/')
        return layout_responder_fornecedor(token)

    if not logado:
        return layout_login()

    if pathname and pathname.startswith('/resultado/'):
        cotacao_id = pathname.replace('/resultado/', '').strip('/')
        return layout_resultado_cotacao(cotacao_id)

    return layout_cotacao_interna()

# ============================================================
# CALLBACK: LOGIN
# ============================================================
@callback(
    Output('sessao-interna', 'data'),
    Output('login-feedback', 'children'),
    Input('btn-login', 'n_clicks'),
    State('input-senha', 'value'),
    prevent_initial_call=True
)
def realizar_login(n_clicks, senha_digitada):
    if senha_digitada == SENHA_INTERNA:
        return True, None
    return False, dbc.Alert("Senha incorreta. Tente novamente.", color="danger")

# ============================================================
# DEMAIS CALLBACKS
# ============================================================
@callback(
    Output('produtos', 'options'), Output('produtos', 'value'), Output('input-marca', 'value'), Output('input-volume', 'value'), Output('input-qtd', 'value'), Output('lista-store', 'data'), Output('tabela-lista', 'data'), Output('badge-total-itens', 'children'), Output('badge-total-qtd', 'children'),
    Input('grupo', 'value'), Input('Btn-salvar', 'n_clicks'), Input('Btn-remover', 'n_clicks'),
    State('tab-pn', 'value'), State('grupo', 'value'), State('produtos', 'value'), State('input-marca', 'value'), State('input-volume', 'value'), State('input-qtd', 'value'), State('lista-store', 'data'), State('tabela-lista', 'selected_rows'),
    prevent_initial_call=True
)
def gerenciar(grupo_selecionado, salvar, remover, fornecedor_sel, grupo_sel, produto_sel, marca, volume, qtd, lista_atual, linhas_selecionadas):
    def resumo(lista):
        total_itens = len(lista)
        total_qtd = sum(item['qtd'] for item in lista if isinstance(item['qtd'], (int, float)))
        return f"{total_itens} item(ns)", f"{total_qtd} un."

    ctx = callback_context
    if not ctx.triggered: return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    botao_acionado = ctx.triggered[0]['prop_id'].split('.')[0]

    if botao_acionado == 'grupo':
        if grupo_selecionado is None: options_produto = [{'label': i, 'value': i} for i in todos_produtos]
        else:
            produtos_filtrados = produtos[produtos['Nome do grupo'] == grupo_selecionado]['Descrição do item'].dropna().unique()
            options_produto = [{'label': i, 'value': i} for i in produtos_filtrados]
        itens_txt, qtd_txt = resumo(lista_atual)
        return options_produto, None, None, no_update, no_update, lista_atual, lista_atual, itens_txt, qtd_txt

    if botao_acionado == 'Btn-salvar':
        if produto_sel is None: return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        novo_item = {"fornecedor": fornecedor_sel if fornecedor_sel else "-", "grupo": grupo_sel if grupo_sel else "-", "item": produto_sel, "marca": marca if marca else "-", "volume": volume if volume else "-", "qtd": qtd if qtd else 0}
        lista_atual.append(novo_item)
        itens_txt, qtd_txt = resumo(lista_atual)
        return no_update, None, None, None, None, lista_atual, lista_atual, itens_txt, qtd_txt

    if botao_acionado == 'Btn-remover':
        if not linhas_selecionadas: return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        lista_atual.pop(linhas_selecionadas[0])
        itens_txt, qtd_txt = resumo(lista_atual)
        return no_update, no_update, no_update, no_update, no_update, lista_atual, lista_atual, itens_txt, qtd_txt
    return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

@callback(
    Output('resultado-link', 'children'), Output('lista-store', 'data', allow_duplicate=True), Output('tabela-lista', 'data', allow_duplicate=True),
    Input('Btn-finalizar', 'n_clicks'), State('tab-pn', 'value'), State('lista-store', 'data'),
    prevent_initial_call=True
)
def finalizar_cotacao(n_clicks, fornecedor_sel, lista_atual):
    if not lista_atual: return dbc.Alert("Adicione ao menos um item antes de finalizar.", color="warning", style={'marginTop': '10px'}), no_update, no_update
    cotacao_id, token = bd.criar_cotacao(fornecedor_sel, lista_atual)
    base_url = request.host_url.rstrip('/')
    link = f"{base_url}/responder/{token}"
    resultado = html.Div([
        html.Div([html.I(className="bi bi-check-circle-fill me-2", style={'color': COR_SUCESSO}), html.Span(f"Cotação nº {cotacao_id} salva com sucesso.", style={'color': COR_TEXTO, 'fontWeight': '600'})], style={'marginBottom': '10px'}),
        html.Div("Link para enviar ao fornecedor:", style={'color': COR_MUTED, 'fontSize': '13px', 'marginBottom': '6px'}),
        dbc.Row([
            dbc.Col(html.Div(link, className="caixa-link"), width=9),
            dbc.Col(dcc.Clipboard(target_id=None, content=link, style={'fontSize': '22px', 'color': COR_ACCENT_2, 'cursor': 'pointer'}), width=1, className="d-flex align-items-center justify-content-center"),
        ], align='center', className="g-2"),
    ])
    return resultado, [], []

@callback(Output('url', 'pathname'), Input('tabela-cotacoes', 'active_cell'), State('tabela-cotacoes', 'data'), prevent_initial_call=True)
def ir_para_resultado(celula_ativa, linhas):
    if not celula_ativa or not linhas: return no_update
    if celula_ativa.get('column_id') == 'link': return no_update
    linha = linhas[celula_ativa['row']]
    return f"/resultado/{linha['id']}"

@callback(
    Output('lista-cotacoes-criadas', 'children'),
    Input('url', 'pathname'), Input('Btn-finalizar', 'n_clicks'), Input('filtro-busca', 'value'), Input('filtro-status', 'value'), Input('filtro-data-inicio', 'date'), Input('filtro-data-fim', 'date'),
    prevent_initial_call=False
)
def atualizar_lista_cotacoes(pathname, n_clicks, busca, status, data_inicio, data_fim):
    if pathname not in (None, '', '/'): return no_update
    return montar_tabela_cotacoes(busca, status, data_inicio, data_fim)

@callback(
    Output('mensagem-envio', 'children'), Output('Btn-enviar-precos', 'disabled'),
    Input('Btn-enviar-precos', 'n_clicks'), 
    State({'type': 'preco-input', 'index': ALL}, 'value'), 
    State({'type': 'preco-input', 'index': ALL}, 'id'), 
    State('token-cotacao', 'data'),
    State('rodada-atual-fornecedor', 'data'),
    prevent_initial_call=True
)
def enviar_precos(n_clicks, valores, ids, token, rodada_atual):
    precos = []
    invalidos = 0
    for id_componente, valor in zip(ids, valores):
        preco = parse_preco(valor)
        if preco is None: invalidos += 1
        precos.append({'id': id_componente['index'], 'preco_unitario': preco})
    if invalidos: return dbc.Alert("Preencha o preço de todos os itens com um número válido (ex: 12,50) antes de enviar.", color="warning"), False
    
    bd.salvar_precos(token, precos, rodada_atual)
    return dbc.Alert(f"Preços da {rodada_atual}ª Rodada enviados com sucesso. Obrigado!", color="success"), True

@callback(
    Output('feedback-nova-rodada', 'children'),
    Input('btn-nova-rodada', 'n_clicks'),
    State('url', 'pathname'),
    prevent_initial_call=True
)
def disparar_nova_rodada(n_clicks, pathname):
    if not pathname or not pathname.startswith('/resultado/'):
        return no_update
    cotacao_id = pathname.replace('/resultado/', '').strip('/')
    bd.abrir_nova_rodada_negociacao(int(cotacao_id))
    return dbc.Alert("Nova rodada aberta com sucesso! O mesmo link do fornecedor foi liberado para receber os novos preços.", color="success")

@callback(
    Output("download-excel", "data"),
    Output("feedback-excel", "children"),
    Input("btn-baixar-excel", "n_clicks"),
    State("dropdown-rodada-excel", "value"),
    State("url", "pathname"),
    prevent_initial_call=True
)
def gerar_excel_rodada(n_clicks, rodada_selecionada, pathname):
    if not rodada_selecionada:
        return no_update, dbc.Alert("Selecione uma rodada antes de baixar.", color="warning", style={'fontSize': '12px', 'padding': '5px'})
        
    if not pathname or not pathname.startswith('/resultado/'):
        return no_update, no_update
        
    cotacao_id = pathname.replace('/resultado/', '').strip('/')
    cotacao_completa = bd.buscar_todas_rodadas_id(int(cotacao_id))
    if not cotacao_completa:
        return no_update, no_update
        
    fornecedor_nome = cotacao_completa['fornecedor'] or "Fornecedor"
    itens_filtrados = [i for i in cotacao_completa['itens'] if i['rodada'] == int(rodada_selecionada)]
    
    if not itens_filtrados:
        return no_update, dbc.Alert("Nenhum dado encontrado para esta rodada.", color="danger", style={'fontSize': '12px', 'padding': '5px'})
        
    dados_excel = []
    for item in itens_filtrados:
        preco = parse_preco(item['preco_unitario'])
        qtd = item['qtd'] or 0
        valor_total = (preco * qtd) if preco is not None else 0
        
        dados_excel.append({
            "Fornecedor": fornecedor_nome,
            "Produto": item['item'],
            "Marca Aceita": item.get('marca', '-'),
            "Unidade": item['volume'] or "-",
            "Quantidade": qtd,
            "Valor Total": valor_total
        })
        
    df = pd.DataFrame(dados_excel)
    nome_arquivo = f"Cotacao_{cotacao_id}_Rodada_{rodada_selecionada}_{fornecedor_nome.replace(' ', '_')}.xlsx"
    return dcc.send_data_frame(df.to_excel, nome_arquivo, index=False), None

if __name__ == '__main__':
    porta = int(os.environ.get("PORT", 8050))
    app.run(host='0.0.0.0', port=porta, debug=False)

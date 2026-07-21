import os
from dash import html, dcc, dash_table, Output, Input, State, callback, Dash, callback_context, no_update, ALL
import dash_bootstrap_components as dbc
import pandas as pd
from flask import request
from werkzeug.middleware.proxy_fix import ProxyFix
import banco as bd
import plotly.express as px
import plotly.graph_objects as go

# Executa a criação das tabelas se elas não existirem no Postgres local/Supabase
bd.criar_banco()

# ============================================================
# TEMA VISUAL E CONFIGURAÇÃO
# ============================================================

FONTS_URL = "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght=500;600;700&family=Inter:wght@400;500;600&display=swap"

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP, FONTS_URL],
    suppress_callback_exceptions=True,
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}]
)
server = app.server
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

# Carregamento de Planilhas Base
produtos = pd.read_excel('produtos.xlsx')
fornecedor = pd.read_excel('fornecedor.xlsx')
fn = fornecedor['Nome do PN'].dropna().unique()
grupo = produtos['Nome do grupo'].dropna().unique()
todos_produtos = produtos['Descrição do item'].dropna().unique()

def campo(label, componente, largura):
    return dbc.Col([
        html.Div(label, className="rotulo-campo"),
        componente
    ], xs=12, md=largura)

def parse_preco(valor):
    if valor is None or valor == "": return None
    if isinstance(valor, (int, float)): return float(valor)
    texto = str(valor).strip().replace("R$", "").strip()
    if "," in texto and "." in texto: texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto: texto = texto.replace(",", ".")
    try: return float(texto)
    except ValueError: return None

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
            ], xs=12, md=6, lg=4)
        ], justify="center", align="center", style={'minHeight': '80vh'})
    ], fluid=True, className="p-3 p-md-5")

# ============================================================
# LAYOUT 1: TELA INTERNA (CRIAÇÃO + RELATÓRIOS)
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
                            dbc.Row([campo("Fornecedor", dcc.Dropdown(id='tab-pn', options=[{'label': f, 'value': f} for f in fn], placeholder="Selecione o fornecedor...", style={'color': '#000'}), 12)])
                        ])
                    ], className="card-cotacao mb-3 mt-4"),

                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                campo("Grupo", dcc.Dropdown(id='grupo', options=[{'label': g, 'value': g} for g in grupo], placeholder="Selecione...", style={'color': '#000'}), 3),
                                campo("Produto", dcc.Dropdown(id='produtos', placeholder="Selecione o produto...", style={'color': '#000'}), 4),
                                campo("Volume", dcc.Input(id='input-volume', type='text', placeholder="Ex: CX", style={'width': '100%', 'height': '38px', 'borderRadius': '6px'}), 2),
                                campo("Qtd", dcc.Input(id='input-qtd', type='number', placeholder="0", style={'width': '100%', 'height': '38px', 'borderRadius': '6px'}), 2),
                                dbc.Col(dbc.Button([html.I(className="bi bi-plus-circle me-2"), "Add"], id='Btn-salvar', n_clicks=0, style={'backgroundColor': COR_ACCENT_2, 'border': 'none', 'marginTop': '24px', 'width': '100%'}), xs=12, md=1)
                            ], className="g-2")
                        ])
                    ], className="card-cotacao mb-3"),

                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col(html.Span(id='badge-total-itens', className="badge badge-resumo me-2"), width='auto'),
                                dbc.Col(html.Span(id='badge-total-qtd', className="badge badge-resumo"), width='auto'),
                                dbc.Col(dbc.Button([html.I(className="bi bi-trash me-2"), "Remover Selecionado"], id='Btn-remover', n_clicks=0, size="sm", color="danger", outline=True, className="ms-auto"), width='auto', className="mt-2 mt-md-0")
                            ], className="mb-3 d-flex flex-wrap align-items-center"),
                            
                            dash_table.DataTable(
                                id='tabela-lista',
                                row_selectable='single',
                                style_table={'overflowX': 'auto'},
                                style_header={'backgroundColor': COR_CARD_2, 'color': COR_MUTED, 'fontWeight': '600'},
                                style_cell={'backgroundColor': COR_CARD, 'color': COR_TEXTO, 'textAlign': 'left'}
                            )
                        ])
                    ], className="card-cotacao mb-4"),

                    dbc.Card([
                        dbc.CardBody([
                            html.Div("Envio da Cotação", style={'color': COR_TEXTO, 'fontWeight': '600', 'marginBottom': '12px'}),
                            dbc.Button([html.I(className="bi bi-send-check me-2"), "Finalizar Cotação e Gerar Link"], id='Btn-finalizar', n_clicks=0, style={'backgroundColor': COR_ACCENT, 'border': 'none', 'color': '#12161c', 'fontWeight': '700', 'width': '100%'}),
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
                                campo("Fornecedor", dcc.Dropdown(id='rel-fornecedor', options=fornecedores_opts, value='todos', clearable=False, style={'color': '#000'}), 3),
                                campo("Produto", dcc.Dropdown(id='rel-produto', options=produtos_opts, value='todos', clearable=False, style={'color': '#000'}), 3),
                            ], className="g-3")
                        ])
                    ], className="card-cotacao mb-4 mt-4"),

                    dbc.Row([
                        dbc.Col(dbc.Card([dbc.CardBody([html.Div("Total Cotações", style={'color': COR_MUTED, 'fontSize': '12px'}), html.H3(id="kpi-total-cotacoes", style={'color': COR_TEXTO, 'fontWeight': '700'})])], className="card-cotacao"), xs=12, sm=6, lg=3, className="mb-3 mb-lg-0"),
                        dbc.Col(dbc.Card([dbc.CardBody([html.Div("Inicial (1ª Rodada)", style={'color': COR_MUTED, 'fontSize': '12px'}), html.H3(id="kpi-valor-inicial", style={'color': COR_TEXTO, 'fontWeight': '700'})])], className="card-cotacao"), xs=12, sm=6, lg=3, className="mb-3 mb-lg-0"),
                        dbc.Col(dbc.Card([dbc.CardBody([html.Div("Final (Última)", style={'color': COR_MUTED, 'fontSize': '12px'}), html.H3(id="kpi-valor-final", style={'color': COR_TEXTO, 'fontWeight': '700'})])], className="card-cotacao"), xs=12, sm=6, lg=3, className="mb-3 mb-lg-0"),
                        dbc.Col(dbc.Card([dbc.CardBody([html.Div("Resultado", style={'color': COR_MUTED, 'fontSize': '12px'}), html.H3(id="kpi-resultado-financeiro", style={'fontWeight': '700'})])], className="card-cotacao"), xs=12, sm=6, lg=3),
                    ], className="mb-4"),

                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardBody([
                                html.Div("Evolução do Valor Total por Rodada", style={'color': COR_TEXTO, 'fontWeight': '600', 'marginBottom': '12px'}),
                                dcc.Graph(id='grafico-evolucao-rodadas', config={'displayModeBar': False})
                            ])
                        ], className="card-cotacao"), xs=12, lg=7, className="mb-3 mb-lg-0"),
                        dbc.Col(dbc.Card([
                            dbc.CardBody([
                                html.Div("Economia por Fornecedor (R$)", style={'color': COR_TEXTO, 'fontWeight': '600', 'marginBottom': '12px'}),
                                dcc.Graph(id='grafico-economia-fornecedor', config={'displayModeBar': False})
                            ])
                        ], className="card-cotacao"), xs=12, lg=5),
                    ], className="mb-4"),

                    # MATRIZ DE COMPARAÇÃO
                    dbc.Card([
                        dbc.CardBody([
                            html.Div("Matriz de Comparação: Melhor Preço por Fornecedor", style={'color': COR_TEXTO, 'fontWeight': '600', 'marginBottom': '12px'}),
                            html.Div(id='tabela-matriz-comparativa')
                        ])
                    ], className="card-cotacao mb-4"),

                    # TABELA DETALHADA
                    dbc.Card([
                        dbc.CardBody([
                            html.Div("Histórico Detalhado dos Itens Negociados", style={'color': COR_TEXTO, 'fontWeight': '600', 'marginBottom': '12px'}),
                            html.Div(id='tabela-relatorio-detalhada')
                        ])
                    ], className="card-cotacao mb-4")
                ], style={'paddingTop': '20px'})
            ])
        ], id="tabs-painel", active_tab="tab-operacional")
    ], fluid=True, className="p-3 p-md-5", style={'minHeight': '100vh', 'paddingBottom': '60px'})


def montar_tabela_cotacoes(busca=None, status=None, data_inicio=None, data_fim=None):
    cotacoes = bd.listar_cotacoes()
    if busca:
        busca_lower = busca.strip().lower()
        cotacoes = [c for c in cotacoes if busca_lower in str(c['id']) or busca_lower in (c['fornecedor'] or "").lower()]
    if status and status != 'todas':
        cotacoes = [c for c in cotacoes if c['status'] == status]
    if data_inicio:
        cotacoes = [c for c in cotacoes if c['data_criacao'][:10] >= data_inicio[:10]]
    if data_fim:
        cotacoes = [c for c in cotacoes if c['data_criacao'][:10] <= data_fim[:10]]

    if not cotacoes: return html.Div("Nenhuma cotação encontrada.", style={'color': COR_MUTED, 'fontSize': '13px'})

    base_url = request.host_url.rstrip('/')
    linhas = []
    for c in cotacoes:
        # CORREÇÃO BLINDADA FUSO HORÁRIO
        try:
            dt_obj = pd.to_datetime(c['data_criacao'])
            if dt_obj.tz is None:
                dt_obj = dt_obj.tz_localize('UTC')
            data_corrigida = dt_obj.tz_convert('America/Sao_Paulo').strftime('%d/%m/%Y %H:%M')
        except:
            data_corrigida = c['data_criacao']

        linhas.append({
            "id": c['id'], "cotacao": f"#{c['id']}", "fornecedor": c['fornecedor'] or "-",
            "data_criacao": data_corrigida,
            "status": "Respondida" if c['status'] == 'respondida' else "Aguardando fornecedor",
            "link": f"{base_url}/responder/{c['token']}",
        })

    return html.Div([
        dash_table.DataTable(
            id='tabela-cotacoes',
            columns=[
                {"name": "Cotação", "id": "cotacao"}, {"name": "Fornecedor", "id": "fornecedor"},
                {"name": "Criada em", "id": "data_criacao"}, {"name": "Status", "id": "status"},
                {"name": "Link para o fornecedor", "id": "link"},
            ],
            data=linhas,
            style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': COR_CARD_2, 'color': COR_MUTED, 'fontWeight': '600', 'fontSize': '12px'},
            style_cell={'backgroundColor': COR_CARD, 'color': COR_TEXTO, 'textAlign': 'left', 'padding': '10px', 'borderBottom': f'1px solid {COR_BORDA}', 'cursor': 'pointer'},
            style_cell_conditional=[{'if': {'column_id': 'link'}, 'fontFamily': 'monospace', 'color': COR_ACCENT_2}],
            style_as_list_view=True,
        )
    ])


# ============================================================
# LAYOUT 2 e 3 (FORNECEDOR E RESULTADO)
# ============================================================
def layout_responder_fornecedor(token):
    cotacao = bd.buscar_cotacao_para_responder(token)
    if cotacao is None: return dbc.Container([html.Div("Link inválido.")], fluid=True, className="p-5")

    rodada = cotacao['rodada_atual']
    ja_respondida = cotacao['status'] == 'respondida'
    linhas = []
    
    for item in cotacao['itens']:
        if ja_respondida:
            campo_preco = html.Div(f"R$ {parse_preco(item['preco_unitario']):,.2f}" if item['preco_unitario'] is not None else "-", style={'color': COR_TEXTO})
        else:
            campo_preco = dcc.Input(id={'type': 'preco-input', 'index': item['id']}, type="text", placeholder="Ex: 12,50", value=(str(item['preco_unitario']) if item['preco_unitario'] is not None else None), style={'width': '100%', 'height': '36px', 'borderRadius': '6px'})
        
        linhas.append(dbc.Row([
            dbc.Col(item['grupo'] or "-", xs=3, md=3, style={'fontSize': '13px'}), dbc.Col(item['item'], xs=3, md=3, style={'fontSize': '13px'}),
            dbc.Col(item['volume'] or "-", xs=2, md=2, style={'fontSize': '13px'}), dbc.Col(item['qtd'], xs=1, md=1, style={'fontSize': '13px'}),
            dbc.Col(campo_preco, xs=3, md=3)
        ], className="py-2 align-items-center", style={'borderBottom': f'1px solid {COR_BORDA}'}))

    return dbc.Container([
        html.Div([html.Span(f"NEGOCIAÇÃO ONLINE - {rodada}ª RODADA", className="titulo-cotacao", style={'fontSize': '22px', 'fontWeight': '700', 'color': COR_TEXTO})]),
        dcc.Store(id='token-cotacao', data=token), dcc.Store(id='rodada-atual-fornecedor', data=rodada),
        dbc.Card([
            dbc.CardBody([
                html.Div([dbc.Row([dbc.Col("Grupo", xs=3, md=3), dbc.Col("Item", xs=3, md=3), dbc.Col("Vol", xs=2, md=2), dbc.Col("Qtd", xs=1, md=1), dbc.Col("Preço", xs=3, md=3)], className="py-2"), html.Div(linhas)], style={'overflowX': 'auto', 'minWidth': '500px'}), 
                dbc.Button("Enviar preços da Rodada", id='Btn-enviar-precos', n_clicks=0, style={'backgroundColor': COR_ACCENT, 'border': 'none', 'color': '#12161c', 'fontWeight': '700', 'marginTop': '18px', 'width': '100%'}, disabled=ja_respondida),
                html.Div(id='mensagem-envio', style={'marginTop': '14px'}),
            ])
        ], className="card-cotacao mt-3"),
    ], fluid=True, className="p-3 p-md-5")

def layout_resultado_cotacao(cotacao_id):
    cotacao_completa = bd.buscar_todas_rodadas_id(int(cotacao_id))
    if cotacao_completa is None: return dbc.Container([html.Div("Cotação não encontrada.")], fluid=True)

    linhas_tabela = []
    rodadas_disponiveis = set()
    for item in cotacao_completa['itens']:
        preco = parse_preco(item['preco_unitario'])
        qtd = item['qtd'] or 0
        rodadas_disponiveis.add(item['rodada'])
        linhas_tabela.append({
            "rodada": f"{item['rodada']}ª Rodada", "grupo": item['grupo'] or "-", "item": item['item'],
            "volume": item['volume'] or "-", "qtd": qtd, "preco_unitario": f"R$ {preco:,.2f}" if preco is not None else "Aguardando",
            "subtotal": f"R$ {(preco * qtd):,.2f}" if preco is not None else "-"
        })

    opcoes_rodadas = [{'label': f'{r}ª Rodada', 'value': r} for r in sorted(rodadas_disponiveis)]
    return dbc.Container([
        dcc.Download(id="download-excel"),
        html.Div([
            dcc.Link("← Voltar", href="/", style={'color': COR_MUTED}),
            html.Div([html.Span(f"HISTÓRICO - COTAÇÃO Nº {cotacao_completa['id']}", className="titulo-cotacao", style={'fontSize': '22px', 'fontWeight': '700', 'color': COR_TEXTO})], style={'marginTop': '10px'})
        ]),
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([dbc.Button("Reabrir Cotação (Nova Rodada)", id='btn-nova-rodada', n_clicks=0, style={'backgroundColor': COR_ACCENT, 'color': '#12161c', 'width': '100%'}), html.Div(id='feedback-nova-rodada')], xs=12, md=6),
                    dbc.Col([dbc.Row([dbc.Col(dcc.Dropdown(id='dropdown-rodada-excel', options=opcoes_rodadas, placeholder="Escolha a rodada..."), xs=12, sm=7), dbc.Col(dbc.Button("Baixar Excel", id='btn-baixar-excel', n_clicks=0, style={'backgroundColor': COR_SUCESSO, 'width': '100%'}), xs=12, sm=5)]), html.Div(id='feedback-excel')], xs=12, md=6)
                ])
            ])
        ], className="card-cotacao mb-4 mt-3"),
        dbc.Card([
            dbc.CardBody([
                dash_table.DataTable(
                    columns=[{"name": c.capitalize(), "id": c} for c in ["rodada", "grupo", "item", "volume", "qtd", "preco_unitario", "subtotal"]],
                    data=linhas_tabela, style_table={'overflowX': 'auto'}, style_header={'backgroundColor': COR_CARD_2, 'color': COR_MUTED},
                    style_cell={'backgroundColor': COR_CARD, 'color': COR_TEXTO, 'textAlign': 'left', 'padding': '10px'}, page_size=30, style_as_list_view=True
                )
            ])
        ], className="card-cotacao"),
    ], fluid=True, className="p-3 p-md-5")

# ============================================================
# CALLBACKS
# ============================================================

app.layout = html.Div([dcc.Location(id='url', refresh=False), dcc.Store(id='sessao-interna', storage_type='session', data=False), html.Div(id='conteudo-pagina')])

@callback(Output('conteudo-pagina', 'children'), Input('url', 'pathname'), Input('sessao-interna', 'data'))
def rotear_pagina(pathname, logado):
    if pathname and pathname.startswith('/responder/'): return layout_responder_fornecedor(pathname.replace('/responder/', '').strip('/'))
    if not logado: return layout_login()
    if pathname and pathname.startswith('/resultado/'): return layout_resultado_cotacao(pathname.replace('/resultado/', '').strip('/'))
    return layout_cotacao_interna()

@callback(Output('sessao-interna', 'data'), Output('login-feedback', 'children'), Input('btn-login', 'n_clicks'), State('input-senha', 'value'), prevent_initial_call=True)
def realizar_login(n_clicks, senha): return (True, None) if senha == SENHA_INTERNA else (False, dbc.Alert("Senha incorreta.", color="danger"))

@callback(
    Output('produtos', 'options'), Output('produtos', 'value'), Output('input-volume', 'value'), Output('input-qtd', 'value'),
    Output('lista-store', 'data'), Output('tabela-lista', 'data'), Output('badge-total-itens', 'children'), Output('badge-total-qtd', 'children'),
    Input('grupo', 'value'), Input('Btn-salvar', 'n_clicks'), Input('Btn-remover', 'n_clicks'),
    State('tab-pn', 'value'), State('grupo', 'value'), State('produtos', 'value'), State('input-volume', 'value'), State('input-qtd', 'value'),
    State('lista-store', 'data'), State('tabela-lista', 'selected_rows'), prevent_initial_call=True
)
def gerenciar(grupo_sel_in, salvar, remover, f_sel, g_sel, p_sel, vol, qtd, lista, sel_rows):
    ctx = callback_context
    if not ctx.triggered: return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    btn = ctx.triggered[0]['prop_id'].split('.')[0]
    if btn == 'grupo': return [{'label': i, 'value': i} for i in (produtos[produtos['Nome do grupo'] == grupo_sel_in]['Descrição do item'].dropna().unique() if grupo_sel_in else todos_produtos)], None, no_update, no_update, lista, lista, f"{len(lista)} itens", f"{sum(i['qtd'] for i in lista if isinstance(i['qtd'], (int, float)))} un."
    if btn == 'Btn-salvar' and p_sel:
        lista.append({"fornecedor": f_sel or "-", "grupo": g_sel or "-", "item": p_sel, "volume": vol or "-", "qtd": qtd or 0})
        return no_update, None, None, None, lista, lista, f"{len(lista)} itens", f"{sum(i['qtd'] for i in lista if isinstance(i['qtd'], (int, float)))} un."
    if btn == 'Btn-remover' and sel_rows:
        lista.pop(sel_rows[0])
        return no_update, no_update, no_update, no_update, lista, lista, f"{len(lista)} itens", f"{sum(i['qtd'] for i in lista if isinstance(i['qtd'], (int, float)))} un."
    return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

@callback(
    Output('resultado-link', 'children'), Output('lista-store', 'data', allow_duplicate=True), Output('tabela-lista', 'data', allow_duplicate=True),
    Input('Btn-finalizar', 'n_clicks'), State('tab-pn', 'value'), State('lista-store', 'data'), prevent_initial_call=True
)
def finalizar(n_clicks, f_sel, lista):
    if not lista: return dbc.Alert("Adicione ao menos um item.", color="warning"), no_update, no_update
    c_id, token = bd.criar_cotacao(f_sel, lista)
    link = f"{request.host_url.rstrip('/')}/responder/{token}"
    return html.Div([dbc.Alert(f"Cotação {c_id} salva! Link: {link}", color="success")]), [], []

@callback(Output('url', 'pathname'), Input('tabela-cotacoes', 'active_cell'), State('tabela-cotacoes', 'data'), prevent_initial_call=True)
def ir_resultado(celula, linhas): return f"/resultado/{linhas[celula['row']]['id']}" if celula and linhas and celula.get('column_id') != 'link' else no_update

@callback(Output('lista-cotacoes-criadas', 'children'), Input('url', 'pathname'), Input('Btn-finalizar', 'n_clicks'), Input('filtro-busca', 'value'), Input('filtro-status', 'value'), Input('filtro-data-inicio', 'date'), Input('filtro-data-fim', 'date'), prevent_initial_call=False)
def att_lista(p, n, b, s, di, df): return montar_tabela_cotacoes(b, s, di, df) if p in (None, '', '/') else no_update

@callback(Output('mensagem-envio', 'children'), Output('Btn-enviar-precos', 'disabled'), Input('Btn-enviar-precos', 'n_clicks'), State({'type': 'preco-input', 'index': ALL}, 'value'), State({'type': 'preco-input', 'index': ALL}, 'id'), State('token-cotacao', 'data'), State('rodada-atual-fornecedor', 'data'), prevent_initial_call=True)
def enviar_precos(n, valores, ids, token, rodada):
    precos = [{'id': i['index'], 'preco_unitario': parse_preco(v)} for i, v in zip(ids, valores)]
    if any(p['preco_unitario'] is None for p in precos): return dbc.Alert("Preencha todos com números válidos.", color="warning"), False
    bd.salvar_precos(token, precos, rodada)
    return dbc.Alert("Enviado com sucesso!", color="success"), True

@callback(Output('feedback-nova-rodada', 'children'), Input('btn-nova-rodada', 'n_clicks'), State('url', 'pathname'), prevent_initial_call=True)
def nova_rodada(n, p):
    if p and p.startswith('/resultado/'):
        bd.abrir_nova_rodada_negociacao(int(p.replace('/resultado/', '').strip('/')))
        return dbc.Alert("Nova rodada aberta!", color="success")
    return no_update

@callback(Output("download-excel", "data"), Output("feedback-excel", "children"), Input("btn-baixar-excel", "n_clicks"), State("dropdown-rodada-excel", "value"), State("url", "pathname"), prevent_initial_call=True)
def baixar_excel(n, r, p):
    if not r: return no_update, dbc.Alert("Selecione a rodada.", color="warning")
    c = bd.buscar_todas_rodadas_id(int(p.replace('/resultado/', '').strip('/')))
    df = pd.DataFrame([{"Fornecedor": c['fornecedor'], "Produto": i['item'], "Valor Total": (parse_preco(i['preco_unitario']) or 0) * (i['qtd'] or 0)} for i in c['itens'] if i['rodada'] == int(r)])
    return dcc.send_data_frame(df.to_excel, f"Cotacao_{c['id']}_Rodada_{r}.xlsx", index=False), None


@callback(
    Output('kpi-total-cotacoes', 'children'), Output('kpi-valor-inicial', 'children'),
    Output('kpi-valor-final', 'children'), Output('kpi-resultado-financeiro', 'children'),
    Output('kpi-resultado-financeiro', 'style'), Output('grafico-evolucao-rodadas', 'figure'),
    Output('grafico-economia-fornecedor', 'figure'), Output('tabela-matriz-comparativa', 'children'), 
    Output('tabela-relatorio-detalhada', 'children'),
    Input('rel-data-inicio', 'date'), Input('rel-data-fim', 'date'),
    Input('rel-fornecedor', 'value'), Input('rel-produto', 'value'), prevent_initial_call=False
)
def atualizar_painel_relatorio(dt_inicio, dt_fim, fornecedor, produto):
    dados = bd.gerar_relatorio_negociacoes(dt_inicio, dt_fim, fornecedor, produto)
    fig_vazia = go.Figure().update_layout(template="plotly_dark", paper_bgcolor=COR_CARD, plot_bgcolor=COR_CARD)
    if not dados: return "0", "R$ 0,00", "R$ 0,00", "R$ 0,00", {'color': COR_MUTED}, fig_vazia, fig_vazia, html.Div("Sem dados."), html.Div("Sem dados.")
        
    df = pd.DataFrame(dados)
    cotacoes_unicas = df['cotacao_id'].nunique()
    
    agrupado = df.groupby(['cotacao_id', 'rodada'])['total_item'].sum().reset_index()
    val_inicial = sum([agrupado[(agrupado['cotacao_id'] == row['cotacao_id']) & (agrupado['rodada'] == row['rodada'])]['total_item'].values[0] for _, row in agrupado.groupby('cotacao_id')['rodada'].min().reset_index().iterrows()])
    val_final = sum([agrupado[(agrupado['cotacao_id'] == row['cotacao_id']) & (agrupado['rodada'] == row['rodada'])]['total_item'].values[0] for _, row in agrupado.groupby('cotacao_id')['rodada'].max().reset_index().iterrows()])
    
    dif = val_inicial - val_final
    txt_res = f"Economia: R$ {dif:,.2f}" if dif > 0 else (f"Prejuízo: R$ {abs(dif):,.2f}" if dif < 0 else "Sem alteração")
    est_res = {'color': COR_SUCESSO} if dif > 0 else ({'color': COR_PERIGO} if dif < 0 else {'color': COR_MUTED})

    df_evo = df.groupby(['rodada', 'cotacao_id'])['total_item'].sum().reset_index()
    df_evo['rodada_label'] = df_evo['rodada'].astype(str) + "ª Rod"
    f_evo = px.line(df_evo, x='rodada_label', y='total_item', color='cotacao_id', markers=True).update_layout(template="plotly_dark", paper_bgcolor=COR_CARD, plot_bgcolor=COR_CARD, margin=dict(l=20, r=20, t=20, b=20))

    df_forn = df.groupby(['fornecedor', 'rodada'])['total_item'].sum().reset_index()
    econ_forn = [{'fornecedor': f, 'economia': df_forn[(df_forn['fornecedor'] == f) & (df_forn['rodada'] == df_forn[df_forn['fornecedor'] == f]['rodada'].min())]['total_item'].values[0] - df_forn[(df_forn['fornecedor'] == f) & (df_forn['rodada'] == df_forn[df_forn['fornecedor'] == f]['rodada'].max())]['total_item'].values[0]} for f in df_forn['fornecedor'].unique()]
    f_eco = px.bar(pd.DataFrame(econ_forn), x='fornecedor', y='economia', color='economia', color_continuous_scale=['red', 'yellow', 'green']).update_layout(template="plotly_dark", paper_bgcolor=COR_CARD, plot_bgcolor=COR_CARD, margin=dict(l=20, r=20, t=20, b=20))

    # ============================================================
    # MATRIZ DE COMPARAÇÃO (PIVOT TABLE) + REGRAS DE CORES
    # ============================================================
    df_comparativo = df.pivot_table(index='produto', columns='fornecedor', values='preco_unitario', aggfunc='min').reset_index()
    
    estilos_condicionais = []
    colunas_fornecedores = [c for c in df_comparativo.columns if c != 'produto']

    for index, row in df_comparativo.iterrows():
        valores = [row[c] for c in colunas_fornecedores if pd.notnull(row[c])]
        if valores:
            menor_valor = min(valores)
            for c in colunas_fornecedores:
                if row[c] == menor_valor:
                    # Aplica a cor verde na célula do fornecedor mais barato
                    estilos_condicionais.append({
                        'if': {'filter_query': f'{{produto}} = "{row["produto"]}"', 'column_id': str(c)},
                        'backgroundColor': '#1e4620',
                        'color': '#4ade80',
                        'fontWeight': 'bold'
                    })

    # Formata os valores monetários da tabela comparativa
    for col in colunas_fornecedores:
        df_comparativo[col] = df_comparativo[col].apply(lambda x: f"R$ {x:,.2f}" if pd.notnull(x) else "-")
        
    tabela_comparativo = dash_table.DataTable(
        columns=[{"name": str(i), "id": str(i)} for i in df_comparativo.columns],
        data=df_comparativo.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_header={'backgroundColor': COR_CARD_2, 'color': COR_MUTED, 'fontWeight': '600'},
        style_cell={'backgroundColor': COR_CARD, 'color': COR_TEXTO, 'textAlign': 'left', 'padding': '10px'},
        style_data_conditional=estilos_condicionais,
        page_size=10, style_as_list_view=True
    )

    # ============================================================
    # CORREÇÃO DEFINITIVA DE FUSO HORÁRIO NO RELATÓRIO
    # ============================================================
    df['data_criacao'] = pd.to_datetime(df['data_criacao'])
    if df['data_criacao'].dt.tz is None:
        df['data_criacao'] = df['data_criacao'].dt.tz_localize('UTC')
    df['data_criacao'] = df['data_criacao'].dt.tz_convert('America/Sao_Paulo').dt.strftime('%d/%m/%Y %H:%M')
    
    df['preco_unitario'] = df['preco_unitario'].apply(lambda x: f"R$ {x:,.2f}")
    df['total_item'] = df['total_item'].apply(lambda x: f"R$ {x:,.2f}")
    
    tabela_detalhada = dash_table.DataTable(
        columns=[{"name": "Cotação Nº", "id": "cotacao_id"}, {"name": "Data", "id": "data_criacao"}, {"name": "Fornecedor", "id": "fornecedor"}, {"name": "Rodada", "id": "rodada"}, {"name": "Produto", "id": "produto"}, {"name": "Qtd", "id": "qtd"}, {"name": "Preço Unit.", "id": "preco_unitario"}, {"name": "Subtotal", "id": "total_item"}],
        data=df.to_dict('records'), style_table={'overflowX': 'auto'}, style_header={'backgroundColor': COR_CARD_2, 'color': COR_MUTED}, style_cell={'backgroundColor': COR_CARD, 'color': COR_TEXTO, 'textAlign': 'left', 'padding': '10px'}, page_size=10, style_as_list_view=True
    )
    return str(cotacoes_unicas), f"R$ {val_inicial:,.2f}", f"R$ {val_final:,.2f}", txt_res, est_res, f_evo, f_eco, tabela_comparativo, tabela_detalhada

if __name__ == '__main__':
    porta = int(os.environ.get("PORT", 8050))
    app.run(host='0.0.0.0', port=porta, debug=False)

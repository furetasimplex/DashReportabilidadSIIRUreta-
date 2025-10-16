from dash import html


simplexLoader = html.Div(className="simplex-loader",children=[html.Div("SIMPL", className="simplex-text"),html.Div( className="simplex-e",children=[html.Div(className="bar bar1"),html.Div(className="bar bar2"),html.Div(className="bar bar3"),],),html.Div("X", className="simplex-text"),html.Div("INGENIERÍA", className="simplex-subtitle"),],)

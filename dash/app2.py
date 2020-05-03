import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import numpy as np
import pandas as pd
import uuid
import time

class MaxSizeCache:
    def __init__(self, size):
        self.cache = {}
        self.size = size
        self.birth_time = time.time()

    def in_cache(self, key):
        self.check_and_clear()
        return key in self.cache.keys()

    def add_to_cache(self, key, value):
        # if the max size have been reached delete the first 5 keys
        self.check_and_clear()
        self.manage_size()
        self.cache[key] = value

    def get(self, key):
        return self.cache[key]

    def check_and_clear(self):
        # check if the cache is older than 3 hours
        if self.birth_time + 10800 < time.time():
            print('Resenting Cache')
            self.cache = {}
            self.birth_time = time.time()

    def manage_size(self):
        if len(self.cache) == self.size:
            print('Removing Some Cache Items')
            keys = list(self.cache.keys())
            for i in range(5):
                del self.cache[keys[i]]

#external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
external_stylesheets = [dbc.themes.BOOTSTRAP]
default_point_color = '#69A0CB'
trend_session_cache = MaxSizeCache(100)

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


def get_map(lats, lons, lat, lon, indexes):
    mapbox_access_token = open(".mapbox_token").read()
    colors = [default_point_color] * len(lats)
    opacity = [0.25] * len(lats)
    for index in indexes:
        colors[index] = 'red'
        opacity[index] = 1.0
    fig = go.Figure(go.Scattermapbox(\
            lat=lats,
            lon=lons,
            mode='markers',
            marker=go.scattermapbox.Marker(size=14,
                                           opacity=opacity,
                                           color=colors) ))

    fig.update_layout(
        hovermode='closest',
        mapbox=dict(
            accesstoken=mapbox_access_token,
            bearing=0,
            center=go.layout.mapbox.Center(
                lat=lat,
                lon=lon
            ),
            pitch=0,
            zoom=10,
        )
    )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig


def make_ws_hists(num_weeks, ws_df):
    fig = make_subplots(rows=1, cols=num_weeks)
    ws_weeks = ws_df.columns[6:]

    week_i = 1
    for week in ws_weeks:
        h = go.Histogram(x=ws_df[week],
                         name='Week ' + str(week_i))
        fig.append_trace( h, 1, week_i)

        week_i += 1
    return fig


def move_index_to_end(items,index):
    val = items[index]
    del items[index]
    items.append(val)
    return items


def move_all_index_to_end(X,Y,df_indexes,index):
    X = move_index_to_end(X,index)
    Y = move_index_to_end(Y,index)
    df_indexes = move_index_to_end(df_indexes,index)
    return X, Y, df_indexes


@app.callback(
    [Output('slip_score', 'figure'),
    Output('weekend_score', 'figure'),
    Output('trend_lines', 'figure'),
    Output('map', 'figure')],
    [Input('week-slider', 'value'),
    Input('slip_score', 'clickData'),
    Input('weekend_score', 'clickData'),
    Input('trend_lines','clickData'),
    Input('session-id','children'),
    Input('map','clickData'),
    Input('map','selectedData')])
def update_scatter_plots(selected_col_i,ss_data,ws_data,trend_data,session_id,map_data,map_selection):
    lon = 40.588928
    lat = -112.071533
    lons = list(ws_df['lon'])
    lats = list(ws_df['lat'])
    ctx = dash.callback_context
    indexes = [-1]
    if ctx.triggered[0]['prop_id'] == 'weekend_score.clickData':
        indexes = [int(ws_data['points'][0]['customdata'])]
        lon = ws_df.iloc[indexes[0],:]['lon']
        lat = ws_df.iloc[indexes[0],:]['lat']
    elif ctx.triggered[0]['prop_id'] == 'slip_score.clickData':
        indexes = [int(ss_data['points'][0]['customdata'])]
        lon = ss_df.iloc[indexes[0],:]['lon']
        lat = ss_df.iloc[indexes[0],:]['lat']
    elif ctx.triggered[0]['prop_id'] == 'trend_lines.clickData':
        trend_index = trend_data['points'][0]['curveNumber']
        indexes = [trend_session_cache.get(session_id)[trend_index]]
        lon = trend_df.iloc[indexes[0],:]['lon']
        lat = trend_df.iloc[indexes[0],:]['lat']
    elif ctx.triggered[0]['prop_id'] == 'map.clickData':
        indexes = [map_data['points'][0]['pointNumber']]
        lon = ss_df.iloc[indexes[0],:]['lon']
        lat = ss_df.iloc[indexes[0],:]['lat']
    elif ctx.triggered[0]['prop_id'] == 'map.selectedData':
        indexes = [x['pointNumber'] for x in map_selection['points']]
        lon = ss_df.iloc[indexes[0],:]['lon']
        lat = ss_df.iloc[indexes[0],:]['lat']
    print(indexes)
    return slip_score_callback(selected_col_i,ss_data,indexes),  \
           weekend_score_callback(selected_col_i,ws_data,indexes), \
           make_trend(indexes,session_id), get_map(lons, lats, lon, lat, indexes)


def slip_score_callback(selected_col_i,ss_data,point_indexes):
    slip_weeks = ss_df.columns[5:]
    selected_col = slip_weeks[selected_col_i]
    df_indexes = list(range(ss_df.shape[0]))
    point_color = default_point_color
    filtered_df = ss_df[['baseline_density',selected_col]]

    X = list(filtered_df['baseline_density'])
    Y = list(filtered_df[selected_col])
    df_indexes = list(range(len(X)))
    marker_colors = [default_point_color] * len(X)

    if point_indexes[0] != -1:
        point_color = 'red'
        # move the point of interest to the end so it displays on top
        for index in point_indexes:
            X,Y,df_indexes = move_all_index_to_end(X,Y,df_indexes,index)
            marker_colors = move_index_to_end(marker_colors,index)
            marker_colors[-1] = 'red'

    traces = []
    traces.append(dict(
        x=X,
        y=Y,
        customdata=df_indexes,
        mode='markers',
        opacity=0.7,
        marker={
            'size': 15,
            'line': {'width': 0.5, 'color': 'white'},
            'color': marker_colors
        },
    ))

    week_1 = 'Week ' + str(selected_col_i) if selected_col_i > 0 else 'Baseline'
    week_2 = 'week ' +str(selected_col_i+1)
    y_label = week_1 + ' to ' + week_2 + ' slip'

    return {
        'data': traces,
        'layout': dict(
            xaxis={'title':'Baseline density'},
            yaxis={'title':y_label},
            hovermode='closest',
            transition = {'duration': 500},
            margin={'t':10,'l':50,'r':0}
           # margin={'t':0,'b':0,'r':0,'l':0}
        )
    }


def weekend_score_callback(selected_col_i,ws_data,point_indexes):
    ws_weeks = ws_df.columns[6:]
    selected_col = ws_weeks[selected_col_i]
    point_color = default_point_color
    X = list(ws_df['baseline_ws'])
    Y = list(ws_df[selected_col])
    df_indexes = list(range(len(X)))

    marker_colors = [default_point_color] * len(X)

    if point_indexes[0] != -1:
        point_color = 'red'
        # move the point of interest to the end so it displays on top
        for index in point_indexes:
            X,Y,df_indexes = move_all_index_to_end(X,Y,df_indexes,index)
            marker_colors = move_index_to_end(marker_colors,index)
            marker_colors[-1] = 'red'

    traces = []
    traces.append(dict(
        x=X,
        y=Y,
        customdata=df_indexes,
        mode='markers',
        opacity=0.7,
        marker={
            'size': 15,
            'line': {'width': 0.5, 'color': 'white'},
            'color':marker_colors
        },
    ))

    y_label = 'Week ' + str(selected_col_i+1) + ' weekend score'
    x_label = 'Week ' + str(selected_col_i) + ' weekend score'
    if selected_col_i == 0:
        x_label = 'Baseline weekend score'

    return {
        'data': traces,
        'layout': dict(
            xaxis={'title': x_label},
            yaxis={'title': y_label},
            hovermode='closest',
            transition = {'duration': 500},
            margin={'t':10,'l':50,'r':0}
            #margin={'t':0,'b':0,'r':0,'l':0}
        )
    }


@app.callback(
    Output('weekend_hist', 'figure'),
    [Input('week-slider', 'value')])
def make_ws_hist(selected_col_i):
    ws_weeks = ws_df.columns[6:]
    selected_col = ws_weeks[selected_col_i]
    x_label = 'Week ' + str(selected_col_i+1) + ' weekend score'
    return {
        'data' : [
            { 
                'x'   : ws_df[selected_col], 
                'type': 'histogram' 
            } 
        ],
        'layout': {
            'margin':{'t':10,'b':50,'r':0,'l':50},
            'xaxis' : {'title': x_label},
            'yaxis' : {'title': 'Frequency'}
        }
    }


def make_trend(indexes,session_id):
    dow_date_time= [ x.split()[1:] for x in trend_df.columns[6:]]
    #date_time = [x[1] for x in dow_date_time]
    date_time = [x[1] + x[2][:2] + ':' + x[2][2:] for x in dow_date_time]

    b = np.array(trend_df.baseline_density.tolist())
    b_norm = 1 + (5*((b - np.min(b)) / np.max(b)))

    fig = go.Figure()
    traces = []
    for idx,row in trend_df.iterrows():
        line_color = default_point_color
        if idx in indexes:
            line_color = 'red'
        y = row.tolist()[6:]
        #x = [i for i in range(len(y))]
        x = date_time
        loc = str(row.lat) + ',' + str(row.lon)
        traces.append(go.Scatter(x=x,
                                 y=y,
                                 text=loc,
                                 opacity=0.5,
                                 line=dict(width=b_norm[idx],
                                           color=line_color)))
        if idx == 100:
            break
    trace_indexes = list(range(len(traces)))
    for index in indexes:
        traces = move_index_to_end(traces,index)
        trace_indexes = move_index_to_end(trace_indexes,index)

    trend_session_cache.add_to_cache(session_id,trace_indexes)
    for t in traces:
        fig.add_trace(t)
    fig.update_layout(showlegend=False)
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig


ss_df = pd.read_csv('slip.csv')
ws_df = pd.read_csv('ws.csv')
trend_df = pd.read_csv('trend.csv')

y_min = ss_df.iloc[:,5:].min().min()
y_max = ss_df.iloc[:,5:].max().max()


num_weeks = len(ss_df.columns[5:])
pretty_weeks = ['Week ' + str(i+1) for i in range(num_weeks)]

hists = make_ws_hists(num_weeks, ws_df)

marks={i:pretty_weeks[i] for i in range(num_weeks)}

def layout():
    session_id = str(uuid.uuid4())
    return html.Div([
        dbc.Col([
            dbc.Row( [
                dbc.Col( dcc.Graph(id='map',
                                   figure=get_map([40.588928],
                                                  [-112.071533],
                                                  40.588928,
                                                  -112.071533,[0]),
                                   style={'height':'47vh'})),
            ],no_gutters=True),
            dbc.Row([
                dbc.Col(dcc.Graph(id='trend_lines',style={'height':'47vh'}))
            ],no_gutters=True),
        ],width=8,style={'float': 'left','height':'100vh','padding':'0'}),
        dbc.Col([
            dcc.Graph(id='weekend_hist',
                      style={'height':'30vh','margin-top':'5px'}),
            dcc.Graph(id='weekend_score',
                      style={'height':'30vh','margin-top':'5px'}),
            dcc.Graph(id='slip_score',
                      style={'height':'30vh','margin-top':'5px'}),
            dcc.Slider(id='week-slider',
                       min=0,
                       max=num_weeks-1,
                       value=num_weeks-1,
                       marks=marks,
                       step=None)
        ],width=4,style={'float': 'left','height':'100vh'}),
        # Hidden div inside the app that stores the intermediate value
        html.Div(session_id,id='session-id', style={'display': 'none'})
    ])

app.layout = layout


if __name__ == '__main__':
    app.run_server(debug=True)

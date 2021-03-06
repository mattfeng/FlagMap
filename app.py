from flask import Flask, render_template, request, session, abort, flash, redirect, url_for

import json

import plotly.utils
import plotly.plotly as py
from plotly.graph_objs import *

import pandas as pd
import numpy as np

import networkx as nx

import matplotlib
from matplotlib import cm

import os

import hashlib

from sqlalchemy.orm import sessionmaker
from tabledef import *

from mapper import *

app = Flask(__name__)
app.debug = True

engine = create_engine('sqlite:///users.db', echo=True)

# load problems (aka questions)
problems = json.load(open('./questions.json'))['problems']
print problems

# set up colorschemes
cmap = matplotlib.cm.get_cmap('YlGnBu')
rgb = []
norm = matplotlib.colors.Normalize(vmin=0, vmax=255)

for i in range(0, 255):
    k = matplotlib.colors.colorConverter.to_rgb(cmap(norm(i)))
    rgb.append(k)

def matplotlib_to_plotly(cmap, pl_entries):
    h = 1.0/(pl_entries-1)
    LIMIT_FRAC = 0.75
    pl_colorscale = []
    
    for k in range(pl_entries):
        C = map(np.uint8, np.array(cmap(k*h*LIMIT_FRAC)[:3])*255)
        pl_colorscale.append([k*h, 'rgb'+str((C[0], C[1], C[2]))])
        
    return pl_colorscale

colorscheme = matplotlib_to_plotly(cmap, 255)


# prep network for display
def scatter_edges(G, pos, line_color='#888', line_width=0.5):
    trace = Scatter(x=[], y=[], mode='lines')
    for edge in G.edges():
        trace['x'] += [pos[edge[0]][0],pos[edge[1]][0], None]
        trace['y'] += [pos[edge[0]][1],pos[edge[1]][1], None]  
        trace['hoverinfo'] = 'none'
        trace['line']['width'] = line_width
        if line_color is not None: # when it is None a default Plotly color is used
            trace['line']['color'] = line_color
    return trace  

def scatter_nodes(G, opacity=1):
    pos = nx.drawing.nx_pydot.graphviz_layout(G)

    marker = Marker(
        showscale = True,
        cmin = 10,
        cmax = 600,
        colorscale = colorscheme,
        color = [],
        size = 32,
        colorbar = dict(
            thickness = 30,
            title = 'Point Value',
            xanchor = 'left',
            titleside = 'right'
        ),
        line = dict(width=2))

    trace = Scatter(x=[], y=[],  mode='markers', marker=marker)

    node_ids = G.node.keys()

    labels = []

    for k in node_ids:
        label = G.node[k]['label']
        color = G.node[k]['point_value']

        trace['x'].append(pos[k][0])
        trace['y'].append(pos[k][1])
        trace['marker']['color'].append(color)
        labels.append(label)

    attrib = dict(name='', text=labels, hoverinfo='text', opacity=opacity)
    trace = dict(trace, **attrib)
    return trace, pos


# begin app
@app.route('/map')
def show_map():

    if not session.get('logged_in'):
        return home()

    team_id = session.get('team_id')

    Session = sessionmaker(bind=engine)
    s = Session()
    query = s.query(User).filter(User.username.in_([team_id]))
    result = query.first()

    if not result:
        return home()

    print result.solved
    solved = []
    if result.solved != '':
        for problem_id in result.solved.split(','):
            solved.append(int(problem_id))

    G = make_graph_from_solved(solved, problems)

    node_trace, pos = scatter_nodes(G)
    edge_trace = scatter_edges(G, pos)

    data = Data([edge_trace, node_trace])
    layout = Layout(title = "HSF Finals Challenge Map",
                    xaxis = XAxis(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis = YAxis(showgrid=False, zeroline=False, showticklabels=False),
                    showlegend = False,
                    hovermode = 'closest',
                    titlefont = dict(size=16),
                    margin = dict(b=20,l=5,r=5,t=40),
                    height = 650)

    graphs = [ dict(data=data, layout=layout) ]
    ids = ['map{}'.format(i) for i, _ in enumerate(graphs)]
    graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('map.html',
                           ids=ids,
                           graphJSON=graphJSON,
                           username=session.get('team_id'))


def validate_answer(given, correct):
    return given == correct


# attempt to solve a question
@app.route('/solve', methods=['POST'])
def solve():
    if not session.get('logged_in'):
        return abort(401)

    if request.method == 'POST':
        prob_id = str(request.form['prob_id'])
        answer = str(request.form['answer'])

        # check if team has access to question:
        team_id = session.get('team_id')

        Session = sessionmaker(bind=engine)
        s = Session()
        query = s.query(User).filter(User.username.in_([team_id]))
        result = query.first()

        if not result:
            return abort(401)

        solved = []
        if result.solved != '':
            for problem_id in result.solved.split(','):
                solved.append(str(problem_id))

        visible = get_visible(solved, problems)
        # end check

        # TODO: edit the terms of what is valid later on
        print 'REQUEST:', prob_id, answer, team_id

        is_valid = answer != '' and prob_id in problems.keys()

        if not is_valid:
            return abort(400)

        is_allowed = prob_id in visible

        if not is_allowed:
            return abort(403)

        already_solved = prob_id in solved

        if already_solved:
            return abort(400)

        correct_answer = problems[prob_id]['answer']

        print 'correct answer:', correct_answer

        if validate_answer(answer, correct_answer):
            result.solved = ','.join(solved + [str(prob_id)])
            s.commit()
            return 'right'

        return 'wrong'
    else:
        print 'ERROR! /solve only accepts POST requests'

# attempt to get a question
@app.route('/question', methods=['POST'])
def get_question():

    if not session.get('logged_in'):
        return abort(401)

    if request.method == 'POST':
        prob_id = request.form['prob_id']

        print 'question request:', prob_id

        # check if team has access to question:
        team_id = session.get('team_id')

        Session = sessionmaker(bind=engine)
        s = Session()
        query = s.query(User).filter(User.username.in_([team_id]))
        result = query.first()

        if not result:
            return abort(401)

        solved = []
        if result.solved != '':
            for problem_id in result.solved.split(','):
                solved.append(str(problem_id))

        visible = get_visible(solved, problems)
        print 'visible:', visible
        # end check

        if prob_id not in problems.keys():
            return abort(404)

        if prob_id not in visible:
            return abort(403)

        prob = problems[prob_id]

        return '%s::%s::%s' % (prob['title'],
                               prob['question'],
                               prob['point_value'])
    else:
        print 'ERROR! /question only accepts POST requests'


@app.route('/reload_questions', methods=['GET'])
def reload_questions():
    if request.method == 'GET':

        if not session.get('logged_in'):
            return redirect(url_for('home'))

        team_id = session.get('team_id')

        if team_id == 'admin':
            global problems

            problems = json.load(open('./questions.json'))['problems']
            print problems

            return 'success - reloaded'
        else:
            return 'invalid'
    else:
        print 'ERROR! /reload_questions only accepts POST requests'


@app.route('/login', methods=['POST'])
def login():
    POST_USERNAME = str(request.form['username'])
    POST_PASSWORD = str(request.form['password'])

    Session = sessionmaker(bind=engine)
    s = Session()
    query = s.query(User).filter(User.username.in_([POST_USERNAME]))
    result = query.first()

    if result:
        salt = result.salt
        HASHED = hashlib.sha512(POST_PASSWORD + salt).hexdigest()
        print result.username
        print result.password
        print result.salt
        if HASHED == result.password:
            session['logged_in'] = True
            session['team_id'] = POST_USERNAME

    return home()

@app.route('/')
def home():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        return redirect(url_for('show_map'))

@app.route('/logout', methods=['POST'])
def logout():
    if session.get('logged_in'):
        session['logged_in'] = False
        session['team_id'] = None
    return home()

if __name__ == '__main__':
    app.secret_key = os.urandom(24)
    app.run(host='0.0.0.0', port=1234)
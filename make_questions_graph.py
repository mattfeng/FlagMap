import networkx as nx
import json

problems = json.loads(open('./questions.json').read())['problems']

G = nx.Graph()

def add_question(prob_id, title, question,
				 answer, point_value, unlocks):
	global G

	unlocks_str = '(' + ','.join(str(i) for i in unlocks) + ')'
	print unlocks_str

	label = '%s: %d' % (title, point_value)
	G.add_node(prob_id, label=label, title=title,
			   question=question, answer=answer,
			   point_value=point_value, unlocks=unlocks_str)

	for unlock in unlocks:
		G.add_edge(prob_id, unlock)

for prob in problems.values():
	prob_id = prob['prob_id']
	title = prob['title']
	question = prob['question']
	answer = prob['answer']
	point_val = prob['point_value']
	unlocks = prob['unlocks']
	print prob
	add_question(prob_id, title, question, answer, point_val, unlocks)

nx.write_gpickle(G, 'questions.gpickle')
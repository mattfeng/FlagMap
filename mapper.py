import networkx as nx
import json

def get_problem_info(prob_id, all_problems):
    problems = all_problems[str(prob_id)]
    return problems['title'], problems['point_value'], problems['unlocks']
    
def make_graph_from_solved(solved, all_problems):
    G = nx.Graph()

    if len(solved) == 0:
        title, point_value, unlocks = get_problem_info(1, all_problems)
        label = '%s: %d' % (title, point_value)
        G.add_node(1, label=label, point_value=point_value)

    for pid in solved:
        pid = int(pid) # needs to be int for proper duplication checking
        title, point_value, unlocks = get_problem_info(pid, all_problems)
        label = '%s: %d' % (title, point_value)

        if pid not in G.node.keys():
            print 'adding:', pid
            G.add_node(pid, label=label, point_value=point_value)

        for unlock in unlocks:
            unlock = int(unlock)
            title, point_value, unlocks = get_problem_info(unlock, all_problems)
            label = '%s: %d' % (title, point_value)
            if unlock not in G.node.keys():
                print 'adding:', unlock
                G.add_node(unlock, label=label, point_value=point_value)
            G.add_edge(pid, unlock)

    return G

def get_visible(solved, all_problems):
    visible = []
    visible.extend(solved)

    for pid in solved:
        title, point_value, unlocks = get_problem_info(pid, all_problems)
        visible.extend(unlocks)

    return list(set([str(i) for i in visible]))

if __name__ == '__main__':
    problems = json.load(open('./questions.json'))['problems']
    graph = make_graph_from_solved([1, 3], problems)
    nx.write_gpickle(graph, 'test.gpickle')
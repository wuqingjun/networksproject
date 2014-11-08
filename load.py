#!/usr/bin/python
from os import walk, path
from re import search
import networkx as nx
import matplotlib.pyplot as plt

# MAIL_REGEX = "([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}).*\r\n$"
ENRON_MAIL_REGEX = "([A-Za-z0-9._%+-]+@enron.com).*\r\n$"
LOC = "/path/to/enron_mail_20110402/maildir"

# read a file and emit from address and to address
def process_lines(fd):
    from_addr = None
    to_addr = None
    for line in fd.readlines():

        if from_addr is None:
            fr = search(r'^From: ' + ENRON_MAIL_REGEX, line)

            if fr:
                from_addr = fr.group(1).strip()
        if to_addr is None:
            to = search(r'^To: ' + ENRON_MAIL_REGEX, line)

            if to:
                to_addr = to.group(1).strip()

        if from_addr is not None and to_addr is not None: break

    return from_addr, to_addr

# open a file and process its content
def find_addrs(dirpath, fname):
    with open(path.join(dirpath, fname), 'r') as fd:
        return process_lines(fd)

# create graph
def print_graph(G):
    pos = nx.spring_layout(G)

    # nodes
    nx.draw_networkx_nodes(G,pos,
                                node_color='r',
                                node_size=500,
                                alpha=0.8)

    # edges
    nx.draw_networkx_edges(G,pos)

    # labels
    nx.draw_networkx_labels(G,pos)

    plt.axis('off')
    plt.savefig("project.png") # save as png
    plt.show() # display

def main():
    G = nx.Graph()

    # parse each file and add from/to addresses to graph
    for dirpath, dnames, fnames in walk(LOC):
        for fname in fnames:
            print fname
            from_addr, to_addr = find_addrs(dirpath, fname)

            if from_addr is not None:
                G.add_node(from_addr)
            if to_addr is not None:
                G.add_node(to_addr)

            # if email had from and to address, add an edge
            if from_addr is not None and to_addr is not None:
                if from_addr in G.neighbors(to_addr):
                    G[to_addr][from_addr]['weight'] += 1
                else:
                    G.add_edge(from_addr, to_addr, weight=1)

    # print_graph(G)

    print G.number_of_nodes(), G.number_of_edges()
    print G.nodes(data=True)
    print G.edges(data=True)

if __name__ == "__main__":
    main()

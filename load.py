#!/usr/bin/python
from os import walk, path
from re import search, compile, findall
from uuid import uuid4
import networkx as nx
import matplotlib.pyplot as plt
import collections

FROM_MAIL_REGEX = "([A-Za-z0-9._%+-]+@enron.com).*\r\n$"
LOC = "/path/to/enron_mail_20110402/maildir"
ENRON_MAIL_REGEX = compile(r'([A-Za-z0-9._%+-]+@enron.com)')

class Employee:
    id = ""
    first_name = ""
    last_name = ""
    middle_init = ""
    email_addresses = set()

    def __init__(self, first_name, middle_init, last_name):
        self.first_name = first_name
        self.middle_init = middle_init
        self.last_name = last_name
        self.id = uuid4()
        self.email_addresses = set()

    def add_email(self, email):
        self.email_addresses.add(email)

    def __repr__(self):
        return "%s, %s, %s, %s, %s" % (self.id, self.first_name, self.middle_init, self.last_name, self.email_addresses)

# read a file and emit from address and to address
def process_lines(fd):
    from_addr = None
    to_addr = None
    cc_addr = None

    for line in fd.readlines():

        if from_addr is None:
            fr = search(r'^From: ' + FROM_MAIL_REGEX, line)

            if fr:
                from_addr = fr.group(1).strip()
        if to_addr is None and line.startswith("To: "):
            to_addr = findall(ENRON_MAIL_REGEX, line)

        if cc_addr is None and line.startswith("Cc: "):
            cc_addr = findall(ENRON_MAIL_REGEX, line)

        if from_addr is not None and to_addr is not None and cc_addr is not None: break

    if to_addr is None:
        to_addr = []
    if cc_addr is None:
        cc_addr = []

    return from_addr, set(to_addr + cc_addr)

# open a file and process its content
def find_addrs(dirpath, fname):
    with open(path.join(dirpath, fname), 'r') as fd:
        return process_lines(fd)

# given an email in known forms, attempt to extract name
def extract_name(email):
    # check for 'john.h.smith@enron.com'
    full_re = search(r'^([A-Za-z]+)[.|_]([A-Za-z])[.|_]([A-Za-z]+)@enron.com$', email)
    if full_re:
        return full_re.group(1), full_re.group(2), full_re.group(3)

    # check for 'john.smith@enron.com'
    most_re = search(r'^([A-Za-z]+)[.|_]([A-Za-z]+)@enron.com$', email)
    if most_re:
        return most_re.group(1), None, most_re.group(2)

    # check for 'h..smith@enron.com'
    middle_re = search(r'^([A-Za-z])[.|_][.|_]([A-Za-z]+)@enron.com$', email)
    if middle_re:
        return None, middle_re.group(1), middle_re.group(2)

    return None, None, None

# create graph
def print_graph(G):
    pos = nx.spring_layout(G)

    # nodes
    nx.draw_networkx_nodes(G,pos,
                                node_color='r',
                                node_size=10,
                                alpha=0.8)

    # edges
    nx.draw_networkx_edges(G,pos)

    # labels
    # nx.draw_networkx_labels(G,pos)

    plt.axis('off')
    plt.savefig("project.png") # save as png
    plt.show() # display

def disambig_email_and_add(G, m, email):
    first_name, middle_init, last_name = extract_name(email)

    # if last name not found, persona could not be extracted
    if last_name is None:
        alias_re = search(r'^([A-Za-z]+)@enron.com$', email)
        if alias_re:
            alias = alias_re.group(1)
            first_name_init = alias[0]
            last_name = alias[1:]
        else:
            G.add_node(email)
            return email

    # if persona could be tied to existing employee, add this email address
    if m.has_key(last_name):
        for employee in m[last_name]:
            if middle_init is not None and first_name is not None: # match 'john.h.smith'
                if employee.middle_init is not None and employee.middle_init != middle_init: continue
                if employee.first_name is not None and employee.first_name != first_name: continue

                employee.middle_init = middle_init
                employee.first_name = first_name
                employee.add_email(email)
                return employee.id
            elif first_name is not None and middle_init is None: # match 'john.smith'
                if employee.first_name is not None and employee.first_name != first_name: continue

                employee.first_name = first_name
                employee.add_email(email)
                return employee.id
            elif first_name is None and middle_init is not None: # match 'h..smith'
                if employee.middle_init is not None and employee.middle_init != middle_init: continue

                employee.middle_init = middle_init
                employee.add_email(email)
                return employee.id
            elif first_name_init is not None: # match 'jsmith'
                if employee.first_name is not None and employee.first_name[0] != first_name_init: continue

                employee.add_email(email)
                return employee.id

    e = Employee(first_name, middle_init, last_name)
    e.add_email(email)
    if m.has_key(last_name):
        m[last_name] += [(e)]
    else:
        m[last_name] = [(e)]

    G.add_node(e.id)

    return e.id

def main():
    G = nx.Graph()
    m = {}

    # parse each file and add from/to/cc addresses to graph
    for dirpath, dnames, fnames in walk(LOC):
        for fname in fnames:
             # extract from addr and list of to/cc addrs
            from_addr, to_addr = find_addrs(dirpath, fname)

            # convert from addr to appropriate id
            if from_addr is not None:
                from_addr_id = disambig_email_and_add(G, m, from_addr)
            else:
                from_addr_id = None

            # evaluate each to/cc addr from this sender
            if to_addr is None: continue

            for indiv_to_addr in to_addr:
                to_addr_id = disambig_email_and_add(G, m, indiv_to_addr)

                # if email had from and to address, add an edge
                if from_addr_id is None or to_addr_id is None: continue

                if from_addr_id in G.neighbors(to_addr_id):
                    G[to_addr_id][from_addr_id]['weight'] += 1
                else:
                    G.add_edge(from_addr_id, to_addr_id, weight=1)

    # print_graph(G)

    print 'components'
    print nx.number_connected_components(G)
    subgraphs = sorted(nx.connected_component_subgraphs(G), key = len, reverse=True)
    print 'giant component nodes, edges'
    print subgraphs[0].number_of_nodes(), subgraphs[0].number_of_edges()
    print 'giant component diameter'
    print nx.diameter(subgraphs[0])

    # m = collections.OrderedDict(sorted(m.items()))
    # for key, value in m.iteritems():
    #     print key, value
    #
    # print G.number_of_nodes(), G.number_of_edges()
    # for node in G.nodes(data=True):
    #     print node, G.degree(node[0])

    # print G.edges(data=True)

if __name__ == "__main__":
    main()

import itertools
import timeit
from collections import defaultdict
import networkx as nx
import pprint
import re


def actor_movie_graph(file_directory):

    actor_count = 0
    movie_count = 0
    actor_dict = {}
    movie_dict = {}
    imdb_graph = nx.Graph()

    with open(file_directory) as file:

        for line in file:
            line = line.split("\t")  # l contains array [actor, movie] created from line

            if line[0] not in actor_dict.keys():  # if actor hasn't been considered before
                actor_id = "a-" + str(actor_count)  # create actor id
                actor_dict[line[0]] = actor_id  # add new entry in dict with actor's name as key and number-id as value
                imdb_graph.add_node(actor_id, name=line[0], type="actor")  # create new node in graph
                actor_count += 1  # update counter

            else:  # actor already added to graph
                actor_id = actor_dict[line[0]]  # retrieve actor's id

            if line[1] not in movie_dict.keys():  # if movie hasn't been considered before
                movie_id = "m-" + str(movie_count)  # create movie id
                movie_dict[line[1]] = movie_id  # add new entry in dict with movie's name as key and number-id as value
                movie_year = re.findall(r"^.*?\((\d{4})[^\d]*\).*$",
                                        line[1])  # extract 4-digit number between parentheses
                if movie_year:  # check if regex match is not empty
                    movie_year = int(movie_year[0])  # convert string to int
                else:
                    movie_year = None  # not every movie has a year
                imdb_graph.add_node(movie_id, name=line[1], type="movie",
                                    year=movie_year)  # create new node in graph
                movie_count += 1  # update counter
            else:  # movie already added to graph
                movie_id = movie_dict[line[1]]  # retrieve movie's id

            imdb_graph.add_edge(actor_id, movie_id)  # add new edge to the graph

    print("Actors: \n")
    pprint.pprint(len(actor_dict.keys()))
    print("\n Movies: \n")
    pprint.pprint(len(movie_dict.keys()))
    print(imdb_graph)
    return imdb_graph, actor_dict, movie_dict


def prolific_actor_by_year(graph, actor_dict, year_range):

    # Results are stored in a dictionary with year as key and tuples (number of movies, actor id) as values
    total_max = {}
    for year in year_range:
        total_max[year] = (0, "")

    for actor_node in actor_dict.values():

        actor_movie_counter = {}  # create a dictionary to store how many movies each actor_node has filmed
        for year in year_range:  # considering only the ones made up to year x
            actor_movie_counter[year] = 0

        for movie_node in graph.adj[actor_node]:  # check every movie the actor participated in
            movie_year = graph.nodes[movie_node]["year"]
            if movie_year is not None:  # skip movies with no year
                for year in year_range:  # count movies considering increasing year range
                    if movie_year <= year:
                        actor_movie_counter[year] += 1

        for year in year_range:  # check max considering increasing year range
            if actor_movie_counter[year] > total_max[year][0]:
                total_max[year] = (actor_movie_counter[year], actor_node)

    return total_max


def max_shared_cast(graph, movie_dict):

    max_shared_cast = 0
    movie_pair = ()
    movie_list = list(movie_dict.values())  # list of all the movies' id
    discarded = set()  # contains all movies that don't need to be checked again

    for i in range(len(movie_list) - 1):  # check every movie in the list but the last one

        if movie_list[i] not in discarded:
            cast = set(graph.adj[movie_list[i]])

            if len(cast) > max_shared_cast:
                for j in range(i + 1, len(movie_list)):  # check every other movie in the rest of the list

                    if movie_list[j] not in discarded:
                        other_cast = set(graph.adj[movie_list[j]])

                        if len(other_cast) > max_shared_cast:
                            shared_cast = len(cast.intersection(other_cast))

                            if shared_cast > max_shared_cast:
                                max_shared_cast = shared_cast
                                movie_pair = (movie_list[i], movie_list[j])

                        else:  # discard  if j-th movie's cast is too small
                            discarded.add(movie_list[j])

            else:    # discard if i-th movie's cast is too small
                discarded.add(movie_list[i])

    return movie_pair, max_shared_cast


def bfs_tree_ecc(graph, source):

    gray_nodes = {}  # dictionary to store for each node the distance from source
    layers = defaultdict(list)  # each entry contains a list of nodes at distance key
    current_dis = 0
    # initialize dictionaries with source values
    q = [source]
    gray_nodes[source] = current_dis
    layers[current_dis] = [source]
    # classic BFS implementation
    while len(q) > 0:
        current_node = q.pop(0)
        current_dis = gray_nodes[current_node]
        for neighbour in list(graph.adj[current_node]):
            if neighbour not in gray_nodes:
                q.append(neighbour)
                gray_nodes[neighbour] = current_dis + 1
                layers[current_dis + 1].append(neighbour)

    ecc = current_dis
    return layers, ecc


def bounded_diameter(graph):

    # find the highest degree node in the graph
    max_connections = 0
    source = None
    for node in graph.nodes:
        if len(graph.adj[node]) > max_connections:
            max_connections = len(graph.adj[node])
            source = node

    layers, ecc = bfs_tree_ecc(graph, source)
    lb = 0
    bfs_count = 1
    for i in range(ecc, 0, -1):
        F_i = layers[i]
        B_i = 0
        for node in F_i:
            ecc_i = max(nx.single_source_shortest_path_length(graph, node).values()) # eccentricity
            # _, ecc_i = bfs_tree_ecc(graph, node)  # eccentricity
            bfs_count += 1
            if ecc_i > B_i:
                B_i = ecc_i
        if lb > 2 * (i - 1):  # lower bound > upper bound
            print(f"Number of BFS: {bfs_count}")
            break
        elif lb < B_i:
            lb = B_i

    return lb


def actor_graph(graph, movie_dict, act_dict):

    """
    Builds a weighted graph, where the weight of an edge represents how many times two actors have worked together.
    :param graph:
        A networkx graph
    :param movie_dict:
    :param act_dict:
    :return: graph
        actors' graph
    """

    actors_graph = nx.Graph()

    actors_graph.add_nodes_from(act_dict.values)  # create a node for every actor

    for movie_id in movie_dict.values():  # iterate over movies in the graph
        cast = list(graph.adj[movie_id])
        if len(cast) > 1:
            for pair in itertools.combinations(cast, 2):  # consider all possible combinations of pairs of actors
                if actors_graph.has_edge(pair[0], pair[1]):
                    actors_graph.edges[pair[0], pair[1]]["weight"] += 1  # increase edge weight
                else:
                    actors_graph.add_edge(pair[0], pair[1], weight=1)  # add edge with unitary weight

    return actors_graph


def subgraph_by_year(graph, year_cutoff):

    if year_cutoff == 2020:
        subgraph = graph
    else:
        nodes_list = []
        for node, att_dict in graph.nodes.items():
            if att_dict["type"] == "actor":
                nodes_list.append(node)
            elif att_dict["type"] == "movie":
                if att_dict["year"] is None or att_dict["year"] <= year_cutoff:
                    nodes_list.append(node)

        subgraph = nx.Graph(graph.subgraph(nodes_list))

        subgraph.remove_nodes_from(list(nx.isolates(subgraph)))

    return subgraph


if __name__ == '__main__':

    ### Create Graph ###

    file_directory = "imdb-actors-actresses-movies.tsv"
    imdb_graph, act_dict, movie_dict = actor_movie_graph(file_directory)

    year_range = {1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020}

    ### Question C:

    # print(" Which is the actor who did more movies, considering only the movies up to year x with x in"
    #       "{1930,1940,1950,1960,1970,1980,1990,2000,2010,2020}?")
    # pprint.pprint(prolific_actor_by_year(imdb_graph, act_dict, year_range))

    ### Question 1:

    print("Considering only the movies up to year x with x in {1930,1940,1950,1960,1970,1980,1990,2000,2010,2020} "
          "and restricting to the largest connected component of the graph, \n compute exactly the diameter of G")
    for year in year_range:
        print(year)
        subgraph = subgraph_by_year(imdb_graph, year)
        d = bounded_diameter(subgraph)
        print(f"Diameter ({year}): {d}")

    ### Question III:

    # print("Which is the pair of movies that share the largest number of actors?")
    # movie_pair, max_shared_cast = max_shared_cast(imdb_graph, movie_dict)
    # print(f"The movies {movie_pair} share {max_shared_cast} actors")

    ### Question 4:

    # print("Build the actor graph, whose nodes are only actors and two actors are connected if they did a movie together")
    # act_graph = actor_graph(imdb_graph, movie_dict, act_dict)
    #
    # print("Which is the pair of actors who collaborated the most among themselves?")
    #
    # # Find the heaviest edge in the graph
    # max_weight = 0
    # pair = None
    # for u, v, att in g.edges(data=True):
    #     if att["weight"] > max_weight:
    #         max_weight = att["weight"]
    #         pair = (u, v)
    #
    # print(f"The pair {pair} worked together {max_weight} times")




# encoding: utf-8
"""
CCMHistoryGraph.py

Graph representation of Synergy History

Created by Aske Olsson 2010-12-10.
Copyright (c) 2010 Aske Olsson. All rights reserved.
"""

import FileObject
import TaskObject
import cPickle
from datetime import datetime
from operator import itemgetter, attrgetter
from pygraph.classes.digraph import digraph 
from pygraph.classes.hypergraph import hypergraph 


class CCMHistoryGraph(object):
    """ Create a graph object of tasks and objects from a ccm release"""
    def __init(self, release):
        pass
        
    def find_objects_without_associated_tasks(self, objects, tasks):
        objects_from_tasks = []
        # compare objects in the tasks with objects in release, to see if there is any single objects
        objects_from_tasks = [o for task in tasks for o in task.get_objects()]
        single_objects = [o for o in objects if o not in objects_from_tasks]
        return single_objects    
    
    
    def create_graphs(self, release, previous_release):
        tasks = release['tasks']
        objects = release['objects']
        
        object_graph = self.create_object_graph(objects)
        task_graph = self.create_task_graph(task, objects)
        release_graph = create_release_graph(objects, release['name'], release['previous');
        commit_graph = self.create_commits_graph(object_graph, task_graph)
        
        
    def create_commits_graph(self, object_graph, task_graph, release_graph):
        commit_graph = digraph()
        
        [commit_graph.add_node(task) for task in task_graph.edges()]
        [commit_graph.add_node(release) for release in release_graph.edges()]
                
        # Create the edges from the tasks to the releases
        [commit_graph.add_edge((task, release)) for (release, task) in product(release_graph.edges(), task_graph.edges()) if set(release_graph.links(release)) & set(task_graph.links(task))]
        
        # Create the edges from tasks to tasks and from releases to tasks    
        for (t1, t2) in [(t1, t2) for (t1, t2) in permutations(task_graph.edges(), 2)]:
            for (obj1, obj2) in [(obj1, obj2) for (obj1, obj2) in product(task_graph.links(t1), task_graph.links(t2)) if (obj1, obj2) in object_graph.edges()]:
                for release in release_graph.edges():
                    if commit_graph.has_edge((t1, release)):
                        if not commit_graph.has_edge((release, t2)):
                            commit_graph.add_edge((release, t2))
                        break
                else:
                    if not commit_graph.has_edge((t1, t2)):        
                        commit_graph.add_edge((t1, t2))
                    
        return commit_graph        
        
        
    def create_release_graph(self, objects, release, previous):
        release_graph = hypergraph()
        release_graph.add_nodes(objects)
        release_graph.add_edges([release, previous])
        
        object_names = [o.get_object_name() for o in objects]
        for o in objects:
            # Bind objects to this release
            if o.get_successors() is None:
                release_graph.link(o, release)

            # Bind objects to previous release
            predecessors = o.get_predecessors()
            for p in predecessors:
                if p not in object_names:
                    release_graph.link(o,previous)

        return release_graph
        
        
    def create_task_graph(self, tasks, objects):
        task_graph = hypergraph()
        task_graph.add_nodes(objects)
        task_graph.add_hyperedges(tasks)
        #link the objects and the tasks
        for t in tasks:
            for o in t.get_objects():
                #There might be objects associated with the task, that is outside the project scope... gotta love Synergy
                if o in objects:
                    task_graph.link(o, t)
        # Add single_objects to task_graph
        for o in self.find_objects_without_associated_tasks(objects, tasks):
            task_graph.add_hyperedge(o)
            task_graph.link(o, o)
            
        return task_graph
        
    def sanitize_tasks(task_graph):
        common_objects = [(t1, t2, set(task_graph.links(t1)) & set(task_graph.links(t2))) 
                          for (t1, t2) in combinations(task_graph.edges(), 2) 
                          if set(task_graph.links(t1)) & set(task_graph.links(t2))]
        
        for (t1, t2, common_objs) in common_objects:
            for obj in common_objs:
                task_graph.unlink(obj, t1)
                task_graph.unlink(obj, t2)
                
                task_name = obj.get_object_name()            
                task_graph.add_edge(task_name)
                task_graph.link(obj, task_name)
                
        return tasks        
        
    def create_object_graph(self, objects):
        # create dict to map objectname to file object
        mapped_objects = {}
        for o in objects:
            mapped_objects[o.get_object_name()] = o
        object_graph = digraph()
        object_graph.add_nodes(objects)        
        # Create relationship list 
        successors = [(i, [] if i.get_successors() is None else [mapped_objects[j] for j in i.get_successors()] ) for i in objects]
        #   
        for obj, suc in successors:
            for s in suc:
                object_graph.add_edge((obj, s))
                
        return object_graph
        
    
    
def main():
    #
    #print "Creating graph..."
    #graph = CCMHistoryGraph();
    #graph.create_graphs(release)
    f = open('history.p', 'rb')
    releases = cPickle.load(f)
    ccm_graph = CCMHistoryGraph()
    object_graph = ccm_graph.create_object_graph(releases['s30_11w03_sb9_fam']['objects'])
    task_graph = ccm_graph.create_task_graph(releases['s30_11w03_sb9_fam']['tasks'], releases['s30_11w03_sb9_fam']['objects'])

if __name__ == '__main__':
    main()

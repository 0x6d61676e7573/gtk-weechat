import pickle
import os

class State():
    """Class to save and restore application state information."""
    def __init__(self, filename):
        self.filename=filename
        self.data={"expanded":[], "active":""}

    def dump_to_file(self):
        """Saves state information to file. """
        with open(self.filename, "wb") as f:
            pickle.dump(self.data,f)
            
    def load_from_file(self):
        """Reads state information from file. Returns True if file exists."""
        if not os.path.isfile("./"+self.filename):
            return False
        with open(self.filename, "rb") as f:
            self.data=pickle.load(f)
            return True

    def set_expanded_nodes(self, node_ptr_list):
        """ Stores a list of pointers to expanded nodes. """
        self.data["expanded"]=node_ptr_list

    def set_active_node(self, node_ptr):
        """ Stores pointer to active node. """
        self.data["active"]=node_ptr

    def get_active_node(self):
        """ Returns pointer to last active buffer. """
        return self.data["active"]

    def get_expanded_nodes(self):
        """ Returns list of pointers to all expanded nodes. """
        return self.data["expanded"]

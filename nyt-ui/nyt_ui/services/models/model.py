
class Model(object):
    """
    Costum model class object
    """
    def __init__(self) -> None:
        pass

    def load_from_dict(self, dict_: dict) -> None:
        """
        Loads the model from a dict object.

        Args:
            dict_ (dict): A dict containing the model's attribute's values.

        Returns:
            None.
        """
        for att in self.__annotations__:
            setattr(self, att, dict_[att])

        return self
    
    def dump_dict(self) -> None:
        """
        Dumps the model into a dict object.

        Args:
            None.

        Returns:
            dict: The dict object containing the model.
        """
        res = {}

        for att in self.__annotations__:
            res[att] = getattr(self, att)
        
        return res

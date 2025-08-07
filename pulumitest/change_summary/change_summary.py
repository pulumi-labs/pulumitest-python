from pulumi import automation as auto
from typing import Self

class ChangeSummary():
    def __init__(self, op_map: auto.events.OpMap):
        self.change_summary = op_map

    def where_op_not_equals(self, *op_types: auto.events.OpType):
        return dict(filter(lambda item: item[0] not in op_types, self.change_summary.items()))

    def where_op_equals(self, *op_types: auto.events.OpType):
        return dict(filter(lambda item: item[0] in op_types, self.change_summary.items()))
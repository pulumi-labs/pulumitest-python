from pulumi import automation as auto
from typing import Self

class ChangeSummary():
    def __init__(self, op_map: auto.events.OpMap):
        self.change_summary = op_map

    def where_op_not_equals(self, *op_types: auto.events.OpType):
        return dict(filter(lambda item: item[0] not in op_types, self.change_summary.items()))

    def where_op_equals(self, *op_types: auto.events.OpType):
        return dict(filter(lambda item: item[0] in op_types, self.change_summary.items()))

    def count_op(self, op_type: auto.events.OpType) -> int:
        """
        Get the count of operations for a specific operation type.

        Args:
            op_type: The operation type to count (e.g., OpType.UPDATE, OpType.CREATE)

        Returns:
            Count of operations for the given type, or 0 if no operations of that type
        """
        return self.change_summary.get(op_type, 0)
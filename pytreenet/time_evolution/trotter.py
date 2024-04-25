"""
This module provides all classes required to define arbitrary trotterisations.

A trotterisation is a splitting of an operator/matrix exponential into factors
even though the exponents are non-commuting. This does cause an error.
"""
from __future__ import annotations
from typing import List, Union, Tuple

from ..operators.operator import NumericOperator
from ..operators.tensorproduct import TensorProduct
from ..operators.common_operators import swap_gate
from ..core.ttn import TreeTensorNetwork

class SWAPlist(list):
    """
    A list of symbolic SWAP gates.

    As the name suggests a SWAP gates swaps the state of two neighbouring
    nodes. This class represents a list of such SWAP gates. It is used to
    represent a consecutive application of SWAPs of neighbouring nodes.
    """

    def __init__(self, swap_list = None):
        """
        Initialise a SWAPlist.

        Args:
            swap_list (List[Tuple[str, str]], optional): A list of pairs of
                node names that should be swapped. Only neigbouring nodes with
                the same open leg dimension can be swapped. The order of the
                identifiers in the pair is the order in which the legs of the
                resulting SWAP tensor are ordered.
        """
        for pair in swap_list:
            if not len(pair) == 2:
                raise ValueError("SWAPs can only happen between exactly two nodes!")
        if swap_list is None:
            swap_list = []
        list.__init__(self, swap_list)

    def is_compatible_with_ttn(self, ttn: TreeTensorNetwork) -> bool:
        """
        Returns, if a SWAPlist is compatible with a given TreeTensorNetwork.

        This means it checks if all nodes in the SWAP-list are actually
        neighbours with the same open leg dimension.

        Args:
            ttn (TreeTensorNetwork): A TTN for which to check compatability.

        Returns:
            bool: True if the SWAPlist is compatible with the TTN and False,
                if not.
        """
        for swap_pair in self:
            # Check if the first swap node is in the TTN
            if swap_pair[0] not in ttn.nodes:
                return False
            # If it is check, if the other is actually connected and thus also
            #  in the TTN
            node1 = ttn.nodes[swap_pair[0]]
            if not swap_pair[1] not in node1.neighbouring_nodes():
                return False
            # Finally check if both have the same total physical dimension.
            node2 = ttn.nodes[swap_pair[1]]
            if node1.open_dimension() != node2.open_dimension():
                return False
        return True

    def into_operators(self,
                       ttn: Union[TreeTensorNetwork, None] = None,
                       dim: Union[int, None] = None) -> List[NumericOperator]:
        """
        Turns the list of abstract swaps into a list of numeric operators.

        Args:
            ttn (TreeTensorNetwork): A tree tensor network from which the
                dimensions can be determined. Default to None.
            dim (Union[int, None], optional): Can be given, if all nodes that
                have to be swapped have the same dimension. Defaults to None.

        Returns:
            List[NumericOperator]: A list of numeric operators corresponding to the
             swaps defined in this instance.

        Raises:
            ValueError: If ttn and dim are both None.
        """
        if ttn is None and dim is None and len(self) != 0:
            errstr = "`ttn` and `dim` cannot both be `None`!"
            raise ValueError(errstr)
        operator_list = []
        if dim is not None:
            swap_matrix = swap_gate(dimension=dim)
        for swap_pair in self:
            if ttn is not None:
                dim = ttn.nodes[swap_pair[0]].open_dimension()
                swap_matrix = swap_gate(dimension=dim)
            swap_operator = NumericOperator(swap_matrix, list(swap_pair))
            swap_operator = swap_operator.to_tensor(dim=dim, ttn=ttn)
            operator_list.append(swap_operator)
        return operator_list

class TrotterStep:
    """
    A single trotter step of a trotterisation.

    A trotterisation splits a multi term exponent into multiple smaller
    operator exponents inccurring an error. A single trotter step is one
    such smaller operator, including swap gates before and after the
    exponented operator.
    
    Attributes:
        operator (TensorProduct): The operator that should become the exponent.
        factor (float): A factor to be included in the exponent.
        swaps_before (Swaplist): The swaps that should occur, before the
            exponentiated operator is applied.
        swaps_after (Swaplist): The swaps that should occur, after the
            exponentiated operator is applied.
    """

    def __init__(self,
                 operator: TensorProduct,
                 factor: float,
                 swaps_before: Union[SWAPlist,None] = None,
                 swaps_after: Union[SWAPlist,None] = None):
        """
        Initialise a single trotter step.

        Args:
            operator (TensorProduct): The operator that should become the
                exponent of this trotter step. The operators should be numeric
                arrays and not symbolic strings.
            factor (float): A factor to be included in the exponent.
            swaps_before (Union[Swaplist,None]): The swaps that should occur,
                before the exponentiated operator is applied. Defaults to None,
                meaning no swap gates will be applied.
            swaps_after (Union[Swaplist,None]): The swaps that should occur,
                after the exponentiated operator is applied. Defaults to None,
                meaning no swap gates will be applied. 
        """
        self.operator = operator
        self.factor = factor
        if swaps_before is None:
            self.swaps_before = SWAPlist()
        else:
            self.swaps_before = swaps_before
        if swaps_after is None:
            self.swaps_after = SWAPlist()
        else:
            self.swaps_after = swaps_after

    def exponentiate_operator(self,
                              delta_time: float,
                              ttn: Union[TreeTensorNetwork,None] = None,
                              dim: Union[int,None] = None) -> NumericOperator:
        """
        Exponentiates the operator part of this trotter step.

        Args:
            delta_time (float): The time factor that should be multiplied
                to the exponent operator.
            dim (Union[int, None], optional): If all nodes have the same open
                dimension it can be given here. Defaults to None.
            ttn (Union[TreeTensorNetwork, None], optional): If not all nodes
                have the same open dimension a TTN is needed as a reference.
                Defaults to None.
        """
        factor = -1j * self.factor * delta_time
        exponentiated_operator = self.operator.exp(factor)
        exponentiated_operator = exponentiated_operator.to_tensor(dim=dim, ttn=ttn)
        return exponentiated_operator

    def realise_swaps(self,
                      ttn: Union[TreeTensorNetwork,None] = None,
                      dim: Union[int,None] = None) -> Tuple[List[NumericOperator],List[NumericOperator]]:
        """
        Turns the SWAP gates into numeric operators.

        The gates are only saved with a simplified representation. This
        method turns them into actual gates.

        Args:
            dim (Union[int, None], optional): If all nodes have the same open
                dimension it can be given here. Defaults to None.
            ttn (Union[TreeTensorNetwork, None], optional): If not all nodes
                have the same open dimension a TTN is needed as a reference.
                Defaults to None.
        """
        swap_tensors_before = self.swaps_before.into_operators(ttn,dim)
        swap_tensors_after = self.swaps_after.into_operators(ttn,dim)
        return swap_tensors_before, swap_tensors_after

class TrotterSplitting:
    """
    A trotter splitting allows the approximate breaking of exponentials of operators.
     Different kinds of splitting lead to different error sizes.
    """

    def __init__(self, tensor_products: List[TensorProduct],
                 splitting: Union[List[Tuple[int, int], int], None] = None,
                 swaps_before: Union[List[SWAPlist], None] = None,
                 swaps_after: Union[List[SWAPlist], None] = None):
        """Initialises a TrotterSplitting instance.

        Args:
            tensor_products (List[TensorProduct]): The tensor_products to be considered.
            splitting (Union[List[Tuple[int, int], int], None], optional): Gives the order
             of the splitting. The first tuple entry is a the index of an operator in
             operators and the second entry is a factor, which will be multiplied to the
             operator once exponentiated. If only an integer is given, it is assumed to be
             the index in the operator list and the factor is set to 1. In case of no given
             splitting the splitting is assumed to be in the order as given in the operator
             list and all factors are set to 1. Defaults to None.
            swaps_before (Union[List[SWAPlist], None], optional): The swaps to be applied
             before an exponentiated operator is applied. The indices are the same as in the
             splitting. So the SWAP gates given with index `i` will be applied before the
             operator specified with the `i`th element of splitting happens. Defaults to None.
            swaps_after (Union[List[SWAPlist], None], optional): The swaps to be applied
             after an exponentiated operator is applied. The indices are the same as in the
             splitting. So the SWAP gates given with index `i` will be applied after the
             operator specified with the `i`th element of splitting happens. Defaults to None.

        Raises:
            TypeError: Raised if the splitting contains unallowed types.
        """
        self.tensor_products = tensor_products

        if splitting is None:
            # Default splitting
            self.splitting = [(index, 1) for index in range(len(tensor_products))]
        else:
            self.splitting = []
            for item in splitting:
                if isinstance(item, int):
                    self.splitting.append((item, 1))
                elif isinstance(item, tuple):
                    self.splitting.append(item)
                else:
                    errstr = "Items in the `splitting` list may only be int or tuple with length 2!"
                    raise TypeError(errstr)

        if swaps_before is None:
            self.swaps_before = [SWAPlist([])] * len(self.splitting)
        else:
            self.swaps_before = swaps_before
        if swaps_after is None:
            self.swaps_after = [SWAPlist([])] * len(self.splitting)
        else:
            self.swaps_after = swaps_after

    def exponentiate_splitting(self, delta_time: float, ttn: TreeTensorNetwork = None,
                               dim: Union[int, None] = None) -> List[NumericOperator]:
        """
        Computes all operators, which are to actually be applied in a time-
        evolution algorithm. This includes SWAP gates and exponentiated
        operators.

        Parameters
        ----------
        delta_time : float
            The time step size for the trotter-splitting.
        ttn : TreeTensorNetwork
            A TTN which is compatible with this splitting.
            Provides the required dimensionality for the SWAPs.
        dim : int, optional
            If all nodes have the same physical dimension, it can be provided
            here. Speeds up the computation especially for big TTN.
            The default is None.

        Returns
        -------
        unitary_operators : list of Operator
            All operators that make up one time-step of the Trotter splitting.
             They are to be applied according to their index order in the list.
             Each operator is either a SWAP-gate or an exponentiated operator
             of an evaluated tensor product.
            """

        unitary_operators = [] # Includes the neccessary SWAPs
        for i, split in enumerate(self.splitting):
            tensor_product = self.tensor_products[split[0]]
            factor = -1j * split[1] * delta_time
            exponentiated_operator = tensor_product.exp(factor)
            exponentiated_operator = exponentiated_operator.to_tensor(dim=dim, ttn=ttn)

            # Build required swaps for befor trotter tensor_product
            swaps_before = self.swaps_before[i].into_operators(ttn=ttn, dim=dim)
            # Build required swaps for after trotter tensor_product
            swaps_after = self.swaps_after[i].into_operators(ttn=ttn, dim=dim)

            # Add all operators associated with this tensor_product to the list of unitaries
            unitary_operators.extend(swaps_before)
            unitary_operators.append(exponentiated_operator)
            unitary_operators.extend(swaps_after)
        return unitary_operators

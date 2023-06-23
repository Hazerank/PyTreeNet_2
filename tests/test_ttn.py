import unittest
import pytreenet as ptn
import numpy as np


class TestTreeTensorNetworkBasics(unittest.TestCase):

    def setUp(self):
        self.tensortree = ptn.TreeTensorNetwork()
        self.node1, self.tensor1 = ptn.random_tensor_node((2, 3, 4, 5), identifier="orig_root")
        self.node2, self.tensor2 = ptn.random_tensor_node((2, 3), identifier="child1")
        self.node3, self.tensor3 = ptn.random_tensor_node((2, 3, 4, 5), identifier="child2")
        self.node4, self.tensor4 = ptn.random_tensor_node((2, 3, 4, 5), identifier="new_root")

    def test_add_root(self):
        self.assertEqual(self.tensortree.root_id, None)
        self.assertEqual(self.tensortree.nodes, {})

        self.tensortree.add_root(self.node1, self.tensor1)

        self.assertEqual(self.tensortree.root_id, "orig_root")
        self.assertEqual(len(self.tensortree.nodes), 1)
        self.assertEqual(len(self.tensortree.tensors), 1)

    def test_add_child_to_parent(self):
        self.tensortree.add_root(self.node1, self.tensor1)

        # Depth 2
        self.tensortree.add_child_to_parent(self.node2, self.tensor2, 1, "orig_root", 1)
        self.assertEqual(len(self.tensortree.nodes), 2)
        permutation = self.tensortree.nodes["child1"].leg_permutation
        transposed_tensor = self.tensor2.transpose(permutation)
        self.assertTrue(np.allclose(self.tensortree.tensors["child1"], transposed_tensor))
        self.assertEqual(self.tensortree.nodes["child1"].parent, "orig_root")
        self.assertEqual(self.tensortree.nodes["child1"].children, [])
        self.assertEqual(self.tensortree.nodes["orig_root"].children, ["child1"])

        # Depth 3
        self.tensortree.add_child_to_parent(self.node3, self.tensor3, 0, "child1", 0)
        self.assertEqual(len(self.tensortree.nodes), 3)
        permutation = self.tensortree.nodes["child2"].leg_permutation
        transposed_tensor = self.tensor3.transpose(permutation)
        self.assertTrue(np.allclose(self.tensortree.tensors["child2"], transposed_tensor))
        self.assertEqual(self.tensortree.nodes["child2"].parent, "child1")
        self.assertEqual(self.tensortree.nodes["child2"].children, [])
        self.assertEqual(self.tensortree.nodes["child1"].children, ["child2"])

    def test_add_parent_to_root(self):
        # Setup
        self.tensortree.add_root(self.node1, self.tensor1)
        self.tensortree.add_child_to_parent(self.node2, self.tensor2, 1, "orig_root", 1)
        self.tensortree.add_child_to_parent(self.node3, self.tensor3, 0, "child1", 0)

        self.tensortree.add_parent_to_root(0, self.node4, self.tensor4, 0)
        self.assertEqual(self.tensortree.root_id, "new_root")
        self.assertEqual(len(self.tensortree.nodes), 4)
        permutation = self.tensortree.nodes["new_root"].leg_permutation
        transposed_tensor = self.tensor4.transpose(permutation)
        self.assertTrue(np.allclose(self.tensortree.tensors["new_root"], transposed_tensor))
        self.assertEqual(self.tensortree.nodes["new_root"].parent, None)
        self.assertEqual(self.tensortree.nodes["new_root"].children, ["orig_root"])
        self.assertEqual(self.tensortree.nodes["orig_root"].parent, "new_root")

class TestTreeTensorNetworkBigTree(unittest.TestCase):
    def setUp(self):
        self.tensortree = ptn.TreeTensorNetwork()

        node1, tensor1 = ptn.random_tensor_node((2, 3, 4, 5), identifier="id1")
        node2, tensor2 = ptn.random_tensor_node((2, 3, 4, 5), identifier="id2")
        node3, tensor3 = ptn.random_tensor_node((2, 3, 4, 5), identifier="id3")
        node4, tensor4 = ptn.random_tensor_node((2, 3, 4, 5), identifier="id4")
        node5, tensor5 = ptn.random_tensor_node((2, 3, 4, 5), identifier="id5")
        node6, tensor6 = ptn.random_tensor_node((2, 3, 4, 5), identifier="id6")
        node7, tensor7 = ptn.random_tensor_node((2, 3, 4, 5), identifier="id7")
        node8, tensor8 = ptn.random_tensor_node((2, 3, 4, 5), identifier="id8")
        node9, tensor9 = ptn.random_tensor_node((2, 3, 4, 5), identifier="id9")

        self.tensortree.add_root(node1, tensor1)
        self.tensortree.add_child_to_parent(node2, tensor2, 0, "id1", 0)
        self.tensortree.add_child_to_parent(node3, tensor3, 3, "id2", 3)
        self.tensortree.add_child_to_parent(node4, tensor4, 0, "id3", 0)
        self.tensortree.add_child_to_parent(node5, tensor5, 2, "id2", 2)
        self.tensortree.add_child_to_parent(node6, tensor6, 0, "id5", 0)
        self.tensortree.add_child_to_parent(node7, tensor7, 1, "id5", 1)
        self.tensortree.add_child_to_parent(node8, tensor8, 1, "id1", 1)
        self.tensortree.add_child_to_parent(node9, tensor9, 2, "id8", 2)

    def test_tensor_contraction_leaf_only_child(self):
        self.tensortree.contract_nodes("id8", "id9")
        contracted_node, contracted_tensor = self.tensortree["id8contrid9"]

        # Test Node
        self.assertTrue(isinstance(contracted_node, ptn.LegNode))
        self.assertEqual(contracted_node.children, [])
        self.assertEqual(contracted_node.parent, "id1")

        # Test Tensor
        correct_shape = (3,2,5,2,3,5)
        self.assertEqual(correct_shape, contracted_tensor.shape)

        # Test Connectivity
        self.assertTrue(self.tensortree.is_parent_of("id1", "id8contrid9"))

    def test_tensor_contraction_leaf_not_only_child(self):
        self.tensortree.contract_nodes("id5", "id7")
        contracted_id = "id5contrid7"
        contracted_node, contracted_tensor = self.tensortree[contracted_id]

        # Test Node
        self.assertTrue(isinstance(contracted_node, ptn.LegNode))
        self.assertEqual(contracted_node.children, ["id6"])
        self.assertEqual(contracted_node.parent, "id2")

        # Test Tensor
        correct_shape = (4,2,5,2,4,5)
        self.assertEqual(correct_shape, contracted_tensor.shape)

        # Test Connectivity
        self.assertTrue(self.tensortree.is_parent_of("id2", contracted_id))
        self.assertTrue(self.tensortree.is_child_of("id6", contracted_id))

    def test_tensor_contraction_middle_node(self):
        self.tensortree.contract_nodes("id2", "id5")
        contracted_id = "id2contrid5"
        contracted_node, contracted_tensor = self.tensortree[contracted_id]

        # Test Node
        child_ids = ["id3","id6","id7"]
        self.assertTrue(isinstance(contracted_node, ptn.LegNode))
        self.assertEqual(contracted_node.children, child_ids)
        self.assertEqual(contracted_node.parent, "id1")

        # Test Tensor
        correct_shape = (2,5,2,3,3,5)
        self.assertEqual(correct_shape, contracted_tensor.shape)

        # Test Connectivity
        self.assertTrue(self.tensortree.is_parent_of("id1", contracted_id))
        for child_id in child_ids:
            self.assertTrue(self.tensortree.is_child_of(child_id, contracted_id))

    def test_tensor_contraction_root(self):
        self.tensortree.contract_nodes("id1", "id2")
        contracted_id = "id1contrid2"
        contracted_node, contracted_tensor = self.tensortree[contracted_id]

        # Test Node
        child_ids = ["id8","id3","id5"]
        self.assertTrue(isinstance(contracted_node, ptn.LegNode))
        self.assertEqual(contracted_node.children, child_ids)
        self.assertTrue(contracted_node.is_root())

        # Test Tensor
        correct_shape = (3,5,4,4,5,3)
        self.assertEqual(correct_shape, contracted_tensor.shape)

        # Test Connectivity
        for child_id in child_ids:
            self.assertTrue(self.tensortree.is_child_of(child_id, contracted_id))

    

    # TODO: Reactivate later
    # def test_apply_hamiltonian(self):
    #     ttns = ptn.TreeTensorNetwork()
    #     node1, tensor1 = ptn.random_tensor_node((2, 3), identifier="site1")
    #     node2, tensor2 = ptn.random_tensor_node((2, 4), identifier="site2")

    #     ttns.add_root(node1, tensor1)
    #     ttns.add_child_to_parent(node2, tensor2, 0, "site1", 0)

    #     full_state = ttns.completely_contract_tree(to_copy=True).tensors["site1_contr_site2"]

    #     term1 = {"site1": "11", "site2": "21"}
    #     term2 = {"site1": "12", "site2": "22"}
    #     conversion_dict = {"11": ptn.crandn((3, 3)), "12": ptn.crandn((3, 3)),
    #                        "21": ptn.crandn((4, 4)), "22": ptn.crandn((4, 4))}

    #     hamiltonian = ptn.Hamiltonian(terms=[term1, term2],
    #                                   conversion_dictionary=conversion_dict)

    #     ttns.apply_hamiltonian(hamiltonian, conversion_dict)
    #     test_output = ttns.completely_contract_tree(to_copy=True).tensors["site1_contr_site2"]

    #     full_tensor = hamiltonian.to_tensor(ttns)
    #     ttno_output = np.tensordot(full_state, full_tensor, axes=([0, 1], [2, 3]))
    #     np.allclose(test_output, ttno_output)


if __name__ == "__main__":
    unittest.main()

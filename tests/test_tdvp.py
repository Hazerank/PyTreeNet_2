
import unittest
from copy import deepcopy

import numpy as np
from scipy.linalg import expm

import pytreenet as ptn
from pytreenet.contractions.state_operator_contraction import (contract_any)

class TestTDVPInit(unittest.TestCase):

    def setUp(self):
        self.conversion_dict = {"root_op1": ptn.random_hermitian_matrix(),
                                "root_op2": ptn.random_hermitian_matrix(),
                                "I2": np.eye(2),
                                "c1_op": ptn.random_hermitian_matrix(size=3),
                                "I3": np.eye(3),
                                "c2_op": ptn.random_hermitian_matrix(size=4),
                                "I4": np.eye(4)}
        self.ref_tree = ptn.random_small_ttns()
        tensor_prod = [ptn.TensorProduct({"c1": "I3", "root": "root_op1", "c2": "I4"}),
                       ptn.TensorProduct({"c1": "c1_op", "root": "root_op1", "c2": "I4"}),
                       ptn.TensorProduct({"c1": "c1_op", "root": "root_op2", "c2": "c2_op"}),
                       ptn.TensorProduct({"c1": "c1_op", "root": "I2", "c2": "c2_op"})
                       ]
        ham = ptn.Hamiltonian(tensor_prod, self.conversion_dict)
        operator = ptn.TensorProduct({"root": ptn.crandn((2,2))})
        self.hamiltonian = ptn.TTNO.from_hamiltonian(ham, self.ref_tree)
        self.tdvp = ptn.TDVPAlgorithm(self.ref_tree, self.hamiltonian,
                                      0.1, 1, operator)

    def test_init_hamiltonian(self):
        self.assertEqual(self.hamiltonian, self.tdvp.hamiltonian)

    def test_state_initialisation(self):
        for node_id in self.ref_tree.nodes:
            ref_node, ref_tensor = self.ref_tree[node_id]
            node, tensor = self.tdvp.state[node_id]
            self.assertEqual(ref_node.shape, node.shape)
            self.assertEqual(ref_tensor.shape, tensor.shape)

    def test_init_update_path(self):
        self.assertEqual(["c1","root","c2"], self.tdvp.update_path)

    def test_init_orth_path(self):
        self.assertEqual([["root"],["c2"]], self.tdvp.orthogonalization_path)

    def test_find_caching_path(self):
        caching_path, next_node_id_dict = self.tdvp._find_caching_path()
        self.assertEqual(["c2", "root", "c1"], caching_path)
        self.assertEqual({"c2": "root", "root": "c1"}, next_node_id_dict)

    def test_init_partial_tree_cache(self):
        # Creating reference
        ref_tdvp = deepcopy(self.tdvp)
        partial_tree_cache = ptn.PartialTreeCachDict()
        c2_block = contract_any("c2", "root",
                                ref_tdvp.state,
                                ref_tdvp.hamiltonian,
                                partial_tree_cache)
        partial_tree_cache.add_entry("c2", "root", c2_block)
        root_block = contract_any("root", "c1",
                                  ref_tdvp.state,
                                  ref_tdvp.hamiltonian,
                                  partial_tree_cache)
        partial_tree_cache.add_entry("root", "c1", root_block)

        for ids, tensor in partial_tree_cache.items():
            found_tensor = self.tdvp.partial_tree_cache.get_entry(ids[0], ids[1])
            self.assertTrue(np.allclose(tensor, found_tensor))

class TestContractionMethods(unittest.TestCase):

    def setUp(self):
        self.conversion_dict = {"root_op1": ptn.random_hermitian_matrix(),
                                "root_op2": ptn.random_hermitian_matrix(),
                                "I2": np.eye(2),
                                "c1_op": ptn.random_hermitian_matrix(size=3),
                                "I3": np.eye(3),
                                "c2_op": ptn.random_hermitian_matrix(size=4),
                                "I4": np.eye(4)}
        self.ref_tree = ptn.random_small_ttns()
        tensor_prod = [ptn.TensorProduct({"c1": "I3", "root": "root_op1", "c2": "I4"}),
                       ptn.TensorProduct({"c1": "c1_op", "root": "root_op1", "c2": "I4"}),
                       ptn.TensorProduct({"c1": "c1_op", "root": "root_op2", "c2": "c2_op"}),
                       ptn.TensorProduct({"c1": "c1_op", "root": "I2", "c2": "c2_op"})
                       ]
        ham = ptn.Hamiltonian(tensor_prod, self.conversion_dict)
        operator = ptn.TensorProduct({"root": ptn.crandn((2,2))})
        self.hamiltonian = ptn.TTNO.from_hamiltonian(ham, self.ref_tree)
        self.tdvp = ptn.TDVPAlgorithm(self.ref_tree, self.hamiltonian,
                                      0.1, 1, operator)

        # Computing the other cached tensors for use
        c1_cache = contract_any("c1", "root",
                                self.tdvp.state, self.tdvp.hamiltonian,
                                self.tdvp.partial_tree_cache)
        self.tdvp.partial_tree_cache.add_entry("c1", "root", c1_cache)
        root_to_c2_cache = contract_any("root", "c2",
                                        self.tdvp.state, self.tdvp.hamiltonian,
                                        self.tdvp.partial_tree_cache)
        self.tdvp.partial_tree_cache.add_entry("root", "c2", root_to_c2_cache)

    def test_move_orth_and_update_cache_for_path_c1_to_c2(self):
        ref_tdvp = deepcopy(self.tdvp)
        ref_tdvp.state.move_orthogonalization_center("c2",
                                                     mode=ptn.SplitMode.KEEP)
        update_c1_cache = contract_any("c1", "root",
                                       ref_tdvp.state, ref_tdvp.hamiltonian,
                                       ref_tdvp.partial_tree_cache)
        ref_tdvp.partial_tree_cache.add_entry("c1","root",
                                              update_c1_cache)
        update_root_to_c2_cache = contract_any("root", "c2",
                                               ref_tdvp.state,
                                               ref_tdvp.hamiltonian,
                                               ref_tdvp.partial_tree_cache)
        ref_tdvp.partial_tree_cache.add_entry("root","c2",
                                              update_root_to_c2_cache)

    def test_move_orth_and_update_cache_for_path_c1_to_root_to_c2(self):
        path1 = ["c1","root"]
        ref_tdvp = deepcopy(self.tdvp)
        ref_tdvp.state.move_orthogonalization_center("root",
                                                     mode=ptn.SplitMode.KEEP)
        update_c1_cache = contract_any("c1", "root",
                                       ref_tdvp.state,
                                       ref_tdvp.hamiltonian,
                                       ref_tdvp.partial_tree_cache)
        ref_tdvp.partial_tree_cache.add_entry("c1","root",
                                              update_c1_cache)

        self.tdvp._move_orth_and_update_cache_for_path(path1)

        self.assertEqual("root",self.tdvp.state.orthogonality_center_id)
        self.assertEqual(ref_tdvp.state,self.tdvp.state)
        for identifiers in ref_tdvp.partial_tree_cache:
            correct_cache = ref_tdvp.partial_tree_cache.get_entry(identifiers[0],
                                                                          identifiers[1])
            found_cache = self.tdvp.partial_tree_cache.get_entry(identifiers[0],
                                                                         identifiers[1])
            self.assertTrue(np.allclose(correct_cache,found_cache))

        ref_tdvp.state.move_orthogonalization_center("c2",
                                                     mode=ptn.SplitMode.KEEP)
        update_root_to_c2_cache = contract_any("root", "c2",
                                               ref_tdvp.state, ref_tdvp.hamiltonian,
                                               ref_tdvp.partial_tree_cache)
        ref_tdvp.partial_tree_cache.add_entry("root","c2",
                                              update_root_to_c2_cache)

    def test_move_orth_and_update_cache_for_path_c1_to_c1(self):
        path = ["c1"]
        # In this case nothing should happen
        ref_tdvp = deepcopy(self.tdvp)
        self.tdvp._move_orth_and_update_cache_for_path(path)

        self.assertEqual("c1",self.tdvp.state.orthogonality_center_id)
        self.assertEqual(ref_tdvp.state,self.tdvp.state)
        for identifiers in ref_tdvp.partial_tree_cache:
            correct_cache = ref_tdvp.partial_tree_cache.get_entry(identifiers[0],
                                                                          identifiers[1])
            found_cache = self.tdvp.partial_tree_cache.get_entry(identifiers[0],
                                                                         identifiers[1])
            self.assertTrue(np.allclose(correct_cache,found_cache))

    def test_move_orth_and_update_cache_for_path_empty_path(self):
        path = []
        # In this case nothing should happen
        ref_tdvp = deepcopy(self.tdvp)
        self.tdvp._move_orth_and_update_cache_for_path(path)

        self.assertEqual("c1",self.tdvp.state.orthogonality_center_id)
        self.assertEqual(ref_tdvp.state,self.tdvp.state)
        for identifiers in ref_tdvp.partial_tree_cache:
            correct_cache = ref_tdvp.partial_tree_cache.get_entry(identifiers[0],
                                                                          identifiers[1])
            found_cache = self.tdvp.partial_tree_cache.get_entry(identifiers[0],
                                                                         identifiers[1])
            self.assertTrue(np.allclose(correct_cache,found_cache))

    def test_move_orth_and_update_cache_for_path_non_orth_center(self):
        self.assertRaises(AssertionError,
                          self.tdvp._move_orth_and_update_cache_for_path,
                          ["root","c2"])

    def test_contract_all_except_node_c1(self):
        # Compute Reference
        ham_tensor = self.tdvp.hamiltonian.tensors["c1"]
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("root", "c1")
        ref_tensor = np.tensordot(ham_tensor, cache_tensor,
                                  axes=(0,1))
        ref_tensor = np.transpose(ref_tensor, axes=[3,0,2,1])
        found_tensor = self.tdvp._contract_all_except_node("c1")

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_contract_all_except_node_c2(self):
        # Compute Reference
        ham_tensor = self.tdvp.hamiltonian.tensors["c2"]
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("root", "c2")
        ref_tensor = np.tensordot(ham_tensor, cache_tensor,
                                  axes=(0,1))
        ref_tensor = np.transpose(ref_tensor, axes=[3,0,2,1])

        found_tensor = self.tdvp._contract_all_except_node("c2")

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_contract_all_except_node_root(self):
        # Compute Reference
        ham_tensor = self.tdvp.hamiltonian.tensors["root"]
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("c1", "root")
        ref_tensor = np.tensordot(ham_tensor, cache_tensor,
                                  axes=(0,1))
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("c2", "root")
        ref_tensor = np.tensordot(ref_tensor, cache_tensor,
                                  axes=(0,1))
        ref_tensor = np.transpose(ref_tensor, axes=[3,5,0,2,4,1])

        found_tensor = self.tdvp._contract_all_except_node("root")

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_get_effective_site_hamiltonian_c1(self):
        # Copmute Reference
        ref_tensor = np.tensordot(self.tdvp.partial_tree_cache.get_entry("root", "c1"),
                                  self.tdvp.hamiltonian.tensors["c1"],
                                  axes=(1,0))
        ref_tensor = np.transpose(ref_tensor, axes=(1,2,0,3))
        ref_tensor = np.reshape(ref_tensor, (15,15))

        found_tensor = self.tdvp._get_effective_site_hamiltonian("c1")
        self.assertTrue(np.allclose(ref_tensor, found_tensor))

    def test_get_effective_site_hamiltonian_c2(self):
        # Compute Reference
        ham_tensor = self.tdvp.hamiltonian.tensors["c2"]
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("root", "c2")
        ref_tensor = np.tensordot(ham_tensor, cache_tensor,
                                  axes=(0,1))
        ref_tensor = np.transpose(ref_tensor, axes=[3,0,2,1])
        ref_tensor = np.reshape(ref_tensor, (24,24))

        found_tensor = self.tdvp._get_effective_site_hamiltonian("c2")

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_get_effective_site_hamiltonian_root(self):
        # Compute Reference
        ham_tensor = self.tdvp.hamiltonian.tensors["root"]
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("c1", "root")
        ref_tensor = np.tensordot(ham_tensor, cache_tensor,
                                  axes=(0,1))
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("c2", "root")
        ref_tensor = np.tensordot(ref_tensor, cache_tensor,
                                  axes=(0,1))
        ref_tensor = np.transpose(ref_tensor, axes=[3,5,0,2,4,1])
        ref_tensor = np.reshape(ref_tensor, (60,60))

        found_tensor = self.tdvp._get_effective_site_hamiltonian("root")

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_update_cache_after_split_c1_to_root(self):
        node_id = "c1"
        q_legs = ptn.LegSpecification(None,[],[1])
        r_legs = ptn.LegSpecification("root",[],[])
        self.tdvp.state.split_node_qr(node_id, q_legs, r_legs,
                                      q_identifier=node_id,
                                      r_identifier=self.tdvp.create_link_id(node_id,"root"))

        # Compute Reference
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(1,2))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(2,1))

        self.tdvp._update_cache_after_split(node_id, "root")
        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,"root")

        self.assertTrue(np.allclose(ref_tensor, found_tensor))

    def test_update_cache_after_split_c2_to_root(self):
        node_id = "c2"
        q_legs = ptn.LegSpecification(None,[],[1])
        r_legs = ptn.LegSpecification("root",[],[])
        self.tdvp.state.split_node_qr(node_id, q_legs, r_legs,
                                      q_identifier=node_id,
                                      r_identifier=self.tdvp.create_link_id(node_id,"root"))

        # Compute Reference
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(1,2))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(2,1))

        self.tdvp._update_cache_after_split(node_id, "root")
        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,"root")

        self.assertTrue(np.allclose(ref_tensor, found_tensor))

    def test_update_cache_after_split_root_to_c1(self):
        node_id = "root"
        q_legs = ptn.LegSpecification(None,["c2"],[2])
        r_legs = ptn.LegSpecification(None,["c1"],[])
        self.tdvp.state.split_node_qr(node_id, q_legs, r_legs,
                                      q_identifier=node_id,
                                      r_identifier=self.tdvp.create_link_id(node_id, "c1"))

        # Compute Reference
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(2,3))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(4,2))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.partial_tree_cache.get_entry("c2",node_id),
                                  axes=([1,3,5],[0,1,2]))

        self.tdvp._update_cache_after_split(node_id,"c1")
        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,"c1")

        self.assertTrue(np.allclose(ref_tensor, found_tensor))

    def test_update_cache_after_split_root_to_c2(self):
        node_id = "root"
        q_legs = ptn.LegSpecification(None,["c1"],[2])
        r_legs = ptn.LegSpecification(None,["c2"],[])
        self.tdvp.state.split_node_qr(node_id, q_legs, r_legs,
                                      q_identifier=node_id,
                                      r_identifier=self.tdvp.create_link_id(node_id, "c2"))
        # Compute Reference
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(2,3))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(4,2))
        cached_node = self.tdvp.partial_tree_cache.get_entry("c1",node_id)
        # Note the link tensor is the first child of root not c1!
        ref_tensor = np.tensordot(ref_tensor,
                                  cached_node,
                                  axes=([1,3,5],[0,1,2]))

        self.tdvp._update_cache_after_split(node_id,"c2")
        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,"c2")

        self.assertTrue(np.allclose(ref_tensor, found_tensor))

    def test_split_updated_site_c1(self):
        node_id = "c1"
        q_legs = ptn.LegSpecification(None,[],[1])
        r_legs = ptn.LegSpecification("root",[],[])
        ref_state = deepcopy(self.tdvp.state)
        ref_state.split_node_qr(node_id, q_legs, r_legs,
                                q_identifier=node_id,
                                r_identifier=self.tdvp.create_link_id(node_id, "root"),
                                mode=ptn.SplitMode.KEEP)
        ref_old_cache = deepcopy(self.tdvp.partial_tree_cache.get_entry(node_id,"root"))

        self.tdvp._split_updated_site(node_id,"root")
        self.assertTrue(np.allclose(ref_state.tensors[node_id],
                                    self.tdvp.state.tensors[node_id]))
        self.assertFalse(np.allclose(ref_old_cache,
                                     self.tdvp.partial_tree_cache.get_entry(node_id,"root")))
        link_id = self.tdvp.create_link_id(node_id,"root")
        self.assertTrue(link_id in self.tdvp.state)
        self.assertTrue(np.allclose(ref_state.tensors[link_id],
                                    self.tdvp.state.tensors[link_id]))

    def test_split_updated_site_c2(self):
        node_id = "c2"
        q_legs = ptn.LegSpecification(None,[],[1])
        r_legs = ptn.LegSpecification("root",[],[])
        ref_state = deepcopy(self.tdvp.state)
        ref_state.split_node_qr(node_id, q_legs, r_legs,
                                q_identifier=node_id,
                                r_identifier=self.tdvp.create_link_id(node_id, "root"),
                                mode=ptn.SplitMode.KEEP)

        self.tdvp._split_updated_site(node_id,"root")
        self.assertTrue(np.allclose(ref_state.tensors[node_id],
                                    self.tdvp.state.tensors[node_id]))
        link_id = self.tdvp.create_link_id(node_id,"root")
        self.assertTrue(link_id in self.tdvp.state)
        self.assertTrue(np.allclose(ref_state.tensors[link_id],
                                    self.tdvp.state.tensors[link_id]))

    def test_split_updated_site_root_to_c1(self):
        node_id = "c1"
        root_id = "root"
        q_legs = ptn.LegSpecification(None,["c2"],[2])
        r_legs = ptn.LegSpecification(None,[node_id],[])
        ref_state = deepcopy(self.tdvp.state)
        ref_state.split_node_qr(root_id, q_legs, r_legs,
                                q_identifier=root_id,
                                r_identifier=self.tdvp.create_link_id(root_id, node_id))

        self.tdvp._split_updated_site(root_id, node_id)
        self.assertTrue(np.allclose(ref_state.tensors[root_id],
                                    self.tdvp.state.tensors[root_id]))
        link_id = self.tdvp.create_link_id(root_id,node_id)
        self.assertTrue(link_id in self.tdvp.state)
        self.assertTrue(np.allclose(ref_state.tensors[link_id],
                                    self.tdvp.state.tensors[link_id]))

    def test_split_updated_site_root_to_c2(self):
        node_id = "c2"
        root_id = "root"
        q_legs = ptn.LegSpecification(None,["c1"],[2])
        r_legs = ptn.LegSpecification(None,[node_id],[])
        ref_state = deepcopy(self.tdvp.state)
        ref_state.split_node_qr(root_id, q_legs, r_legs,
                                q_identifier=root_id,
                                r_identifier=self.tdvp.create_link_id(root_id, node_id))

        self.tdvp._split_updated_site(root_id, node_id)
        self.assertTrue(np.allclose(ref_state.tensors[root_id],
                                    self.tdvp.state.tensors[root_id]))
        link_id = self.tdvp.create_link_id(root_id,node_id)
        self.assertTrue(link_id in self.tdvp.state)
        self.assertTrue(np.allclose(ref_state.tensors[link_id],
                                    self.tdvp.state.tensors[link_id]))

    def test_split_updated_site_exception(self):
        self.assertRaises(ptn.NoConnectionException,
                          self.tdvp._split_updated_site,
                          "c1", "c2")

    def test_get_effective_link_hamiltonian_c1_to_root(self):
        root_id = "root"
        node_id = "c1"
        self.tdvp._split_updated_site(node_id, root_id)
        cache_c1 = self.tdvp.partial_tree_cache.get_entry(root_id,node_id)
        cache_root = self.tdvp.partial_tree_cache.get_entry(node_id,root_id)
        ref_tensor = np.tensordot(cache_c1,cache_root,
                                  axes=(1,1))
        ref_tensor = np.transpose(ref_tensor, axes=[1,3,0,2])
        ref_tensor = np.reshape(ref_tensor, (25,25))

        found_tensor = self.tdvp._get_effective_link_hamiltonian(node_id,root_id)

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_get_effective_link_hamiltonian_c2_to_root(self):
        root_id = "root"
        node_id = "c2"
        self.tdvp._split_updated_site(node_id, root_id)
        cache_c1 = self.tdvp.partial_tree_cache.get_entry(root_id,node_id)
        cache_root = self.tdvp.partial_tree_cache.get_entry(node_id,root_id)
        ref_tensor = np.tensordot(cache_c1,cache_root,
                                  axes=(1,1))
        ref_tensor = np.transpose(ref_tensor, axes=[1,3,0,2])
        ref_tensor = np.reshape(ref_tensor, (36,36))

        found_tensor = self.tdvp._get_effective_link_hamiltonian(node_id,root_id)

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_get_effective_link_hamiltonian_root_to_c1(self):
        root_id = "root"
        node_id = "c1"
        self.tdvp._split_updated_site(root_id, node_id)
        cache_c1 = self.tdvp.partial_tree_cache.get_entry(node_id,root_id)
        cache_root = self.tdvp.partial_tree_cache.get_entry(root_id,node_id)
        ref_tensor = np.tensordot(cache_root,cache_c1,
                                  axes=(1,1))
        ref_tensor = np.transpose(ref_tensor, axes=[1,3,0,2])
        ref_tensor = np.reshape(ref_tensor, (25,25))

        found_tensor = self.tdvp._get_effective_link_hamiltonian(root_id,node_id)

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_get_effective_link_hamiltonian_root_to_c2(self):
        root_id = "root"
        node_id = "c2"
        self.tdvp._split_updated_site(root_id, node_id)
        cache_c1 = self.tdvp.partial_tree_cache.get_entry(node_id,root_id)
        cache_root = self.tdvp.partial_tree_cache.get_entry(root_id,node_id)
        ref_tensor = np.tensordot(cache_root,cache_c1,
                                  axes=(1,1))
        ref_tensor = np.transpose(ref_tensor, axes=[1,3,0,2])
        ref_tensor = np.reshape(ref_tensor, (36,36))

        found_tensor = self.tdvp._get_effective_link_hamiltonian(root_id,node_id)

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_update_site_c1(self):
        node_id = "c1"
        ref_state = deepcopy(self.tdvp.state)
        eff_site_ham = self.tdvp._get_effective_site_hamiltonian(node_id)
        node_tensor = ref_state[node_id][1]
        node_state = np.reshape(node_tensor,15)
        exponent = expm(-1j * self.tdvp.time_step_size * eff_site_ham)
        ref_updated_state = exponent @ node_state
        ref_node_tensor = np.reshape(ref_updated_state,(5,3))

        self.tdvp._update_site(node_id)
        found_node_tensor = self.tdvp.state.tensors[node_id]
        self.assertTrue(np.allclose(ref_node_tensor, found_node_tensor))

    def test_update_site_root(self):
        node_id = "root"
        self.tdvp.state.move_orthogonalization_center(node_id,
                                                      mode=ptn.SplitMode.KEEP)
        self.tdvp.update_tree_cache("c1", node_id)
        ref_state = deepcopy(self.tdvp.state)
        eff_site_ham = self.tdvp._get_effective_site_hamiltonian(node_id)
        node_tensor = ref_state[node_id][1]
        node_state = np.reshape(node_tensor,60)
        exponent = expm(-1j * self.tdvp.time_step_size * eff_site_ham)
        ref_updated_state = exponent @ node_state
        ref_node_tensor = np.reshape(ref_updated_state,(6,5,2))

        self.tdvp._update_site(node_id)
        found_node_tensor = self.tdvp.state.tensors[node_id]
        self.assertTrue(np.allclose(ref_node_tensor, found_node_tensor))

    def test_update_site_c2(self):
        node_id = "c2"
        self.tdvp.state.move_orthogonalization_center(node_id,
                                                      mode=ptn.SplitMode.KEEP)
        self.tdvp.update_tree_cache("c1", "root")
        self.tdvp.update_tree_cache("root", node_id)
        ref_state = deepcopy(self.tdvp.state)
        eff_site_ham = self.tdvp._get_effective_site_hamiltonian(node_id)
        node_tensor = ref_state[node_id][1]
        node_state = np.reshape(node_tensor,24)
        exponent = expm(-1j * self.tdvp.time_step_size * eff_site_ham)
        ref_updated_state = exponent @ node_state
        ref_node_tensor = np.reshape(ref_updated_state,(6,4))

        self.tdvp._update_site(node_id)
        found_node_tensor = self.tdvp.state.tensors[node_id]
        self.assertTrue(np.allclose(ref_node_tensor, found_node_tensor))

    def test_time_evolve_link_tensor_c1_to_root(self):
        node_id = "c1"
        next_node_id = "root"
        ref_tdvp = deepcopy(self.tdvp)
        ref_tdvp._split_updated_site(node_id,next_node_id)
        link_id = ref_tdvp.create_link_id(node_id,next_node_id)
        ref_tensor = ref_tdvp.state[link_id][1]
        ref_tensor = np.reshape(ref_tensor, 25)
        eff_link_ham = ref_tdvp._get_effective_link_hamiltonian(node_id, next_node_id)
        exponent = expm(1j * ref_tdvp.time_step_size * eff_link_ham)
        updated_ref_tensor = exponent @ ref_tensor
        updated_ref_tensor = np.reshape(updated_ref_tensor, (5,5))
        ref_tdvp.state.tensors[link_id] = updated_ref_tensor

        self.tdvp._split_updated_site(node_id,next_node_id)
        self.tdvp._time_evolve_link_tensor(node_id,next_node_id)
        self.assertTrue(np.allclose(ref_tdvp.state.tensors[node_id],
                                    self.tdvp.state.tensors[node_id]))
        self.assertTrue(np.allclose(ref_tdvp.state.tensors[link_id],
                                    self.tdvp.state.tensors[link_id]))

    def test_update_link_wrong_orth_center(self):
        self.assertRaises(AssertionError, self.tdvp._update_link,
                          "root", "c2")

    def test_update_link_c1_to_root(self):
        node_id = "c1"
        next_node_id = "root"
        ref_tdvp = deepcopy(self.tdvp)
        ref_tdvp._split_updated_site(node_id,next_node_id)
        link_id = ref_tdvp.create_link_id(node_id,next_node_id)
        ref_tensor = ref_tdvp.state[link_id][1]
        ref_tensor = np.reshape(ref_tensor, 25)
        eff_link_ham = ref_tdvp._get_effective_link_hamiltonian(node_id, next_node_id)
        exponent = expm(1j * ref_tdvp.time_step_size * eff_link_ham)
        updated_ref_tensor = exponent @ ref_tensor
        updated_ref_tensor = np.reshape(updated_ref_tensor, (5,5))
        ref_tdvp.state.tensors[link_id] = updated_ref_tensor
        ref_tdvp.state.contract_nodes(link_id, next_node_id,
                                      new_identifier=next_node_id)

        self.tdvp._update_link(node_id, next_node_id)
        transfer_tensor = ptn.compute_transfer_tensor(ref_tdvp.state.tensors[node_id],
                                                      (0, ))
        self.assertTrue(np.allclose(np.eye(3),transfer_tensor))
        self.assertEqual(ref_tdvp.state,self.tdvp.state)
        self.assertEqual(next_node_id,self.tdvp.state.orthogonality_center_id)

    def test_update_link_root_to_c1(self):
        node_id = "root"
        next_node_id = "c1"
        self.tdvp._move_orth_and_update_cache_for_path(["c1","root"])
        ref_tdvp = deepcopy(self.tdvp)
        ref_tdvp._split_updated_site(node_id,next_node_id)
        link_id = ref_tdvp.create_link_id(node_id,next_node_id)
        ref_link_tensor = ref_tdvp.state.tensors[link_id]
        orig_shape = ref_link_tensor.shape
        ref_link_tensor = np.reshape(ref_link_tensor,
                                     np.prod(orig_shape))
        eff_link_ham = ref_tdvp._get_effective_link_hamiltonian(node_id,
                                                                next_node_id)
        exponent = expm(1j*ref_tdvp.time_step_size*eff_link_ham)
        updated_ref_tensor = exponent @ ref_link_tensor
        updated_ref_tensor = np.reshape(updated_ref_tensor, orig_shape)
        ref_tdvp.state.tensors[link_id] = updated_ref_tensor
        ref_tdvp.state.contract_nodes(link_id,next_node_id,
                                      new_identifier=next_node_id)

        self.tdvp._update_link(node_id,next_node_id)
        self.assertEqual(ref_tdvp.state,self.tdvp.state)
        self.assertEqual(next_node_id,self.tdvp.state.orthogonality_center_id)

    def test_update_link_root_to_c2(self):
        node_id = "root"
        next_node_id = "c2"
        self.tdvp._move_orth_and_update_cache_for_path(["c1","root"])
        ref_tdvp = deepcopy(self.tdvp)
        ref_tdvp._split_updated_site(node_id,next_node_id)
        link_id = ref_tdvp.create_link_id(node_id,next_node_id)
        ref_link_tensor = ref_tdvp.state.tensors[link_id]
        orig_shape = ref_link_tensor.shape
        ref_link_tensor = np.reshape(ref_link_tensor,
                                     np.prod(orig_shape))
        eff_link_ham = ref_tdvp._get_effective_link_hamiltonian(node_id,
                                                                next_node_id)
        exponent = expm(1j*ref_tdvp.time_step_size*eff_link_ham)
        updated_ref_tensor = exponent @ ref_link_tensor
        updated_ref_tensor = np.reshape(updated_ref_tensor, orig_shape)
        ref_tdvp.state.tensors[link_id] = updated_ref_tensor
        ref_tdvp.state.contract_nodes(link_id,next_node_id,
                                      new_identifier=next_node_id)

        self.tdvp._update_link(node_id,next_node_id)
        self.assertEqual(ref_tdvp.state,self.tdvp.state)
        self.assertEqual(next_node_id,self.tdvp.state.orthogonality_center_id)

    def test_update_link_c2_to_root(self):
        node_id = "c2"
        next_node_id = "root"
        self.tdvp._move_orth_and_update_cache_for_path(["c1","root","c2"])
        ref_tdvp = deepcopy(self.tdvp)
        ref_tdvp._split_updated_site(node_id,next_node_id)
        link_id = ref_tdvp.create_link_id(node_id,next_node_id)
        ref_link_tensor = ref_tdvp.state.tensors[link_id]
        orig_shape = ref_link_tensor.shape
        ref_link_tensor = np.reshape(ref_link_tensor,
                                     np.prod(orig_shape))
        eff_link_ham = ref_tdvp._get_effective_link_hamiltonian(node_id,
                                                                next_node_id)
        exponent = expm(1j*ref_tdvp.time_step_size*eff_link_ham)
        updated_ref_tensor = exponent @ ref_link_tensor
        updated_ref_tensor = np.reshape(updated_ref_tensor, orig_shape)
        ref_tdvp.state.tensors[link_id] = updated_ref_tensor
        ref_tdvp.state.contract_nodes(link_id,next_node_id,
                                      new_identifier=next_node_id)

        self.tdvp._update_link(node_id,next_node_id)
        self.assertEqual(ref_tdvp.state,self.tdvp.state)
        self.assertEqual(next_node_id,self.tdvp.state.orthogonality_center_id)

class TestTDVPInitComplicated(unittest.TestCase):
    def setUp(self):
        self.ref_tree = ptn.random_big_ttns_two_root_children()
        self.hamiltonian = ptn.TTNO.from_hamiltonian(ptn.random_hamiltonian_compatible(),
                                                     self.ref_tree)
        self.tdvp = ptn.TDVPAlgorithm(self.ref_tree, self.hamiltonian, 0.1,1,
                                      ptn.TensorProduct({"site0": ptn.pauli_matrices()[0]}))

    def test_init_hamiltonian(self):
        self.assertEqual(self.hamiltonian, self.tdvp.hamiltonian)

    def test_init_state(self):
        self.assertEqual(self.ref_tree, self.tdvp.initial_state)

    def test_init_update_path(self):
        correct_path = ["site4","site5","site3","site2",
                        "site1","site0","site6","site7"]
        self.assertEqual(correct_path, self.tdvp.update_path)

    def test_init_orth_path(self):
        correct_path = [["site3","site5"],["site3"],["site1","site2"],
                        ["site1"],["site0"],["site6"],["site7"]]
        self.assertEqual(correct_path, self.tdvp.orthogonalization_path)

    def test_find_caching_path(self):
        caching_path, next_node_id_dict = self.tdvp._find_caching_path()
        correct_path = ["site7", "site6", "site0", "site2",
                        "site1", "site5", "site3", "site4"]
        self.assertEqual(correct_path, caching_path)
        correct_dict = {"site7": "site6", "site6": "site0",
                        "site0": "site1", "site2": "site1",
                        "site1": "site3", "site5": "site3", "site3": "site4"}
        self.assertEqual(correct_dict, next_node_id_dict)

    def test_init_tree_cache_7_to_6(self):
        node_id = "site7"
        next_node_id = "site6"
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(1,2))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(2,1))
        self.assertTrue((node_id,next_node_id) in self.tdvp.partial_tree_cache)

        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_init_tree_cache_2_to_1(self):
        node_id = "site2"
        next_node_id = "site1"
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(1,2))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(2,1))
        self.assertTrue((node_id,next_node_id) in self.tdvp.partial_tree_cache)

        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_init_tree_cache_5_to_3(self):
        node_id = "site2"
        next_node_id = "site1"
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(1,2))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(2,1))
        self.assertTrue((node_id,next_node_id) in self.tdvp.partial_tree_cache)

        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_init_tree_cache_6_to_0(self):
        node_id = "site6"
        next_node_id = "site0"
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(2,3))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(4,2))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.partial_tree_cache.get_entry("site7","site6"),
                                  axes=((1,3,5),(0,1,2)))
        self.assertTrue((node_id,next_node_id) in self.tdvp.partial_tree_cache)

        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_init_tree_cache_0_to_1(self):
        node_id = "site0"
        next_node_id = "site1"
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(2,3))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(4,2))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.partial_tree_cache.get_entry("site6","site0"),
                                  axes=((1,3,5),(0,1,2)))
        self.assertTrue((node_id,next_node_id) in self.tdvp.partial_tree_cache)

        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_init_tree_cache_1_to_3(self):
        node_id = "site1"
        next_node_id = "site3"
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.hamiltonian.tensors[node_id],
                                  axes=(3,4))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(6,3))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.partial_tree_cache.get_entry("site0",node_id),
                                  axes=((0,3,6),(0,1,2)))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.partial_tree_cache.get_entry("site2",node_id),
                                  axes=((1,2,5),(0,1,2)))

        self.assertTrue((node_id,next_node_id) in self.tdvp.partial_tree_cache)
        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_init_tree_cache_3_to_4(self):
        node_id = "site3"
        next_node_id = "site4"
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.hamiltonian.tensors[node_id],
                                  axes=(3,4))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(6,3))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.partial_tree_cache.get_entry("site5",node_id),
                                  axes=((2,5,8),(0,1,2)))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.partial_tree_cache.get_entry("site1",node_id),
                                  axes=((0,2,4),(0,1,2)))

        self.assertTrue((node_id,next_node_id) in self.tdvp.partial_tree_cache)
        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

class TestContractionMethodsComplicated(unittest.TestCase):
    def setUp(self) -> None:
        ref_tree = ptn.random_big_ttns_two_root_children()
        hamiltonian = ptn.TTNO.from_hamiltonian(ptn.random_hamiltonian_compatible(),
                                                     ref_tree)
        self.tdvp = ptn.TDVPAlgorithm(ref_tree, hamiltonian, 0.1,1,
                                      ptn.TensorProduct({"site0": ptn.pauli_matrices()[0]}))
        # To correctly compute the contractions we need all potential cached tensors
        non_init_pairs = [("site4","site3"),("site3","site5"),("site3","site1"),
                          ("site1","site2"),("site1","site0"),("site0","site6"),
                          ("site6","site7")]
        for pair in non_init_pairs:
            self.tdvp.update_tree_cache(pair[0],pair[1])

    def test_contract_all_except_node_4(self):
        node_id = "site4"
        ref_tensor = np.tensordot(self.tdvp.partial_tree_cache.get_entry("site3",node_id),
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(1,0))
        ref_tensor = np.transpose(ref_tensor, [1,2,0,3])

        found_tensor = self.tdvp._contract_all_except_node(node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_contract_all_except_node_5(self):
        node_id = "site5"
        ref_tensor = np.tensordot(self.tdvp.partial_tree_cache.get_entry("site3",node_id),
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(1,0))
        ref_tensor = np.transpose(ref_tensor, [1,2,0,3])

        found_tensor = self.tdvp._contract_all_except_node(node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_contract_all_except_node_2(self):
        node_id = "site2"
        ref_tensor = np.tensordot(self.tdvp.partial_tree_cache.get_entry("site1",node_id),
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(1,0))
        ref_tensor = np.transpose(ref_tensor, [1,2,0,3])

        found_tensor = self.tdvp._contract_all_except_node(node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_contract_all_except_node_7(self):
        node_id = "site7"
        ref_tensor = np.tensordot(self.tdvp.partial_tree_cache.get_entry("site6",node_id),
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(1,0))
        ref_tensor = np.transpose(ref_tensor, [1,2,0,3])

        found_tensor = self.tdvp._contract_all_except_node(node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_contract_all_except_node_0(self):
        node_id = "site0"
        ham_tensor = self.tdvp.hamiltonian.tensors[node_id]
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("site1",node_id)
        ref_tensor = np.tensordot(ham_tensor,
                                  cache_tensor,
                                  axes=(0,1))
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("site6",node_id)
        ref_tensor = np.tensordot(ref_tensor,
                                  cache_tensor,
                                  axes=(0,1))
        ref_tensor = np.transpose(ref_tensor, axes=(3,5,0,2,4,1))

        found_tensor = self.tdvp._contract_all_except_node(node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_contract_all_except_node_6(self):
        node_id = "site6"
        ham_tensor = self.tdvp.hamiltonian.tensors[node_id]
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("site0",node_id)
        ref_tensor = np.tensordot(ham_tensor,
                                  cache_tensor,
                                  axes=(0,1))
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("site7",node_id)
        ref_tensor = np.tensordot(ref_tensor,
                                  cache_tensor,
                                  axes=(0,1))
        ref_tensor = np.transpose(ref_tensor, axes=(3,5,0,2,4,1))

        found_tensor = self.tdvp._contract_all_except_node(node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_contract_all_except_node_1(self):
        node_id = "site1"
        ham_tensor = self.tdvp.hamiltonian.tensors[node_id]
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("site0",node_id)
        ref_tensor = np.tensordot(ham_tensor,
                                  cache_tensor,
                                  axes=(0,1))
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("site3",node_id)
        ref_tensor = np.tensordot(ref_tensor,
                                  cache_tensor,
                                  axes=(0,1))
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("site2",node_id)
        ref_tensor = np.tensordot(ref_tensor,
                                  cache_tensor,
                                  axes=(0,1))
        ref_tensor = np.transpose(ref_tensor, axes=(3,5,7,0,2,4,6,1))

        found_tensor = self.tdvp._contract_all_except_node(node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_contract_all_except_node_3(self):
        node_id = "site3"
        ham_tensor = self.tdvp.hamiltonian.tensors[node_id]
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("site1",node_id)
        ref_tensor = np.tensordot(ham_tensor,
                                  cache_tensor,
                                  axes=(0,1))
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("site4",node_id)
        ref_tensor = np.tensordot(ref_tensor,
                                  cache_tensor,
                                  axes=(0,1))
        cache_tensor = self.tdvp.partial_tree_cache.get_entry("site5",node_id)
        ref_tensor = np.tensordot(ref_tensor,
                                  cache_tensor,
                                  axes=(0,1))
        ref_tensor = np.transpose(ref_tensor, axes=(3,5,7,0,2,4,6,1))

        found_tensor = self.tdvp._contract_all_except_node(node_id)
        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_get_effective_hamiltonian_4(self):
        node_id = "site4"
        ref_matrix = self.tdvp._contract_all_except_node(node_id)
        ref_matrix = np.reshape(ref_matrix,(4,4))

        found_matrix = self.tdvp._get_effective_site_hamiltonian(node_id)
        self.assertTrue(np.allclose(ref_matrix,found_matrix))

    def test_get_effective_hamiltonian_5(self):
        node_id = "site5"
        ref_matrix = self.tdvp._contract_all_except_node(node_id)
        ref_matrix = np.reshape(ref_matrix,(4,4))

        found_matrix = self.tdvp._get_effective_site_hamiltonian(node_id)
        self.assertTrue(np.allclose(ref_matrix,found_matrix))

    def test_get_effective_hamiltonian_2(self):
        node_id = "site2"
        ref_matrix = self.tdvp._contract_all_except_node(node_id)
        ref_matrix = np.reshape(ref_matrix,(4,4))

        found_matrix = self.tdvp._get_effective_site_hamiltonian(node_id)
        self.assertTrue(np.allclose(ref_matrix,found_matrix))

    def test_get_effective_hamiltonian_7(self):
        node_id = "site7"
        ref_matrix = self.tdvp._contract_all_except_node(node_id)
        ref_matrix = np.reshape(ref_matrix,(4,4))

        found_matrix = self.tdvp._get_effective_site_hamiltonian(node_id)
        self.assertTrue(np.allclose(ref_matrix,found_matrix))

    def test_get_effective_hamiltonian_0(self):
        node_id = "site0"
        ref_matrix = self.tdvp._contract_all_except_node(node_id)
        ref_matrix = np.reshape(ref_matrix,(8,8))

        found_matrix = self.tdvp._get_effective_site_hamiltonian(node_id)
        self.assertTrue(np.allclose(ref_matrix,found_matrix))

    def test_get_effective_hamiltonian_6(self):
        node_id = "site6"
        ref_matrix = self.tdvp._contract_all_except_node(node_id)
        ref_matrix = np.reshape(ref_matrix,(8,8))

        found_matrix = self.tdvp._get_effective_site_hamiltonian(node_id)
        self.assertTrue(np.allclose(ref_matrix,found_matrix))

    def test_get_effective_hamiltonian_1(self):
        node_id = "site1"
        ref_matrix = self.tdvp._contract_all_except_node(node_id)
        ref_matrix = np.reshape(ref_matrix,(16,16))

        found_matrix = self.tdvp._get_effective_site_hamiltonian(node_id)
        self.assertTrue(np.allclose(ref_matrix,found_matrix))

    def test_get_effective_hamiltonian_3(self):
        node_id = "site3"
        ref_matrix = self.tdvp._contract_all_except_node(node_id)
        ref_matrix = np.reshape(ref_matrix,(16,16))

        found_matrix = self.tdvp._get_effective_site_hamiltonian(node_id)
        self.assertTrue(np.allclose(ref_matrix,found_matrix))

    def test_update_cache_after_1_root_to_2(self):
        node_id = "site1"
        q_legs = ptn.LegSpecification("site0",["site3"],[3])
        r_legs = ptn.LegSpecification(None,["site2"],[])
        self.tdvp.state.split_node_qr(node_id, q_legs, r_legs,
                                      q_identifier=node_id,
                                      r_identifier=self.tdvp.create_link_id(node_id, "site2"))
        # Compute Reference
        # Note that the qr decomposition caused the children to flip again
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(3,4))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(6,3))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.partial_tree_cache.get_entry("site0",node_id),
                                  axes=([0,3,6],[0,1,2]))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.partial_tree_cache.get_entry("site3",node_id),
                                  axes=([1,3,5],[0,1,2]))

        self.tdvp._update_cache_after_split(node_id,"site2")
        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,"site2")

        self.assertTrue(np.allclose(ref_tensor, found_tensor))

    def test_update_cache_after_1_root_to_3(self):
        node_id = "site1"
        q_legs = ptn.LegSpecification("site0",["site2"],[3])
        r_legs = ptn.LegSpecification(None,["site3"],[])
        self.tdvp.state.split_node_qr(node_id, q_legs, r_legs,
                                      q_identifier=node_id,
                                      r_identifier=self.tdvp.create_link_id(node_id, "site3"))
        # Compute Reference
        ref_tensor = np.tensordot(self.tdvp.state.tensors[node_id],
                                  self.tdvp.hamiltonian.tensors[node_id],
                                  axes=(3,4))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.state.tensors[node_id].conj(),
                                  axes=(6,3))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.partial_tree_cache.get_entry("site0",node_id),
                                  axes=([0,3,6],[0,1,2]))
        ref_tensor = np.tensordot(ref_tensor,
                                  self.tdvp.partial_tree_cache.get_entry("site2",node_id),
                                  axes=([1,2,5],[0,1,2]))

        self.tdvp._update_cache_after_split(node_id,"site3")
        found_tensor = self.tdvp.partial_tree_cache.get_entry(node_id,"site3")

        self.assertTrue(np.allclose(ref_tensor, found_tensor))

    def test_split_updated_site_1_to_2(self):
        node_id = "site1"
        next_node_id = "site2"
        q_legs = ptn.LegSpecification("site0",["site3"],[3])
        r_legs = ptn.LegSpecification(None,["site2"],[])
        ref_state = deepcopy(self.tdvp.state)
        ref_state.split_node_qr(node_id, q_legs, r_legs,
                                q_identifier=node_id,
                                r_identifier=self.tdvp.create_link_id(node_id,next_node_id))

        self.tdvp._split_updated_site(node_id,next_node_id)
        self.assertTrue(np.allclose(ref_state.tensors[node_id],
                                    self.tdvp.state.tensors[node_id]))
        link_id = self.tdvp.create_link_id(node_id,next_node_id)
        self.assertTrue(link_id in self.tdvp.state)
        self.assertTrue(np.allclose(ref_state.tensors[link_id],
                                    self.tdvp.state.tensors[link_id]))

    def test_split_updated_site_1_to_3(self):
        node_id = "site1"
        next_node_id = "site3"
        q_legs = ptn.LegSpecification("site0",["site2"],[3])
        r_legs = ptn.LegSpecification(None,["site3"],[])
        ref_state = deepcopy(self.tdvp.state)
        ref_state.split_node_qr(node_id, q_legs, r_legs,
                                q_identifier=node_id,
                                r_identifier=self.tdvp.create_link_id(node_id,next_node_id))

        self.tdvp._split_updated_site(node_id,next_node_id)
        self.assertTrue(np.allclose(ref_state.tensors[node_id],
                                    self.tdvp.state.tensors[node_id]))
        link_id = self.tdvp.create_link_id(node_id,next_node_id)
        self.assertTrue(link_id in self.tdvp.state)
        self.assertTrue(np.allclose(ref_state.tensors[link_id],
                                    self.tdvp.state.tensors[link_id]))

    def test_get_effective_link_hamiltonian_1_to_2(self):
        node_id = "site1"
        next_node_id = "site2"
        self.tdvp._split_updated_site(node_id,next_node_id)
        cache_1 = self.tdvp.partial_tree_cache.get_entry(next_node_id,node_id)
        cache_2 = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        ref_tensor = np.tensordot(cache_2,cache_1,
                                  axes=(1,1))
        ref_tensor = np.transpose(ref_tensor, axes=[1,3,0,2])
        ref_tensor = np.reshape(ref_tensor, (4,4))

        found_tensor = self.tdvp._get_effective_link_hamiltonian(node_id,next_node_id)

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_get_effective_link_hamiltonian_2_to_1(self):
        node_id = "site2"
        next_node_id = "site1"
        self.tdvp._split_updated_site(node_id,next_node_id)
        cache_1 = self.tdvp.partial_tree_cache.get_entry(next_node_id,node_id)
        cache_2 = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        ref_tensor = np.tensordot(cache_1,cache_2,
                                  axes=(1,1))
        ref_tensor = np.transpose(ref_tensor, axes=[1,3,0,2])
        ref_tensor = np.reshape(ref_tensor, (4,4))

        found_tensor = self.tdvp._get_effective_link_hamiltonian(node_id,next_node_id)

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_get_effective_link_hamiltonian_1_to_3(self):
        node_id = "site1"
        next_node_id = "site3"
        self.tdvp._split_updated_site(node_id,next_node_id)
        cache_1 = self.tdvp.partial_tree_cache.get_entry(next_node_id,node_id)
        cache_2 = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        ref_tensor = np.tensordot(cache_2,cache_1,
                                  axes=(1,1))
        ref_tensor = np.transpose(ref_tensor, axes=[1,3,0,2])
        ref_tensor = np.reshape(ref_tensor, (4,4))

        found_tensor = self.tdvp._get_effective_link_hamiltonian(node_id,next_node_id)

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_get_effective_link_hamiltonian_3_to_1(self):
        node_id = "site3"
        next_node_id = "site1"
        self.tdvp._split_updated_site(node_id,next_node_id)
        cache_1 = self.tdvp.partial_tree_cache.get_entry(next_node_id,node_id)
        cache_2 = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        ref_tensor = np.tensordot(cache_1,cache_2,
                                  axes=(1,1))
        ref_tensor = np.transpose(ref_tensor, axes=[1,3,0,2])
        ref_tensor = np.reshape(ref_tensor, (4,4))

        found_tensor = self.tdvp._get_effective_link_hamiltonian(node_id,next_node_id)

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_get_effective_link_hamiltonian_1_to_0(self):
        node_id = "site1"
        next_node_id = "site0"
        self.tdvp._split_updated_site(node_id,next_node_id)
        cache_1 = self.tdvp.partial_tree_cache.get_entry(next_node_id,node_id)
        cache_2 = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        ref_tensor = np.tensordot(cache_1,cache_2,
                                  axes=(1,1))
        ref_tensor = np.transpose(ref_tensor, axes=[1,3,0,2])
        ref_tensor = np.reshape(ref_tensor, (4,4))

        found_tensor = self.tdvp._get_effective_link_hamiltonian(node_id,next_node_id)

        self.assertTrue(np.allclose(ref_tensor,found_tensor))

    def test_get_effective_link_hamiltonian_0_to_1(self):
        node_id = "site0"
        next_node_id = "site1"
        self.tdvp._split_updated_site(node_id,next_node_id)
        cache_1 = self.tdvp.partial_tree_cache.get_entry(next_node_id,node_id)
        cache_2 = self.tdvp.partial_tree_cache.get_entry(node_id,next_node_id)
        ref_tensor = np.tensordot(cache_2,cache_1,
                                  axes=(1,1))
        ref_tensor = np.transpose(ref_tensor, axes=[1,3,0,2])
        ref_tensor = np.reshape(ref_tensor, (4,4))

        found_tensor = self.tdvp._get_effective_link_hamiltonian(node_id,next_node_id)

        self.assertTrue(np.allclose(ref_tensor,found_tensor))


if __name__ == "__main__":
    unittest.main()

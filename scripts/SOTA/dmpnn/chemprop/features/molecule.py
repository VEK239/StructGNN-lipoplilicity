from collections import defaultdict

from rdkit import Chem
from rdkit.Chem import rdmolfiles

BT_MAPPING_CHAR = {
    Chem.rdchem.BondType.SINGLE: 'S',
    Chem.rdchem.BondType.DOUBLE: 'D',
    Chem.rdchem.BondType.TRIPLE: 'T',
    Chem.rdchem.BondType.AROMATIC: 'A',
}
BT_MAPPING_INT = {
    Chem.rdchem.BondType.SINGLE: 1,
    Chem.rdchem.BondType.DOUBLE: 2,
    Chem.rdchem.BondType.TRIPLE: 3,
    Chem.rdchem.BondType.AROMATIC: 1.5,
}
STRUCT_TO_NUM = {
    'ATOM': 0,
    'RING': 1,
    'ACID': 2,
    'AMIN': 3,
    'ESTER': 4,
    'SULFONAMID': 5
}


def get_cycles_for_molecule(mol, merging_cycles=False):
    """
    Finds all the cycles in a given RDKit mol
    :param mol: The given RDKit molecule
    :param merging_cycles: If True merges cycles with neighboring atoms
    :return: A list of cycles in a mol
    """
    all_cycles = Chem.GetSymmSSSR(mol)
    all_cycles = [set(ring) for ring in all_cycles]
    if merging_cycles:
        atom_to_ring = defaultdict(set)
        for cycle_idx, cycle in enumerate(all_cycles):
            for atom in cycle:
                atom_to_ring[atom].add(cycle_idx)
        rings_to_merge = [1]
        while rings_to_merge:
            rings_to_merge = None
            for atom, atom_cycles in atom_to_ring.items():
                if len(atom_cycles) > 1:
                    rings_to_merge = atom_cycles.copy()
            if rings_to_merge:
                ring_new_idx = min(rings_to_merge)
                for ring_idx in rings_to_merge:
                    for atom in all_cycles[ring_idx]:
                        all_cycles[ring_new_idx].add(atom)
                        atom_to_ring[atom].remove(ring_idx)
                        atom_to_ring[atom].add(ring_new_idx)
                for ring_idx in rings_to_merge:
                    if ring_idx != ring_new_idx:
                        all_cycles[ring_idx] = []
    all_cycles = [list(cycle) for cycle in all_cycles if len(cycle) > 2]
    return all_cycles


def get_acids_for_molecule(mol):
    """
    Finds all acid parts in a given RDKit mol
    :param mol: The given RDKit molecule
    :return: A list of acid parts in a mol
    """
    acid_pattern = Chem.MolFromSmarts('[CX3](=O)[OX2H1]')
    acids = mol.GetSubstructMatches(acid_pattern)
    return [list(acid) for acid in acids]


def get_esters_for_molecule(mol):
    """
    Finds all ester parts in a given RDKit mol
    :param mol: The given RDKit molecule
    :return: A list of ester parts in a mol
    """
    ester_pattern = Chem.MolFromSmarts('[#6][CX3](=O)[OX2H0][#6]')
    esters = mol.GetSubstructMatches(ester_pattern)
    esters = [list(ester) for ester in esters]
    ester_atoms = []
    for ester in esters:
        atoms = []
        for atom in ester:
            if mol.GetAtomWithIdx(atom).GetSymbol() == 'O':
                atoms.append(atom)
        for atom in ester:
            if mol.GetBondBetweenAtoms(atom, atoms[0]) and mol.GetBondBetweenAtoms(atom, atoms[1]):
                atoms.append(atom)
        ester_atoms.append(atoms)
    return ester_atoms


def get_amins_for_molecule(mol):
    """
    Finds all amino parts in a given RDKit mol
    :param mol: The given RDKit molecule
    :return: A list of amino parts in a mol
    """
    sulfonamids = get_sulfonamids_for_molecule(mol)
    sulfonamid_atoms = []
    for sulfo in sulfonamids:
        for atom in sulfo:
            sulfonamid_atoms.append(atom)
    amin_pattern = Chem.MolFromSmarts('[NX3;H2,H1;!$(NC=O)]')
    amins = mol.GetSubstructMatches(amin_pattern)
    amins = [list(amin) for amin in amins]
    amins = [[amin[0] if mol.GetAtomWithIdx(amin[0]).GetSymbol() == 'N' else amin[1]] for amin in amins]
    return [amin for amin in amins if amin[0] not in sulfonamid_atoms]


def get_sulfonamids_for_molecule(mol):
    """
    Finds all sulfonamid parts in a given RDKit mol
    :param mol: The given RDKit molecule
    :return: A list of sulfonamid parts in a mol
    """
    sulphoneamid_pattern = Chem.MolFromSmarts(
        '[$([#16X4]([NX3])(=[OX1])(=[OX1])[#6]),$([#16X4+2]([NX3])([OX1-])([OX1-])[#6])]')
    sulfonamids = mol.GetSubstructMatches(sulphoneamid_pattern)
    sulfonamid_atoms = []
    for sulfonamid in sulfonamids:
        sulfonamid = list(sulfonamid)
        atoms = [sulfonamid[0]]
        for neighbor in mol.GetAtomWithIdx(atoms[0]).GetNeighbors():
            if neighbor.GetSymbol() != 'C':
                atoms.append(neighbor.GetIdx())
        sulfonamid_atoms.append(atoms)
    return sulfonamid_atoms


def structure_encoding(atoms):
    """
    Generates one-hot mapping for molecule structure
    :param atoms: A list of atoms to encode
    :return: A vector with encoding
    """
    enc = [0 for _ in range(55)]
    for atom in atoms:
        enc[atom.GetAtomicNum()] += 1
    return enc


def onek_encoding_unk(value, choices_len):
    """
    Creates a one-hot encoding.
    :param value: The value for which the encoding should be one.
    :param choices_len: A list of possible values.
    :return: A one-hot encoding of the value.
    """
    encoding = [0] * choices_len
    encoding[int(value)] = 1
    return encoding

def onek_encoding_hybridization(atom_idx, mol):
    s_h = 1 if atom_idx in [a[0] for a in mol.GetSubstructMatches(Chem.MolFromSmarts('[^0]'))] else 0
    sp_h = 1 if atom_idx in [a[0] for a in mol.GetSubstructMatches(Chem.MolFromSmarts('[^1]'))] else 0
    sp2_h = 1 if atom_idx in [a[0] for a in mol.GetSubstructMatches(Chem.MolFromSmarts('[^2]'))] else 0
    sp3_h = 1 if atom_idx in [a[0] for a in mol.GetSubstructMatches(Chem.MolFromSmarts('[^3]'))] else 0
    sp3d_h = 1 if atom_idx in [a[0] for a in mol.GetSubstructMatches(Chem.MolFromSmarts('[^4]'))] else 0
    sp3d2_h = 1 if atom_idx in [a[0] for a in mol.GetSubstructMatches(Chem.MolFromSmarts('[^5]'))] else 0
    return [s_h, sp_h, sp2_h, sp3_h, sp3d_h, sp3d2_h]

def get_num_rings_in_ring(substruct, sssr):
    cycles_in_ring = set()
    for cycle in sssr:
        all_atoms_in_ring = True
        for atom in cycle:
            if atom not in substruct:
                all_atoms_in_ring = False
        if all_atoms_in_ring:
            cycles_in_ring.add(cycle)
    return len(cycles_in_ring)


def generate_substructure_sum_vector_mapping(substruct, mol, structure_type, args, sssr, ranking):
    """
    Generates a vector with mapping for a substructure
    :param substruct: The given substructure
    :param mol: RDKit molecule
    :param structure_type: The type of a structure (one of STRUCT_TO_NUM)
    :return: An encoding vector
    """
    atoms = [mol.GetAtomWithIdx(i) for i in substruct]

    substruct_atomic_encoding = structure_encoding(atoms)

    implicit_substruct_valence = 0
    for i in range(len(atoms)):
        for j in range(i, len(atoms)):
            bond = mol.GetBondBetweenAtoms(substruct[i], substruct[j])
            if bond:
                implicit_substruct_valence += BT_MAPPING_INT[
                    mol.GetBondBetweenAtoms(substruct[i], substruct[j]).GetBondType()]
    substruct_valence = sum(atom.GetExplicitValence() for atom in atoms) - 2 * implicit_substruct_valence
    substruct_valence_array = onek_encoding_unk(substruct_valence, 40)

    substruct_formal_charge = sum(atom.GetFormalCharge() for atom in atoms)

    substruct_num_Hs = sum(atom.GetTotalNumHs() for atom in atoms)
    substruct_Hs_array = onek_encoding_unk(substruct_num_Hs, 65 if args.substructures_merge else 60)

    substruct_is_aromatic = 1 if sum(atom.GetIsAromatic() for atom in atoms) > 0 else 0

    substruct_mass = sum(atom.GetMass() for atom in atoms)

    substruct_edges_sum = implicit_substruct_valence

    if args.substructures_use_substructures:
        substruct_type = onek_encoding_unk(STRUCT_TO_NUM[structure_type], len(STRUCT_TO_NUM))
        if structure_type == 'RING':
            substruct_type[STRUCT_TO_NUM['RING']] = get_num_rings_in_ring(substruct, sssr)
    else:
        substruct_type = [get_num_rings_in_ring(substruct, sssr) if structure_type == 'RING' else 0]

    features = substruct_atomic_encoding + substruct_valence_array + substruct_Hs_array + substruct_type + \
               [substruct_formal_charge, substruct_is_aromatic, substruct_mass * 0.01,
                substruct_edges_sum * 0.1]

    if args.substructures_symmetry_feature:
        substruct_symmetry_feature = sum(ranking[i] for i in substruct) / len(substruct)
        features += substruct_symmetry_feature

    if args.use_hybridization_features:
        hybridization_features = []
        for atom_idx in substruct:
            hybridization_features.append(onek_encoding_hybridization(atom_idx, mol))
        hybridization_features = [sum(x) for x in zip(*hybridization_features)]
        features += hybridization_features
    return tuple(features)


def add_substructures_extra_atom_features(mol, args):
    for atom in mol.get_atoms():
        if atom.atom_type == 'ATOM':
            atom.atom_representation += tuple([0] * (
                    args.substructures_extra_max_in_to_in + args.substructures_extra_max_in_to_out
                    + args.substructures_extra_max_out_to_out))
            continue

        in_to_in_features = []
        for dist in range(1, args.substructures_extra_max_in_to_in + 1):
            cur_dist_sum = 0
            for atom_1 in atom.simple_atoms:
                for atom_2 in atom.simple_atoms:
                    if atom_1 >= atom_2 or mol.rdkit_mol.GetAtomWithIdx(atom_1).GetAtomicNum() == 6\
                            or mol.rdkit_mol.GetAtomWithIdx(atom_2).GetAtomicNum() == 6:
                        continue
                    if mol.rdkit_distance_matrix[atom_1][atom_2] == dist:
                        cur_dist_sum += dist * mol.rdkit_mol.GetAtomWithIdx(atom_1).GetMass() * mol.rdkit_mol.GetAtomWithIdx(
                            atom_2).GetMass()
            in_to_in_features.append(cur_dist_sum)
        atom.atom_representation += tuple(in_to_in_features)

        in_to_out_features = []
        for dist in range(1, args.substructures_extra_max_in_to_out + 1):
            cur_dist_sum = 0
            for atom_1 in atom.simple_atoms:
                if mol.rdkit_mol.GetAtomWithIdx(atom_1).GetAtomicNum() != 6:
                    for substruct_2 in mol.get_atoms():
                        if substruct_2 == atom:
                            continue
                        min_distance = 1e10
                        for atom_2 in substruct_2.simple_atoms:
                            if mol.rdkit_mol.GetAtomWithIdx(atom_2).GetAtomicNum() != 6:
                                min_distance = min(min_distance, mol.rdkit_distance_matrix[atom_1][atom_2])

                        if min_distance == dist:
                            cur_dist_sum += dist * mol.rdkit_mol.GetAtomWithIdx(atom_1).GetMass() * substruct_2.get_mass()
            in_to_out_features.append(cur_dist_sum)
        atom.atom_representation += tuple(in_to_out_features)


        # getting all neighbours of this substruct
        neighbours = set()
        for atom_1 in atom.simple_atoms:
            for substruct_2 in mol.get_atoms():
                if substruct_2 == atom:
                    continue
                min_distance = 1e10
                for atom_2 in substruct_2.simple_atoms:
                    min_distance = min(min_distance, mol.rdkit_distance_matrix[atom_1][atom_2])

                if min_distance == 1:
                    neighbours.add(substruct_2)

        out_to_out_features = []
        for dist in range(1, args.substructures_extra_max_out_to_out + 1):
            cur_dist_sum = 0
            for substruct_1 in neighbours:
                for substruct_2 in neighbours:
                    if substruct_2.idx >= substruct_1.idx:
                        continue
                    min_distance = 1e10
                    for atom_1 in substruct_1.simple_atoms:
                        for atom_2 in substruct_2.simple_atoms:
                            if atom_1 >= atom_2 or mol.rdkit_mol.GetAtomWithIdx(atom_1).GetAtomicNum() == 6 \
                                    or mol.rdkit_mol.GetAtomWithIdx(atom_2).GetAtomicNum() == 6:
                                continue
                            min_distance = min(min_distance, mol.rdkit_distance_matrix[atom_1][atom_2])
                    if min_distance == dist:
                        cur_dist_sum += substruct_1.get_mass() * substruct_2.get_mass() / 100
            out_to_out_features.append(cur_dist_sum)
        atom.atom_representation += tuple(out_to_out_features)


class Atom:
    def __init__(self, idx, atom_representation, atom_type, simple_atoms, rdkit_atoms, symbol=''):
        self.symbol = symbol
        self.idx = idx
        self.atom_representation = atom_representation
        self.atom_type = atom_type
        self.bonds = []
        self.simple_atoms = simple_atoms
        self.mass = None
        self.rdkit_atoms = rdkit_atoms

    def add_bond(self, bond):
        self.bonds.append(bond)

    def get_representation(self):
        return list(self.atom_representation)

    def get_mass(self):
        if self.mass is None:
            self.mass = sum(atom.GetAtomicNum() for atom in self.rdkit_atoms)
        return self.mass

class Bond:
    def __init__(self, rdkit_bond, idx, out_atom_idx, in_atom_idx, bond_type):
        self.rdkit_bond = rdkit_bond
        self.idx = idx
        self.out_atom_idx = out_atom_idx
        self.in_atom_idx = in_atom_idx
        self.bond_type = bond_type

    def get_rdkit_bond(self):
        return self.rdkit_bond


class Molecule:
    def __init__(self, atoms, bonds, rdkit_mol):
        self.atoms = atoms
        self.bonds = bonds
        self.rdkit_mol = rdkit_mol
        self.rdkit_distance_matrix = Chem.GetDistanceMatrix(rdkit_mol)

    def get_bond(self, atom_1, atom_2):
        # If bond does not exist between atom_1 and atom_2, return None
        for bond in self.atoms[atom_1].bonds:
            if atom_2 == bond.out_atom_idx or atom_2 == bond.in_atom_idx:
                return bond
        return None

    def get_atoms(self):
        return self.atoms

    def get_atom(self, atom_idx):
        return self.atoms[atom_idx]

    def get_num_atoms(self):
        return len(self.atoms)

    def prnt(self):
        for atom in self.atoms:
            print(atom.symbol, atom.idx, atom.bonds, atom.atom_representation)
        for bond in self.bonds:
            print(bond.out_atom_idx, bond.in_atom_idx)


def create_molecule_for_smiles(smiles, args):
    mol = Chem.MolFromSmiles(smiles)
    distance_matrix = Chem.GetDistanceMatrix(mol)
    sssr = Chem.GetSymmSSSR(mol)
    ranking = rdmolfiles.CanonicalRankAtoms(mol)
    rings = get_cycles_for_molecule(mol, args.substructures_merge)
    if args.substructures_use_substructures:
        acids = get_acids_for_molecule(mol)
        esters = get_esters_for_molecule(mol)
        amins = get_amins_for_molecule(mol)
        sulfonamids = get_sulfonamids_for_molecule(mol)
    else:
        acids = []
        esters = []
        amins = []
        sulfonamids = []

    used_atoms = set()
    mol_bonds = []
    mol_atoms = []
    idx_to_atom = defaultdict(set)
    min_not_used_atom = 1

    for structure_type in [[rings, 'RING'], [acids, 'ACID'], [esters, 'ESTER'], [amins, 'AMIN'],
                           [sulfonamids, 'SULFONAMID']]:
        substructure_type_string = structure_type[1]
        substructures = structure_type[0]
        for substruct in substructures:
            mapping = generate_substructure_sum_vector_mapping(substruct, mol, substructure_type_string, args, sssr, ranking)
            substruct_atom = Atom(idx=min_not_used_atom,
                                  atom_representation=mapping, atom_type=substructure_type_string,
                                  simple_atoms=substruct, rdkit_atoms = [mol.GetAtomWithIdx(i) for i in substruct])
            min_not_used_atom +=1
            mol_atoms.append(substruct_atom)
            for idx in substruct:
                idx_to_atom[idx].add(substruct_atom)
                used_atoms.add(idx)

    for atom in mol.GetAtoms():
        atom_idx = atom.GetIdx()
        if atom_idx not in used_atoms:
            atom_repr = generate_substructure_sum_vector_mapping([atom_idx], mol, 'ATOM', args, sssr, ranking)
            custom_atom = Atom(idx=min_not_used_atom, atom_representation=atom_repr, symbol=atom.GetSymbol(), atom_type='ATOM',
                               simple_atoms=[atom_idx], rdkit_atoms=[atom])
            min_not_used_atom += 1
            mol_atoms.append(custom_atom)
            idx_to_atom[atom_idx].add(custom_atom)

    for idx, bond in enumerate(mol.GetBonds()):
        start_atoms = idx_to_atom[bond.GetBeginAtomIdx()]
        end_atoms = idx_to_atom[bond.GetEndAtomIdx()]
        if len(start_atoms & end_atoms) == 0:
            custom_bond = Bond(bond, idx, start_atoms, end_atoms, bond.GetBondType())
            mol_bonds.append(custom_bond)
            for start_atom in start_atoms:
                start_atom.add_bond(custom_bond)
            for end_atom in end_atoms:
                end_atom.add_bond(custom_bond)

    custom_mol = Molecule(mol_atoms, mol_bonds, mol)

    if args.substructures_extra_features:
        add_substructures_extra_atom_features(custom_mol, args)

    return custom_mol

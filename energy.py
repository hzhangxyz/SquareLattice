# -*- coding: utf-8 -*-

"""
    try to support the energy calculation of square lattice
"""

import numpy as np
from node import Node
from tool import decompose_tool, very_simple_contract, unitarilize, attempt_step

#hat
hat = [Node(["phy"], [2], data=np.array([1,0])), Node(["phy"], [2], data=np.array([0,1]))]

class square_lattice(object):
    """
        tensor_array
        lattice_type
        redu_tensor redutensor[i][j][0 or 1]
    """
    def __init__(self, arr, phy, rows, cols, H, spins=None):
        self.tensor_array = [[Node.copy(j) for j in i] for i in arr]
        for i in self.tensor_array:
            for j in i:
                j.envf = False
        self.redu_tensor = [[[Node.contract(j, [phy], hat[k], ["phy"]) \
                    for k in range(2)] for j in i] for i in self.tensor_array]
        self.Hamilton = H.copy()
        if spins==None:
            self.spins = [[0 for _ in range(cols)] for _ in range(rows)]
        else:
            self.spins = spins

    @staticmethod
    def contract_two_row(psi0, operator, left="l", up="u", down="d", right="r"):
        """
            psi0: left, up, right
            operator: left, up, down, right
        """
        delta = 5e-4
        L = len(psi0)
        ##disable normf
        for i in psi0 + operator:
            i.normf = False
        ##unitarilize
        psi_new = [Node.copy(i) for i in psi0]
        unitarilize(psi_new, left, right)
        ##initiate side
        tmp = Node.contract(psi0[L-1], [up], operator[L-1], [down], {left:"down"}, {left:"mid"})
        tmp = Node.contract(tmp, [up], psi_new[L-1], [up], {}, {left:"up"})
        side = [tmp]
        for i in range(L-2, 0, -1):
            tmp = Node.contract(tmp, ["down"], psi0[i], [right], {}, {left:"down"})
            tmp = Node.contract(tmp, ["mid", up], operator[i], [right, down], {}, {left:"mid"})
            tmp = Node.contract(tmp, ["up", up], psi_new[i], [right, up], {}, {left:"up"})
            side = [tmp] + side
        side = [None] + side
        ##target energy
        tmp = [[Node.copy(i).rename_leg({up:down}) for i in psi0], \
               [Node.copy(i).rename_leg({up:down, down:up}) for i in operator], operator, psi0]
        energy0 = very_simple_contract(tmp, 4, L, up, down, left, right)
        ##main part
        dir = 1
        dir_dict = {1:right, -1:left}
        pos = 0
        energy1 = very_simple_contract([[Node.copy(i).rename_leg({up:down}) for i in psi_new], \
                                        psi_new], 2, L, up, down, left, right)
        print(energy0)
        while (abs(energy1-energy0)>abs(energy0)*delta):
            print(pos, energy1)
            in_range = (pos-dir) in range(L)
            if in_range:
                tmp = Node.contract(side[pos-dir], ["down"], psi0[pos], [dir_dict[-dir]], {}, {dir_dict[dir]:"down"})
                tmp = Node.contract(tmp, ["mid", up], operator[pos], [dir_dict[-dir], down], {}, {dir_dict[dir]:"mid"})
            else:
                tmp = Node.copy(psi0[pos]).rename_leg({dir_dict[dir]:"down"})
                tmp = Node.contract(tmp, [up], operator[pos], [down], {}, {dir_dict[dir]:"mid"})
            psi_new[pos] = Node.contract(tmp, ["mid", "down"], side[pos+dir], ["mid", "down"], {"up":dir_dict[-dir]} \
                                if in_range else {}, {"up":dir_dict[dir]})
            psi_new[pos],r = decompose_tool(Node.qr, psi_new[pos], dir_dict[dir], dir_dict[dir], dir_dict[-dir])
            psi_new[pos+dir] = Node.contract(r, [dir_dict[dir]], psi_new[pos+dir], [dir_dict[-dir]])
            side[pos] = Node.contract(tmp, ["up", up] if in_range else [up], psi_new[pos], \
                                      [dir_dict[-dir], up] if in_range else [up], {}, {dir_dict[dir]:"up"})
            pos += dir
            if pos in [0, L-1]:
                dir = -dir
            energy1 = very_simple_contract([[Node.copy(i).rename_leg({up:down}) for i in psi_new], \
                                            psi_new], 2, L, up, down, left, right)
        return psi_new

    def calc_cnfig_weight(self, cnfig):
        """
            !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            cnfig is a 01 matrix
            a better abbreviation for configuration, rather than cnfig, is required
            if cnfig has been calculated, return that answer
            wait to complete
        """
        n = len(cnfig)
        m = len(cnfig[0])
        ans = [self.redu_tensor[-1][i][cnfig[-1][i]] for i in range(m)]
        for i in range(n-2,0,-1):
            print(i)
            ans = square_lattice.contract_two_row(ans, [self.redu_tensor[i][j][cnfig[i][j]] for j in range(m)])
        ans = very_simple_contract([[self.redu_tensor[0][i][cnfig[0][i]] for i in range(m)],ans], 2, m)
        return ans

    def calc_weight(self):
        return self.calc_cnfig_weight(self.spins)

    def calc_cnfig_energy(self, cnfig):
        ans = 1
        return ans

    def calc_energy(self):
        return self.calc_cnfig_energy(self.cnfig)

    def evolve(self):
        new_spins = attempt_step(self.spins)
        w1 = self.calc_weight().tolist()
        w2 = self.calc_cnfig_weight(new_spins).tolist()
        w1 = w1[0] ** 2
        w2 = w2[0] ** 2
        p = min(1, w2 / w1)
        if np.random.rand()<p:
            self.spins = new_spins

    def preheat(self, preheat_time):
        for _ in range(preheat_time):
            self.evolve()

    def sampling(self, sampling_time):
        ans = 0
        for _ in range(sampling_time):
            self.evolve()
            ans += self.calc_energy() / sampling_time
        return ans

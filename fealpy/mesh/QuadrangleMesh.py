import numpy as np
from .TriangleMesh import TriangleMesh
from .Mesh2d import Mesh2d, Mesh2dDataStructure
from ..quadrature import QuadrangleQuadrature, GaussLegendreQuadrature
from ..common import hash2map


class QuadrangleMeshDataStructure(Mesh2dDataStructure):
    localEdge = np.array([(0, 1), (1, 2), (2, 3), (3, 0)])
    ccw = np.array([0, 1, 2, 3])

    NVE = 2
    NVF = 2
    NVC = 4

    NEC = 4
    NFC = 4

    localCell = np.array([
        (0, 1, 2, 3),
        (1, 2, 3, 0),
        (2, 3, 0, 1),
        (3, 0, 1, 2)])

    def __init__(self, NN, cell):
        super().__init__(NN, cell)


class QuadrangleMesh(Mesh2d):
    def __init__(self, node, cell):
        assert cell.shape[-1] == 4
        self.node = node
        NN = node.shape[0]
        self.ds = QuadrangleMeshDataStructure(NN, cell)

        self.meshtype = 'quad'
        self.p = 1 # 最低次的四边形 

        self.itype = cell.dtype
        self.ftype = node.dtype

        self.celldata = {}
        self.nodedata = {}
        self.edgedata = {}

    def number_of_corner_nodes(self):
        return self.ds.NN

    def reorder_cell(self, idx):
        NC = self.number_of_cells()
        NN = self.number_of_nodes()
        cell = self.entity('cell')
        cell = cell[np.arange(NC).reshape(-1, 1), self.ds.localCell[idx]]
        self.ds.reinit(NN, cell)

    def integrator(self, k, etype='cell'):
        if etype in {'cell', 2}:
            return QuadrangleQuadrature(k)
        elif etype in {'edge', 'face', 1}:
            return GaussLegendreQuadrature(k)

    def area(self, index=np.s_[:]):
        return self.cell_area(index=index)

    def cell_area(self, index=np.s_[:]):
        NC = self.number_of_cells()
        node = self.entity('node')
        edge = self.entity('edge')
        edge2cell = self.ds.edge_to_cell()
        isInEdge = (edge2cell[:, 0] != edge2cell[:, 1])
        v = self.edge_normal()
        val = np.sum(v*node[edge[:, 0], :], axis=1)

        a = np.zeros(NC, dtype=self.ftype)
        np.add.at(a, edge2cell[:, 0], val)
        np.add.at(a, edge2cell[isInEdge, 1], -val[isInEdge])
        a /=2
        return a

    def uniform_refine(self, n=1):
        for i in range(n):
            N = self.number_of_nodes()
            NE = self.number_of_edges()
            NC = self.number_of_cells()

            # Find the cutted edge  
            cell2edge = self.ds.cell_to_edge()
            edgeCenter = self.entity_barycenter('edge')
            cellCenter = self.entity_barycenter('cell')

            edge2center = np.arange(N, N+NE)

            cell = self.ds.cell
            cp = [cell[:, i].reshape(-1, 1) for i in range(4)]
            ep = [edge2center[cell2edge[:, i]].reshape(-1, 1) for i in range(4)]
            cc = np.arange(N + NE, N + NE + NC).reshape(-1, 1)
 
            cell = np.zeros((4*NC, 4), dtype=np.int_)
            cell[0::4, :] = np.r_['1', cp[0], ep[0], cc, ep[3]] 
            cell[1::4, :] = np.r_['1', ep[0], cp[1], ep[1], cc]
            cell[2::4, :] = np.r_['1', cc, ep[1], cp[2], ep[2]]
            cell[3::4, :] = np.r_['1', ep[3], cc, ep[2], cp[3]]

            self.node = np.r_['0', self.node, edgeCenter, cellCenter]
            self.ds.reinit(N + NE + NC, cell)


    def angle(self):
        NC = self.number_of_cells()
        node = self.entity('node')
        cell = self.ds.cell
        localEdge = self.ds.local_edge()
        angle = np.zeros((NC, 4), dtype=np.float)
        iprev = [3, 0, 1, 2]
        for i, j in localEdge:
            k = iprev[i]
            v0 = node[cell[:, j], :] - node[cell[:, i], :]
            v1 = node[cell[:, k], :] - node[cell[:, i], :]
            angle[:, i] = np.arccos(
                    np.sum(
                        v0*v1, axis=1
                    )/np.sqrt(
                        np.sum(v0**2, axis=1)*np.sum(v1**2, axis=1)))
        return angle

    def jacobi_at_corner(self):
        NC = self.number_of_cells()
        node = self.entity('node')
        cell = self.entity('cell')
        localEdge = self.ds.local_edge()
        jacobi = np.zeros((NC, 4), dtype=np.float)
        iprev = [3, 0, 1, 2]
        for i, j in localEdge:
            k = iprev[i]
            v0 = node[cell[:, j], :] - node[cell[:, i], :]
            v1 = node[cell[:, k], :] - node[cell[:, i], :]
            jacobi[:, i] = v0[:, 0]*v1[:, 1] - v0[:, 1]*v1[:, 0]
        return jacobi

    def cell_quality(self):
        jacobi = self.jacobi_at_corner()
        return jacobi.sum(axis=1)/4

    def bc_to_point(self, bc):
        bc0 = bc[0]
        bc1 = bc[1]
        node = self.node
        cell = self.ds.cell
        p = np.einsum('...j, ijk->...ik', bc, node[cell])
        return p 

    def to_trimesh(self):
        cell = self.entity('cell')
        node = self.entity('node')
        hexCell2face = self.ds.cell_to_face()
        localCell = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int_)
        cell = cell[:, localCell].reshape(-1, 3)

        celldata = self.celldata
        nodedata = self.nodedata

        mesh = TriangleMesh(node, cell)
        for key in celldata:
            mesh.celldata[key] = np.tile(celldata[key], (6, 1)).T.reshape(-1)
        mesh.nodedata = nodedata
        return mesh

    def vtk_cell_type(self, etype='cell'):
        if etype in {'cell', 2}:
            VTK_Quad = 9
            return VTK_Quad
        elif etype in {'face', 'edge', 1}:
            VTK_LINE = 3
            return VTK_LINE


    def to_vtk(self, etype='cell', index=np.s_[:], fname=None):
        """
        Parameters
        ----------

        Notes
        -----
        把网格转化为 VTK 的格式
        """
        from .vtk_extent import vtk_cell_index, write_to_vtu

        node = self.entity('node')
        GD = self.geo_dimension()
        if GD == 2:
            node = np.concatenate((node, np.zeros((node.shape[0], 1), dtype=self.ftype)), axis=1)

        cell = self.entity(etype)[index]
        cellType = self.vtk_cell_type(etype)
        NV = cell.shape[-1]

        cell = np.r_['1', np.zeros((len(cell), 1), dtype=cell.dtype), cell]
        cell[:, 0] = NV

        NC = len(cell)
        if fname is None:
            return node, cell.flatten(), cellType, NC 
        else:
            print("Writting to vtk...")
            write_to_vtu(fname, node, NC, cellType, cell.flatten(),
                    nodedata=self.nodedata,
                    celldata=self.celldata)

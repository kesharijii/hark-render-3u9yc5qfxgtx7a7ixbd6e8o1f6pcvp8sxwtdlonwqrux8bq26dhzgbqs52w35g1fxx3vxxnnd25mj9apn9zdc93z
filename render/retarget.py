"""Retarget MoMask/HumanML3D joint positions (T,22,3, Y-up) onto an MPFB 'default' rig.

Position-driven, hierarchical swing retarget:
  * root bone gets the full pelvis frame (hip line + spine direction) and trajectory,
  * every mapped bone is swung (minimal rotation) so its Y axis points along the source joint vector,
    twist is inherited from the parent, unmapped bones keep their rest offset.
This is independent of rest pose (MPFB A-pose vs MoMask T-pose) because only directions are matched.
"""
import numpy as np
from mathutils import Matrix, Vector, Quaternion

# SMPL / HumanML3D 22-joint order
J = dict(pelvis=0, lhip=1, rhip=2, sp1=3, lknee=4, rknee=5, sp2=6, lank=7, rank=8, sp3=9, lfoot=10, rfoot=11,
         neck=12, lcol=13, rcol=14, head=15, lsho=16, rsho=17, lelb=18, relb=19, lwri=20, rwri=21)

# MPFB default rig bone -> (from joint, to joint)
BONEMAP = {
    'spine05': ('pelvis', 'sp1'), 'spine04': ('pelvis', 'sp1'),
    'spine03': ('sp1', 'sp2'), 'spine02': ('sp2', 'sp3'), 'spine01': ('sp3', 'neck'),
    'neck01': ('neck', 'head'), 'head': ('neck', 'head'),
    'upperleg01.L': ('lhip', 'lknee'), 'lowerleg01.L': ('lknee', 'lank'), 'foot.L': ('lank', 'lfoot'),
    'upperleg01.R': ('rhip', 'rknee'), 'lowerleg01.R': ('rknee', 'rank'), 'foot.R': ('rank', 'rfoot'),
    'clavicle.L': ('lcol', 'lsho'), 'upperarm01.L': ('lsho', 'lelb'), 'lowerarm01.L': ('lelb', 'lwri'),
    'clavicle.R': ('rcol', 'rsho'), 'upperarm01.R': ('rsho', 'relb'), 'lowerarm01.R': ('relb', 'rwri'),
}


def load_joints(path):
    p = np.load(path).astype(np.float64)  # (T,22,3) y-up, facing +z
    return np.stack([p[..., 0], -p[..., 2], p[..., 1]], -1)  # blender: z-up, facing -y


def resample(P, src_fps, dst_times):
    """Linear resample joint positions at arbitrary times (seconds, clamped)."""
    T = len(P)
    f = np.clip(np.asarray(dst_times) * src_fps, 0, T - 1)
    i0 = np.floor(f).astype(int); i1 = np.minimum(i0 + 1, T - 1); w = (f - i0)[:, None, None]
    return P[i0] * (1 - w) + P[i1] * w


def _frame(Pt):
    x = Vector(Pt[J['lhip']] - Pt[J['rhip']]).normalized()
    up = Vector(Pt[J['sp1']] - Pt[J['pelvis']]).normalized()
    z = (up - x * up.dot(x)).normalized()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()  # columns x,y,z


class Retargeter:
    def __init__(self, rig, P0):
        """rig: armature object; P0: full source clip (T,22,3) used for normalisation (frame 0 = reference)."""
        self.rig = rig
        bones = list(rig.data.bones)
        depth = lambda b: 0 if b.parent is None else 1 + depth(b.parent)
        self.bones = sorted(bones, key=depth)
        self.rest = {b.name: b.matrix_local.copy() for b in bones}
        self.root = [b for b in bones if b.parent is None][0].name
        # yaw of frame 0 -> canonical (facing -y)
        F0 = _frame(P0[0])
        fwd = -F0.col[1]  # facing direction (frame y points backwards for a -y facing body)
        fwd.z = 0; fwd.normalize()
        ang = np.arctan2(fwd.x, -fwd.y)  # angle from -y
        self.yaw0inv = Matrix.Rotation(-ang, 3, 'Z')  # rotate source so frame-0 facing becomes -y
        self.p0 = Vector(P0[0][J['pelvis']])
        # scale: source leg length vs target leg length
        src_leg = np.linalg.norm(P0[0][J['lhip']] - P0[0][J['lknee']]) + np.linalg.norm(P0[0][J['lknee']] - P0[0][J['lank']])
        r = self.rest
        tgt_leg = (r['upperleg01.L'].translation - r['lowerleg01.L'].translation).length + \
                  (r['lowerleg01.L'].translation - r['foot.L'].translation).length
        self.s = tgt_leg / src_leg
        self.root_rest_head = r[self.root].translation.copy()

    def pose_frame(self, Pt):
        """Return dict bone -> armature-space pose matrix for one frame of source positions (already in blender axes)."""
        Y = self.yaw0inv
        pos = lambda j: Y @ (Vector(Pt[J[j]]) - self.p0)
        pose = {}
        rest = self.rest
        for b in self.bones:
            n = b.name
            if b.parent is None:
                F = Y @ _frame(Pt)
                R = F @ rest[n].to_3x3()
                M = R.to_4x4()
                M.translation = self.root_rest_head + pos('pelvis') * self.s
                pose[n] = M
                continue
            pn = b.parent.name
            un = pose[pn] @ rest[pn].inverted() @ rest[n]
            if n in BONEMAP:
                a, c = BONEMAP[n]
                d = (pos(c) - pos(a)).normalized()
                cur = un.to_3x3().col[1].normalized()
                q = cur.rotation_difference(d)
                M = (q.to_matrix() @ un.to_3x3()).to_4x4()
                M.translation = un.translation
                pose[n] = M
            else:
                pose[n] = un
        return pose

    def basis(self, pose):
        out = {}
        rest = self.rest
        for b in self.bones:
            n = b.name
            if b.parent is None:
                out[n] = rest[n].inverted() @ pose[n]
            else:
                pn = b.parent.name
                out[n] = (rest[pn].inverted() @ rest[n]).inverted() @ pose[pn].inverted() @ pose[n]
        return out

    def keyframe(self, P, frames, only_mapped=True):
        """P: (N,22,3) resampled positions for each scene frame in `frames`. Returns list of pose dicts."""
        rig = self.rig
        keep = set(BONEMAP) | {self.root}
        poses = [self.pose_frame(Pt) for Pt in P]
        # ground contact: lowest ankle sits at its rest height (one foot always planted; no jumps in these clips)
        ank = self.rest['foot.L'].translation.z
        dz = np.array([ank - min(p['foot.L'].translation.z, p['foot.R'].translation.z) for p in poses])
        if len(dz) > 4:
            k = np.ones(5) / 5; dz = np.convolve(np.pad(dz, 2, mode='edge'), k, mode='valid')
        for p, d in zip(poses, dz):
            for n in p:
                p[n].translation.z += d
        for pose, f in zip(poses, frames):
            B = self.basis(pose)
            for n, M in B.items():
                if only_mapped and n not in keep and not M.to_quaternion().angle > 1e-4:
                    continue
                pb = rig.pose.bones[n]
                pb.rotation_mode = 'QUATERNION'
                loc, rot, _ = M.decompose()
                pb.rotation_quaternion = rot
                pb.keyframe_insert('rotation_quaternion', frame=f)
                if n == self.root:
                    pb.location = loc
                    pb.keyframe_insert('location', frame=f)
        return poses
